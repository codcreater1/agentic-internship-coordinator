"""Thin wrapper around an OpenAI-compatible LLM API for structured CV evaluation.

Provider-agnostic: talks to any OpenAI-compatible endpoint via the ``openai``
SDK. Defaults to Groq (free, fast). Switch providers via env vars — see
``.env.example``.

When ``LANGFUSE_PUBLIC_KEY`` and ``LANGFUSE_SECRET_KEY`` are set, every LLM
call is automatically traced in LangFuse (latency, tokens, input/output).
Set ``LANGFUSE_HOST`` to self-host; defaults to cloud.langfuse.com.
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
    return bool(_api_key())


def _langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


@lru_cache(maxsize=1)
def _client():
    if _langfuse_enabled():
        from langfuse.openai import OpenAI
        logger.info("LLM client initialised with LangFuse observability")
    else:
        from openai import OpenAI

    return OpenAI(api_key=_api_key(), base_url=settings.llm_base_url)


def complete_json(
    *,
    system: str,
    user: str,
    schema: dict[str, Any],
    max_tokens: int = 1500,
    trace_name: str = "llm-call",
) -> dict[str, Any] | None:
    """Call the LLM and return a JSON dict matching *schema*, or ``None`` on failure.

    ``trace_name`` labels the call in LangFuse (e.g. "cv-evaluation",
    "email-generation"). Ignored when LangFuse is not configured.
    """
    if not is_enabled():
        return None

    system_prompt = (
        f"{system}\n\n"
        "Respond with ONE valid JSON object and nothing else (no markdown, no "
        "code fences). It must match this JSON schema:\n"
        f"{json.dumps(schema)}"
    )

    kwargs: dict[str, Any] = dict(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=max_tokens,
    )
    if _langfuse_enabled():
        kwargs["name"] = trace_name

    try:
        response = _client().chat.completions.create(**kwargs)
        text = (response.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("LLM request failed; falling back to deterministic logic")
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("LLM returned non-JSON content: %s", text[:200])
        return None
