"""High-level apply flow: ensure materials exist, then submit for real."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import cover_letter_agent, resume_agent
from app.agents.client import ai_enabled
from app.models import (
    Application,
    ApplicationStatus,
    Job,
    SubmissionStatus,
    User,
)
from app.services import submitter

logger = logging.getLogger(__name__)


def ensure_materials(db: Session, user: User, job: Job, application: Application) -> None:
    """Generate a tailored resume + cover letter if missing and AI is enabled."""
    if not ai_enabled() or not user.profile:
        return
    try:
        if not application.tailored_resume:
            application.tailored_resume = resume_agent.tailor_resume(user.profile, job)
        if not application.cover_letter:
            application.cover_letter = cover_letter_agent.write_cover_letter(
                user.profile, job
            )
    except Exception as exc:
        logger.warning("Material prep failed for job %s: %s", job.id, exc)


def get_or_create_application(db: Session, user: User, job: Job) -> Application:
    app = db.scalar(
        select(Application).where(
            Application.user_id == user.id, Application.job_id == job.id
        )
    )
    if not app:
        app = Application(user_id=user.id, job_id=job.id)
        db.add(app)
        db.flush()
    return app


def submit_application(
    db: Session, user: User, job: Job, *, dry_run: bool = True
) -> Application:
    """Prepare materials (if needed) and submit to the posting. Persists the
    submission outcome on the Application."""
    application = get_or_create_application(db, user, job)
    ensure_materials(db, user, job, application)

    application.submission_status = SubmissionStatus.submitting
    db.commit()

    result = asyncio.run(
        submitter.submit(user.profile, application, job, dry_run=dry_run)
    )

    application.submission_status = result.status
    application.submission_method = result.method
    application.submission_note = result.note
    application.screenshot_path = result.screenshot_path
    if result.status == SubmissionStatus.submitted:
        application.status = ApplicationStatus.applied
        application.submitted_at = submitter.now_utc()
    db.commit()
    db.refresh(application)
    return application
