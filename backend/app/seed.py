"""Демонстрационные данные. Всё вымышлено: люди, проекты, машины и события.

Запуск: python -m app.seed  (или SEED_DEMO=1 при старте API). Пустая база — заполняет, иначе ничего не делает.
Даты считаются от сегодняшнего дня, чтобы экран «Сегодня» был живым в любой день.
"""
import logging
import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from .auth import hash_password, key_hash
from .db import engine, next_id
from .models import ApiKey, Beat, CalendarEvent, FeedEvent, JournalEntry, Note, Project, Task, User
from .v2.projects import sync_stages

log = logging.getLogger("crm.seed")

ROADMAPS = {
    "Домашний медиасервер": ("~/projects/media-server", """# Дорожная карта — Домашний медиасервер

- [x] **Этап 0 · Железо и ОС.** (закрыт {d20}) Старый системник, Debian 13, диски в RAID1.
  Маркер: сервер грузится без монитора, ssh по ключу.
- [x] **Этап 1 · Docker и бэкапы.** (закрыт {d9}) compose, restic в облако раз в сутки.
  Маркер: восстановление тестового тома из бэкапа прошло.
- [ ] **Этап 2 · Jellyfin и индексация.** Медиатека, аппаратное транскодирование.
  Маркер: фильм играет на телевизоре без подтормаживаний.
- [ ] **Этап 3 · Доступ снаружи.** WireGuard, без открытых портов.
  Маркер: с телефона в мобильной сети открывается библиотека.
- [ ] **Этап 4 · Мониторинг.** Биения таймеров в CRM, тревога в мессенджер.
  Маркер: выключенный таймер виден в пульсе через час.
"""),
    "Блог на Astro": ("~/projects/blog", """# Дорожная карта — Блог на Astro

## Этап 1 · Перенос статей (закрыт {d14})
Экспорт из старой платформы, конвертер в Markdown.
Маркер: все 42 статьи собираются без ошибок.

## Этап 2 · Дизайн и тёмная тема
Свои шрифты, тёмная тема по системной настройке.
Маркер: Lighthouse ≥ 95 на главной.

## Этап 3 · Деплой
GitHub Actions → статический хостинг, превью на каждый PR.
Маркер: пуш в main публикует сайт за 2 минуты.
"""),
    "Изучение Rust": ("~/learning/rust", """# Дорожная карта — Изучение Rust

| № | Этап | Что делаем | Готово, когда | Статус |
|---|---|---|---|---|
| 1 | Основы | The Book, главы 1–10 | решены упражнения rustlings | готово {d30s} |
| 2 | Владение и заимствование | главы 4, 15, 16 | свой связный список без unsafe | готово {d6s} |
| 3 | Асинхронность | tokio, своё мини-приложение | CLI-клиент с параллельными запросами | |
| 4 | WebAssembly — заморожен до весны | wasm-bindgen | демо в браузере | |
"""),
    "Ремонт велосипеда": ("~/home/bike", """# Ремонт велосипеда

- [x] Заменить цепь
- [x] Отрегулировать задний переключатель
- [ ] Новые тормозные колодки
- [ ] Прокачать гидравлику
"""),
}

TASKS = [
    # (заголовок, проект, план (дни от сегодня), срок, приоритет, готово, заметки)
    ("Проверить SMART дисков перед установкой Jellyfin", "Домашний медиасервер", 0, None, 1, False,
     "smartctl -a на оба диска, сравнить Reallocated_Sector_Ct."),
    ("Включить аппаратное транскодирование (VAAPI)", "Домашний медиасервер", 0, 2, 2, False, ""),
    ("Описать в журнале, почему restic, а не borg", "Домашний медиасервер", -1, None, 0, False,
     "Решение уже принято — записать причину, чтобы не переигрывать."),
    ("Собрать палитру тёмной темы", "Блог на Astro", 0, 3, 1, False, ""),
    ("Починить битые ссылки после переноса", "Блог на Astro", -2, -1, 2, False,
     "Список из link-checker: 7 ссылок на старые адреса."),
    ("Прочитать главу 16 про потоки", "Изучение Rust", 1, None, 0, False, ""),
    ("Написать CLI-клиент на reqwest + tokio", "Изучение Rust", 3, 7, 1, False, ""),
    ("Купить тормозные колодки", "Ремонт велосипеда", 2, None, 0, False, "Полимерные, не металлические."),
    ("Оплатить хостинг на год", None, 0, 1, 2, False, ""),
    ("Записаться к стоматологу", None, None, None, 0, False, ""),
    ("Разобрать загрузки на ноутбуке", None, None, None, 0, False, ""),
    ("Обновить ядро на сервере", "Домашний медиасервер", -1, None, 1, True, ""),
    ("Настроить restic на ежедневный прогон", "Домашний медиасервер", -3, None, 1, True, ""),
    ("Перенести 42 статьи", "Блог на Astro", -5, None, 1, True, ""),
]

