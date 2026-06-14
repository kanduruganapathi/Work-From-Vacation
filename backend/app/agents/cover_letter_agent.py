"""Cover Letter Agent — drafts a tailored cover letter for a role."""

from __future__ import annotations

from app.agents.client import MODEL, THINKING, get_client
from app.models import Job, Profile

_SYSTEM = (
    "You are an expert career writer. You draft concise, specific, and genuine "
    "cover letters tailored to a role and candidate. Avoid clichés and filler. "
    "Three to four short paragraphs. Do not invent facts about the candidate."
)


def write_cover_letter(profile: Profile, job: Job, tone: str = "professional") -> str:
    background = profile.resume_text or profile.summary or profile.headline or ""
    if not background.strip():
        raise ValueError(
            "No profile background on file. Add a summary or resume_text first."
        )

    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        thinking=THINKING,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write a {tone} cover letter for this role.\n\n"
                    f"Role: {job.title} at {job.company or 'the company'}\n"
                    f"Job description:\n{(job.description or '')[:3500]}\n\n"
                    f"Candidate background:\n{background[:4000]}\n\n"
                    f"Candidate skills: {', '.join(profile.skills or [])}"
                ),
            }
        ],
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()
