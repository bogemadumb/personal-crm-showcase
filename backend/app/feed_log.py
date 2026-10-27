from typing import Optional

from sqlmodel import Session

from .auth import Subject
from .models import FeedEvent


def log_event(session: Session, subject: Optional[Subject], source: str, kind: str, title: str,
              ref: Optional[str] = None, level: str = "info", detail: Optional[str] = None) -> None:
    """Событие в общую ленту в той же транзакции, что и само действие: откатилось действие — нет и записи."""
    payload = {"ref": ref} if ref else {}
    if subject is not None:
        payload["actor"] = subject.id
    session.add(FeedEvent(source=source, kind=kind, level=level, title=title[:300], detail=detail, payload=payload))
