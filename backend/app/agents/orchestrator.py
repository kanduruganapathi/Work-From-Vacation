"""Orchestrator agent — plans and runs the automated job hunt.

Runs a manual agentic loop: Claude decides which tools to call (search the job DB,
read the profile, score jobs), we execute them, and feed results back until it
produces a final summary. This is the "automation brain" that coordinates the
specialist agents.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.agents.client import MODEL, THINKING, get_client
from app.agents.tools import TOOLS, ToolContext, execute_tool
from app.models import User

logger = logging.getLogger(__name__)

_MAX_TURNS = 12

_SYSTEM = (
    "You are the orchestrator of an automated job-search assistant called Work From "
    "Vacation. Your goal is to find and score the best job opportunities for the "
    "candidate across full-time, contract, freelance, and remote roles.\n\n"
    "Workflow:\n"
    "1. Call get_candidate_profile to understand the candidate.\n"
    "2. Run one or more search_jobs calls using keywords drawn from their skills and "
    "desired titles. Try a few keyword combinations to widen coverage.\n"
    "3. Pick the most promising jobs and call score_jobs on them (cap around 10-15).\n"
    "4. Finish with a concise summary: the strongest matches, why, and one or two "
    "suggestions to improve the search.\n\n"
    "Be efficient — don't over-search. When you are done, stop calling tools and "
    "write the summary."
)


def run_job_hunt(db: Session, user: User, instruction: str, max_jobs: int = 15) -> str:
    """Execute the orchestrated hunt and return the agent's final summary text."""
    client = get_client()
    ctx = ToolContext(db=db, user=user)

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"{instruction}\n\nScore at most {max_jobs} jobs in total."
            ),
        }
    ]

    for _ in range(_MAX_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            thinking=THINKING,
            system=_SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info("orchestrator tool: %s", block.name)
                    try:
                        result = execute_tool(ctx, block.name, block.input)
                    except Exception as exc:  # surface errors to the model
                        result = f'{{"error": "{exc}"}}'
                        logger.warning("tool %s failed: %s", block.name, exc)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        # No more tool calls — return the final text.
        return "".join(b.text for b in response.content if b.type == "text").strip()

    return (
        "The search ran out of steps before finishing. Some jobs may have been "
        "scored — check your matches."
    )
