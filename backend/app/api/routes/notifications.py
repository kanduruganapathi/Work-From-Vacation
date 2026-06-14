"""In-app notification routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Notification, User
from app.schemas import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(100)
    return list(db.scalars(stmt).all())


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    note = db.get(Notification, notification_id)
    if not note or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    note.read = True
    db.commit()
    db.refresh(note)
    return note


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read.is_(False))
        .values(read=True)
    )
    db.commit()
    from fastapi import Response

    return Response(status_code=status.HTTP_204_NO_CONTENT)
