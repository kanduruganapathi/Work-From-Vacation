"""RemoteOK connector — https://remoteok.com/api (no auth)."""

from __future__ import annotations

from datetime import datetime

import httpx

from app.models import EmploymentType
from app.sources.base import JobSource, RawJob

API_URL = "https://remoteok.com/api"


class RemoteOKSource(JobSource):
    name = "remoteok"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        async with httpx.AsyncClient(
            timeout=30, headers={"User-Agent": "WorkFromVacation/0.1"}
        ) as client:
            resp = await client.get(API_URL)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        # The first element is a legal/metadata notice; skip entries without an id.
        for item in data:
            if not isinstance(item, dict) or "id" not in item:
                continue
            title = item.get("position") or item.get("title") or "Untitled"
            tags = item.get("tags", []) or []
            if query and not _matches(query, title, tags, item.get("company")):
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=title,
                    company=item.get("company"),
                    location=item.get("location") or "Remote",
                    remote=True,
                    employment_type=EmploymentType.unknown,
                    category=None,
                    tags=tags,
                    description=item.get("description"),
                    url=item.get("url") or item.get("apply_url"),
                    salary_text=_salary(item),
                    posted_at=_parse_date(item.get("date")),
                )
            )
            if len(jobs) >= limit:
                break
        return jobs


def _matches(query: str, title: str, tags: list[str], company: str | None) -> bool:
    haystack = " ".join([title, company or "", *tags]).lower()
    return all(term in haystack for term in query.lower().split())


def _salary(item: dict) -> str | None:
    low, high = item.get("salary_min"), item.get("salary_max")
    if low and high:
        return f"${low:,} - ${high:,}"
    return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
