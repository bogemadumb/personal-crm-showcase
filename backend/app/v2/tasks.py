from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import col, select

from ..auth import SubjectDep, require
from ..db import SessionDep, next_id
from ..feed_log import log_event
from ..models import Project, Task, now

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskOut(BaseModel):
    id: str
    title: str
    notes: str
    project_id: Optional[str]
    project_name: Optional[str] = None
    plan_date: Optional[date]
    due: Optional[date]
    priority: int
    status: str
    overdue: bool = False
    created_at: datetime
    done_at: Optional[datetime]


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    notes: str = Field(default="", max_length=20000)
    project_id: Optional[str] = None
    plan_date: Optional[date] = None
    due: Optional[date] = None
    priority: int = Field(default=0, ge=0, le=2)


class TaskPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    notes: Optional[str] = Field(default=None, max_length=20000)
    project_id: Optional[str] = None
    plan_date: Optional[date] = None
    due: Optional[date] = None
    priority: Optional[int] = Field(default=None, ge=0, le=2)
    status: Optional[Literal["open", "done"]] = None


def to_out(t: Task, names: dict[str, str]) -> TaskOut:
    today = date.today()
    return TaskOut(**t.model_dump(), project_name=names.get(t.project_id or ""),
                   overdue=t.status == "open" and t.due is not None and t.due < today)


def project_names(session) -> dict[str, str]:
    return {p.id: p.name for p in session.exec(select(Project)).all()}


@router.get("", response_model=list[TaskOut])
def list_tasks(subject: SubjectDep, session: SessionDep,
               status: Literal["open", "done", "all"] = "open",
               view: Literal["all", "today", "upcoming", "inbox"] = "all",
               project_id: Optional[str] = None,
               limit: int = Query(200, le=1000)) -> list[TaskOut]:
    require(subject, "read")
    q = select(Task)
    if status != "all":
        q = q.where(Task.status == status)
    if project_id:
        q = q.where(Task.project_id == project_id)
    today = date.today()
    if view == "today":
        q = q.where((Task.plan_date <= today) | (Task.due <= today))
    elif view == "upcoming":
        q = q.where((Task.plan_date > today) | ((Task.plan_date == None) & (Task.due > today)))  # noqa: E711
    elif view == "inbox":
        q = q.where(Task.plan_date == None, Task.due == None, Task.project_id == None)  # noqa: E711
    q = q.order_by(col(Task.priority).desc(), col(Task.due).asc().nulls_last(), Task.created_at).limit(limit)
    names = project_names(session)
    return [to_out(t, names) for t in session.exec(q).all()]


@router.post("", response_model=TaskOut, status_code=201)
def create_task(data: TaskIn, subject: SubjectDep, session: SessionDep) -> TaskOut:
    require(subject, "tasks.write")
    if data.project_id and not session.get(Project, data.project_id):
        raise HTTPException(400, "нет такого проекта")
    t = Task(id=next_id(session, "tasks", "tsk"), **data.model_dump())
    session.add(t)
    log_event(session, subject, "tasks", "task_created", f"Новая задача: {t.title}", ref=t.id)
    session.commit()
    return to_out(t, project_names(session))


@router.patch("/{task_id}", response_model=TaskOut)
def patch_task(task_id: str, data: TaskPatch, subject: SubjectDep, session: SessionDep) -> TaskOut:
    require(subject, "tasks.write")
    t = session.get(Task, task_id)
    if not t:
        raise HTTPException(404, "задачи нет")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("status") == "done" and t.status != "done":
        t.done_at = now()
        log_event(session, subject, "tasks", "task_done", f"Готово: {t.title}", ref=t.id)
    elif changes.get("status") == "open":
        t.done_at = None
    for k, v in changes.items():
        setattr(t, k, v)
    session.add(t)
    session.commit()
    return to_out(t, project_names(session))


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, subject: SubjectDep, session: SessionDep) -> None:
    require(subject, "tasks.write")
    t = session.get(Task, task_id)
    if not t:
        raise HTTPException(404, "задачи нет")
    session.delete(t)
    session.commit()
