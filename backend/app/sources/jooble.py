"""Jooble connector — https://jooble.org/api/ (free API key required).

Jooble is a worldwide job aggregator with strong India coverage; it syndicates
listings from many boards (the kind you'd otherwise see on Naukri/Indeed/etc.).
Get a free key at https://jooble.org/api/about and set ``JOOBLE_API_KEY``.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "https://jooble.org/api/{key}"


class JoobleSource(JobSource):
    name = "jooble"

    @property
    def configured(self) -> bool:
        return bool(settings.jooble_api_key)

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        if not self.configured:
            return []
        payload = {
            "keywords": query or settings.jobs_default_query,
            "location": settings.jobs_default_location,
        }
        url = API_URL.format(key=settings.jooble_api_key)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for item in data.get("jobs", [])[:limit]:
            location = item.get("location") or ""
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=item.get("title", "Untitled"),
                    company=item.get("company"),
                    location=location or None,
                    remote="remote" in (item.get("title", "") + location).lower(),
                    employment_type=normalize_employment_type(item.get("type")),
                    category=None,
                    tags=[],
                    description=item.get("snippet"),
                    url=item.get("link"),
                    salary_text=item.get("salary") or None,
                    posted_at=None,
                )
            )
        return jobs
