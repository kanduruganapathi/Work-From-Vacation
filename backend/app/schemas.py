"""Pydantic schemas for request/response bodies."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ApplicationStatus, EmploymentType, TaskKind, TaskStatus


# ── Auth ──────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str | None = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Profile ───────────────────────────────────────────────────────────────
class ProfileIn(BaseModel):
    headline: str | None = None
    summary: str | None = None
    resume_text: str | None = None
    skills: list[str] = []
    desired_titles: list[str] = []
    desired_employment_types: list[str] = []
    locations: list[str] = []
    remote_only: bool = True
    min_salary: int | None = None
    years_experience: int | None = None
    autopilot_enabled: bool = False
    autopilot_min_score: int = Field(default=85, ge=0, le=100)
    autopilot_daily_limit: int = Field(default=5, ge=1, le=50)


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    updated_at: datetime


# ── Jobs ──────────────────────────────────────────────────────────────────
class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    title: str
    company: str | None = None
    company_type: str | None = None
    company_tier: str | None = None
    location: str | None = None
    remote: bool
    employment_type: EmploymentType
    category: str | None = None
    tags: list[str] = []
    description: str | None = None
    url: str | None = None
    salary_text: str | None = None
    posted_at: datetime | None = None
    fetched_at: datetime


class RefreshResult(BaseModel):
    fetched: int
    inserted: int
    sources: dict[str, int]


class JobFacets(BaseModel):
    employment_types: dict[str, int] = {}
    sources: dict[str, int] = {}
    company_types: dict[str, int] = {}
    company_tiers: dict[str, int] = {}
    locations: dict[str, int] = {}
    remote: int = 0


class JobSearchResult(BaseModel):
    total: int
    items: list[JobOut] = []
    facets: JobFacets = JobFacets()


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    params: dict = {}
    alert_enabled: bool = True


class SavedSearchUpdate(BaseModel):
    name: str | None = None
    params: dict | None = None
    alert_enabled: bool | None = None


class SavedSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    params: dict
    alert_enabled: bool
    created_at: datetime


# ── Matching ──────────────────────────────────────────────────────────────
class JobMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    score: float
    reasons: list[str] = []
    concerns: list[str] = []
    summary: str | None = None
    created_at: datetime
    job: JobOut


class MatchRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)


# ── Applications ──────────────────────────────────────────────────────────
class ApplicationCreate(BaseModel):
    job_id: int
    status: ApplicationStatus = ApplicationStatus.saved
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    tailored_resume: str | None = None
    cover_letter: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    status: ApplicationStatus
    tailored_resume: str | None = None
    cover_letter: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    job: JobOut


# ── AI agents ─────────────────────────────────────────────────────────────
class TailorResumeRequest(BaseModel):
    job_id: int


class TailorResumeResponse(BaseModel):
    tailored_resume: str


class CoverLetterRequest(BaseModel):
    job_id: int
    tone: str = "professional"


class CoverLetterResponse(BaseModel):
    cover_letter: str


class SearchStrategyResponse(BaseModel):
    suggested_titles: list[str] = []
    suggested_keywords: list[str] = []
    suggested_sources: list[str] = []
    advice: str | None = None


class AgentRunRequest(BaseModel):
    """Free-form instruction to the orchestrator agent."""

    instruction: str = Field(
        default="Find and score the best jobs for me, then suggest how to improve my search.",
    )
    max_jobs: int = Field(default=15, ge=1, le=50)


class AgentRunResponse(BaseModel):
    summary: str
    matches: list[JobMatchOut] = []


class AutoApplyRequest(BaseModel):
    job_id: int
    tone: str = "professional"


# ── Background tasks ──────────────────────────────────────────────────────
class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: TaskKind
    status: TaskStatus
    progress: int
    message: str | None = None
    result: dict | None = None
    created_at: datetime
    updated_at: datetime


class BatchApplyRequest(BaseModel):
    min_score: int = Field(default=80, ge=0, le=100)
    limit: int = Field(default=5, ge=1, le=20)


# ── Notifications ─────────────────────────────────────────────────────────
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    body: str | None = None
    job_id: int | None = None
    read: bool
    created_at: datetime


# ── Interview prep ────────────────────────────────────────────────────────
class InterviewPrepRequest(BaseModel):
    job_id: int


class InterviewPrepResponse(BaseModel):
    likely_questions: list[str] = []
    talking_points: list[str] = []
    focus_areas: list[str] = []
    summary: str | None = None
