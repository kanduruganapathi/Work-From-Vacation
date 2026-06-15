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
    q: str | None,
    tag: str | None,
    posted_within_days: int | None,
    location: str | None,
) -> list[ColumnElement[bool]]:
    """Filters that define the *search context* (independent of the facet dims)."""
    conditions: list[ColumnElement[bool]] = []
    if q:
        for term in q.split():
            conditions.append(_term_condition(term))
    if tag:
        conditions.append(func.lower(cast(Job.tags, String)).like(f"%{tag.lower()}%"))
    if location:
        conditions.append(
            func.lower(func.coalesce(Job.location, "")).like(f"%{location.lower()}%")
        )
    if posted_within_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=posted_within_days)
        conditions.append(Job.posted_at >= cutoff)
    return conditions


# Facetable dimensions: name -> (column, active value).
def _dim_conditions(dims: dict[str, object]) -> dict[str, ColumnElement[bool]]:
    conds: dict[str, ColumnElement[bool]] = {}
    if dims.get("employment_type") is not None:
        conds["employment_type"] = Job.employment_type == dims["employment_type"]
    if dims.get("remote") is not None:
        conds["remote"] = Job.remote.is_(bool(dims["remote"]))
    if dims.get("source"):
        conds["source"] = Job.source == dims["source"]
    if dims.get("company_type"):
        conds["company_type"] = Job.company_type == dims["company_type"]
    if dims.get("company_tier"):
        conds["company_tier"] = Job.company_tier == dims["company_tier"]
    return conds


def _relevance(job: Job, terms: list[str]) -> int:
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
    location: str | None = None,
    company_type: str | None = None,
    company_tier: str | None = None,
    posted_within_days: int | None = None,
    sort: str = "recent",
    limit: int = 24,
    offset: int = 0,
) -> tuple[int, list[Job], dict]:
    """Return ``(total, items, facets)`` for the given filters."""
    content = _content_conditions(q, tag, posted_within_days, location)
    dims = {
        "employment_type": employment_type,
        "remote": remote,
        "source": source,
        "company_type": company_type,
        "company_tier": company_tier,
    }
    dim_conds = _dim_conditions(dims)
    where = content + list(dim_conds.values())

    total = db.scalar(select(func.count(Job.id)).where(*where)) or 0

    if sort == "relevance" and q:
        candidates = list(db.scalars(select(Job).where(*where).limit(500)).all())
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

    facets = _facets(db, content, dim_conds)
    return total, items, facets


# Columns we build facets for.
_FACET_COLUMNS = {
    "employment_types": Job.employment_type,
    "sources": Job.source,
    "company_types": Job.company_type,
    "company_tiers": Job.company_tier,
}


def _facets(
    db: Session,
    content: list[ColumnElement[bool]],
    dim_conds: dict[str, ColumnElement[bool]],
) -> dict:
    """Per-facet counts. Each facet excludes its *own* dimension so the user
    sees what they'd get by switching that filter, respecting the others."""
    facet_to_dim = {
        "employment_types": "employment_type",
        "sources": "source",
        "company_types": "company_type",
        "company_tiers": "company_tier",
    }
    result: dict = {}
    for facet, column in _FACET_COLUMNS.items():
        own = facet_to_dim[facet]
        others = [c for name, c in dim_conds.items() if name != own]
        rows = db.execute(
            select(column, func.count(Job.id))
            .where(*content, *others, column.isnot(None))
            .group_by(column)
        ).all()
        result[facet] = {
            (k.value if hasattr(k, "value") else str(k)): v for k, v in rows
        }

    # Remote is a boolean facet (excludes the remote dim).
    others = [c for name, c in dim_conds.items() if name != "remote"]
    result["remote"] = (
        db.scalar(
            select(func.count(Job.id)).where(*content, *others, Job.remote.is_(True))
        )
        or 0
    )

    # Top locations within the full filtered set.
    loc_others = list(dim_conds.values())
    locs = db.execute(
        select(Job.location, func.count(Job.id))
        .where(*content, *loc_others, Job.location.isnot(None))
        .group_by(Job.location)
        .order_by(func.count(Job.id).desc())
        .limit(12)
    ).all()
    result["locations"] = {str(k): v for k, v in locs}
    return result


def count_matching_since(db: Session, params: dict, since: datetime) -> int:
    """Count jobs matching a saved search's params fetched after ``since``."""
    content = _content_conditions(
        params.get("q"),
        params.get("tag"),
        params.get("posted_within_days"),
        params.get("location"),
    )
    dim_conds = _dim_conditions(params)
    where = content + list(dim_conds.values()) + [Job.fetched_at > since]
    return db.scalar(select(func.count(Job.id)).where(*where)) or 0
