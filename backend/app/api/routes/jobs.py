"""Job feed + aggregation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EmploymentType, Job
from app.schemas import (
    JobFacets,
    JobOut,
    JobSearchResult,
    RefreshResult,
    SubmitabilityOut,
)
from app.services import aggregator, search, submitter
from app.services.sample_data import sample_jobs

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


@router.get("/search", response_model=JobSearchResult)
def search_jobs(
    q: str | None = Query(default=None, description="Multi-term keyword search"),
    employment_type: EmploymentType | None = None,
    remote: bool | None = None,
    source: str | None = None,
    tag: str | None = Query(default=None, description="Match a single tag/skill"),
    location: str | None = Query(default=None, description="Match a location substring"),
    company_type: str | None = Query(
        default=None, description="product | startup | mnc | service | other"
    ),
    company_tier: str | None = Query(default=None, description="tier1 | tier2 | tier3"),
    posted_within_days: int | None = Query(default=None, ge=1, le=365),
    sort: str = Query(default="recent", pattern="^(recent|relevance)$"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> JobSearchResult:
    """Rich job search with multi-term matching, filters, sorting, and facet counts."""
    total, items, facets = search.search_jobs(
        db,
        q=q,
        employment_type=employment_type,
        remote=remote,
        source=source,
        tag=tag,
        location=location,
        company_type=company_type,
        company_tier=company_tier,
        posted_within_days=posted_within_days,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return JobSearchResult(
        total=total,
        items=[JobOut.model_validate(j) for j in items],
        facets=JobFacets(**facets),
    )


@router.get("/{job_id}/submittability", response_model=SubmitabilityOut)
def job_submittability(job_id: int, db: Session = Depends(get_db)) -> SubmitabilityOut:
    """How this posting can be applied to (auto vs manual)."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    method = submitter.detect_ats(job.url)
    return SubmitabilityOut(
        method=method, auto_submittable=submitter.can_auto_submit(job.url)
    )


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


@router.post("/seed", response_model=RefreshResult)
def seed_demo_jobs(db: Session = Depends(get_db)) -> RefreshResult:
    """Load curated sample jobs.

    Handy for demos and offline development when live sources are unreachable.
    Idempotent — re-running only adds jobs not already present.
    """
    jobs = sample_jobs()
    inserted, per_source = aggregator.upsert_jobs(db, jobs)
    return RefreshResult(fetched=len(jobs), inserted=inserted, sources=per_source)