NOTES = [
    ("Шпаргалка: systemd-таймеры", ["linux", "шпаргалка"], True, """# systemd-таймеры

```ini
[Timer]
OnCalendar=*-*-* 03:30
Persistent=true
RandomizedDelaySec=10m
```

- `systemctl list-timers` — когда следующий запуск;
- `Persistent=true` — пропущенный запуск догонит после включения;
- в конце юнита — `curl` биения в CRM, чтобы молчание было видно в пульсе.
"""),
    ("Чек-лист бэкапа", ["бэкап", "сервер"], True, """1. Дамп базы → шифрование → копия на другую машину.
2. Размер дампа меньше 70 % прошлого — тревога, а не «успех».
3. Раз в месяц — **восстановление** в пустой контейнер. Бэкап, который не восстанавливали, — не бэкап.
"""),
    ("Идеи для блога", ["блог"], False, """- Как я перестал бояться миграций Alembic
- Pulse: мониторинг таймеров без Prometheus
- Почему файл дорожной карты — источник правды, а база — кэш
"""),
    ("Команды Docker, которые забываю", ["docker", "шпаргалка"], False, """```sh
docker compose logs -f --tail=100 api
docker system df
docker compose exec postgres psql -U crm
```
"""),
    ("Книги на осень", ["чтение"], False, "- «Designing Data-Intensive Applications»\n- «The Rust Programming Language»\n- «Site Reliability Engineering»\n"),
    ("Рецепт: шакшука", ["еда"], False, "Помидоры, перец, лук, яйца, кумин, паприка. 20 минут на сковороде под крышкой."),
]

EVENTS = [
    # (заголовок, день от сегодня, час, длительность ч, место, вид)
    ("Созвон по домашнему серверу с другом", 0, 19, 1, "онлайн", "event"),
    ("Спортзал", 0, 8, 1.5, "фитнес-клуб", "event"),
    ("Срок оплаты хостинга", 1, 12, None, None, "deadline"),
    ("Митап по Rust", 2, 18, 3, "коворкинг в центре", "event"),
    ("Стрижка", 3, 11, 1, None, "event"),
    ("Напоминание: продлить домен", 5, 10, None, None, "reminder"),
    ("Велопрогулка", 6, 9, 3, "набережная", "event"),
]

FEED = [
    ("server-backup", "beat_ok", "info", "Бэкап базы: дамп 18 МБ, копия на домашний ПК", 2),
    ("server-certbot", "renewed", "info", "Сертификат продлён на 90 дней", 7),
    ("home-pc-media-index", "beat_fail", "error", "Индексация медиатеки: диск /mnt/media не смонтирован", 26),
    ("tasks", "task_done", "info", "Готово: Обновить ядро на сервере", 30),
    ("projects", "stage_done", "info", "Домашний медиасервер: этап 1 закрыт", 60 * 9),
    ("server-rss", "beat_fail", "warn", "RSS-сборщик: 2 источника ответили 503", 90),
    ("mcp", "journal", "info", "Claude Code записал решение в журнал «Блог на Astro»", 140),
    ("laptop-sync", "beat_ok", "info", "Синхронизация заметок: 3 файла", 200),
]

BEATS = [
    # (source, title, machine, ожидать каждые, минут назад, статус, заметка)
    ("server", "Агент сервера", "server", 300, 1, "ok", "load 0.21, диск 41 %"),
    ("server-backup", "Ежедневный бэкап", "server", 86400, 120, "ok", "дамп 18 МБ"),
    ("server-certbot", "Продление сертификатов", "server", 86400 * 7, 60 * 30, "ok", None),
    ("server-rss", "RSS-сборщик", "server", 1800, 12, "fail", "2 источника ответили 503"),
    ("home-pc", "Агент домашнего ПК", "home-pc", 300, 2, "ok", None),
    ("home-pc-media-index", "Индексация медиатеки", "home-pc", 3600, 190, "ok", None),
    ("laptop", "Агент ноутбука", "laptop", 120, 95, "ok", None),
    ("laptop-sync", "Синхронизация заметок", "laptop", 900, 98, "ok", "3 файла"),
]

