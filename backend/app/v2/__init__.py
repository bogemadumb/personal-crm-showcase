"""JSON-слой для SPA: /api/v2/*. Только JSON и схемы Pydantic — OpenAPI потом превращается в типы фронта.

Модули подключаются по именам: каждый экспортирует `router = APIRouter()`. Нет модуля — предупреждение
в лог, приложение поднимается без него. В приватной версии так подключено ~90 модулей, и их можно
собирать параллельно, не трогая общий файл маршрутов.
"""
import importlib
import logging

from fastapi import APIRouter

log = logging.getLogger("crm.v2")

v2 = APIRouter(prefix="/v2")

MODULES = ("health", "auth", "today", "tasks", "projects", "notes", "calendar", "feed", "search")

for name in MODULES:
    try:
        module = importlib.import_module(f".{name}", __package__)
    except ModuleNotFoundError as e:
        if e.name and e.name.endswith(name):
            log.warning("v2: module %s not found, skipping", name)
            continue
        raise
    router = getattr(module, "router", None)
    if router is not None:
        v2.include_router(router)
