"""Smoke tests that run without an Anthropic API key.

These exercise auth, profile, and the source/aggregation plumbing using an
in-memory SQLite database and a stubbed job source.
"""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.models import Job
from app.services import aggregator
from app.sources.base import JobSource, RawJob

client = TestClient(app)


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_login_and_profile() -> None:
    email = "vacationer@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "supersecret", "full_name": "Ada"},
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": "supersecret"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(
        "/api/profile",
        json={"skills": ["python", "fastapi"], "desired_titles": ["Backend Engineer"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["skills"] == ["python", "fastapi"]


class _StubSource(JobSource):
    name = "stub"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        return [
            RawJob(
                source=self.name,
                external_id="1",
                title="Senior Python Engineer",
                company="Acme",
                remote=True,
            )
        ]


def test_aggregator_upserts_and_dedupes() -> None:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        raw = asyncio.run(aggregator.fetch_all(sources=[_StubSource()]))
        inserted, _ = aggregator.upsert_jobs(db, raw)
        assert inserted == 1
        # Second run should dedupe.
        inserted_again, _ = aggregator.upsert_jobs(db, raw)
        assert inserted_again == 0
        assert db.query(Job).filter(Job.title == "Senior Python Engineer").count() == 1
    finally:
        db.close()
