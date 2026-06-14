"""Arbeitnow connector — https://www.arbeitnow.com/api/job-board-api (no auth)."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.models import EmploymentType
from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource(JobSource):
    name = "arbeitnow"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for item in data.get("data", []):
            title = item.get("title", "Untitled")
            tags = item.get("tags", []) or []
            if query and not _matches(query, title, tags, item.get("company_name")):
                continue
            job_types = item.get("job_types", []) or []
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("slug")),
                    title=title,
                    company=item.get("company_name"),
                    location=item.get("location"),
                    remote=bool(item.get("remote")),
                    employment_type=(
                        normalize_employment_type(job_types[0])
                        if job_types
                        else EmploymentType.unknown
                    ),
                    category=None,
                    tags=tags,
                    description=item.get("description"),
                    url=item.get("url"),
                    salary_text=None,
                    posted_at=_parse_ts(item.get("created_at")),
                )
            )
            if len(jobs) >= limit:
                break
        return jobs


def _matches(query: str, title: str, tags: list[str], company: str | None) -> bool:
    haystack = " ".join([title, company or "", *tags]).lower()
    return all(term in haystack for term in query.lower().split())


def _parse_ts(value: int | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, OSError):
        return None
