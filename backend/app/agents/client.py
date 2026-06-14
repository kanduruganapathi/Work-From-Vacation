"""Anthropic client factory and shared constants for the AI agents."""

from __future__ import annotations

from functools import lru_cache

import anthropic

from app.config import settings

# The agents run on the latest Opus with adaptive thinking. See the Claude API
# docs: budget_tokens is removed on this model family — use adaptive thinking.
MODEL = settings.ai_model
THINKING = {"type": "adaptive"}


class AgentConfigError(RuntimeError):
    """Raised when the AI layer is used without an API key configured."""


@lru_cache
def get_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise AgentConfigError(
            "ANTHROPIC_API_KEY is not set. Add it to your environment to enable "
            "the AI agents."
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def ai_enabled() -> bool:
    return bool(settings.anthropic_api_key)
