"""FastAPI application entrypoint for Work From Vacation."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.client import ai_enabled
from app.api.routes import (
    agents,
    applications,
    auth,
    jobs,
    notifications,
    profiles,
    saved_searches,
)
from app.config import settings
from app.database import init_db
from app.services import scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Automated job search across full-time, contract, freelance, and remote roles.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(agents.router)
app.include_router(notifications.router)
app.include_router(saved_searches.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "ai_enabled": ai_enabled(),
    }


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }
