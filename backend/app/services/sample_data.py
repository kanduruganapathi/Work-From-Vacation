"""Curated sample jobs for demos and offline development.

Useful when outbound network access to live sources is unavailable (sandboxes,
CI, first-run demos). Seed them via ``POST /api/jobs/seed``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import EmploymentType
from app.sources.base import RawJob

_NOW = datetime.now(timezone.utc)


def _ago(days: int) -> datetime:
    return _NOW - timedelta(days=days)


SAMPLE_JOBS: list[RawJob] = [
    RawJob(
        source="sample",
        external_id="sample-1",
        title="Senior Backend Engineer (Python)",
        company="Lumen Labs",
        location="Remote — Worldwide",
        remote=True,
        employment_type=EmploymentType.full_time,
        category="Software Development",
        tags=["python", "fastapi", "postgres", "aws"],
        description=(
            "Build and scale the API platform powering our analytics product. "
            "You'll own services end to end: design, FastAPI implementation, "
            "Postgres data modeling, and deployment on AWS. 5+ years with Python."
        ),
        url="https://example.com/jobs/sample-1",
        salary_text="$140,000 - $180,000",
        posted_at=_ago(1),
    ),
    RawJob(
        source="sample",
        external_id="sample-2",
        title="Freelance React Developer",
        company="Brightside Studio",
        location="Remote — Europe",
        remote=True,
        employment_type=EmploymentType.freelance,
        category="Frontend",
        tags=["react", "typescript", "nextjs", "tailwind"],
        description=(
            "Short-term freelance engagement to ship a marketing site and a "
            "customer dashboard in Next.js. ~20 hrs/week for 3 months."
        ),
        url="https://example.com/jobs/sample-2",
        salary_text="$60 - $90 / hour",
        posted_at=_ago(2),
    ),
    RawJob(
        source="sample",
        external_id="sample-3",
        title="Contract DevOps Engineer",
        company="Northwind Cloud",
        location="Remote — US",
        remote=True,
        employment_type=EmploymentType.contract,
        category="DevOps",
        tags=["kubernetes", "terraform", "ci/cd", "gcp"],
        description=(
            "6-month contract to harden our Kubernetes platform and migrate CI "
            "to GitHub Actions. Strong Terraform and GCP experience required."
        ),
        url="https://example.com/jobs/sample-3",
        salary_text="$80 - $110 / hour",
        posted_at=_ago(3),
    ),
    RawJob(
        source="sample",
        external_id="sample-4",
        title="Full-Stack Engineer",
        company="Cadence Health",
        location="Remote — US/Canada",
        remote=True,
        employment_type=EmploymentType.full_time,
        category="Software Development",
        tags=["typescript", "node", "react", "graphql"],
        description=(
            "Join a small product team building patient-facing tools. Full-stack "
            "TypeScript across a Node/GraphQL API and a React frontend."
        ),
        url="https://example.com/jobs/sample-4",
        salary_text="$120,000 - $155,000",
        posted_at=_ago(1),
    ),
    RawJob(
        source="sample",
        external_id="sample-5",
        title="Machine Learning Engineer (LLMs)",
        company="Vela AI",
        location="Remote — Worldwide",
        remote=True,
        employment_type=EmploymentType.full_time,
        category="Machine Learning",
        tags=["python", "pytorch", "llm", "rag"],
        description=(
            "Design and ship LLM-powered features: retrieval pipelines, "
            "evaluation harnesses, and agentic workflows. Experience with "
            "production ML and prompt engineering preferred."
        ),
        url="https://example.com/jobs/sample-5",
        salary_text="$160,000 - $210,000",
        posted_at=_ago(0),
    ),
    RawJob(
        source="sample",
        external_id="sample-6",
        title="Part-Time Data Analyst",
        company="Harbor Metrics",
        location="Remote — Anywhere",
        remote=True,
        employment_type=EmploymentType.part_time,
        category="Data",
        tags=["sql", "python", "dashboards", "analytics"],
        description=(
            "Part-time analyst to build dashboards and answer product questions "
            "with SQL and lightweight Python. ~15 hrs/week, flexible hours."
        ),
        url="https://example.com/jobs/sample-6",
        salary_text="$45 - $65 / hour",
        posted_at=_ago(4),
    ),
    RawJob(
        source="sample",
        external_id="sample-7",
        title="Platform Engineer",
        company="Solstice Systems",
        location="Remote — EMEA",
        remote=True,
        employment_type=EmploymentType.full_time,
        category="Infrastructure",
        tags=["go", "kubernetes", "observability", "grpc"],
        description=(
            "Own developer experience and platform reliability. Go services, "
            "Kubernetes operators, and observability tooling for ~80 engineers."
        ),
        url="https://example.com/jobs/sample-7",
        salary_text="€90,000 - €120,000",
        posted_at=_ago(2),
    ),
    RawJob(
        source="sample",
        external_id="sample-8",
        title="Freelance Technical Writer",
        company="Docflow",
        location="Remote — Worldwide",
        remote=True,
        employment_type=EmploymentType.freelance,
        category="Content",
        tags=["documentation", "api", "developer-tools"],
        description=(
            "Write developer documentation and tutorials for a cloud API. "
            "Project-based; strong technical background and clear writing."
        ),
        url="https://example.com/jobs/sample-8",
        salary_text="$50 - $80 / hour",
        posted_at=_ago(5),
    ),
    RawJob(
        source="sample",
        external_id="sample-9",
        title="Senior Frontend Engineer",
        company="Aurora Commerce",
        location="Remote — US",
        remote=True,
        employment_type=EmploymentType.full_time,
        category="Frontend",
        tags=["react", "typescript", "performance", "design-systems"],
        description=(
            "Lead frontend architecture for a high-traffic commerce platform. "
            "Deep React/TypeScript expertise and a feel for performance and UX."
        ),
        url="https://example.com/jobs/sample-9",
        salary_text="$150,000 - $190,000",
        posted_at=_ago(1),
    ),
    RawJob(
        source="sample",
        external_id="sample-10",
        title="Contract Mobile Developer (React Native)",
        company="Tidal Apps",
        location="Remote — LATAM",
        remote=True,
        employment_type=EmploymentType.contract,
        category="Mobile",
        tags=["react-native", "typescript", "ios", "android"],
        description=(
            "4-month contract to build cross-platform features in React Native. "
            "Ship to both iOS and Android with a small, fast-moving team."
        ),
        url="https://example.com/jobs/sample-10",
        salary_text="$55 - $75 / hour",
        posted_at=_ago(3),
    ),
    RawJob(
        source="sample",
        external_id="sample-11",
        title="Staff Software Engineer",
        company="Meridian",
        location="Remote — Worldwide",
        remote=True,
        employment_type=EmploymentType.full_time,
        category="Software Development",
        tags=["python", "distributed-systems", "architecture"],
        description=(
            "Technical leadership across multiple teams. Set architecture "
            "direction for distributed systems handling millions of requests."
        ),
        url="https://example.com/jobs/sample-11",
        salary_text="$200,000 - $250,000",
        posted_at=_ago(0),
    ),
    RawJob(
        source="sample",
        external_id="sample-12",
        title="Junior Backend Developer",
        company="Sproutly",
        location="Remote — Worldwide",
        remote=True,
        employment_type=EmploymentType.full_time,
        category="Software Development",
        tags=["python", "django", "rest", "entry-level"],
        description=(
            "Great first remote role: build REST APIs in Django with mentorship "
            "and code review. We hire for curiosity and fundamentals."
        ),
        url="https://example.com/jobs/sample-12",
        salary_text="$70,000 - $95,000",
        posted_at=_ago(2),
    ),
]


def sample_jobs() -> list[RawJob]:
    """Return a fresh copy of the sample jobs (timestamps fixed at import)."""
    return [dict(job) for job in SAMPLE_JOBS]  # type: ignore[misc]
