"""Greenhouse job-board connector.

Greenhouse exposes a public JSON board per company at
``https://boards-api.greenhouse.io/v1/boards/{slug}/jobs``. Point it at the
companies you want to track — this is how you source directly from employers
(and the same boards you'd later auto-apply into).
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.models import EmploymentType
from app.sources.base import JobSource, RawJob

API_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


class GreenhouseSource(JobSource):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.name = f"greenhouse:{slug}"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL.format(slug=self.slug))
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for item in data.get("jobs", []):
            title = item.get("title", "Untitled")
            content = item.get("content", "")
            if query and query.lower() not in f"{title} {content}".lower():
                continue
            location = (item.get("location") or {}).get("name")
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=title,
                    company=self.slug,
                    location=location,
                    remote="remote" in (location or "").lower(),
                    employment_type=EmploymentType.full_time,
                    category=None,
                    tags=[],
                    description=content,
                    url=item.get("absolute_url"),
                    salary_text=None,
                    posted_at=_parse(item.get("updated_at")),
                )
            )
            if len(jobs) >= limit:
                break
        return jobs


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
