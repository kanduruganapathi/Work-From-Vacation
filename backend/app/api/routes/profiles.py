"""Candidate profile routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Profile, User
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileOut | None)
def get_profile(current_user: User = Depends(get_current_user)) -> Profile | None:
    return current_user.profile


@router.put("", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = current_user.profile
    if profile is None:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
