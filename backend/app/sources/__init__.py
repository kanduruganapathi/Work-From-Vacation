"""Job source connectors.

Each connector implements :class:`app.sources.base.JobSource` and returns a list
of :class:`RawJob` dicts. ``active_sources()`` returns the connectors that should
run on a refresh, including credential-gated ones (Adzuna) when configured.

Per-company ATS connectors (Greenhouse, Lever) and the generic scraper require a
slug / URL, so they're constructed on demand rather than listed here.
"""

from app.sources.adzuna import AdzunaSource
from app.sources.arbeitnow import ArbeitnowSource
from app.sources.base import JobSource, RawJob
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource
from app.sources.remoteok import RemoteOKSource
from app.sources.remotive import RemotiveSource
from app.sources.rss import RSSSource
from app.sources.scraper import ScraperSource

# Free, no-credential sources that always run.
DEFAULT_SOURCES: list[JobSource] = [
    RemotiveSource(),
    RemoteOKSource(),
    ArbeitnowSource(),
]


def active_sources() -> list[JobSource]:
    """Sources to run on a refresh, including credential-gated ones."""
    sources = list(DEFAULT_SOURCES)
    adzuna = AdzunaSource()
    if adzuna.configured:
        sources.append(adzuna)
    return sources


# Backwards-compatible alias.
ALL_SOURCES = DEFAULT_SOURCES

__all__ = [
    "JobSource",
    "RawJob",
    "DEFAULT_SOURCES",
    "ALL_SOURCES",
    "active_sources",
    "AdzunaSource",
    "GreenhouseSource",
    "LeverSource",
    "RSSSource",
    "ScraperSource",
]
