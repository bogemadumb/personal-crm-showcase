from alembic import context
from sqlalchemy import create_engine, text
from sqlmodel import SQLModel

from app import models  # noqa: F401  — регистрирует таблицы в metadata
from app.config import settings

target_metadata = SQLModel.metadata


def run() -> None:
    engine = create_engine(settings.dsn)
    with engine.connect() as conn:
        # схема для таблицы версий должна существовать до первой миграции
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS crm"))
        conn.commit()
        context.configure(connection=conn, target_metadata=target_metadata, include_schemas=True,
                          version_table_schema="crm")
        with context.begin_transaction():
            context.run_migrations()


run()
