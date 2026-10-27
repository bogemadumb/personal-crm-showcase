from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


def ts(**kw) -> Any:
    return Field(default_factory=now, sa_column=Column(DateTime(timezone=True), nullable=False, **kw))


def ts_opt() -> Any:
    return Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


def jsonb(default=dict) -> Any:
    return Field(default_factory=default, sa_column=Column(JSONB, nullable=False))


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"schema": "crm"}

    id: str = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    password_hash: str
    role: str = "owner"
    created_at: datetime = ts()


class ApiKey(SQLModel, table=True):
    """Ключ для скриптов, мостов и MCP. В базе — только sha256 ключа и первые символы для узнавания."""
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "crm"}

    id: str = Field(primary_key=True)
    name: str
    key_hash: str = Field(unique=True, index=True)
    prefix: str
    role: str = "agent"
    revoked: bool = False
    created_at: datetime = ts()
    last_used_at: Optional[datetime] = ts_opt()


class Project(SQLModel, table=True):
    """Проект = папка со спецификацией, дорожной картой и журналом. Файл карты — источник правды,
    таблица stages — её разобранный кэш."""
    __tablename__ = "projects"
    __table_args__ = {"schema": "crm"}

    id: str = Field(primary_key=True)
    name: str
    folder: Optional[str] = None
    status: str = "active"            # active | paused | done
    roadmap_text: str = ""
    progress: int = 0                 # 0..100, считается по этапам без замороженных
    updated_at: datetime = ts()


class Stage(SQLModel, table=True):
    __tablename__ = "stages"
    __table_args__ = {"schema": "crm"}

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(foreign_key="crm.projects.id", index=True)
    n: int
    title: str
    marker: Optional[str] = None
    status: str = "todo"              # done | cur | todo
    frozen: bool = False
    closed_at: Optional[datetime] = ts_opt()


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal"
    __table_args__ = {"schema": "crm"}

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(foreign_key="crm.projects.id", index=True)
    kind: str = "note"                # note | decision | stage
    text: str
    files: list = jsonb(list)
    author: Optional[str] = None
    created_at: datetime = ts()


class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    __table_args__ = {"schema": "crm"}

    id: str = Field(primary_key=True)
    title: str
    notes: str = ""
    project_id: Optional[str] = Field(default=None, foreign_key="crm.projects.id", index=True)
    plan_date: Optional[date] = Field(default=None, index=True)
    due: Optional[date] = None
    priority: int = 0                 # 0 обычная, 1 важная, 2 срочная
    status: str = "open"              # open | done
    created_at: datetime = ts()
    done_at: Optional[datetime] = ts_opt()


class Note(SQLModel, table=True):
    __tablename__ = "notes"
    __table_args__ = {"schema": "crm"}

    id: str = Field(primary_key=True)
    title: str
    body: str = ""
    tags: list = jsonb(list)
    pinned: bool = False
    updated_at: datetime = ts()


class CalendarEvent(SQLModel, table=True):
    __tablename__ = "events"
    __table_args__ = {"schema": "crm"}

    id: str = Field(primary_key=True)
    title: str
    starts_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
    ends_at: Optional[datetime] = ts_opt()
    location: Optional[str] = None
    kind: str = "event"               # event | deadline | reminder


class FeedEvent(SQLModel, table=True):
    """Общая лента событий: всё, что сделали скрипты, боты и люди, — одной хронологией."""
    __tablename__ = "feed"
    __table_args__ = {"schema": "hub"}

    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(index=True)
    kind: str = "info"
    level: str = "info"               # info | warn | error
    title: str
    detail: Optional[str] = None
    external_id: Optional[str] = None
    payload: dict = jsonb(dict)
    created_at: datetime = ts(index=True)


class Beat(SQLModel, table=True):
    """Биение фоновой задачи: «я жив, отработал так-то, жди меня через N секунд».
    Пульс считает опоздавших — так видно упавший таймер раньше, чем его последствия."""
    __tablename__ = "beats"
    __table_args__ = {"schema": "hub"}

    source: str = Field(primary_key=True)
    title: str
    machine: str = "server"
    expect_every: int = 3600          # секунды
    status: str = "ok"                # ok | fail
    note: Optional[str] = None
    fails: int = 0                    # сбоев подряд
    muted_until: Optional[datetime] = ts_opt()
    last_at: datetime = ts()
