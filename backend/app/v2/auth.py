import time

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlmodel import select

from ..auth import COOKIE, ROLES, SubjectDep, find_user, issue_token, key_hash, new_api_key, require, verify_password
from ..config import settings
from ..db import SessionDep, next_id
from ..models import ApiKey

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


class Me(BaseModel):
    id: str
    name: str
    type: str
    role: str


_FAILS: dict[str, list[float]] = {}


@router.post("/login", response_model=Me)
def login(data: LoginIn, response: Response, session: SessionDep) -> Me:
    # не больше 5 неудачных попыток за 10 минут на адрес — перебор пароля упирается в стену
    k = data.email.strip().lower()
    t = time.monotonic()
    fails = [x for x in _FAILS.get(k, []) if t - x < 600]
    if len(fails) >= 5:
        raise HTTPException(429, "слишком много попыток, подождите")
    user = find_user(session, k)
    if not user or not verify_password(user.password_hash, data.password):
        _FAILS[k] = fails + [t]
        raise HTTPException(401, "неверная почта или пароль")
    _FAILS.pop(k, None)
    response.set_cookie(COOKIE, issue_token(user), max_age=settings.jwt_ttl_hours * 3600,
                        httponly=True, samesite="lax", secure=settings.cookie_secure, path="/api")
    return Me(id=user.id, name=user.name, type="user", role=user.role)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/api")


@router.get("/me", response_model=Me)
def me(subject: SubjectDep) -> Me:
    return Me(id=subject.id, name=subject.name, type=subject.type, role=subject.role)


class KeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: str = "agent"


class KeyOut(BaseModel):
    id: str
    name: str
    role: str
    prefix: str
    key: str | None = None


@router.get("/keys", response_model=list[KeyOut])
def keys(subject: SubjectDep, session: SessionDep) -> list[KeyOut]:
    require(subject, "keys.manage")
    rows = session.exec(select(ApiKey).where(ApiKey.revoked == False).order_by(ApiKey.id)).all()  # noqa: E712
    return [KeyOut(id=r.id, name=r.name, role=r.role, prefix=r.prefix) for r in rows]


@router.post("/keys", response_model=KeyOut, status_code=201)
def create_key(data: KeyIn, subject: SubjectDep, session: SessionDep) -> KeyOut:
    """Ключ показывается один раз — в базе остаётся только его хэш."""
    require(subject, "keys.manage")
    if data.role not in ROLES or data.role == "owner":
        raise HTTPException(400, "роль ключа: " + ", ".join(r for r in ROLES if r != "owner"))
    key = new_api_key()
    row = ApiKey(id=next_id(session, "api_keys", "key"), name=data.name, key_hash=key_hash(key),
                 prefix=key[:8], role=data.role)
    session.add(row)
    session.commit()
    return KeyOut(id=row.id, name=row.name, role=row.role, prefix=row.prefix, key=key)


@router.delete("/keys/{key_id}", status_code=204)
def revoke_key(key_id: str, subject: SubjectDep, session: SessionDep) -> None:
    require(subject, "keys.manage")
    row = session.get(ApiKey, key_id)
    if not row:
        raise HTTPException(404, "ключа нет")
    row.revoked = True
    session.add(row)
    session.commit()
