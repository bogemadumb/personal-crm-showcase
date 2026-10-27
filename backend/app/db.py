import re
import threading
import time
from collections.abc import Callable, Hashable, Iterator
from typing import Annotated, Any, TypeVar

from fastapi import Depends
from sqlalchemy import event
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session as SaSession
from sqlmodel import Session, create_engine

from .config import settings

# ожидание свободного соединения — быстрая ошибка, а не 30 с зависания всего SPA
engine = create_engine(
    settings.dsn,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    pool_timeout=5,
    pool_recycle=1800,
)


def get_session() -> Iterator[Session]:
    # после commit обработчики читают только то, что сами записали; перечитывать каждый объект незачем
    with Session(engine, expire_on_commit=False) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


# ── поколение записей и кэш тяжёлых чтений ───────────────────────────────────
# Любой COMMIT процесса, в котором был INSERT/UPDATE/DELETE, сдвигает «поколение» — кэши сводок
# (экран «Сегодня», счётчики) после любого действия сбрасываются сами, без ручной инвалидации.

_WRITE = re.compile(r"^\s*(INSERT|UPDATE|DELETE|MERGE)\b|^\s*WITH\b.*\b(INSERT|UPDATE|DELETE)\b",
                    re.IGNORECASE | re.DOTALL)
_GENERATION = [0]
_CACHE: dict[Hashable, tuple[float, int, Any]] = {}
_CACHE_LOCK = threading.Lock()
_BUILDING: dict[Hashable, threading.Lock] = {}
T = TypeVar("T")


@event.listens_for(engine, "after_cursor_execute")
def _mark_write(conn, cursor, statement, parameters, context, executemany):
    if conn.info.get("wrote"):
        return
    m = _WRITE.match(statement)
    if not m:
        return
    # запись, не задевшая ни строки (ON CONFLICT DO NOTHING, пустой UPDATE), — не запись:
    # фоновые опросы иначе сбивали бы кэш впустую
    if m.group(1) and not executemany and cursor.rowcount == 0:
        return
    conn.info["wrote"] = True


@event.listens_for(engine, "commit")
def _after_commit(conn):
    if conn.info.pop("wrote", False):
        with _CACHE_LOCK:
            _GENERATION[0] += 1
        _ONCE_MORE.needed = True


# событие commit приходит ДО настоящего COMMIT: сборка, начатая в эти миллисекунды, видит старые строки
# с новым поколением — второй сдвиг после COMMIT её отбрасывает
_ONCE_MORE = threading.local()


@event.listens_for(SaSession, "after_commit")
def _after_real_commit(session):
    if getattr(_ONCE_MORE, "needed", False):
        _ONCE_MORE.needed = False
        with _CACHE_LOCK:
            _GENERATION[0] += 1


@event.listens_for(engine, "rollback")
def _after_rollback(conn):
    conn.info.pop("wrote", None)


def cached(key: Hashable, ttl: float, build: Callable[[], T]) -> T:
    """Значение из кэша процесса, если ему меньше ttl секунд и после него не было записей.
    Иначе — build() и в кэш. Залп одинаковых запросов (несколько вкладок) собирает одно значение."""
    arrived = time.monotonic()

    def fresh():
        with _CACHE_LOCK:
            z = _CACHE.get(key)
            return z if z and time.monotonic() - z[0] < ttl and z[1] == _GENERATION[0] else None

    z = fresh()
    if z:
        return z[2]
    with _CACHE_LOCK:
        lock = _BUILDING.setdefault(key, threading.Lock())
    with lock:
        z = fresh()
        if z:
            return z[2]
        # собрано, пока ждали замка, и начато после нашего прихода — для нас свежее при любом поколении
        with _CACHE_LOCK:
            z = _CACHE.get(key)
        if z and z[0] >= arrived:
            return z[2]
        with _CACHE_LOCK:
            now, gen = time.monotonic(), _GENERATION[0]
        value = build()
        with _CACHE_LOCK:
            if len(_CACHE) > 500:
                _CACHE.clear()
                _BUILDING.clear()
            _CACHE[key] = (now, gen, value)
    return value


def next_id(session: Session, table: str, prefix: str, width: int = 6, schema: str = "crm") -> str:
    """Следующий читаемый идентификатор вида tsk-000005.

    Максимум берём ЧИСЛОМ, а не строкой (tsk-004 и tsk-000005 сравниваются неверно как текст).
    Advisory-замок на таблицу до конца транзакции: без него два запроса в одну секунду
    получали один номер, и второй коммит падал на уникальности.
    Номер удалённого объекта повторно не выдаётся — его хранит crm.id_counters,
    иначе ссылки и «недавние» в палитре открыли бы чужой объект.
    """
    session.exec(sql_text("SELECT pg_advisory_xact_lock(hashtext(:k))").bindparams(k=f"{schema}.{table}"))
    row = session.exec(
        sql_text("SELECT max(substring(id from '[0-9]+$')::bigint) "
                 f"FROM {schema}.{table} WHERE id ~ :re")
        .bindparams(re=f"^{prefix}-[0-9]+$")
    ).first()
    number = int(row[0] or 0) + 1
    key = f"{schema}.{table}:{prefix}"
    last = session.exec(sql_text("SELECT nomer FROM crm.id_counters WHERE key = :k").bindparams(k=key)).first()
    if last and last[0] >= number:
        number = int(last[0]) + 1
    session.exec(sql_text(
        "INSERT INTO crm.id_counters (key, nomer) VALUES (:k, :n) ON CONFLICT (key) "
        "DO UPDATE SET nomer = GREATEST(crm.id_counters.nomer, EXCLUDED.nomer)").bindparams(k=key, n=number))
    return f"{prefix}-{number:0{width}d}"
