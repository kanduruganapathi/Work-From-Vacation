"""Job Matching Agent — scores a single job against a candidate profile.

Uses Claude with structured outputs so the result is always valid JSON we can
persist directly into the ``job_matches`` table.
"""

from __future__ import annotations

import json

from app.agents.client import MODEL, THINKING, get_client
from app.models import Job, Profile

_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {
            "type": "integer",
            "description": "Overall fit from 0 (no fit) to 100 (perfect fit).",
        },
        "summary": {
            "type": "string",
            "description": "One or two sentences explaining the score.",
        },
        "reasons": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete reasons this role fits the candidate.",
        },
        "concerns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Gaps, mismatches, or red flags to be aware of.",
        },
    },
    "required": ["score", "summary", "reasons", "concerns"],
    "additionalProperties": False,
}

_SYSTEM = (
    "You are an expert technical recruiter and career coach. You evaluate how well "
    "a specific job fits a candidate based on their skills, experience, and "
    "preferences. Be honest and calibrated: reserve scores above 85 for genuinely "
    "strong matches, and surface real concerns rather than flattering the candidate."
)


def _profile_brief(profile: Profile) -> str:
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
        },
        indent=2,
    )


def _job_brief(job: Job) -> str:
    description = (job.description or "")[:4000]
    return json.dumps(
        {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "remote": job.remote,
            "employment_type": job.employment_type.value,
            "tags": job.tags,
            "salary": job.salary_text,
            "description": description,
        },
        indent=2,
    )


def score_job(profile: Profile, job: Job) -> dict:
    """Return ``{score, summary, reasons, concerns}`` for one job."""
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        thinking=THINKING,
        system=_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": _MATCH_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    "Candidate profile:\n"
                    f"{_profile_brief(profile)}\n\n"
                    "Job posting:\n"
                    f"{_job_brief(job)}\n\n"
                    "Score how well this job fits the candidate."
                ),
            }
        ],
    )
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    data = json.loads(text)
    # Clamp the score defensively.
    data["score"] = max(0, min(100, int(data.get("score", 0))))
    return data
