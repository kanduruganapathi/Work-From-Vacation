"""Application configuration, loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_name: str = "Work From Vacation"
    environment: str = "development"

    # Database
    database_url: str = "sqlite:///./work_from_vacation.db"

    # Auth
    secret_key: str = "change-me-to-a-long-random-secret"
    access_token_expire_minutes: int = 60 * 24 * 7  # one week

    # AI / Anthropic
    anthropic_api_key: str | None = None
    ai_model: str = "claude-opus-4-8"

    # Optional source credentials
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None

    # Background scheduler (periodic refresh + auto-scoring + alerts)
    scheduler_enabled: bool = False
    scheduler_refresh_minutes: int = 60
    # New matches at or above this score raise an alert.
    alert_match_threshold: int = 75
    # Per-run cap on jobs scored per user (cost control).
    auto_score_limit: int = 10

    # Optional SMTP for email alerts. If unset, alerts are in-app only.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
