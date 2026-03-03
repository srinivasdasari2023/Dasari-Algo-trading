"""Application settings from environment. No hardcoded secrets."""
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from project root (parent of backend/) or from backend/ so it works either way
_backend_dir = Path(__file__).resolve().parent.parent.parent  # backend/
_project_root = _backend_dir.parent
_env_files = [_project_root / ".env", _backend_dir / ".env"]
_env_file = [str(p) for p in _env_files if p.exists()] or [".env"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_NAME: str = "Dasari's Algo Trading terminal"  # Used in email notifications and API title
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/capitalguard"
    DATABASE_POOL_SIZE: int = 5

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_LOCK_PREFIX: str = "capitalguard:lock"

    UPSTOX_API_BASE_URL: str = "https://api.upstox.com/v2"
    # Must match exactly what you set in Upstox developer dashboard (no trailing slash)
    UPSTOX_OAUTH_REDIRECT_URI: str = "http://localhost:3000/auth/callback"

    @field_validator("UPSTOX_OAUTH_REDIRECT_URI", mode="after")
    @classmethod
    def strip_redirect_uri_trailing_slash(cls, v: str) -> str:
        """Ensure no trailing slash so OAuth exchange matches Upstox console."""
        return v.rstrip("/") if v else v
    UPSTOX_CLIENT_ID: str = ""
    UPSTOX_CLIENT_SECRET: str = ""

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    MAX_TRADES_PER_DAY: int = 3
    SQUARE_OFF_TIME: str = "15:15"
    ENTRY_CUTOFF_TIME: str = "12:30"

    FRONTEND_URL: str = "http://localhost:3000"

    # Email (Gmail) – notifications for login, signals, orders, SL/TSL
    # In .env: set MAIL_FROM (or GMAIL_USER), MAIL_TO (or GMAIL_TO), and one of MAIL_APP_PASSWORD, MAIL_PASSWORD, PASSWORDKEY
    MAIL_ENABLED: bool = False
    MAIL_FROM: str = ""
    MAIL_TO: str = ""
    GMAIL_USER: str = ""
    GMAIL_TO: str = ""
    MAIL_APP_PASSWORD: str = ""
    MAIL_PASSWORD: str = ""
    PASSWORDKEY: str = ""

    @property
    def CORS_ORIGINS(self) -> list[str]:
        origins = [
            self.FRONTEND_URL.rstrip("/") if self.FRONTEND_URL else "http://localhost:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        return list(dict.fromkeys(o for o in origins if o))


settings = Settings()
