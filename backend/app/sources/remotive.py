"""Remotive connector — https://remotive.com/api/remote-jobs (no auth)."""

from __future__ import annotations

from datetime import datetime

import httpx

from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSource(JobSource):
    name = "remotive"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        params: dict[str, str | int] = {"limit": limit}
        if query:
            params["search"] = query
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for item in data.get("jobs", [])[:limit]:
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=item.get("title", "Untitled"),
                    company=item.get("company_name"),
                    location=item.get("candidate_required_location") or "Remote",
                    remote=True,
                    employment_type=normalize_employment_type(item.get("job_type")),
                    category=item.get("category"),
                    tags=item.get("tags", []) or [],
                    description=item.get("description"),
                    url=item.get("url"),
                    salary_text=item.get("salary") or None,
                    posted_at=_parse_date(item.get("publication_date")),
                )
            )
        return jobs


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
