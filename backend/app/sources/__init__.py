"""Job source connectors.

Each connector implements :class:`app.sources.base.JobSource` and returns a list
of :class:`RawJob` dicts. Register active sources in ``ALL_SOURCES`` below.
"""

from app.sources.arbeitnow import ArbeitnowSource
from app.sources.base import JobSource, RawJob
from app.sources.remoteok import RemoteOKSource
from app.sources.remotive import RemotiveSource

# Sources that run by default (no credentials required).
ALL_SOURCES: list[JobSource] = [
    RemotiveSource(),
    RemoteOKSource(),
    ArbeitnowSource(),
]

__all__ = ["JobSource", "RawJob", "ALL_SOURCES"]
