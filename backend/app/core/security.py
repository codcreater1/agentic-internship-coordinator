import hmac

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency: when `api_secret_key` is configured, require
    'Authorization: Bearer <key>'. A no-op when no key is set (open dev mode).

    Use to protect machine-facing endpoints (e.g. the n8n webhook) without
    locking out the local frontend.
    """
    expected = settings.api_secret_key
    if not expected:
        return

    # Constant-time: a plain `!=` on a secret leaks its prefix through timing,
    # and this key is guessable one character at a time without it.
    if not hmac.compare_digest(authorization or "", f"Bearer {expected}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
