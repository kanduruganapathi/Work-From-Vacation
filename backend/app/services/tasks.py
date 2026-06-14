"""In-process background task runner.

Runs slow AI work (orchestrated hunts, scoring, batch apply) off the request
thread using a small thread pool, tracking progress in the ``tasks`` table so the
frontend can poll. For a multi-process production deployment, swap this for a
real queue (Celery/RQ/Arq) — the Task model and API stay the same.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from app.agents import orchestrator
from app.database import SessionLocal
from app.models import Task, TaskKind, TaskStatus, User
from app.services import scoring

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="wfv-task")


def create_task(user_id: int, kind: TaskKind, params: dict | None = None) -> Task:
    """Persist a queued task and schedule it on the executor. Returns the row."""
    db = SessionLocal()
    try:
        task = Task(user_id=user_id, kind=kind, status=TaskStatus.queued, progress=0)
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
    finally:
        db.close()

    _executor.submit(_run, task_id, user_id, kind, params or {})
    return task


def _run(task_id: int, user_id: int, kind: TaskKind, params: dict) -> None:
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        user = db.get(User, user_id)
        if not task or not user:
            return

        def progress(pct: int, msg: str) -> None:
            task.progress = max(0, min(100, pct))
            task.message = msg
            db.commit()

        task.status = TaskStatus.running
        task.message = "Starting..."
        db.commit()

        if kind == TaskKind.job_hunt:
            result = _run_job_hunt(db, user, params, progress)
        elif kind == TaskKind.auto_score:
            result = _run_auto_score(db, user, params, progress)
        elif kind == TaskKind.batch_apply:
            result = _run_batch_apply(db, user, params, progress)
        else:
            result = {"error": f"Unknown task kind: {kind}"}

        task.status = TaskStatus.done
        task.progress = 100
        task.result = result
        task.message = result.get("message", "Done.")
        db.commit()
    except Exception as exc:  # surface failures on the task row
        logger.exception("Task %s failed", task_id)
        task = db.get(Task, task_id)
        if task:
            task.status = TaskStatus.error
            task.message = str(exc)[:500]
            db.commit()
    finally:
        db.close()


def _run_job_hunt(db, user, params, progress) -> dict:
    progress(10, "Planning your search...")
    instruction = params.get(
        "instruction",
        "Find and score the best jobs for me and suggest how to improve my search.",
    )
    max_jobs = int(params.get("max_jobs", 15))
    summary = orchestrator.run_job_hunt(db, user, instruction, max_jobs=max_jobs)
    return {"message": "Hunt complete.", "summary": summary}


def _run_auto_score(db, user, params, progress) -> dict:
    limit = params.get("limit")
    matches = scoring.score_new_jobs(db, user, limit=limit, progress=progress)
    return {"message": f"Scored {len(matches)} new jobs.", "scored": len(matches)}


def _run_batch_apply(db, user, params, progress) -> dict:
    min_score = int(params.get("min_score", 80))
    limit = int(params.get("limit", 5))
    created = scoring.batch_auto_apply(
        db, user, min_score=min_score, limit=limit, progress=progress
    )
    return {"message": f"Auto-applied to {len(created)} roles.", "applied": len(created)}
