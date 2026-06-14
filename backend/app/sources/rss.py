"""Generic RSS/Atom job-feed connector.

Point it at any job-board feed (many boards expose ``/feed`` or ``/rss``).
Construct with a feed URL and add it to ``ALL_SOURCES`` in ``__init__`` or use it
ad hoc.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from time import mktime

import feedparser

from app.models import EmploymentType
from app.sources.base import JobSource, RawJob


class RSSSource(JobSource):
    def __init__(self, feed_url: str, name: str | None = None) -> None:
        self.feed_url = feed_url
        self.name = name or f"rss:{_short_hash(feed_url)}"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        # feedparser is synchronous; fine for periodic refresh jobs.
        parsed = feedparser.parse(self.feed_url)
        jobs: list[RawJob] = []
        for entry in parsed.entries[:limit]:
            title = getattr(entry, "title", "Untitled")
            summary = getattr(entry, "summary", None)
            if query and query.lower() not in f"{title} {summary or ''}".lower():
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=getattr(entry, "id", None) or _short_hash(title),
                    title=title,
                    company=getattr(entry, "author", None),
                    location=None,
                    remote="remote" in f"{title} {summary or ''}".lower(),
                    employment_type=EmploymentType.unknown,
                    category=None,
                    tags=[t.term for t in getattr(entry, "tags", [])] or [],
                    description=summary,
                    url=getattr(entry, "link", None),
                    salary_text=None,
                    posted_at=_entry_date(entry),
                )
            )
        return jobs


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode()).hexdigest()[:12]


def _entry_date(entry) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if not parsed:
        return None
    return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
