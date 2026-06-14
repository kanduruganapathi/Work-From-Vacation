"""Generic HTML careers-page scraper.

A best-effort connector for boards that expose neither an API nor an RSS feed.
It fetches a page and extracts anchor links whose text/URL look like job
postings, optionally filtered by a keyword present in the link text.

⚠️ Scraping may violate a site's Terms of Service and is **disabled by default**.
Only use it for pages you are authorized to scrape, set a realistic
``rate_limit`` between requests, and prefer the API/RSS connectors where
available. This uses the Python standard library only (no headless browser), so
it cannot read JavaScript-rendered content.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from app.models import EmploymentType
from app.sources.base import JobSource, RawJob

# Heuristics for spotting job links on a careers page.
_JOB_URL_HINTS = re.compile(r"(job|career|position|opening|vacanc|posting|gh_jid|lever)", re.I)


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []  # (href, text)
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._href = href
                self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = " ".join("".join(self._text).split())
            if text:
                self.links.append((self._href, text))
            self._href = None
            self._text = []


class ScraperSource(JobSource):
    def __init__(self, page_url: str, name: str | None = None) -> None:
        self.page_url = page_url
        self.name = name or f"scrape:{_short(page_url)}"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        async with httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": "WorkFromVacation/0.1 (+respecting-robots)"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(self.page_url)
            resp.raise_for_status()
            html = resp.text

        parser = _LinkExtractor()
        parser.feed(html)

        seen: set[str] = set()
        jobs: list[RawJob] = []
        for href, text in parser.links:
            url = urljoin(self.page_url, href)
            looks_like_job = _JOB_URL_HINTS.search(href) or _JOB_URL_HINTS.search(text)
            if not looks_like_job:
                continue
            if query and query.lower() not in text.lower():
                continue
            if url in seen or len(text) < 4:
                continue
            seen.add(url)
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=_short(url),
                    title=text[:200],
                    company=None,
                    location=None,
                    remote="remote" in text.lower(),
                    employment_type=EmploymentType.unknown,
                    category=None,
                    tags=[],
                    description=None,
                    url=url,
                    salary_text=None,
                    posted_at=None,
                )
            )
            if len(jobs) >= limit:
                break
        return jobs


def _short(value: str) -> str:
    return hashlib.sha1(value.encode()).hexdigest()[:12]
