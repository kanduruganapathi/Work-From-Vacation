# Work From Vacation 🌴

**Your AI-powered job hunt, on autopilot.**

Work From Vacation is a SaaS platform that automates the entire job search across
**full-time, contract, freelance, and remote** opportunities. It aggregates roles
from many sources, then runs a **multi-agent AI workflow** (powered by Claude) to
match jobs to your profile, tailor your resume, draft cover letters, and track every
application — so you can find your next role while you're, well, on vacation.

---

## ✨ What it does

| Pillar | Description |
| --- | --- |
| **Aggregate** | Pulls jobs from official APIs, RSS feeds, and (optionally) scrapers. Deduplicates and normalizes everything into one feed. |
| **Match** | A multi-agent AI pipeline scores each job against your profile, skills, and preferences, with an explanation. |
| **Apply** | AI tailors your resume and drafts a cover letter per role. Track applications through every stage. |
| **Alert** | Get notified about new high-fit roles as they appear. |

The frontend ships with an animated **three.js** background (a rotating globe of
remote-job nodes) for a polished, product-grade landing and dashboard.

## 🏗️ Architecture

```
                 ┌──────────────────────────────────────────────┐
                 │                Next.js frontend               │
                 │     (dashboard, job feed, applications)       │
                 └───────────────────────┬──────────────────────┘
                                         │  REST / JSON
                 ┌───────────────────────▼──────────────────────┐
                 │                 FastAPI backend                │
                 │  auth · jobs · profiles · applications · ai    │
                 ├───────────────────────┬──────────────────────┤
                 │   Source connectors    │   Multi-agent AI      │
                 │  (APIs · RSS · scrape) │   (Claude + tools)    │
                 └───────────┬───────────┴───────────┬──────────┘
                             │                        │
                     ┌───────▼───────┐        ┌───────▼───────┐
                     │  Job boards   │        │ Anthropic API │
                     │  & feeds      │        │  (Claude)     │
                     └───────────────┘        └───────────────┘
                             │
                     ┌───────▼───────┐
                     │   Database    │  (SQLite dev · Postgres prod)
                     └───────────────┘
```

### The multi-agent AI layer

The "automation brain" is a set of cooperating Claude agents, each with focused tools:

- **Orchestrator** — plans the search, decides which specialist agents to invoke.
- **Job Matching Agent** — scores a job against the user profile (fit %, reasons, red flags).
- **Resume Tailoring Agent** — rewrites resume bullets to target a specific role.
- **Cover Letter Agent** — drafts a tailored cover letter.
- **Search Strategy Agent** — suggests keywords, titles, and sources to widen/narrow the hunt.

All run on `claude-opus-4-8` with adaptive thinking and tool use. See
[`backend/app/agents/`](backend/app/agents/).

## 🚀 Quick start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 20+
- An [Anthropic API key](https://console.anthropic.com/) (`ANTHROPIC_API_KEY`)

### Backend

```bash
cd backend
uv sync --extra dev           # creates .venv and installs everything
cp .env.example .env          # then set ANTHROPIC_API_KEY
uv run uvicorn app.main:app --reload
```

Run the tests with `uv run pytest`.

API docs are served at http://localhost:8000/docs

Seed the job feed from real sources:

```bash
curl -X POST http://localhost:8000/api/jobs/refresh
```

No outbound network (sandbox / offline / CI)? Load curated sample jobs instead —
or just click **Load sample jobs** in the dashboard:

```bash
curl -X POST http://localhost:8000/api/jobs/seed
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

App runs at http://localhost:3000

### Docker (everything at once)

```bash
cp .env.example .env          # set ANTHROPIC_API_KEY
docker compose up --build
```

## 📦 Job sources

| Source | Type | Auth | Notes |
| --- | --- | --- | --- |
| Remotive | API | none | Remote jobs across categories (default) |
| RemoteOK | API | none | Remote / tech roles (default) |
| Arbeitnow | API | none | Remote + EU roles (default) |
| Adzuna | API | key | Full-time / contract aggregator; auto-enabled when `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` are set |
| Greenhouse | API | none | Per-company board (`GreenhouseSource("slug")`) — source directly from employers |
| Lever | API | none | Per-company board (`LeverSource("slug")`) |
| Generic RSS | RSS | none | Point `RSSSource(url)` at any job-board feed |
| Scraper | scrape | none | `ScraperSource(url)` for boards without an API/feed. **Disabled by default; respect each site's ToS.** |

Connectors live in [`backend/app/sources/`](backend/app/sources/) and implement a
common `JobSource` interface, so adding a new source is one file.

## 🗺️ Roadmap

- [x] Project scaffold (FastAPI + Next.js + Docker)
- [x] Source connector framework + real API sources
- [x] Job aggregation, dedupe, and storage
- [x] Multi-agent AI matching pipeline (Claude + tools)
- [x] Resume tailoring & cover letter agents
- [x] Application tracking
- [ ] Background scheduler for periodic refresh + alerts
- [ ] Billing / subscription tiers (Stripe)
- [ ] Auto-apply integrations (Greenhouse / Lever / Workday)
- [ ] Email & push notifications

## ⚖️ Legal note on scraping

Aggregating via official APIs and public RSS feeds is the default. Web scraping is
**off by default** because many sites prohibit it in their Terms of Service. Only
enable a scraper for sources you are authorized to scrape.

## License

MIT
