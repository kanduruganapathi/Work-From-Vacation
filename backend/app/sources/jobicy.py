"""Jobicy connector — https://jobicy.com/api/v2/remote-jobs (no auth)."""

from __future__ import annotations

from datetime import datetime

import httpx

from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "https://jobicy.com/api/v2/remote-jobs"


class JobicySource(JobSource):
    name = "jobicy"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        params: dict[str, str | int] = {"count": min(limit, 50)}
        if query:
            params["tag"] = query
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for item in data.get("jobs", [])[:limit]:
            job_types = item.get("jobType") or []
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=item.get("jobTitle", "Untitled"),
                    company=item.get("companyName"),
                    location=item.get("jobGeo") or "Remote",
                    remote=True,
                    employment_type=normalize_employment_type(
                        job_types[0] if job_types else None
                    ),
                    category=item.get("jobIndustry", [None])[0]
                    if isinstance(item.get("jobIndustry"), list)
                    else item.get("jobIndustry"),
                    tags=[],
                    description=item.get("jobDescription"),
                    url=item.get("url"),
                    salary_text=_salary(item),
                    posted_at=_parse(item.get("pubDate")),
                )
            )
        return jobs


def _salary(item: dict) -> str | None:
    lo, hi = item.get("annualSalaryMin"), item.get("annualSalaryMax")
    cur = item.get("salaryCurrency", "USD")
    if lo and hi:
        return f"{cur} {int(lo):,} - {int(hi):,}"
    return None


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    return None
