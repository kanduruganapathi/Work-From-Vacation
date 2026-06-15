"""Saved searches — named, re-runnable queries with optional alerts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import SavedSearch, User
from app.schemas import SavedSearchCreate, SavedSearchOut, SavedSearchUpdate

router = APIRouter(prefix="/api/saved-searches", tags=["saved-searches"])


@router.get("", response_model=list[SavedSearchOut])
def list_saved(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedSearch]:
    stmt = (
        select(SavedSearch)
        .where(SavedSearch.user_id == current_user.id)
        .order_by(SavedSearch.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.post("", response_model=SavedSearchOut, status_code=status.HTTP_201_CREATED)
def create_saved(
    payload: SavedSearchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearch:
    search = SavedSearch(
        user_id=current_user.id,
        name=payload.name,
        params=payload.params,
        alert_enabled=payload.alert_enabled,
    )
    db.add(search)
    db.commit()
    db.refresh(search)
    return search


@router.patch("/{search_id}", response_model=SavedSearchOut)
def update_saved(
    search_id: int,
    payload: SavedSearchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearch:
    search = _owned(db, current_user, search_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(search, field, value)
    db.commit()
    db.refresh(search)
    return search


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved(
    search_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    search = _owned(db, current_user, search_id)
    db.delete(search)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _owned(db: Session, user: User, search_id: int) -> SavedSearch:
    search = db.get(SavedSearch, search_id)
    if not search or search.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return search
