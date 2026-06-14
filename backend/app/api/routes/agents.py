"""AI agent routes — the automation surface of the product."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import (
    cover_letter_agent,
    orchestrator,
    resume_agent,
    strategy_agent,
)
from app.agents.client import AgentConfigError, ai_enabled
from app.api.deps import get_current_user
from app.database import get_db
from app.models import Application, ApplicationStatus, Job, JobMatch, User
from app.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    ApplicationOut,
    AutoApplyRequest,
    CoverLetterRequest,
    CoverLetterResponse,
    JobMatchOut,
    SearchStrategyResponse,
    TailorResumeRequest,
    TailorResumeResponse,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _require_ai() -> None:
    if not ai_enabled():
        raise HTTPException(
            status_code=503,
            detail="AI features are disabled. Set ANTHROPIC_API_KEY on the server.",
        )


def _require_profile(user: User) -> None:
    if not user.profile:
        raise HTTPException(
            status_code=400,
            detail="Create your candidate profile before using the AI agents.",
        )


def _get_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/status")
def ai_status() -> dict:
    return {"enabled": ai_enabled()}


@router.post("/run", response_model=AgentRunResponse)
def run_orchestrator(
    payload: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    """Run the orchestrator: search, score, and summarize the best opportunities."""
    _require_ai()
    _require_profile(current_user)
    try:
        summary = orchestrator.run_job_hunt(
            db, current_user, payload.instruction, max_jobs=payload.max_jobs
        )
    except AgentConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    matches = db.scalars(
        select(JobMatch)
        .where(JobMatch.user_id == current_user.id)
        .order_by(JobMatch.score.desc())
        .limit(payload.max_jobs)
    ).all()
    return AgentRunResponse(
        summary=summary,
        matches=[JobMatchOut.model_validate(m) for m in matches],
    )


@router.get("/matches", response_model=list[JobMatchOut])
def list_matches(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobMatch]:
    return list(
        db.scalars(
            select(JobMatch)
            .where(JobMatch.user_id == current_user.id)
            .order_by(JobMatch.score.desc())
            .limit(limit)
        ).all()
    )


@router.post("/tailor-resume", response_model=TailorResumeResponse)
def tailor_resume(
    payload: TailorResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TailorResumeResponse:
    _require_ai()
    _require_profile(current_user)
    job = _get_job(db, payload.job_id)
    try:
        text = resume_agent.tailor_resume(current_user.profile, job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TailorResumeResponse(tailored_resume=text)


@router.post("/cover-letter", response_model=CoverLetterResponse)
def cover_letter(
    payload: CoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverLetterResponse:
    _require_ai()
    _require_profile(current_user)
    job = _get_job(db, payload.job_id)
    try:
        text = cover_letter_agent.write_cover_letter(
            current_user.profile, job, tone=payload.tone
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CoverLetterResponse(cover_letter=text)


@router.post("/auto-apply", response_model=ApplicationOut)
def auto_apply(
    payload: AutoApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    """Automate the application: the AI tailors a resume and drafts a cover
    letter for the job, then logs an application marked as 'applied' with those
    materials attached. The user can review/edit before sending externally.
    """
    _require_ai()
    _require_profile(current_user)
    job = _get_job(db, payload.job_id)

    try:
        resume = resume_agent.tailor_resume(current_user.profile, job)
        letter = cover_letter_agent.write_cover_letter(
            current_user.profile, job, tone=payload.tone
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    application = db.scalar(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.job_id == job.id,
        )
    )
    if not application:
        application = Application(user_id=current_user.id, job_id=job.id)
        db.add(application)
    application.tailored_resume = resume
    application.cover_letter = letter
    application.status = ApplicationStatus.applied
    db.commit()
    db.refresh(application)
    return application


@router.post("/strategy", response_model=SearchStrategyResponse)
def strategy(
    current_user: User = Depends(get_current_user),
) -> SearchStrategyResponse:
    _require_ai()
    _require_profile(current_user)
    data = strategy_agent.suggest_strategy(current_user.profile)
    return SearchStrategyResponse(**data)
