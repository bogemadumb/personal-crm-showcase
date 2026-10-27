from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import col, select

from ..auth import SubjectDep, require
from ..db import SessionDep
from ..models import Beat, FeedEvent, now
from ..pulse import pulse_rows

router = APIRouter(prefix="/feed", tags=["feed"])

SOURCE = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9][a-z0-9._-]*$")


class EventIn(BaseModel):
    source: str = SOURCE
    kind: str = Field(default="info", max_length=60)
    level: Literal["info", "warn", "error"] = "info"
    title: str = Field(min_length=1, max_length=300)
    detail: Optional[str] = Field(default=None, max_length=5000)
    # повтор той же отправки (ретрай моста после таймаута) не заводит второе событие
    external_id: Optional[str] = Field(default=None, max_length=200)
    payload: dict = Field(default_factory=dict)


class EventOut(BaseModel):
    id: int
    source: str
    kind: str
    level: str
    title: str
    detail: Optional[str]
    payload: dict
    created_at: datetime


@router.post("/event", response_model=EventOut, status_code=201)
def post_event(data: EventIn, subject: SubjectDep, session: SessionDep) -> EventOut:
    require(subject, "feed.write")
    if data.external_id:
        dup = session.exec(select(FeedEvent).where(FeedEvent.source == data.source,
                                                   FeedEvent.external_id == data.external_id)).first()
        if dup:
            return EventOut(**dup.model_dump())
    e = FeedEvent(**data.model_dump())
    e.payload = {**e.payload, "actor": subject.id}
    session.add(e)
    session.commit()
    return EventOut(**e.model_dump())


@router.get("", response_model=list[EventOut])
def feed(subject: SubjectDep, session: SessionDep, source: Optional[str] = None,
         hours: int = Query(72, ge=1, le=24 * 90), limit: int = Query(100, le=500)) -> list[EventOut]:
    require(subject, "read")
    q = select(FeedEvent).where(FeedEvent.created_at >= now() - timedelta(hours=hours))
    if source:
        q = q.where(FeedEvent.source == source)
    rows = session.exec(q.order_by(col(FeedEvent.created_at).desc()).limit(limit)).all()
    return [EventOut(**e.model_dump()) for e in rows]


class BeatIn(BaseModel):
    source: str = SOURCE
    title: Optional[str] = Field(default=None, max_length=200)
    machine: Optional[str] = Field(default=None, max_length=30)
    expect_every: Optional[int] = Field(default=None, ge=10, le=14 * 86400)
    status: Literal["ok", "fail"] = "ok"
    note: Optional[str] = Field(default=None, max_length=500)
    # когда задача работала на самом деле: мост опрашивает реже, чем тикает таймер
    at: Optional[datetime] = None


class BeatOut(BaseModel):
    source: str
    title: str
    machine: str
    expect_every: int
    status: str
    note: Optional[str]
    fails: int
    last_at: datetime
    silent_min: int
    late: bool
    muted: bool
    sleeping: bool
    machine_down: bool
    alarm: bool


def _beat(session, data: BeatIn) -> Beat:
    b = session.get(Beat, data.source) or Beat(source=data.source, title=data.title or data.source)
    if data.title:
        b.title = data.title
    if data.machine:
        b.machine = data.machine
    if data.expect_every:
        b.expect_every = data.expect_every
    at = data.at or now()
    b.last_at = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    b.status = data.status
    b.note = data.note
    b.fails = b.fails + 1 if data.status != "ok" else 0
    session.add(b)
    return b


@router.post("/beat", status_code=204)
def post_beat(data: BeatIn, subject: SubjectDep, session: SessionDep) -> None:
    """Биение фоновой задачи. Сбой (fail) ещё и пишется в ленту — его видно в хронологии."""
    require(subject, "feed.write")
    b = _beat(session, data)
    if data.status == "fail":
        session.add(FeedEvent(source=data.source, kind="beat_fail", level="error",
                              title=f"{b.title}: сбой", detail=data.note, payload={"fails": b.fails}))
    session.commit()


class BeatsIn(BaseModel):
    beats: list[BeatIn] = Field(max_length=200)


@router.post("/beats", status_code=204)
def post_beats(data: BeatsIn, subject: SubjectDep, session: SessionDep) -> None:
    """Пачка биений одним запросом — агент машины опрашивает свои таймеры и шлёт всё сразу."""
    require(subject, "feed.write")
    for one in data.beats:
        _beat(session, one)
    session.commit()


@router.get("/pulse", response_model=list[BeatOut])
def pulse(subject: SubjectDep, session: SessionDep) -> list[BeatOut]:
    """Кто молчит дольше обещанного. Тревожные — сверху."""
    require(subject, "read")
    beats = session.exec(select(Beat)).all()
    return [BeatOut(**vars(r)) for r in pulse_rows(beats, now())]


class MuteIn(BaseModel):
    hours: int = Field(ge=0, le=24 * 30)


@router.post("/beats/{source}/mute", status_code=204)
def mute(source: str, data: MuteIn, subject: SubjectDep, session: SessionDep) -> None:
    """Выключили задачу намеренно — это не сбой: без заглушки остановленный таймер вечно висел бы в тревоге."""
    require(subject, "feed.write")
    b = session.get(Beat, source)
    if not b:
        raise HTTPException(404, "такого источника нет")
    b.muted_until = now() + timedelta(hours=data.hours) if data.hours else None
    session.add(b)
    session.commit()
