from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import col, select

from ..auth import SubjectDep, require
from ..db import SessionDep, next_id
from ..models import CalendarEvent, Task

router = APIRouter(prefix="/calendar", tags=["calendar"])


class EventOut(BaseModel):
    id: str
    title: str
    starts_at: datetime
    ends_at: Optional[datetime]
    location: Optional[str]
    kind: str


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    starts_at: datetime
    ends_at: Optional[datetime] = None
    location: Optional[str] = Field(default=None, max_length=300)
    kind: Literal["event", "deadline", "reminder"] = "event"


class DayOut(BaseModel):
    day: date
    events: list[EventOut]
    deadlines: list[dict]


@router.get("", response_model=list[DayOut])
def week(subject: SubjectDep, session: SessionDep, start: Optional[date] = None, days: int = 7) -> list[DayOut]:
    """Дни подряд: события календаря и сроки задач — на одной сетке, чтобы дедлайн не жил отдельно."""
    require(subject, "read")
    days = max(1, min(days, 42))
    start = start or date.today() - timedelta(days=date.today().weekday())
    lo = datetime.combine(start, time.min, tzinfo=timezone.utc)
    hi = lo + timedelta(days=days)
    events = session.exec(select(CalendarEvent).where(CalendarEvent.starts_at >= lo, CalendarEvent.starts_at < hi)
                          .order_by(CalendarEvent.starts_at)).all()
    tasks = session.exec(select(Task).where(Task.status == "open", Task.due >= start,
                                            Task.due < start + timedelta(days=days))).all()
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        out.append(DayOut(
            day=d,
            events=[EventOut(**e.model_dump()) for e in events if e.starts_at.date() == d],
            deadlines=[{"id": t.id, "title": t.title} for t in tasks if t.due == d]))
    return out


@router.post("", response_model=EventOut, status_code=201)
def create_event(data: EventIn, subject: SubjectDep, session: SessionDep) -> EventOut:
    require(subject, "tasks.write")
    if data.ends_at and data.ends_at < data.starts_at:
        raise HTTPException(400, "конец раньше начала")
    e = CalendarEvent(id=next_id(session, "events", "evt"), **data.model_dump())
    session.add(e)
    session.commit()
    return EventOut(**e.model_dump())


@router.get("/upcoming", response_model=list[EventOut])
def upcoming(subject: SubjectDep, session: SessionDep, limit: int = 5) -> list[EventOut]:
    require(subject, "read")
    rows = session.exec(select(CalendarEvent).where(CalendarEvent.starts_at >= datetime.now(timezone.utc))
                        .order_by(col(CalendarEvent.starts_at)).limit(min(limit, 50))).all()
    return [EventOut(**e.model_dump()) for e in rows]


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: str, subject: SubjectDep, session: SessionDep) -> None:
    require(subject, "tasks.write")
    e = session.get(CalendarEvent, event_id)
    if not e:
        raise HTTPException(404, "события нет")
    session.delete(e)
    session.commit()