JOURNAL = {
    "Домашний медиасервер": [
        ("decision", "Бэкап — restic, а не borg: нужен S3-совместимый бэкенд без своего сервера на той стороне.", 9 * 24),
        ("note", "Диски в RAID1 собраны, smartctl чистый. Дальше — Jellyfin.", 20 * 24),
    ],
    "Блог на Astro": [
        ("decision", "Статика вместо SSR: блогу не нужен сервер, а превью PR бесплатны на статическом хостинге.", 14 * 24),
    ],
}


def _at(days: float, hour: float = 0) -> datetime:
    # события календаря — в часовом поясе демо-пользователя, а не сервера (в контейнере UTC)
    d = datetime.combine(date.today(), time.min, tzinfo=ZoneInfo(os.environ.get("DEMO_TZ", "Europe/Moscow")))
    return d + timedelta(days=days, hours=hour)


def seed(session: Session) -> None:
    now = datetime.now(timezone.utc)
    today = date.today()
    fmt = {"d20": (today - timedelta(days=20)).strftime("%d.%m.%Y"),
           "d14": (today - timedelta(days=14)).strftime("%d.%m.%Y"),
           "d9": (today - timedelta(days=9)).strftime("%d.%m.%Y"),
           "d30s": (today - timedelta(days=30)).strftime("%d.%m"),
           "d6s": (today - timedelta(days=6)).strftime("%d.%m")}

    session.add(User(id=next_id(session, "users", "usr"), email="demo@example.com", name="Демо Пользователь",
                     password_hash=hash_password(os.environ.get("DEMO_PASSWORD") or "demo")))
    demo_key = os.environ.get("DEMO_API_KEY")
    if demo_key:
        session.add(ApiKey(id=next_id(session, "api_keys", "key"), name="MCP (демо)", key_hash=key_hash(demo_key),
                           prefix=demo_key[:8], role="agent"))
    session.flush()

    ids: dict[str, str] = {}
    for name, (folder, text) in ROADMAPS.items():
        p = Project(id=next_id(session, "projects", "prj"), name=name, folder=folder)
        session.add(p)
        session.flush()
        sync_stages(session, p, text.format(**fmt))
        ids[name] = p.id
    session.get(Project, ids["Ремонт велосипеда"]).status = "paused"
    for name, entries in JOURNAL.items():
        for kind, text, hours_ago in entries:
            session.add(JournalEntry(project_id=ids[name], kind=kind, text=text, author="usr-000001",
                                     created_at=now - timedelta(hours=hours_ago)))

    for title, proj, plan, due, prio, done, notes in TASKS:
        session.add(Task(id=next_id(session, "tasks", "tsk"), title=title, notes=notes,
                         project_id=ids.get(proj) if proj else None,
                         plan_date=today + timedelta(days=plan) if plan is not None else None,
                         due=today + timedelta(days=due) if due is not None else None,
                         priority=prio, status="done" if done else "open",
                         done_at=now - timedelta(hours=3) if done else None))
        session.flush()

    for title, tags, pinned, body in NOTES:
        session.add(Note(id=next_id(session, "notes", "note"), title=title, body=body, tags=tags, pinned=pinned))
        session.flush()

    for title, day, hour, dur, place, kind in EVENTS:
        start = _at(day, hour)
        session.add(CalendarEvent(id=next_id(session, "events", "evt"), title=title, starts_at=start,
                                  ends_at=start + timedelta(hours=dur) if dur else None, location=place, kind=kind))
        session.flush()

    for source, kind, level, title, minutes_ago in FEED:
        session.add(FeedEvent(source=source, kind=kind, level=level, title=title,
                              created_at=now - timedelta(minutes=minutes_ago)))
    for source, title, machine, every, minutes_ago, status, note in BEATS:
        session.add(Beat(source=source, title=title, machine=machine, expect_every=every, status=status, note=note,
                         fails=1 if status == "fail" else 0, last_at=now - timedelta(minutes=minutes_ago)))
    session.commit()


def seed_if_empty() -> None:
    with Session(engine) as session:
        if session.exec(select(User)).first():
            log.info("seed: база не пустая, пропускаю")
            return
        seed(session)
        log.info("seed: демо-данные записаны (вход demo@example.com)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_if_empty()
