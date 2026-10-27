import os
from datetime import datetime, timezone

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import text as sql_text

from ..db import SessionDep

router = APIRouter(tags=["health"])


class Health(BaseModel):
    ok: bool
    time: datetime
    db: bool
    migration: str | None = None
    build: str | None = None


@router.get("/health", response_model=Health, responses={503: {"model": Health}})
def health(response: Response, session: SessionDep) -> Health:
    """Жив ли процесс и видит ли он базу. Открыт без входа; база лежит — 503, чтобы smoke-проверка
    после выкладки и внешний наблюдатель это видели."""
    try:
        migration = session.exec(sql_text("SELECT version_num FROM crm.alembic_version")).scalar()
        ok = True
    except Exception:
        migration, ok = None, False
    if not ok:
        response.status_code = 503
    return Health(ok=ok, time=datetime.now(timezone.utc), db=ok, migration=migration,
                  build=os.environ.get("BUILD_TAG") or None)
