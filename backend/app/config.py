from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8-sig", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///var/gymos.sqlite3"
    secret_key: str
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_pool_size: int = 10
    access_minutes: int = 10
    refresh_days: int = 7
    cookie_secure: bool = False
    allow_registration: bool = True
    upload_dir: Path = Path("var/uploads")
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "gymos@example.com"
    smtp_starttls: bool = True
    auth_rate_limit: int = 15

    @model_validator(mode="after")
    def validate_security(self):
        if len(self.secret_key) < 32 or self.secret_key.startswith("CHANGE_"):
            raise ValueError("SECRET_KEY must be a random secret of at least 32 characters. Run scripts/configure.py.")
        url = make_url(self.database_url)
        if url.drivername in {"sqlite", "sqlite+pysqlite"}:
            if not url.database or url.database == ":memory:" or url.query:
                raise ValueError("SQLite requires a persistent local file, for example sqlite:///var/gymos.sqlite3")
            path = Path(url.database)
            if not path.is_absolute():
                path = BACKEND_DIR / path
            self.database_url = url.set(database=str(path.resolve())).render_as_string(hide_password=False)
        elif url.drivername != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use sqlite:/// or postgresql+psycopg://")
        if not self.upload_dir.is_absolute():
            self.upload_dir = (BACKEND_DIR / self.upload_dir).resolve()
        if self.app_env == "production" and (
            not self.cookie_secure or not self.frontend_url.startswith("https://") or self.allow_registration
        ):
            raise ValueError("Production requires HTTPS, COOKIE_SECURE=true and ALLOW_REGISTRATION=false")
        return self

    @property
    def origins(self):
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]

    @property
    def database_backend(self):
        return make_url(self.database_url).get_backend_name()


@lru_cache
def settings():
    try:
        return Settings()
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, item["loc"])) or "configuration" for item in exc.errors())
        raise RuntimeError(
            f"GymOS configuration is missing or invalid ({fields}). "
            "From the project root run start.bat, or run: py -3.12 scripts/configure.py --database sqlite. "
            f"Configuration file: {BACKEND_DIR / '.env'}"
        ) from None
