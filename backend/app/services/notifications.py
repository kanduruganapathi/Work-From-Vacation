"""In-app (and optional email) notifications."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification, User

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    user: User,
    title: str,
    body: str | None = None,
    *,
    type: str = "match",
    job_id: int | None = None,
    email: bool = True,
) -> Notification:
    """Create an in-app notification and, if SMTP is configured, email it."""
    note = Notification(
        user_id=user.id, title=title, body=body, type=type, job_id=job_id
    )
    db.add(note)
    db.flush()

    if email and settings.smtp_host:
        try:
            _send_email(user.email, title, body or title)
        except Exception as exc:  # email is best-effort, never fail the flow
            logger.warning("Email notification failed: %s", exc)

    return note


def _send_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"[Work From Vacation] {subject}"
    msg["From"] = settings.smtp_from or settings.smtp_user or "noreply@workfromvacation"
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
