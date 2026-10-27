from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlmodel import Session, col, func, select

from .. import roadmap as rm
from ..auth import SubjectDep, require
from ..db import SessionDep, next_id
from ..feed_log import log_event
from ..models import JournalEntry, Project, Stage, Task, now

router = APIRouter(prefix="/projects", tags=["projects"])


class StageOut(BaseModel):
    n: int
    title: str
    marker: Optional[str]
    status: str
    frozen: bool
    closed_at: Optional[datetime]


class JournalOut(BaseModel):
    id: int
    kind: str
    text: str
    files: list
    author: Optional[str]
    created_at: datetime


class ProjectShort(BaseModel):
    id: str
    name: str
    folder: Optional[str]
    status: str
    progress: int
    stages_total: int
    stages_done: int
    current_stage: Optional[str]
    open_tasks: int
    updated_at: datetime


class ProjectFull(ProjectShort):
    roadmap_text: str
    stages: list[StageOut]
    journal: list[JournalOut]


def sync_stages(session: Session, p: Project, text: str) -> list[rm.EtapIzFayla]:
    """Файл карты — источник: разобрать текст и переписать кэш этапов. Дату закрытия этапа,
    который уже был закрыт, не сбиваем."""
    etapy = rm.razobrat_kartu(text)
    lines = text.splitlines()
    was = {s.n: s for s in session.exec(select(Stage).where(Stage.project_id == p.id)).all()}
    session.execute(delete(Stage).where(Stage.project_id == p.id))
    for e, status in rm.statusy(etapy):
        old = was.get(e.n)
        closed = None
        if status == "done":
            in_file = rm.data_zakrytiya(lines[e.line_no - 1] if 0 < e.line_no <= len(lines) else "")
            closed = (in_file.replace(tzinfo=timezone.utc) if in_file
                      else old.closed_at if old and old.status == "done" else now())
        session.add(Stage(project_id=p.id, n=e.n, title=e.title[:300], marker=e.marker, status=status,
                          frozen=e.zamorozhen, closed_at=closed))
    p.roadmap_text = text
    p.progress = rm.progress(etapy)
    p.updated_at = now()
    if etapy and p.progress == 100 and p.status == "active":
        p.status = "done"
    session.add(p)
    return etapy


def _short(session: Session, p: Project) -> ProjectShort:
    stages = session.exec(select(Stage).where(Stage.project_id == p.id).order_by(Stage.n)).all()
    live = [s for s in stages if not s.frozen]
    cur = next((s for s in stages if s.status == "cur"), None)
    open_tasks = session.exec(select(func.count()).select_from(Task)
                              .where(Task.project_id == p.id, Task.status == "open")).one()
    return ProjectShort(id=p.id, name=p.name, folder=p.folder, status=p.status, progress=p.progress,
                        stages_total=len(live), stages_done=sum(s.status == "done" for s in live),
                        current_stage=f"{cur.n}. {cur.title}" if cur else None,
                        open_tasks=open_tasks, updated_at=p.updated_at)


def _full(session: Session, p: Project) -> ProjectFull:
    stages = session.exec(select(Stage).where(Stage.project_id == p.id).order_by(Stage.n)).all()
    journal = session.exec(select(JournalEntry).where(JournalEntry.project_id == p.id)
                           .order_by(col(JournalEntry.created_at).desc()).limit(80)).all()
    return ProjectFull(**_short(session, p).model_dump(), roadmap_text=p.roadmap_text,
                       stages=[StageOut(**s.model_dump()) for s in stages],
                       journal=[JournalOut(**j.model_dump()) for j in journal])


def _get(session: Session, pid: str) -> Project:
    p = session.get(Project, pid)
    if not p:
        raise HTTPException(404, "проекта нет")
    return p


@router.get("", response_model=list[ProjectShort])
def list_projects(subject: SubjectDep, session: SessionDep,
                  status: Literal["active", "all"] = "active") -> list[ProjectShort]:
    require(subject, "read")
    q = select(Project).order_by(col(Project.updated_at).desc())
    if status == "active":
        q = q.where(Project.status == "active")
    return [_short(session, p) for p in session.exec(q).all()]


class FindIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


