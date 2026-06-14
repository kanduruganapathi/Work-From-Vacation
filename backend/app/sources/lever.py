"""Lever job-board connector.

Lever exposes a public JSON postings feed per company at
``https://api.lever.co/v0/postings/{slug}?mode=json``.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"


class LeverSource(JobSource):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.name = f"lever:{slug}"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL.format(slug=self.slug))
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for item in data:
            title = item.get("text", "Untitled")
            categories = item.get("categories", {}) or {}
            description = item.get("descriptionPlain") or item.get("description", "")
            if query and query.lower() not in f"{title} {description}".lower():
                continue
            location = categories.get("location")
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=title,
                    company=self.slug,
                    location=location,
                    remote="remote" in (location or "").lower(),
                    employment_type=normalize_employment_type(categories.get("commitment")),
                    category=categories.get("team"),
                    tags=[t for t in [categories.get("department")] if t],
                    description=description,
                    url=item.get("hostedUrl"),
                    salary_text=None,
                    posted_at=_parse_ms(item.get("createdAt")),
                )
            )
            if len(jobs) >= limit:
                break
        return jobs


def _parse_ms(value: int | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (ValueError, OSError):
        return None
