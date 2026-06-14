"""Job search: multi-term matching, filters, sorting, and facet counts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import EmploymentType, Job


def _term_condition(term: str) -> ColumnElement[bool]:
    """A single search term matched across title, company, description, tags."""
    like = f"%{term.lower()}%"
    return (
        func.lower(Job.title).like(like)
        | func.lower(func.coalesce(Job.company, "")).like(like)
        | func.lower(func.coalesce(Job.description, "")).like(like)
        | func.lower(cast(Job.tags, String)).like(like)
    )


def _content_conditions(
    q: str | None, tag: str | None, posted_within_days: int | None
) -> list[ColumnElement[bool]]:
    """Filters that define the *search context* (independent of the facet dims)."""
    conditions: list[ColumnElement[bool]] = []
    if q:
        # All terms must match (AND), each across multiple fields.
        for term in q.split():
            conditions.append(_term_condition(term))
    if tag:
        conditions.append(func.lower(cast(Job.tags, String)).like(f"%{tag.lower()}%"))
    if posted_within_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=posted_within_days)
        conditions.append(Job.posted_at >= cutoff)
    return conditions


def _relevance(job: Job, terms: list[str]) -> int:
    """Naive relevance: weighted term occurrences across fields."""
    title = (job.title or "").lower()
    company = (job.company or "").lower()
    tags = " ".join(job.tags or []).lower()
    desc = (job.description or "").lower()
    score = 0
    for t in terms:
        score += title.count(t) * 5
        score += company.count(t) * 2
        score += tags.count(t) * 3
        score += desc.count(t) * 1
    return score


def search_jobs(
    db: Session,
    *,
    q: str | None = None,
    employment_type: EmploymentType | None = None,
    remote: bool | None = None,
    source: str | None = None,
    tag: str | None = None,
    posted_within_days: int | None = None,
    sort: str = "recent",
    limit: int = 24,
    offset: int = 0,
) -> tuple[int, list[Job], dict]:
    """Return ``(total, items, facets)`` for the given filters."""
    content = _content_conditions(q, tag, posted_within_days)

    # Dimension filters (also facetable).
    dim: list[ColumnElement[bool]] = []
    if employment_type:
        dim.append(Job.employment_type == employment_type)
    if remote is not None:
        dim.append(Job.remote.is_(remote))
    if source:
        dim.append(Job.source == source)

    where = content + dim
    total = db.scalar(select(func.count(Job.id)).where(*where)) or 0

    if sort == "relevance" and q:
        # Score a bounded candidate set in Python, then page.
        candidates = list(
            db.scalars(select(Job).where(*where).limit(500)).all()
        )
        terms = [t.lower() for t in q.split()]
        candidates.sort(key=lambda j: _relevance(j, terms), reverse=True)
        items = candidates[offset : offset + limit]
    else:
        items = list(
            db.scalars(
                select(Job)
                .where(*where)
                .order_by(Job.fetched_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )

    facets = _facets(db, content, employment_type, remote, source)
    return total, items, facets


def _facets(
    db: Session,
    content: list[ColumnElement[bool]],
    employment_type: EmploymentType | None,
    remote: bool | None,
    source: str | None,
) -> dict:
    """Counts per facet value within the search context.

    Each facet excludes its *own* dimension so the user sees what they'd get by
    switching that filter, while respecting the other active filters.
    """

    def base(extra: list[ColumnElement[bool]]):
        return content + extra

    other_for_type = []
    if remote is not None:
        other_for_type.append(Job.remote.is_(remote))
    if source:
        other_for_type.append(Job.source == source)

    other_for_source = []
    if employment_type:
        other_for_source.append(Job.employment_type == employment_type)
    if remote is not None:
        other_for_source.append(Job.remote.is_(remote))

    types = dict(
        db.execute(
            select(Job.employment_type, func.count(Job.id))
            .where(*base(other_for_type))
            .group_by(Job.employment_type)
        ).all()
    )
    sources = dict(
        db.execute(
            select(Job.source, func.count(Job.id))
            .where(*base(other_for_source))
            .group_by(Job.source)
        ).all()
    )
    remote_count = db.scalar(
        select(func.count(Job.id)).where(*base(other_for_type), Job.remote.is_(True))
    )

    return {
        "employment_types": {
            (k.value if hasattr(k, "value") else str(k)): v for k, v in types.items()
        },
        "sources": {str(k): v for k, v in sources.items()},
        "remote": remote_count or 0,
    }
