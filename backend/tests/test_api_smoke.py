"""Сквозная проверка живого API (после docker compose up):
    CRM_URL=http://localhost:8080 CRM_KEY=<DEMO_API_KEY> pytest tests/test_api_smoke.py
Без CRM_URL пропускается. Создаёт свои объекты и убирает задачу за собой."""
import os

import httpx
import pytest

URL = os.environ.get("CRM_URL")
KEY = os.environ.get("CRM_KEY")
pytestmark = pytest.mark.skipif(not URL, reason="CRM_URL не задан — живого API нет")


@pytest.fixture(scope="module")
def owner():
    c = httpx.Client(base_url=f"{URL}/api/v2", timeout=10)
    r = c.post("/auth/login", json={"email": "demo@example.com", "password": os.environ.get("DEMO_PASSWORD", "demo")})
    assert r.status_code == 200, r.text
    return c


def test_health():
    r = httpx.get(f"{URL}/api/v2/health", timeout=10)
    assert r.status_code == 200 and r.json()["db"] is True


def test_bez_vhoda_401():
    assert httpx.get(f"{URL}/api/v2/tasks", timeout=10).status_code == 401


def test_today(owner):
    d = owner.get("/today").json()
    assert d["projects"] and d["beats_total"] >= 1


def test_zadacha_tuda_i_obratno(owner):
    t = owner.post("/tasks", json={"title": "smoke: проверить API", "priority": 1}).json()
    assert t["id"].startswith("tsk-")
    assert owner.patch(f"/tasks/{t['id']}", json={"status": "done"}).json()["done_at"]
    assert owner.delete(f"/tasks/{t['id']}").status_code == 204


def test_poisk_so_stemmingom(owner):
    hits = owner.get("/search", params={"q": "бэкапы"}).json()
    assert any(h["type"] == "note" for h in hits)


def test_etap_proekta_i_otkat(owner):
    p = owner.post("/projects/find", json={"name": "медиасервер"}).json()
    r = owner.post(f"/projects/{p['id']}/stage", json={"n": 2, "status": "done"}).json()
    assert r["result"] == "izmenen" and "(закрыт" in r["project"]["roadmap_text"]
    r = owner.post(f"/projects/{p['id']}/stage", json={"n": 2, "status": "todo"}).json()
    assert r["result"] == "izmenen"


@pytest.mark.skipif(not KEY, reason="CRM_KEY не задан")
def test_klyuch_agenta_ne_upravlyaet_klyuchami():
    h = {"X-API-Key": KEY}
    assert httpx.get(f"{URL}/api/v2/projects", headers=h, timeout=10).status_code == 200
    assert httpx.get(f"{URL}/api/v2/auth/keys", headers=h, timeout=10).status_code == 403
    r = httpx.post(f"{URL}/api/v2/feed/beat", headers=h, timeout=10,
                   json={"source": "smoke-test", "title": "Smoke", "expect_every": 60})
    assert r.status_code == 204
