"""Careerjet connector — https://www.careerjet.com/partners/ (free affiliate id).

Careerjet is a job-search aggregator with India coverage (locale ``en_IN``).
Register for a free affiliate id and set ``CAREERJET_AFFID``.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.config import settings
from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "http://public.api.careerjet.net/search"


class CareerjetSource(JobSource):
    name = "careerjet"

    @property
    def configured(self) -> bool:
        return bool(settings.careerjet_affid)

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        if not self.configured:
            return []
        params = {
            "affid": settings.careerjet_affid,
            "keywords": query or settings.jobs_default_query,
            "location": settings.jobs_default_location,
            "locale_code": settings.careerjet_locale,
            "pagesize": min(limit, 99),
            "page": 1,
            "user_ip": "1.2.3.4",
            "user_agent": "WorkFromVacation/0.1",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for i, item in enumerate(data.get("jobs", [])[:limit]):
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("url") or i),
                    title=item.get("title", "Untitled"),
                    company=item.get("company"),
                    location=item.get("locations"),
                    remote="remote" in (item.get("title", "")).lower(),
                    employment_type=normalize_employment_type(item.get("contracttime")),
                    category=None,
                    tags=[],
                    description=item.get("description"),
                    url=item.get("url"),
                    salary_text=item.get("salary") or None,
                    posted_at=_parse(item.get("date")),
                )
            )
        return jobs


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:25].strip(), fmt)
        except ValueError:
            continue
    return None
