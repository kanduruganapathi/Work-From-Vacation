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


def test_seed_demo_jobs_is_idempotent() -> None:
    first = client.post("/api/jobs/seed")
    assert first.status_code == 200
    assert first.json()["inserted"] >= 12

    # Re-seeding adds nothing new.
    second = client.post("/api/jobs/seed")
    assert second.status_code == 200
    assert second.json()["inserted"] == 0

    listed = client.get("/api/jobs?source=sample&limit=50")
    assert listed.status_code == 200
    assert len(listed.json()) >= 12


def _auth_headers(email: str) -> dict[str, str]:
    client.post("/api/auth/register", json={"email": email, "password": "supersecret"})
    token = client.post(
        "/api/auth/login", data={"username": email, "password": "supersecret"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_application_tracking_flow() -> None:
    headers = _auth_headers("tracker@example.com")
    client.post("/api/jobs/seed")
    job_id = client.get("/api/jobs?source=sample&limit=1").json()[0]["id"]

    created = client.post(
        "/api/applications", json={"job_id": job_id, "status": "saved"}, headers=headers
    )
    assert created.status_code == 201
    app_id = created.json()["id"]
    assert created.json()["status"] == "saved"

    updated = client.patch(
        f"/api/applications/{app_id}",
        json={"status": "interviewing"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "interviewing"

    listed = client.get("/api/applications", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = client.delete(f"/api/applications/{app_id}", headers=headers)
    assert deleted.status_code == 204


def test_resume_upload_text() -> None:
    headers = _auth_headers("resume@example.com")
    resp = client.post(
        "/api/profile/resume",
        files={"file": ("resume.txt", b"Senior Python engineer, 8 years.", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "Python engineer" in resp.json()["resume_text"]


def test_scraper_link_extraction() -> None:
    # Offline parse test for the generic scraper's link heuristics.
    from app.sources.scraper import _LinkExtractor

    html = (
        '<a href="/jobs/123">Senior Backend Engineer</a>'
        '<a href="/about">About us</a>'
        '<a href="/careers/eng">Remote Frontend Position</a>'
    )
    parser = _LinkExtractor()
    parser.feed(html)
    texts = [t for _, t in parser.links]
    assert "Senior Backend Engineer" in texts
    assert "About us" in texts  # extractor keeps all; ScraperSource filters by hint


def test_auto_apply_requires_ai_key() -> None:
    headers = _auth_headers("autoapply@example.com")
    client.post("/api/jobs/seed")
    job_id = client.get("/api/jobs?source=sample&limit=1").json()[0]["id"]
    # No ANTHROPIC_API_KEY in the test env, so auto-apply should report disabled.
    resp = client.post(
        "/api/ai/auto-apply", json={"job_id": job_id}, headers=headers
    )
    assert resp.status_code == 503


def test_notifications_empty_then_list() -> None:
    headers = _auth_headers("notify@example.com")
    resp = client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_async_ai_endpoints_require_ai_key() -> None:
    headers = _auth_headers("async@example.com")
    client.post("/api/jobs/seed")
    job_id = client.get("/api/jobs?source=sample&limit=1").json()[0]["id"]
    assert (
        client.post("/api/ai/run-async", json={"instruction": "go"}, headers=headers).status_code
        == 503
    )
    assert client.post("/api/ai/score-new", headers=headers).status_code == 503
    assert (
        client.post("/api/ai/batch-apply", json={}, headers=headers).status_code == 503
    )
    assert (
        client.post(
            "/api/ai/interview-prep", json={"job_id": job_id}, headers=headers
        ).status_code
        == 503
    )


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
