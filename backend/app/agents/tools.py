"""Tools the orchestrator agent can call.

Each tool is a JSON-schema definition plus a Python executor. The executors are
bound to a DB session and a user via :class:`ToolContext`, so the agent can search
the live job database and score jobs against the real profile.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.matching_agent import score_job
from app.models import Job, JobMatch, Profile, User

# ── Tool schemas (sent to Claude) ───────────────────────────────────────────
TOOLS = [
    {
        "name": "get_candidate_profile",
        "description": (
            "Get the current candidate's profile: skills, desired titles, "
            "employment types, locations, and preferences. Call this first to "
            "understand who you are searching for."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_jobs",
        "description": (
            "Search the aggregated job database. Returns matching jobs with their "
            "id, title, company, employment type, and a short description snippet. "
            "Use keywords from the candidate's skills and desired titles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Space-separated keywords to match in title/company/tags.",
                },
                "employment_type": {
                    "type": "string",
                    "enum": [
                        "full_time",
                        "contract",
                        "freelance",
                        "part_time",
                        "internship",
                        "any",
                    ],
                },
                "remote_only": {"type": "boolean"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 30},
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "score_jobs",
        "description": (
            "Score a list of job ids against the candidate profile. Persists the "
            "match scores and returns each job's fit score (0-100) with reasons. "
            "Call this on the most promising jobs from search_jobs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "job_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Job ids to score.",
                }
            },
            "required": ["job_ids"],
        },
    },
]


@dataclass
class ToolContext:
    db: Session
    user: User

    @property
    def profile(self) -> Profile | None:
        return self.user.profile


def _require_profile(ctx: ToolContext) -> Profile:
    if not ctx.profile:
        raise ValueError("Candidate has no profile. Ask them to create one first.")
    return ctx.profile


def execute_tool(ctx: ToolContext, name: str, payload: dict) -> str:
    """Dispatch a tool call and return a JSON string result for the model."""
    if name == "get_candidate_profile":
        return _get_candidate_profile(ctx)
    if name == "search_jobs":
        return _search_jobs(ctx, payload)
    if name == "score_jobs":
        return _score_jobs(ctx, payload)
    return json.dumps({"error": f"Unknown tool: {name}"})


def _get_candidate_profile(ctx: ToolContext) -> str:
    profile = _require_profile(ctx)
    return json.dumps(
        {
            "headline": profile.headline,
            "summary": profile.summary,
            "skills": profile.skills,
            "desired_titles": profile.desired_titles,
            "desired_employment_types": profile.desired_employment_types,
            "locations": profile.locations,
            "remote_only": profile.remote_only,
            "min_salary": profile.min_salary,
            "years_experience": profile.years_experience,
        }
    )


def _search_jobs(ctx: ToolContext, payload: dict) -> str:
    keywords = (payload.get("keywords") or "").strip()
    terms = [t for t in keywords.lower().split() if t]
    employment_type = payload.get("employment_type", "any")
    remote_only = payload.get("remote_only")
    limit = int(payload.get("limit", 15))

    stmt = select(Job)
    if remote_only:
        stmt = stmt.where(Job.remote.is_(True))
    if employment_type and employment_type != "any":
        stmt = stmt.where(Job.employment_type == employment_type)
    stmt = stmt.order_by(Job.fetched_at.desc()).limit(300)

    jobs = ctx.db.scalars(stmt).all()

    def relevant(job: Job) -> bool:
        if not terms:
            return True
        haystack = " ".join(
            [job.title, job.company or "", " ".join(job.tags or [])]
        ).lower()
        return any(term in haystack for term in terms)

    results = [
        {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "employment_type": job.employment_type.value,
            "remote": job.remote,
            "location": job.location,
            "snippet": (job.description or "")[:240],
        }
        for job in jobs
        if relevant(job)
    ][:limit]

    return json.dumps({"count": len(results), "jobs": results})


def _score_jobs(ctx: ToolContext, payload: dict) -> str:
    profile = _require_profile(ctx)
    job_ids = payload.get("job_ids", [])[:15]  # cap to bound cost
    scored = []

    for job_id in job_ids:
        job = ctx.db.get(Job, job_id)
        if not job:
            continue
        result = score_job(profile, job)
        _persist_match(ctx, job, result)
        scored.append(
            {
                "job_id": job.id,
                "title": job.title,
                "score": result["score"],
                "summary": result["summary"],
            }
        )

    ctx.db.commit()
    scored.sort(key=lambda x: x["score"], reverse=True)
    return json.dumps({"scored": scored})


def _persist_match(ctx: ToolContext, job: Job, result: dict) -> None:
    match = ctx.db.scalar(
        select(JobMatch).where(
            JobMatch.user_id == ctx.user.id, JobMatch.job_id == job.id
        )
    )
    if not match:
        match = JobMatch(user_id=ctx.user.id, job_id=job.id)
        ctx.db.add(match)
    match.score = result["score"]
    match.summary = result.get("summary")
    match.reasons = result.get("reasons", [])
    match.concerns = result.get("concerns", [])
