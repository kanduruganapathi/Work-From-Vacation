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

    # Default query/location for keyed aggregators (Adzuna/Jooble/Careerjet).
    jobs_default_query: str = "software engineer"
    jobs_default_location: str = "India"

    # Adzuna (free key) — covers India when adzuna_country="in".
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    adzuna_country: str = "in"

    # Jooble (free key) — worldwide aggregator, strong India coverage.
    jooble_api_key: str | None = None

    # Careerjet (free affiliate id) — India locale en_IN.
    careerjet_affid: str | None = None
    careerjet_locale: str = "en_IN"

    # Per-company ATS boards to aggregate (Greenhouse + Lever slugs).
    # These are public boards; unreachable slugs are skipped gracefully.
    ats_greenhouse_slugs: list[str] = [
        "stripe", "airbnb", "dropbox", "coinbase", "databricks", "figma",
        "gitlab", "reddit", "robinhood", "brex", "ramp", "plaid", "discord",
        "instacart", "doordash", "lyft", "pinterest", "asana", "twitch",
        "snyk", "elastic", "gusto", "benchling", "samsara", "affirm", "chime",
        "nerdwallet", "sofi", "opendoor", "roblox", "unity", "scaleai",
        "retool", "webflow", "mixpanel", "amplitude", "anduril", "rippling",
        "cockroachlabs", "hashicorp", "checkr", "flexport",
    ]
    ats_lever_slugs: list[str] = [
        "voiceflow", "kraken", "leadiq", "huma", "mux", "blend", "ironclad",
        "veriff", "spoton",
    ]
    # Extra RSS/Atom remote job feeds.
    extra_rss_feeds: list[str] = [
        "https://weworkremotely.com/remote-jobs.rss",
        "https://www.workingnomads.com/jobsrss",
        "https://remotive.com/remote-jobs/feed",
        "https://jobspresso.co/remote-work/feed/",
    ]

    # Background scheduler (periodic refresh + auto-scoring + alerts)
    scheduler_enabled: bool = False
    scheduler_refresh_minutes: int = 60
    # New matches at or above this score raise an alert.
    alert_match_threshold: int = 75
    # Per-run cap on jobs scored per user (cost control).
    auto_score_limit: int = 10

    # Where email-based applications are sent (for testing, your own address).
    application_email_to: str | None = None

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
