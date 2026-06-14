"""Search Strategy Agent — recommends how to widen or sharpen the hunt."""

from __future__ import annotations

import json

from app.agents.client import MODEL, THINKING, get_client
from app.models import Profile

_SCHEMA = {
    "type": "object",
    "properties": {
        "suggested_titles": {"type": "array", "items": {"type": "string"}},
        "suggested_keywords": {"type": "array", "items": {"type": "string"}},
        "suggested_sources": {"type": "array", "items": {"type": "string"}},
        "advice": {"type": "string"},
    },
    "required": [
        "suggested_titles",
        "suggested_keywords",
        "suggested_sources",
        "advice",
    ],
    "additionalProperties": False,
}

_SYSTEM = (
    "You are a job-search strategist. Given a candidate profile, you recommend job "
    "titles to target, search keywords, and the kinds of sources/boards worth "
    "checking (e.g. remote boards, niche communities, contract marketplaces). Be "
    "concrete and tailored to the candidate's skills and goals."
)


def suggest_strategy(profile: Profile) -> dict:
    client = get_client()
    brief = json.dumps(
        {
            "headline": profile.headline,
            "skills": profile.skills,
            "desired_titles": profile.desired_titles,
            "desired_employment_types": profile.desired_employment_types,
            "years_experience": profile.years_experience,
            "remote_only": profile.remote_only,
        },
        indent=2,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        thinking=THINKING,
        system=_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Candidate profile:\n{brief}\n\n"
                    "Recommend a focused job-search strategy."
                ),
            }
        ],
    )
    text = next((b.text for b in response.content if b.type == "text"), "{}")
    return json.loads(text)
