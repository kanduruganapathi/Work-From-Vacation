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
