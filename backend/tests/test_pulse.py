from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.pulse import pulse_rows

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


@dataclass
class B:
    source: str
    machine: str
    expect_every: int
    minutes_ago: float
    status: str = "ok"
    muted_until: Optional[datetime] = None
    title: str = ""
    note: Optional[str] = None
    fails: int = 0

    @property
    def last_at(self):
        return NOW - timedelta(minutes=self.minutes_ago)


def by(rows):
    return {r.source: r for r in rows}


def test_vovremya_i_opozdanie():
    r = by(pulse_rows([B("server", "server", 300, 1), B("job", "server", 600, 16)], NOW))
    assert not r["server"].alarm
    assert r["job"].late and r["job"].alarm


def test_sboy_trevozhit_dazhe_vovremya():
    r = by(pulse_rows([B("rss", "server", 1800, 1, status="fail")], NOW))
    assert r["rss"].alarm


def test_spyashchiy_noutbuk_ne_trevoga():
    r = by(pulse_rows([B("laptop", "laptop", 120, 30), B("laptop-sync", "laptop", 300, 40)], NOW))
    assert r["laptop-sync"].sleeping and not r["laptop-sync"].alarm
    assert not r["laptop"].alarm


def test_molchit_mashina_odna_trevoga():
    beats = [B("home-pc", "home-pc", 300, 60), B("home-pc-a", "home-pc", 600, 60), B("home-pc-b", "home-pc", 600, 60)]
    r = by(pulse_rows(beats, NOW))
    assert r["home-pc"].alarm
    assert r["home-pc-a"].machine_down and not r["home-pc-a"].alarm
    assert r["home-pc-b"].machine_down and not r["home-pc-b"].alarm


def test_zaglushennyy_ne_trevozhit():
    r = by(pulse_rows([B("old", "server", 60, 600, muted_until=NOW + timedelta(hours=1))], NOW))
    assert r["old"].muted and not r["old"].alarm


def test_trevozhnye_sverhu():
    rows = pulse_rows([B("a", "server", 3600, 1), B("z", "server", 60, 100)], NOW)
    assert rows[0].source == "z"
