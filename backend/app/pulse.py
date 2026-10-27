"""Пульс фоновых задач — чистая функция над биениями, без базы (так её легко тестировать).

Правила, выросшие из эксплуатации:
- задача «молчит», если от неё нет биения дольше 1,5 обещанных интервалов: упавший таймер выглядит как тишина;
- ноутбук молчит дольше 5 минут — он спит, и задачи на нём не тревога;
- молчит сама машина (её агент — источник с source == machine) — одна тревога по машине,
  а не по тревоге на каждую её задачу;
- заглушённая задача (muted_until в будущем) не тревожит, но видна.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

LAPTOP_SLEEP_SEC = 300
LAPTOPS = {"laptop"}


@dataclass
class BeatView:
    source: str
    title: str
    machine: str
    expect_every: int
    status: str
    note: Optional[str]
    fails: int
    last_at: datetime
    silent_min: int
    late: bool
    muted: bool
    sleeping: bool
    machine_down: bool
    alarm: bool


def pulse_rows(beats: list, now: datetime) -> list[BeatView]:
    by_source = {b.source: b for b in beats}
    machine_silent: dict[str, bool] = {}
    for m in {b.machine for b in beats}:
        agent = by_source.get(m)
        if agent is None:
            continue
        silent = (now - agent.last_at).total_seconds()
        limit = LAPTOP_SLEEP_SEC if m in LAPTOPS else agent.expect_every * 1.5
        machine_silent[m] = silent > limit
    out = []
    for b in beats:
        silent = (now - b.last_at).total_seconds()
        late = silent > b.expect_every * 1.5
        muted = b.muted_until is not None and b.muted_until > now
        sleeping = b.machine in LAPTOPS and machine_silent.get(b.machine, False)
        machine_down = (machine_silent.get(b.machine, False) and b.source != b.machine
                        and late and b.status == "ok" and not sleeping)
        alarm = (late or b.status != "ok") and not muted and not sleeping and not machine_down
        out.append(BeatView(source=b.source, title=b.title, machine=b.machine, expect_every=b.expect_every,
                            status=b.status, note=b.note, fails=b.fails, last_at=b.last_at,
                            silent_min=int(silent // 60), late=late, muted=muted, sleeping=sleeping,
                            machine_down=machine_down, alarm=alarm))
    return sorted(out, key=lambda r: (not r.alarm, r.machine, r.source))
