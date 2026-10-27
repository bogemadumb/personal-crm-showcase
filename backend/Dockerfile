FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY tests ./tests
# чистые функции проверяются при сборке: провал тестов — образ не собирается, старый контейнер работает дальше
RUN python -m pytest -q tests/test_roadmap.py tests/test_pulse.py

ARG BUILD_TAG=""
ENV BUILD_TAG=$BUILD_TAG

USER app
EXPOSE 8000

# --limit-concurrency: сверх 200 одновременных — 503 сразу, а не очередь в памяти;
# --timeout-graceful-shutdown: открытые соединения не держат остановку при выкладке дольше 5 с
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --limit-concurrency 200 --timeout-graceful-shutdown 5"]
