"""Application tracking routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Application, Job, User
from app.schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Application]:
    stmt = (
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    if not db.get(Job, payload.job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.scalar(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.job_id == payload.job_id,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already tracking this job")

    application = Application(
        user_id=current_user.id,
        job_id=payload.job_id,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    application = _get_owned(db, current_user, application_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    application = _get_owned(db, current_user, application_id)
    db.delete(application)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_owned(db: Session, user: User, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if not application or application.user_id != user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application
