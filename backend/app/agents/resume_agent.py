"""Resume Tailoring Agent — rewrites a resume to target a specific role."""

from __future__ import annotations

from app.agents.client import MODEL, THINKING, get_client
from app.models import Job, Profile

_SYSTEM = (
    "You are an expert resume writer. You tailor a candidate's existing resume to a "
    "specific job, emphasizing the most relevant experience and aligning language "
    "with the posting. You NEVER fabricate experience, employers, dates, or skills "
    "the candidate does not have — you only reframe and prioritize what is real. "
    "Return clean, ATS-friendly plain text."
)


def tailor_resume(profile: Profile, job: Job) -> str:
    resume = profile.resume_text or profile.summary or ""
    if not resume.strip():
        raise ValueError(
            "No resume or summary on file. Add resume_text to your profile first."
        )

    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        thinking=THINKING,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Target role: {job.title} at {job.company or 'the company'}\n\n"
                    f"Job description:\n{(job.description or '')[:4000]}\n\n"
                    f"Candidate's current resume:\n{resume[:6000]}\n\n"
                    "Rewrite the resume to target this role. Keep it truthful. "
                    "Lead with the most relevant experience and mirror key terms "
                    "from the posting where they genuinely apply."
                ),
            }
        ],
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()
