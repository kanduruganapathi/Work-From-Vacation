# Architecture

This document explains how Work From Vacation is put together and how to extend it.

## Layers

```
frontend (Next.js)  ──REST──▶  backend (FastAPI)
                                  │
            ┌─────────────────────┼──────────────────────┐
            ▼                     ▼                      ▼
      source connectors     aggregator service     multi-agent AI
      (APIs/RSS/scrape)      (fetch/dedupe/store)   (Claude + tools)
                                  │                      │
                                  ▼                      ▼
                              database              Anthropic API
```

## Backend modules

| Path | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI app, router wiring, startup (`init_db`). |
| `app/config.py` | Settings from env (`pydantic-settings`). |
| `app/database.py` | Engine, session, declarative `Base`. |
| `app/models.py` | ORM models: `User`, `Profile`, `Job`, `JobMatch`, `Application`. |
| `app/schemas.py` | Pydantic request/response schemas. |
| `app/core/security.py` | Password hashing + JWT. |
| `app/sources/` | One connector per source, all implementing `JobSource`. |
| `app/services/aggregator.py` | Concurrent fetch, dedupe by `(source, external_id)`, upsert. |
| `app/agents/` | The multi-agent AI layer (see below). |
| `app/api/routes/` | Route modules: `auth`, `profiles`, `jobs`, `applications`, `agents`. |

## The multi-agent AI layer

Everything in `app/agents/` runs on Claude (`claude-opus-4-8`) with adaptive
thinking.

| Agent | File | Pattern |
| --- | --- | --- |
| Orchestrator | `orchestrator.py` | Manual agentic **tool-use loop** — plans the search and calls tools. |
| Job Matching | `matching_agent.py` | Single call with **structured outputs** (JSON schema) → score/reasons/concerns. |
| Resume Tailoring | `resume_agent.py` | Single call, plain-text output. |
| Cover Letter | `cover_letter_agent.py` | Single call, plain-text output. |
| Search Strategy | `strategy_agent.py` | Single call with structured outputs. |

The orchestrator's tools live in `tools.py`:

- `get_candidate_profile` — reads the user's profile.
- `search_jobs` — queries the aggregated job database.
- `score_jobs` — delegates to the Job Matching Agent and persists `JobMatch` rows.

This is the "automation brain": the orchestrator decides which keywords to
search, which jobs to score, and produces a final summary — coordinating the
specialist agents through tools.

## Adding a new job source

1. Create `app/sources/yourservice.py` implementing `JobSource.fetch(...)`,
   returning a list of `RawJob` dicts.
2. Add an instance to `ALL_SOURCES` in `app/sources/__init__.py`.
3. That's it — the aggregator and `/api/jobs/refresh` pick it up automatically.

## Adding a new AI capability

1. Add a module under `app/agents/` (single-call agents are easiest — copy
   `cover_letter_agent.py`).
2. For agents the orchestrator should be able to invoke, add a tool schema +
   executor in `app/agents/tools.py`.
3. Expose it via a route in `app/api/routes/agents.py`.

## Data model

```
User 1───1 Profile
User 1───* Application *───1 Job
User 1───* JobMatch    *───1 Job
Job  *───1 source (string)
```

## Production notes

- Swap SQLite for Postgres via `DATABASE_URL` (the models are portable).
- Replace `Base.metadata.create_all` with Alembic migrations.
- Add a background scheduler (e.g. APScheduler / Celery) to call
  `aggregator.refresh_jobs` and the orchestrator on a cadence, then push alerts.
- Put the Anthropic key in a secret manager; never ship it to the frontend.
