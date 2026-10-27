from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import col, select

from ..auth import SubjectDep, require
from ..db import SessionDep, next_id
from ..models import Note, now

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteOut(BaseModel):
    id: str
    title: str
    body: str
    tags: list[str]
    pinned: bool
    updated_at: datetime


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(default="", max_length=200_000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    pinned: bool = False


class NotePatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    body: Optional[str] = Field(default=None, max_length=200_000)
    tags: Optional[list[str]] = Field(default=None, max_length=20)
    pinned: Optional[bool] = None


def _clean_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    for t in tags:
        t = t.strip().lstrip("#").lower()[:40]
        if t and t not in out:
            out.append(t)
    return out


@router.get("", response_model=list[NoteOut])
def list_notes(subject: SubjectDep, session: SessionDep, tag: Optional[str] = None) -> list[NoteOut]:
    require(subject, "read")
    rows = session.exec(select(Note).order_by(col(Note.pinned).desc(), col(Note.updated_at).desc())).all()
    if tag:
        rows = [n for n in rows if tag.lower() in n.tags]
    return [NoteOut(**n.model_dump()) for n in rows]


@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: str, subject: SubjectDep, session: SessionDep) -> NoteOut:
    require(subject, "read")
    n = session.get(Note, note_id)
    if not n:
        raise HTTPException(404, "заметки нет")
    return NoteOut(**n.model_dump())


@router.post("", response_model=NoteOut, status_code=201)
def create_note(data: NoteIn, subject: SubjectDep, session: SessionDep) -> NoteOut:
    require(subject, "notes.write")
    n = Note(id=next_id(session, "notes", "note"), title=data.title, body=data.body,
             tags=_clean_tags(data.tags), pinned=data.pinned)
    session.add(n)
    session.commit()
    return NoteOut(**n.model_dump())


@router.patch("/{note_id}", response_model=NoteOut)
def patch_note(note_id: str, data: NotePatch, subject: SubjectDep, session: SessionDep) -> NoteOut:
    require(subject, "notes.write")
    n = session.get(Note, note_id)
    if not n:
        raise HTTPException(404, "заметки нет")
    changes = data.model_dump(exclude_unset=True)
    if "tags" in changes:
        changes["tags"] = _clean_tags(changes["tags"] or [])
    for k, v in changes.items():
        setattr(n, k, v)
    n.updated_at = now()
    session.add(n)
    session.commit()
    return NoteOut(**n.model_dump())


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str, subject: SubjectDep, session: SessionDep) -> None:
    require(subject, "notes.write")
    n = session.get(Note, note_id)
    if not n:
        raise HTTPException(404, "заметки нет")
    session.delete(n)
    session.commit()