@router.post("/find", response_model=ProjectShort, responses={409: {"description": "несколько совпадений"}})
def find_project(data: FindIn, subject: SubjectDep, session: SessionDep) -> ProjectShort:
    """Проект по имени или его части — для MCP: Claude называет проект словами, а не id."""
    require(subject, "read")
    rows = session.exec(select(Project).where(col(Project.name).ilike(f"%{data.name.strip()}%"))).all()
    exact = [p for p in rows if p.name.lower() == data.name.strip().lower()]
    rows = exact or rows
    if not rows:
        raise HTTPException(404, "проекта с таким именем нет")
    if len(rows) > 1:
        raise HTTPException(409, {"detail": "несколько проектов подходят", "projects":
                                  [{"id": p.id, "name": p.name} for p in rows]})
    return _short(session, rows[0])


@router.get("/{pid}", response_model=ProjectFull)
def get_project(pid: str, subject: SubjectDep, session: SessionDep) -> ProjectFull:
    require(subject, "read")
    return _full(session, _get(session, pid))


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    folder: Optional[str] = Field(default=None, max_length=500)
    roadmap_text: str = Field(default="", max_length=200_000)


@router.post("", response_model=ProjectFull, status_code=201)
def create_project(data: ProjectIn, subject: SubjectDep, session: SessionDep) -> ProjectFull:
    require(subject, "projects.write")
    p = Project(id=next_id(session, "projects", "prj"), name=data.name, folder=data.folder)
    session.add(p)
    session.flush()
    sync_stages(session, p, data.roadmap_text)
    log_event(session, subject, "projects", "project_created", f"Новый проект: {p.name}", ref=p.id)
    session.commit()
    return _full(session, p)


class RoadmapIn(BaseModel):
    text: str = Field(max_length=200_000)


@router.put("/{pid}/roadmap", response_model=ProjectFull)
def put_roadmap(pid: str, data: RoadmapIn, subject: SubjectDep, session: SessionDep) -> ProjectFull:
    """Новый текст карты (файл поменяли руками или хук прислал свежую версию) — этапы пересобираются."""
    require(subject, "projects.write")
    p = _get(session, pid)
    sync_stages(session, p, data.text)
    session.commit()
    return _full(session, p)


class StageIn(BaseModel):
    n: int
    status: Literal["done", "todo"]
    note: str = Field(default="", max_length=2000)


class StageResult(BaseModel):
    result: str          # izmenen | bez_izmeneniy
    project: ProjectFull


@router.post("/{pid}/stage", response_model=StageResult)
def mark_stage(pid: str, data: StageIn, subject: SubjectDep, session: SessionDep) -> StageResult:
    """Отметить этап: правится сам текст карты («- [ ]» → «- [x]» и «(закрыт ДД.ММ.ГГГГ)»), потом кэш.
    MCP-клиент кладёт вернувшийся текст обратно в файл на машине пользователя."""
    require(subject, "projects.write")
    p = _get(session, pid)
    text, result = rm.pravit_kartu(p.roadmap_text, data.n, data.status, date.today().strftime("%d.%m.%Y"))
    if result == "ne_nayden":
        raise HTTPException(404, f"в карте нет этапа {data.n}")
    sync_stages(session, p, text)
    if result == "izmenen":
        verb = "закрыт" if data.status == "done" else "снова открыт"
        session.add(JournalEntry(project_id=p.id, kind="stage", author=subject.id,
                                 text=f"Этап {data.n} {verb}." + (f" {data.note}" if data.note else "")))
        log_event(session, subject, "projects", "stage_" + data.status, f"{p.name}: этап {data.n} {verb}", ref=p.id)
    session.commit()
    return StageResult(result=result, project=_full(session, p))


class JournalIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    kind: Literal["note", "decision"] = "note"
    files: list[str] = Field(default_factory=list, max_length=50)


@router.post("/{pid}/journal", response_model=JournalOut, status_code=201)
def add_journal(pid: str, data: JournalIn, subject: SubjectDep, session: SessionDep) -> JournalOut:
    """Запись в журнал проекта. Решение (decision) пишется вместе с причиной — чтобы следующая сессия
    не переигрывала его заново."""
    require(subject, "projects.write")
    p = _get(session, pid)
    e = JournalEntry(project_id=p.id, kind=data.kind, text=data.text, files=data.files, author=subject.id)
    p.updated_at = now()
    session.add(e)
    session.add(p)
    session.commit()
    return JournalOut(**e.model_dump())


class StatusIn(BaseModel):
    status: Literal["active", "paused", "done"]


@router.patch("/{pid}", response_model=ProjectFull)
def patch_project(pid: str, data: StatusIn, subject: SubjectDep, session: SessionDep) -> ProjectFull:
    require(subject, "projects.write")
    p = _get(session, pid)
    p.status = data.status
    p.updated_at = now()
    session.add(p)
    session.commit()
    return _full(session, p)
