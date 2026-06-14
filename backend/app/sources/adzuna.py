"""Adzuna connector — https://developer.adzuna.com/ (requires an app id + key).

Adzuna aggregates full-time, contract, and part-time roles across many boards,
so it complements the remote-focused free sources. Enabled automatically when
``ADZUNA_APP_ID`` and ``ADZUNA_APP_KEY`` are set.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.sources.base import JobSource, RawJob, normalize_employment_type

API_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


class AdzunaSource(JobSource):
    name = "adzuna"

    def __init__(self, country: str = "us") -> None:
        self.country = country

    @property
    def configured(self) -> bool:
        return bool(settings.adzuna_app_id and settings.adzuna_app_key)

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        if not self.configured:
            return []
        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "results_per_page": min(limit, 50),
            "content-type": "application/json",
        }
        if query:
            params["what"] = query

        url = API_URL.format(country=self.country)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[RawJob] = []
        for item in data.get("results", [])[:limit]:
            contract = item.get("contract_time") or item.get("contract_type")
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=item.get("title", "Untitled"),
                    company=(item.get("company") or {}).get("display_name"),
                    location=(item.get("location") or {}).get("display_name"),
                    remote="remote" in (item.get("title", "").lower()),
                    employment_type=normalize_employment_type(contract),
                    category=(item.get("category") or {}).get("label"),
                    tags=[],
                    description=item.get("description"),
                    url=item.get("redirect_url"),
                    salary_text=_salary(item),
                    posted_at=None,
                )
            )
        return jobs


def _salary(item: dict) -> str | None:
    low, high = item.get("salary_min"), item.get("salary_max")
    if low and high:
        return f"{int(low):,} - {int(high):,}"
    return None
