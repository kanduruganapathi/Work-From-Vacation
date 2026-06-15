"""The Muse connector — https://www.themuse.com/api/public/jobs (no auth).

Covers full-time roles across many companies and locations (including India),
complementing the remote-focused sources.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "https://www.themuse.com/api/public/jobs"


class TheMuseSource(JobSource):
    name = "themuse"

    def __init__(self, pages: int = 2) -> None:
        self.pages = pages

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        jobs: list[RawJob] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for page in range(self.pages):
                params: dict[str, str | int] = {"page": page}
                resp = await client.get(API_URL, params=params)
                resp.raise_for_status()
                results = resp.json().get("results", [])
                for item in results:
                    locations = [l.get("name") for l in item.get("locations", [])]
                    location = ", ".join(filter(None, locations)) or None
                    title = item.get("name", "Untitled")
                    if query and query.lower() not in title.lower():
                        continue
                    jobs.append(
                        RawJob(
                            source=self.name,
                            external_id=str(item.get("id")),
                            title=title,
                            company=(item.get("company") or {}).get("name"),
                            location=location,
                            remote=bool(location and "remote" in location.lower()),
                            employment_type=normalize_employment_type(item.get("type")),
                            category=(item.get("categories") or [{}])[0].get("name"),
                            tags=[t.get("short_name") for t in item.get("tags", []) if t],
                            description=item.get("contents"),
                            url=(item.get("refs") or {}).get("landing_page"),
                            salary_text=None,
                            posted_at=_parse(item.get("publication_date")),
                        )
                    )
                    if len(jobs) >= limit:
                        return jobs
        return jobs


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
