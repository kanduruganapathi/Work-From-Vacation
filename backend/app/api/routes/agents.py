"""AI agent routes — the automation surface of the product."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import (
    cover_letter_agent,
    interview_agent,
    orchestrator,
    resume_agent,
    strategy_agent,
)
from app.agents.client import AgentConfigError, ai_enabled
from app.api.deps import get_current_user
from app.database import get_db
from app.models import (
    Application,
    ApplicationStatus,
    Job,
    JobMatch,
    Task,
    TaskKind,
    User,
)
from app.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    ApplicationOut,
    AutoApplyRequest,
    BatchApplyRequest,
    CoverLetterRequest,
    CoverLetterResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    JobMatchOut,
    SearchStrategyResponse,
    TailorResumeRequest,
    TailorResumeResponse,
    TaskOut,
)
from app.services import tasks

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


@router.post("/run-async", response_model=TaskOut)
def run_orchestrator_async(
    payload: AgentRunRequest,
    current_user: User = Depends(get_current_user),
) -> Task:
    """Kick off the orchestrated hunt in the background. Poll GET /api/ai/tasks/{id}."""
    _require_ai()
    _require_profile(current_user)
    return tasks.create_task(
        current_user.id,
        TaskKind.job_hunt,
        {"instruction": payload.instruction, "max_jobs": payload.max_jobs},
    )


@router.post("/score-new", response_model=TaskOut)
def score_new(
    current_user: User = Depends(get_current_user),
) -> Task:
    """Background-score the user's newest unscored jobs and raise match alerts."""
    _require_ai()
    _require_profile(current_user)
    return tasks.create_task(current_user.id, TaskKind.auto_score, {})


@router.post("/batch-apply", response_model=TaskOut)
def batch_apply(
    payload: BatchApplyRequest,
    current_user: User = Depends(get_current_user),
) -> Task:
    """Background auto-apply to the user's top matches above a score threshold."""
    _require_ai()
    _require_profile(current_user)
    return tasks.create_task(
        current_user.id,
        TaskKind.batch_apply,
        {"min_score": payload.min_score, "limit": payload.limit},
    )


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    task = db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/interview-prep", response_model=InterviewPrepResponse)
def interview_prep(
    payload: InterviewPrepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewPrepResponse:
    _require_ai()
    _require_profile(current_user)
    job = _get_job(db, payload.job_id)
    data = interview_agent.prepare(current_user.profile, job)
    return InterviewPrepResponse(**data)


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
