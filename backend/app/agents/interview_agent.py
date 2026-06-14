"""Interview Prep Agent — generates tailored prep for a specific role."""

from __future__ import annotations

import json

from app.agents.client import MODEL, THINKING, get_client
from app.models import Job, Profile

_SCHEMA = {
    "type": "object",
    "properties": {
        "likely_questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Questions the candidate is likely to be asked.",
        },
        "talking_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Strengths/experiences the candidate should highlight.",
        },
        "focus_areas": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Topics/skills to brush up on before the interview.",
        },
        "summary": {"type": "string"},
    },
    "required": ["likely_questions", "talking_points", "focus_areas", "summary"],
    "additionalProperties": False,
}

_SYSTEM = (
    "You are an interview coach. Given a job and a candidate, prepare focused, "
    "realistic interview prep: likely questions (mix of technical and behavioral), "
    "talking points drawn from the candidate's actual background, and areas to "
    "study. Be specific to this role, not generic."
)


def prepare(profile: Profile, job: Job) -> dict:
    client = get_client()
    background = profile.resume_text or profile.summary or profile.headline or ""
    response = client.messages.create(
        model=MODEL,
        max_tokens=2500,
        thinking=THINKING,
        system=_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Role: {job.title} at {job.company or 'the company'}\n"
                    f"Job description:\n{(job.description or '')[:3500]}\n\n"
                    f"Candidate background:\n{background[:4000]}\n"
                    f"Skills: {', '.join(profile.skills or [])}\n\n"
                    "Prepare interview prep for this candidate and role."
                ),
            }
        ],
    )
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    return json.loads(text)
