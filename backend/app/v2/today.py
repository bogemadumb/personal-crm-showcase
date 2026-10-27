from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import Session, col, select

from ..auth import SubjectDep, require
from ..db import SessionDep, cached
from ..models import Beat, CalendarEvent, FeedEvent, Project, Task, now
from ..pulse import pulse_rows
from .calendar import EventOut
from .feed import EventOut as FeedOut
from .projects import ProjectShort, _short
from .tasks import TaskOut, project_names, to_out

router = APIRouter(tags=["today"])


class Today(BaseModel):
    date: date
    focus: list[TaskOut]
    overdue: int
    done_today: int
    events: list[EventOut]
    projects: list[ProjectShort]
    alarms: int
    beats_total: int
    feed: list[FeedOut]


def build(session: Session) -> Today:
    d = date.today()
    names = project_names(session)
    open_today = session.exec(select(Task).where(Task.status == "open",
                                                 (Task.plan_date <= d) | (Task.due <= d))
                              .order_by(col(Task.priority).desc(), col(Task.due).asc().nulls_last())).all()
    day_start = datetime.combine(d, time.min, tzinfo=timezone.utc)
    done_today = session.exec(select(Task).where(Task.status == "done", Task.done_at >= day_start)).all()
    events = session.exec(select(CalendarEvent).where(CalendarEvent.starts_at >= day_start,
                                                      CalendarEvent.starts_at < day_start + timedelta(days=2))
                          .order_by(CalendarEvent.starts_at)).all()
    projects = session.exec(select(Project).where(Project.status == "active")
                            .order_by(col(Project.updated_at).desc()).limit(4)).all()
    beats = pulse_rows(session.exec(select(Beat)).all(), now())
    feed = session.exec(select(FeedEvent).order_by(col(FeedEvent.created_at).desc()).limit(6)).all()
    return Today(date=d, focus=[to_out(t, names) for t in open_today[:12]],
                 overdue=sum(1 for t in open_today if t.due and t.due < d),
                 done_today=len(done_today),
                 events=[EventOut(**e.model_dump()) for e in events],
                 projects=[_short(session, p) for p in projects],
                 alarms=sum(b.alarm for b in beats), beats_total=len(beats),
                 feed=[FeedOut(**e.model_dump()) for e in feed])


@router.get("/today", response_model=Today)
def today(subject: SubjectDep, session: SessionDep) -> Today:
    """Главный экран одним запросом. Кэш процесса на 30 с сбрасывается любой записью (db.cached)."""
    require(subject, "read")
    return cached(("today", date.today()), 30, lambda: build(session))
