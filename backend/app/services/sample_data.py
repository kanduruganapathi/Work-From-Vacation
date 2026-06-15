"""Curated sample jobs for demos and offline development.

Useful when outbound network access to live sources is unavailable (sandboxes,
CI, first-run demos). Seed them via ``POST /api/jobs/seed``. The set spans Indian
metros + global remote roles, real companies (so classification populates), and a
variety of source labels (so the source filter is meaningful).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import EmploymentType
from app.sources.base import RawJob

_NOW = datetime.now(timezone.utc)
FT = EmploymentType.full_time
CT = EmploymentType.contract
FL = EmploymentType.freelance
PT = EmploymentType.part_time

# (ext_id, title, company, location, type, source, salary, tags, days_ago)
_ROWS = [
    # ── Bangalore ──────────────────────────────────────────────────────────
    ("s1", "Senior Backend Engineer", "Flipkart", "Bangalore, India", FT, "naukri", "₹35-55 LPA", ["java", "microservices", "kafka"], 1),
    ("s2", "Software Engineer II", "Swiggy", "Bangalore, India", FT, "linkedin", "₹28-42 LPA", ["go", "python", "distributed-systems"], 2),
    ("s3", "Backend Engineer", "Razorpay", "Bangalore, India", FT, "instahyre", "₹30-50 LPA", ["java", "spring", "payments"], 1),
    ("s4", "Senior Python Engineer", "CRED", "Bangalore, India", FT, "wellfound", "₹40-60 LPA", ["python", "fastapi", "aws"], 0),
    ("s5", "SDE - Backend", "PhonePe", "Bangalore, India", FT, "naukri", "₹25-45 LPA", ["java", "scala", "kafka"], 3),
    ("s6", "Frontend Engineer", "Meesho", "Bangalore, India", FT, "cutshort", "₹22-38 LPA", ["react", "typescript", "nextjs"], 2),
    ("s7", "Data Scientist", "Zerodha", "Bangalore, India", FT, "linkedin", "₹30-48 LPA", ["python", "ml", "pandas"], 4),
    ("s8", "Software Engineer", "Google", "Bangalore, India", FT, "linkedin", "₹50-90 LPA", ["c++", "distributed-systems"], 1),
    ("s9", "SDE II", "Amazon", "Bangalore, India", FT, "naukri", "₹40-70 LPA", ["java", "aws", "dynamodb"], 2),
    ("s10", "Platform Engineer", "Atlassian", "Bangalore, India", FT, "wellfound", "₹45-75 LPA", ["go", "kubernetes", "aws"], 1),

    # ── Hyderabad ──────────────────────────────────────────────────────────
    ("s11", "Senior Software Engineer", "Microsoft", "Hyderabad, India", FT, "linkedin", "₹45-80 LPA", ["c#", "azure", "distributed-systems"], 1),
    ("s12", "Backend Developer", "Amazon", "Hyderabad, India", FT, "naukri", "₹38-65 LPA", ["java", "aws"], 2),
    ("s13", "Full-Stack Engineer", "Infosys", "Hyderabad, India", FT, "naukri", "₹12-22 LPA", ["java", "angular", "spring"], 3),
    ("s14", "DevOps Engineer", "Accenture", "Hyderabad, India", FT, "hirist", "₹14-26 LPA", ["aws", "terraform", "jenkins"], 2),
    ("s15", "ML Engineer", "Uber", "Hyderabad, India", FT, "linkedin", "₹42-70 LPA", ["python", "pytorch", "ml"], 0),

    # ── Chennai ────────────────────────────────────────────────────────────
    ("s16", "Product Engineer", "Freshworks", "Chennai, India", FT, "wellfound", "₹28-45 LPA", ["ruby", "rails", "react"], 1),
    ("s17", "Software Developer", "Zoho", "Chennai, India", FT, "naukri", "₹18-32 LPA", ["java", "javascript"], 4),
    ("s18", "Senior Engineer", "Cognizant", "Chennai, India", FT, "hirist", "₹13-24 LPA", ["dotnet", "azure"], 3),
    ("s19", "Frontend Developer", "Wipro", "Chennai, India", FT, "naukri", "₹10-20 LPA", ["react", "typescript"], 5),

    # ── Mumbai ─────────────────────────────────────────────────────────────
    ("s20", "Backend Engineer", "Nykaa", "Mumbai, India", FT, "instahyre", "₹26-42 LPA", ["node", "typescript", "mongodb"], 2),
    ("s21", "Data Engineer", "TCS", "Mumbai, India", FT, "naukri", "₹12-22 LPA", ["spark", "python", "sql"], 3),
    ("s22", "Senior Frontend Engineer", "Dream11", "Mumbai, India", FT, "wellfound", "₹35-55 LPA", ["react", "typescript", "performance"], 1),

    # ── Pune / Delhi NCR ───────────────────────────────────────────────────
    ("s23", "Software Engineer", "Persistent Systems", "Pune, India", FT, "naukri", "₹10-20 LPA", ["java", "spring"], 4),
    ("s24", "SDE", "Paytm", "Noida, India", FT, "naukri", "₹22-40 LPA", ["java", "kafka", "payments"], 2),
    ("s25", "Backend Engineer", "Zomato", "Gurgaon, India", FT, "linkedin", "₹28-46 LPA", ["go", "postgres"], 1),

    # ── Contract / Freelance (India + remote) ──────────────────────────────
    ("s26", "Contract React Developer", "Tidal Apps", "Remote — India", CT, "cutshort", "₹2,500-4,000/hr", ["react", "typescript"], 2),
    ("s27", "Freelance Python Developer", "Brightside Studio", "Remote — Worldwide", FL, "wellfound", "$50-80/hr", ["python", "django"], 3),
    ("s28", "Contract DevOps Engineer", "Northwind Cloud", "Remote — India", CT, "hirist", "₹3,000-5,000/hr", ["kubernetes", "terraform"], 1),
    ("s29", "Freelance Technical Writer", "Docflow", "Remote — Worldwide", FL, "wellfound", "$40-70/hr", ["documentation", "api"], 5),

    # ── Global remote ──────────────────────────────────────────────────────
    ("s30", "Senior Python Engineer", "Vela AI", "Remote — US", FT, "remotive", "$160k-210k", ["python", "llm", "rag"], 0),
    ("s31", "Staff Software Engineer", "Meridian", "Remote — US/Canada", FT, "remotive", "$200k-250k", ["python", "architecture"], 1),
    ("s32", "Full-Stack Engineer", "Aurora Commerce", "Remote — US", FT, "indeed", "$130k-170k", ["typescript", "react", "node"], 2),
    ("s33", "Platform Engineer", "Solstice Systems", "Remote — EMEA", FT, "remotive", "€90k-120k", ["go", "kubernetes"], 2),
    ("s34", "Part-Time Data Analyst", "Harbor Metrics", "Remote — Worldwide", PT, "remotive", "$45-65/hr", ["sql", "python"], 4),
]


def sample_jobs() -> list[RawJob]:
    """Return a fresh list of sample jobs."""
    jobs: list[RawJob] = []
    for ext, title, company, location, etype, source, salary, tags, days in _ROWS:
        jobs.append(
            RawJob(
                source=source,
                external_id=ext,
                title=title,
                company=company,
                location=location,
                remote="remote" in location.lower(),
                employment_type=etype,
                category=None,
                tags=tags,
                description=(
                    f"{title} role at {company} ({location}). "
                    f"Tech: {', '.join(tags)}. "
                    "This is a sample listing for demo/offline use."
                ),
                url=f"https://example.com/jobs/{ext}",
                salary_text=salary,
                posted_at=_NOW - timedelta(days=days),
            )
        )
    return jobs
