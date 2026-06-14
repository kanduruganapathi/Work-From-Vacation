"""Aggregation service: fetch from sources, dedupe, and upsert into the DB."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job
from app.sources import ALL_SOURCES, JobSource, RawJob

logger = logging.getLogger(__name__)


async def _fetch_source(source: JobSource, query: str | None, limit: int) -> list[RawJob]:
    try:
        return await source.fetch(query=query, limit=limit)
    except Exception as exc:  # one bad source shouldn't sink the whole refresh
        logger.warning("Source %s failed: %s", source.name, exc)
        return []


async def fetch_all(
    query: str | None = None,
    limit_per_source: int = 100,
    sources: list[JobSource] | None = None,
) -> list[RawJob]:
    """Fetch from all sources concurrently and return a flat list of raw jobs."""
    sources = sources or ALL_SOURCES
    results = await asyncio.gather(
        *(_fetch_source(s, query, limit_per_source) for s in sources)
    )
    return [job for batch in results for job in batch]


def upsert_jobs(db: Session, raw_jobs: list[RawJob]) -> tuple[int, dict[str, int]]:
    """Insert new jobs, skipping ones already stored (by source + external_id).

    Returns ``(inserted_count, per_source_inserted)``.
    """
    inserted = 0
    per_source: dict[str, int] = {}

    for raw in raw_jobs:
        source = raw.get("source")
        external_id = raw.get("external_id")
        if not source or not external_id:
            continue

        exists = db.scalar(
            select(Job.id).where(
                Job.source == source, Job.external_id == external_id
            )
        )
        if exists:
            continue

        db.add(Job(**raw))
        inserted += 1
        per_source[source] = per_source.get(source, 0) + 1

    db.commit()
    return inserted, per_source


async def refresh_jobs(
    db: Session, query: str | None = None, limit_per_source: int = 100
) -> tuple[int, int, dict[str, int]]:
    """End-to-end refresh. Returns ``(fetched, inserted, per_source)``."""
    raw_jobs = await fetch_all(query=query, limit_per_source=limit_per_source)
    inserted, per_source = upsert_jobs(db, raw_jobs)
    logger.info("Refresh: fetched=%d inserted=%d", len(raw_jobs), inserted)
    return len(raw_jobs), inserted, per_source
