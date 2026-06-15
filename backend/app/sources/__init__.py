"""Job source connectors.

Each connector implements :class:`app.sources.base.JobSource` and returns a list
of :class:`RawJob` dicts. ``active_sources()`` returns the connectors that run on
a refresh: the free no-key APIs, RSS feeds, credential-gated sources (Adzuna),
and a fan-out across the configured per-company ATS boards (Greenhouse/Lever).
"""

from app.config import settings
from app.sources.adzuna import AdzunaSource
from app.sources.arbeitnow import ArbeitnowSource
from app.sources.base import JobSource, RawJob
from app.sources.greenhouse import GreenhouseSource
from app.sources.himalayas import HimalayasSource
from app.sources.jobicy import JobicySource
from app.sources.lever import LeverSource
from app.sources.remoteok import RemoteOKSource
from app.sources.remotive import RemotiveSource
from app.sources.rss import RSSSource
from app.sources.scraper import ScraperSource
from app.sources.themuse import TheMuseSource

# Free, no-credential API/feed sources that always run.
DEFAULT_SOURCES: list[JobSource] = [
    RemotiveSource(),
    RemoteOKSource(),
    ArbeitnowSource(),
    JobicySource(),
    HimalayasSource(),
    TheMuseSource(),
]


def active_sources() -> list[JobSource]:
    """All sources to run on a refresh, assembled from config."""
    sources: list[JobSource] = list(DEFAULT_SOURCES)

    # Credential-gated.
    adzuna = AdzunaSource()
    if adzuna.configured:
        sources.append(adzuna)

    # Per-company ATS boards (fan-out).
    sources += [GreenhouseSource(s) for s in settings.ats_greenhouse_slugs]
    sources += [LeverSource(s) for s in settings.ats_lever_slugs]

    # Extra RSS/Atom feeds.
    sources += [RSSSource(url) for url in settings.extra_rss_feeds]

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
    "JobicySource",
    "HimalayasSource",
    "TheMuseSource",
    "RSSSource",
    "ScraperSource",
]
