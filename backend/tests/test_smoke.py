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

    listed = client.get("/api/jobs?limit=50")
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
    job_id = client.get("/api/jobs?limit=1").json()[0]["id"]

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
    job_id = client.get("/api/jobs?limit=1").json()[0]["id"]
    # No ANTHROPIC_API_KEY in the test env, so auto-apply should report disabled.
    resp = client.post(
        "/api/ai/auto-apply", json={"job_id": job_id}, headers=headers
    )
    assert resp.status_code == 503


def test_job_search() -> None:
    client.post("/api/jobs/seed")

    res = client.get("/api/jobs/search?q=python&sort=relevance&limit=3").json()
    assert res["total"] >= 1
    assert len(res["items"]) >= 1
    # Relevance puts a python-titled role first.
    assert "python" in res["items"][0]["title"].lower()
    assert "facets" in res and "employment_types" in res["facets"]

    contract = client.get("/api/jobs/search?employment_type=contract").json()
    assert all(i["employment_type"] == "contract" for i in contract["items"])

    # Multi-term AND: every result matches both terms somewhere.
    multi = client.get("/api/jobs/search?q=senior+engineer").json()
    assert multi["total"] >= 1

    # Company classification facets + filter.
    assert "company_types" in res["facets"]
    assert "company_tiers" in res["facets"]
    assert "locations" in res["facets"]
    product = client.get("/api/jobs/search?company_type=product").json()
    assert all(i["company_type"] == "product" for i in product["items"])

    # Location substring filter.
    us = client.get("/api/jobs/search?location=US").json()
    assert all("us" in (i["location"] or "").lower() for i in us["items"])


def test_company_classifier() -> None:
    from app.services.company_classifier import classify

    assert classify("Google") == ("product", "tier1")
    assert classify("Infosys") == ("mnc", "tier1")
    assert classify("Vela AI")[0] == "startup"
    assert classify(None) == ("other", None)


def test_saved_searches_crud() -> None:
    headers = _auth_headers("savedsearch@example.com")
    created = client.post(
        "/api/saved-searches",
        json={"name": "Python remote", "params": {"q": "python", "remote": True}},
        headers=headers,
    )
    assert created.status_code == 201
    sid = created.json()["id"]
    assert created.json()["alert_enabled"] is True

    listed = client.get("/api/saved-searches", headers=headers)
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/saved-searches/{sid}", json={"alert_enabled": False}, headers=headers
    )
    assert patched.json()["alert_enabled"] is False

    assert (
        client.delete(f"/api/saved-searches/{sid}", headers=headers).status_code == 204
    )


def test_count_matching_since() -> None:
    from datetime import datetime, timedelta, timezone

    from app.database import SessionLocal
    from app.services import search

    client.post("/api/jobs/seed")
    db = SessionLocal()
    try:
        # All seeded jobs were fetched after this point.
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        count = search.count_matching_since(db, {"q": "python"}, since)
        assert count >= 1
        # Nothing fetched in the future.
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        assert search.count_matching_since(db, {"q": "python"}, future) == 0
    finally:
        db.close()


def test_notifications_empty_then_list() -> None:
    headers = _auth_headers("notify@example.com")
    resp = client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_async_ai_endpoints_require_ai_key() -> None:
    headers = _auth_headers("async@example.com")
    client.post("/api/jobs/seed")
    job_id = client.get("/api/jobs?limit=1").json()[0]["id"]
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


def test_autopilot_gating_and_daily_count() -> None:
    from app.database import SessionLocal
    from app.models import Application, ApplicationStatus, Job, Profile, User
    from app.services import scoring

    db = SessionLocal()
    try:
        user = User(email=f"pilot{__import__('random').randint(0, 99999)}@x.com",
                    hashed_password="x")
        db.add(user)
        db.flush()
        # Autopilot off -> no-op.
        user.profile = Profile(user_id=user.id, autopilot_enabled=False)
        db.flush()
        assert scoring.run_autopilot(db, user) == []

        # Daily count reflects created applications.
        job = db.scalar(__import__("sqlalchemy").select(Job).limit(1)) or Job(
            source="t", external_id="t1", title="T"
        )
        if job.id is None:
            db.add(job)
            db.flush()
        db.add(
            Application(
                user_id=user.id, job_id=job.id, status=ApplicationStatus.applied
            )
        )
        db.flush()
        assert scoring.applications_today(db, user) >= 1
    finally:
        db.rollback()
        db.close()


class _StubSource(JobSource):
    name = "stub"

    async def fetch(self, query: str | None = None, limit: int = 100) -> list[RawJob]:
        return [
            RawJob(
                source=self.name,
                external_id="1",
                title="Zzx Stub Backend Role",
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
        assert db.query(Job).filter(Job.title == "Zzx Stub Backend Role").count() == 1
    finally:
        db.close()
