#!/usr/bin/env python3
"""MCP-сервер CRM: даёт Claude Code (или любому MCP-клиенту) план дня, задачи и проекты.

Тонкий клиент к REST API с ключом X-API-Key (роль agent: читает всё, пишет задачи и журналы,
не трогает ключи и настройки). Подключение:

    claude mcp add crm -e CRM_URL=http://localhost:8080 -e CRM_KEY=<ключ> -- python3 mcp/crm_mcp.py

Сценарий, ради которого он сделан: сессия Claude Code работает в папке проекта, по ходу пишет
решения в журнал (project_journal) и закрывает этапы (project_stage) — сервер правит текст
дорожной карты, а этот клиент кладёт его обратно в файл на диске. Файл остаётся источником правды.
"""
import os
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

BASE = os.environ.get("CRM_URL", "http://localhost:8080").rstrip("/") + "/api/v2"

mcp = MCPServer("crm")


def call(method: str, path: str, **kw):
    key = os.environ.get("CRM_KEY")
    if not key:
        return {"error": 401, "detail": "задайте CRM_KEY — ключ из POST /api/v2/auth/keys"}
    try:
        r = httpx.request(method, f"{BASE}{path}", headers={"X-API-Key": key}, timeout=30, **kw)
    except httpx.HTTPError as e:
        return {"error": 503, "detail": f"CRM недоступна ({BASE}): {type(e).__name__}"}
    if r.status_code == 204:
        return {"ok": True}
    try:
        data = r.json()
    except ValueError:
        data = {"detail": r.text[:300]}
    if r.status_code >= 400:
        return {"error": r.status_code, **(data if isinstance(data, dict) else {"detail": data})}
    return data


def is_error(x) -> bool:
    return isinstance(x, dict) and "error" in x


def project_id(name_or_id: str):
    s = name_or_id.strip()
    if s.startswith("prj-"):
        return s
    found = call("POST", "/projects/find", json={"name": s})
    return found if is_error(found) else found["id"]


@mcp.tool()
def today() -> dict:
    """Сводка дня: задачи в фокусе, просрочки, ближайшие события, проекты в работе, тревоги пульса."""
    return call("GET", "/today")


@mcp.tool()
def tasks(view: str = "today", project: str = "") -> list | dict:
    """Открытые задачи. view: today | upcoming | inbox | all. project — имя или id проекта (необязательно)."""
    params = {"view": view}
    if project:
        pid = project_id(project)
        if is_error(pid):
            return pid
        params["project_id"] = pid
    return call("GET", "/tasks", params=params)


@mcp.tool()
def add_task(title: str, plan_date: str = "", due: str = "", project: str = "", priority: int = 0) -> dict:
    """Новая задача. Даты — YYYY-MM-DD. priority: 0 обычная, 1 важная, 2 срочная."""
    body: dict = {"title": title, "priority": priority}
    if plan_date:
        body["plan_date"] = plan_date
    if due:
        body["due"] = due
    if project:
        pid = project_id(project)
        if is_error(pid):
            return pid
        body["project_id"] = pid
    return call("POST", "/tasks", json=body)


@mcp.tool()
def complete_task(task_id: str) -> dict:
    """Отметить задачу выполненной (id вида tsk-000012)."""
    return call("PATCH", f"/tasks/{task_id}", json={"status": "done"})


@mcp.tool()
def projects(status: str = "active") -> list | dict:
    """Проекты с прогрессом по дорожной карте и текущим этапом. status: active | all."""
    return call("GET", "/projects", params={"status": status})


@mcp.tool()
def project(name: str) -> dict:
    """Карточка проекта: этапы, текст дорожной карты, журнал. name — имя (можно часть) или id."""
    pid = project_id(name)
    return pid if is_error(pid) else call("GET", f"/projects/{pid}")


@mcp.tool()
def project_journal(name: str, text: str, kind: str = "note") -> dict:
    """Запись в журнал проекта. kind: note (что сделано) или decision (решение — вместе с причиной)."""
    pid = project_id(name)
    return pid if is_error(pid) else call("POST", f"/projects/{pid}/journal", json={"text": text, "kind": kind})


@mcp.tool()
def project_stage(name: str, n: int, status: str = "done", roadmap_file: str = "") -> dict:
    """Закрыть (done) или снова открыть (todo) этап N. Сервер правит текст карты: «- [ ]» → «- [x]»
    и «(закрыт ДД.ММ.ГГГГ)». Если передан roadmap_file — новый текст записывается в этот файл."""
    pid = project_id(name)
    if is_error(pid):
        return pid
    out = call("POST", f"/projects/{pid}/stage", json={"n": n, "status": status})
    if is_error(out):
        return out
    file_result = "not_written"
    if roadmap_file and out["result"] == "izmenen":
        p = Path(roadmap_file).expanduser()
        if p.is_file():
            # newline="" — CRLF в карте остаётся CRLF
            with p.open("w", encoding="utf-8", newline="") as f:
                f.write(out["project"]["roadmap_text"])
            file_result = "written"
        else:
            file_result = "file_not_found"
    pr = out["project"]
    return {"result": out["result"], "file": file_result, "progress": pr["progress"],
            "current_stage": pr["current_stage"],
            "stages": [{"n": s["n"], "title": s["title"], "status": s["status"]} for s in pr["stages"]]}


@mcp.tool()
def search(query: str, limit: int = 10) -> list | dict:
    """Полнотекстовый поиск по задачам, заметкам и проектам (русская морфология)."""
    return call("GET", "/search", params={"q": query, "limit": limit})


@mcp.tool()
def pulse() -> list | dict:
    """Состояние фоновых задач: кто молчит дольше обещанного, у кого сбой."""
    return call("GET", "/feed/pulse")


if __name__ == "__main__":
    mcp.run()
