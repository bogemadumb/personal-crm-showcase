import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .config import settings
from .v2 import v2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.seed_demo:
        from .seed import seed_if_empty
        await run_in_threadpool(seed_if_empty)
    yield


app = FastAPI(title="Personal CRM — showcase", lifespan=lifespan,
              docs_url="/api/docs" if settings.api_docs else None,
              openapi_url="/api/openapi.json" if settings.api_docs else None)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # наружу — короткий ответ, подробность — в лог; трассировка клиенту не уходит
    logging.getLogger("crm").exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "внутренняя ошибка"}, status_code=500)


api = APIRouter(prefix="/api")
api.include_router(v2)
app.include_router(api)
