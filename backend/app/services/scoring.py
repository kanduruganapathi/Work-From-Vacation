"""Reusable AI scoring + batch-apply routines.

Shared by the synchronous API routes, the async task runner, and the scheduler.
Each accepts an optional ``progress`` callback ``(pct: int, msg: str) -> None``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents import cover_letter_agent, resume_agent
from app.agents.matching_agent import score_job
from app.config import settings
from app.models import Application, ApplicationStatus, Job, JobMatch, User
from app.services.notifications import create_notification

logger = logging.getLogger(__name__)

Progress = Callable[[int, str], None]


def _noop(pct: int, msg: str) -> None:  # default progress sink
    pass


def unscored_jobs(db: Session, user: User, limit: int) -> list[Job]:
    """Most recent jobs this user has no match for yet."""
    scored_ids = select(JobMatch.job_id).where(JobMatch.user_id == user.id)
    stmt = (
        select(Job)
        .where(Job.id.not_in(scored_ids))
        .order_by(Job.fetched_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def score_new_jobs(
    db: Session,
    user: User,
    limit: int | None = None,
    progress: Progress = _noop,
) -> list[JobMatch]:
    """Score the user's unscored jobs, persist matches, and raise alerts for
    high-fit roles. Returns the new matches."""
    if not user.profile:
        return []
    limit = limit or settings.auto_score_limit
    jobs = unscored_jobs(db, user, limit)
    matches: list[JobMatch] = []

    for i, job in enumerate(jobs):
        progress(
            int(100 * i / max(len(jobs), 1)),
            f"Scoring {i + 1}/{len(jobs)}: {job.title}",
        )
        try:
            result = score_job(user.profile, job)
        except Exception as exc:
            logger.warning("Scoring failed for job %s: %s", job.id, exc)
            continue

        match = JobMatch(
            user_id=user.id,
            job_id=job.id,
            score=result["score"],
            summary=result.get("summary"),
            reasons=result.get("reasons", []),
            concerns=result.get("concerns", []),
        )
        db.add(match)
        matches.append(match)

        if result["score"] >= settings.alert_match_threshold:
            create_notification(
                db,
                user,
                title=f"New {int(result['score'])}% match: {job.title}",
                body=result.get("summary"),
                type="match",
                job_id=job.id,
            )

    db.commit()
    progress(100, f"Scored {len(matches)} new jobs.")
    return matches


def batch_auto_apply(
    db: Session,
    user: User,
    min_score: int = 80,
    limit: int = 5,
    progress: Progress = _noop,
) -> list[Application]:
    """Auto-apply (tailor resume + cover letter, log application) to the user's
    top matches above ``min_score`` that aren't already tracked."""
    if not user.profile:
        return []

    applied_job_ids = select(Application.job_id).where(
        Application.user_id == user.id
    )
    stmt = (
        select(JobMatch)
        .where(
            JobMatch.user_id == user.id,
            JobMatch.score >= min_score,
            JobMatch.job_id.not_in(applied_job_ids),
        )
        .order_by(JobMatch.score.desc())
        .limit(limit)
    )
    top = list(db.scalars(stmt).all())
    created: list[Application] = []

    for i, match in enumerate(top):
        job = db.get(Job, match.job_id)
        if not job:
            continue
        progress(
            int(100 * i / max(len(top), 1)),
            f"Applying {i + 1}/{len(top)}: {job.title}",
        )
        try:
            resume = resume_agent.tailor_resume(user.profile, job)
            letter = cover_letter_agent.write_cover_letter(user.profile, job)
        except Exception as exc:
            logger.warning("Auto-apply failed for job %s: %s", job.id, exc)
            continue

        application = Application(
            user_id=user.id,
            job_id=job.id,
            status=ApplicationStatus.applied,
            tailored_resume=resume,
            cover_letter=letter,
        )
        db.add(application)
        created.append(application)
        create_notification(
            db,
            user,
            title=f"Auto-applied: {job.title}",
            body=f"Tailored resume and cover letter prepared for {job.company or 'the role'}.",
            type="applied",
            job_id=job.id,
            email=False,
        )

    db.commit()
    progress(100, f"Auto-applied to {len(created)} roles.")
    return created


def applications_today(db: Session, user: User) -> int:
    """How many applications this user has created in the last 24h."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return (
        db.scalar(
            select(func.count(Application.id)).where(
                Application.user_id == user.id,
                Application.created_at >= since,
            )
        )
        or 0
    )


def run_autopilot(db: Session, user: User) -> list[Application]:
    """Auto-apply to new high-fit matches per the user's autopilot settings,
    respecting the daily cap. Returns the applications created (possibly none).
    """
    profile = user.profile
    if not profile or not profile.autopilot_enabled:
        return []

    remaining = profile.autopilot_daily_limit - applications_today(db, user)
    if remaining <= 0:
        logger.info("Autopilot: daily limit reached for user %s", user.id)
        return []

    return batch_auto_apply(
        db,
        user,
        min_score=profile.autopilot_min_score,
        limit=remaining,
    )
