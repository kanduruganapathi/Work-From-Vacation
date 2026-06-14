"""Base types shared by all job-source connectors."""

from __future__ import annotations

import abc
from datetime import datetime
from typing import TypedDict

from app.models import EmploymentType


class RawJob(TypedDict, total=False):
    """A normalized job from a source, before it becomes a DB row."""

    source: str
    external_id: str
    title: str
    company: str | None
    location: str | None
    remote: bool
    employment_type: EmploymentType
    category: str | None
    tags: list[str]
    description: str | None
    url: str | None
    salary_text: str | None
    posted_at: datetime | None


class JobSource(abc.ABC):
    """Interface every connector implements."""

    #: Short stable identifier stored on each job row.
    name: str = "base"

    @abc.abstractmethod
    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        """Return normalized jobs, optionally filtered by a free-text query."""
        raise NotImplementedError


def normalize_employment_type(value: str | None) -> EmploymentType:
    """Map a source's free-text contract field to our enum."""
    if not value:
        return EmploymentType.unknown
    v = value.lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "full_time": EmploymentType.full_time,
        "fulltime": EmploymentType.full_time,
        "permanent": EmploymentType.full_time,
        "contract": EmploymentType.contract,
        "contractor": EmploymentType.contract,
        "freelance": EmploymentType.freelance,
        "part_time": EmploymentType.part_time,
        "parttime": EmploymentType.part_time,
        "internship": EmploymentType.internship,
        "intern": EmploymentType.internship,
    }
    return mapping.get(v, EmploymentType.unknown)
