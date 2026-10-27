from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text as sql_text

from ..auth import SubjectDep, require
from ..db import SessionDep

router = APIRouter(prefix="/search", tags=["search"])


class Hit(BaseModel):
    type: Literal["task", "note", "project"]
    id: str
    title: str
    snippet: str
    rank: float


# Полнотекстовый поиск Postgres по-русски (стемминг: «задачи» найдёт «задача»),
# плюс ILIKE по заголовку — для коротких запросов и частей слов, которые стеммер не видит.
SQL = """
WITH q AS (SELECT websearch_to_tsquery('russian', :q) AS tsq, '%' || :like || '%' AS lk)
SELECT * FROM (
  SELECT 'task' AS type, t.id, t.title,
         ts_headline('russian', coalesce(t.notes, ''), q.tsq, 'MaxFragments=1,MaxWords=18,MinWords=6') AS snippet,
         ts_rank(to_tsvector('russian', t.title || ' ' || coalesce(t.notes, '')), q.tsq)
           + CASE WHEN t.title ILIKE q.lk THEN 1 ELSE 0 END AS rank
    FROM crm.tasks t, q
   WHERE to_tsvector('russian', t.title || ' ' || coalesce(t.notes, '')) @@ q.tsq OR t.title ILIKE q.lk
  UNION ALL
  SELECT 'note', n.id, n.title,
         ts_headline('russian', n.body, q.tsq, 'MaxFragments=1,MaxWords=18,MinWords=6'),
         ts_rank(to_tsvector('russian', n.title || ' ' || n.body), q.tsq)
           + CASE WHEN n.title ILIKE q.lk THEN 1 ELSE 0 END
    FROM crm.notes n, q
   WHERE to_tsvector('russian', n.title || ' ' || n.body) @@ q.tsq OR n.title ILIKE q.lk
  UNION ALL
  SELECT 'project', p.id, p.name, '',
         ts_rank(to_tsvector('russian', p.name || ' ' || p.roadmap_text), q.tsq)
           + CASE WHEN p.name ILIKE q.lk THEN 1 ELSE 0 END
    FROM crm.projects p, q
   WHERE to_tsvector('russian', p.name || ' ' || p.roadmap_text) @@ q.tsq OR p.name ILIKE q.lk
) hits ORDER BY rank DESC LIMIT :limit
"""


@router.get("", response_model=list[Hit])
def search(subject: SubjectDep, session: SessionDep, q: str = Query(min_length=1, max_length=200),
           limit: int = Query(20, le=100)) -> list[Hit]:
    require(subject, "read")
    like = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = session.exec(sql_text(SQL).bindparams(q=q.strip(), like=like, limit=limit)).all()
    return [Hit(type=r[0], id=r[1], title=r[2], snippet=r[3] or "", rank=float(r[4] or 0)) for r in rows]
