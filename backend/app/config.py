import logging
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# В проде секреты приходят файлами (compose secrets → /run/secrets), а не переменными окружения:
# переменные видны в `docker inspect` и `compose config`. NAME_FILE кладём в NAME до чтения настроек.
# Переменная NAME главнее файла — удобно локально.
SECRETS = ("PG_PASSWORD", "JWT_SECRET")


def secrets_from_files() -> None:
    for name in SECRETS:
        path = os.environ.get(f"{name}_FILE")
        if not path or os.environ.get(name):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                os.environ[name] = f.read().strip()
        except OSError as e:
            logging.getLogger("crm.config").warning("secret %s: file %s not read (%s)", name, path, e)


secrets_from_files()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pg_host: str = "postgres"
    pg_port: int = 5432
    pg_user: str = "crm"
    pg_password: str = ""
    pg_db: str = "crm"

    jwt_secret: str = ""
    jwt_ttl_hours: int = 12
    cookie_secure: bool = False

    # /api/docs и openapi.json — только при API_DOCS=1 (локально, для генерации типов SPA)
    api_docs: bool = False
    # заполнить базу демонстрационными данными при старте, если она пустая
    seed_demo: bool = False

    @property
    def dsn(self) -> str:
        return (f"postgresql+psycopg://{self.pg_user}:{self.pg_password}"
                f"@{self.pg_host}:{self.pg_port}/{self.pg_db}")


settings = Settings()
