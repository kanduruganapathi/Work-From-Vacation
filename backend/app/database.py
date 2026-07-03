"""Database engine, session, and base model."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite needs a special flag for use across FastAPI's threadpool.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after initial release. For SQLite dev databases (which have no
# migration tooling here) we add any missing ones on startup so existing data
# survives. In production, use Alembic instead.
_ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("profiles", "autopilot_enabled", "BOOLEAN DEFAULT 0"),
    ("profiles", "autopilot_min_score", "INTEGER DEFAULT 85"),
    ("profiles", "autopilot_daily_limit", "INTEGER DEFAULT 5"),
    ("jobs", "company_type", "VARCHAR(32)"),
    ("jobs", "company_tier", "VARCHAR(16)"),
    ("profiles", "full_name", "VARCHAR(255)"),
    ("profiles", "phone", "VARCHAR(64)"),
    ("profiles", "linkedin_url", "VARCHAR(512)"),
    ("profiles", "github_url", "VARCHAR(512)"),
    ("profiles", "portfolio_url", "VARCHAR(512)"),
    ("profiles", "current_location", "VARCHAR(255)"),
    ("profiles", "autopilot_auto_submit", "BOOLEAN DEFAULT 0"),
    ("applications", "submission_status", "VARCHAR(16) DEFAULT 'not_submitted'"),
    ("applications", "submission_method", "VARCHAR(32)"),
    ("applications", "submission_note", "TEXT"),
    ("applications", "screenshot_path", "VARCHAR(512)"),
    ("applications", "submitted_at", "DATETIME"),
]


def _ensure_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import text

    with engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            cols = {
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table})"))
            }
            if column not in cols:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                )


def init_db() -> None:
    """Create all tables. Called on startup; use migrations in production."""
    # Import models so they register on the metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    _backfill_company_classification()


def _backfill_company_classification() -> None:
    """Classify any jobs that don't yet have a company_type (e.g. rows that
    predate the columns)."""
    from app.models import Job
    from app.services.company_classifier import classify

    db = SessionLocal()
    try:
        from sqlalchemy import select

        jobs = db.scalars(select(Job).where(Job.company_type.is_(None))).all()
        for job in jobs:
            job.company_type, job.company_tier = classify(job.company)
        if jobs:
            db.commit()
    finally:
        db.close()
