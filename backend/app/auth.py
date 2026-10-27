"""Кто пришёл и что ему можно.

Три способа войти: Bearer-токен, httpOnly-кука SPA и ключ X-API-Key (скрипты, мосты, MCP).
В приватной версии токены выпускает отдельный сервис «Паспорт» (RS256 + JWKS, роли — в его каталоге);
здесь он свёрнут в один модуль с HS256, чтобы витрина поднималась одним compose.
"""
import hashlib
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session, select

from .config import settings
from .db import get_session
from .models import ApiKey, User, now

COOKIE = "crm_access"
_ph = PasswordHasher()

# Роль → права. «*» — всё. Права проверяются на маршруте: require(subject, "tasks.write").
ROLES: dict[str, set[str]] = {
    "owner": {"*"},
    "viewer": {"read"},
    # агент (MCP, Claude Code): читает всё, пишет задачи и журнал проектов, не трогает настройки и ключи
    "agent": {"read", "tasks.write", "projects.write", "notes.write", "feed.write"},
    # мост: только присылает события и биения
    "bridge": {"feed.write"},
}

KEY_CHARS = re.compile(r"[\x21-\x7e]{1,300}")   # печатный ASCII без пробелов


@dataclass
class Subject:
    type: str        # user | api_key
    id: str
    name: str
    role: str

    def can(self, permission: str) -> bool:
        perms = ROLES.get(self.role, set())
        return "*" in perms or permission in perms


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except VerificationError:
        return False


def key_hash(key: str) -> str:
    # ключ — 32 случайных байта: перебор невозможен, медленный хэш не нужен, а поиск по sha256 — индексом
    return hashlib.sha256(key.encode()).hexdigest()


def new_api_key() -> str:
    return "crm_" + secrets.token_urlsafe(32)


def issue_token(user: User) -> str:
    t = int(time.time())
    payload = {"sub": user.id, "name": user.name, "role": user.role, "iat": t,
               "exp": t + settings.jwt_ttl_hours * 3600, "aud": "crm"}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _check_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience="crm")
    except jwt.PyJWTError:
        raise HTTPException(401, "токен не принят")


# проверенный ключ: чтение верит кэшу минуту, запись сверяется с базой всегда — отзыв действует сразу
_KEYS: dict[str, tuple[datetime, Subject]] = {}
KEY_CACHE = timedelta(seconds=60)
READ_METHODS = ("GET", "HEAD", "OPTIONS")


def current_subject(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    authorization: Annotated[Optional[str], Header()] = None,
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> Subject:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif request.cookies.get(COOKIE):
        token = request.cookies[COOKIE]

    if token:
        p = _check_token(token)
        return Subject("user", p["sub"], p.get("name", ""), p.get("role", "viewer"))

    if x_api_key:
        # Shortcuts и вставка из буфера любят дописать пробел или перенос
        x_api_key = x_api_key.strip()
        if not KEY_CHARS.fullmatch(x_api_key):
            raise HTTPException(401, "ключ недействителен: в заголовке X-API-Key посторонние символы")
        h = key_hash(x_api_key)
        hit = _KEYS.get(h)
        if hit and hit[0] > datetime.now(timezone.utc) and request.method in READ_METHODS:
            return hit[1]
        row = session.exec(select(ApiKey).where(ApiKey.key_hash == h, ApiKey.revoked == False)).first()  # noqa: E712
        if not row:
            _KEYS.pop(h, None)
            raise HTTPException(401, "ключ недействителен")
        row.last_used_at = now()
        session.add(row)
        session.commit()
        subj = Subject("api_key", row.id, row.name, row.role)
        if len(_KEYS) > 500:
            _KEYS.clear()
        _KEYS[h] = (datetime.now(timezone.utc) + KEY_CACHE, subj)
        return subj

    raise HTTPException(401, "нужен вход или ключ доступа")


SubjectDep = Annotated[Subject, Depends(current_subject)]


def require(subject: Subject, permission: str) -> None:
    if not subject.can(permission):
        raise HTTPException(403, f"нет права {permission}")


def find_user(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email.strip().lower())).first()
