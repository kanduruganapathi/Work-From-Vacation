"""Job feed + aggregation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EmploymentType, Job
from app.schemas import JobOut, RefreshResult
from app.services import aggregator

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(
    q: str | None = Query(default=None, description="Free-text title/company search"),
    employment_type: EmploymentType | None = None,
    remote: bool | None = None,
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Job]:
    stmt = select(Job)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            Job.title.ilike(like) | Job.company.ilike(like)
        )
    if employment_type:
        stmt = stmt.where(Job.employment_type == employment_type)
    if remote is not None:
        stmt = stmt.where(Job.remote.is_(remote))
    if source:
        stmt = stmt.where(Job.source == source)
    stmt = stmt.order_by(Job.fetched_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/refresh", response_model=RefreshResult)
async def refresh(
    q: str | None = Query(default=None, description="Optional keyword to focus the pull"),
    limit_per_source: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> RefreshResult:
    """Pull fresh jobs from all active sources and store new ones."""
    fetched, inserted, per_source = await aggregator.refresh_jobs(
        db, query=q, limit_per_source=limit_per_source
    )
    return RefreshResult(fetched=fetched, inserted=inserted, sources=per_source)
