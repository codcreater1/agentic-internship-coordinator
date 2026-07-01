"""Thin wrapper around an OpenAI-compatible LLM API for structured CV evaluation.

Provider-agnostic: it talks to any OpenAI-compatible endpoint via the ``openai``
SDK, so you can use a **free** provider. Defaults to Groq (free, fast). Switch
providers by changing three env vars — see ``.env.example``:

    Groq    (free):  LLM_API_KEY=gsk_...   base_url default,  model llama-3.3-70b-versatile
    Gemini  (free):  LLM_API_KEY=...        PDFSIGN_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/   PDFSIGN_LLM_MODEL=gemini-2.0-flash
    OpenAI  (paid):  LLM_API_KEY=sk-...     PDFSIGN_LLM_BASE_URL=https://api.openai.com/v1   PDFSIGN_LLM_MODEL=gpt-4o-mini

:func:`complete_json` asks the model for a JSON object matching a caller-supplied
schema and returns it as a ``dict`` — or ``None`` if no API key is configured or
the call fails, so callers fall back to deterministic logic and keep working.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _api_key() -> str:
    return os.getenv("LLM_API_KEY", "")


def is_enabled() -> bool:
    """True when an LLM API key is available in the environment."""
    return bool(_api_key())


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI

    return OpenAI(api_key=_api_key(), base_url=settings.llm_base_url)


def complete_json(
    *,
    system: str,
    user: str,
    schema: dict[str, Any],
    max_tokens: int = 1500,
) -> dict[str, Any] | None:
    """Call the LLM with a JSON-only response constrained to *schema*.

    Returns the parsed object, or ``None`` if AI is disabled or anything goes
    wrong (missing key, API error, malformed JSON). Never raises.
    """
    if not is_enabled():
        return None

    system_prompt = (
        f"{system}\n\n"
        "Respond with ONE valid JSON object and nothing else (no markdown, no "
        "code fences). It must match this JSON schema:\n"
        f"{json.dumps(schema)}"
    )

    try:
        response = _client().chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=max_tokens,
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001 — degrade gracefully on any SDK/API error
        logger.exception("LLM request failed; falling back to deterministic logic")
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("LLM returned non-JSON content: %s", text[:200])
        return None
