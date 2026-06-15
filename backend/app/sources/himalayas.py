"""Himalayas connector — https://himalayas.app/jobs/api (no auth)."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "https://himalayas.app/jobs/api"


class HimalayasSource(JobSource):
    name = "himalayas"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        params: dict[str, str | int] = {"limit": min(limit, 50)}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for item in data.get("jobs", [])[:limit]:
            title = item.get("title", "Untitled")
            if query and query.lower() not in title.lower():
                continue
            locations = item.get("locationRestrictions") or []
            employment = item.get("employmentType")
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("guid") or item.get("id") or title),
                    title=title,
                    company=item.get("companyName"),
                    location=", ".join(locations) if locations else "Remote",
                    remote=True,
                    employment_type=normalize_employment_type(
                        employment[0] if isinstance(employment, list) and employment
                        else employment
                    ),
                    category=None,
                    tags=item.get("categories", []) or [],
                    description=item.get("description"),
                    url=item.get("applicationLink") or item.get("url"),
                    salary_text=_salary(item),
                    posted_at=_parse(item.get("pubDate")),
                )
            )
        return jobs


def _salary(item: dict) -> str | None:
    lo, hi = item.get("minSalary"), item.get("maxSalary")
    if lo and hi:
        return f"${int(lo):,} - ${int(hi):,}"
    return None


def _parse(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
