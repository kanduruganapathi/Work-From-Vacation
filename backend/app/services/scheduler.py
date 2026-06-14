"""Periodic background scheduler (APScheduler).

When ``SCHEDULER_ENABLED=true``, runs every ``SCHEDULER_REFRESH_MINUTES`` to:

1. Refresh jobs from all active sources.
2. If the AI is configured, score each user's new jobs and raise alerts for
   high-fit matches.

Disabled by default to avoid surprise API costs. For multi-process deployments,
run this in a single dedicated worker, not on every web process.
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.agents.client import ai_enabled
from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.services import aggregator, scoring

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_cycle() -> None:
    """One refresh + scoring pass. Exceptions are logged, never raised."""
    db = SessionLocal()
    try:
        try:
            fetched, inserted, _ = asyncio.run(aggregator.refresh_jobs(db))
            logger.info("Scheduler refresh: fetched=%d inserted=%d", fetched, inserted)
        except Exception as exc:
            logger.warning("Scheduler refresh failed: %s", exc)

        if not ai_enabled():
            return

        users = db.scalars(select(User)).all()
        for user in users:
            if not user.profile:
                continue
            try:
                matches = scoring.score_new_jobs(db, user)
                if matches:
                    logger.info(
                        "Scheduler scored %d new jobs for user %s",
                        len(matches),
                        user.id,
                    )
            except Exception as exc:
                logger.warning("Scoring failed for user %s: %s", user.id, exc)
    finally:
        db.close()


def start() -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled (set SCHEDULER_ENABLED=true to enable).")
        return
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _run_cycle,
        "interval",
        minutes=settings.scheduler_refresh_minutes,
        id="refresh_and_score",
        next_run_time=None,  # first run after one interval, not at boot
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: every %d min.", settings.scheduler_refresh_minutes
    )


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
