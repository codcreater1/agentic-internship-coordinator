import hmac
import hashlib
import time

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

    if authorization != f"Bearer {expected}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )


def verify_token(task_id: str, token: str) -> bool:
    try:
        exp, sig = token.split(":")
        exp = int(exp)
    except Exception:
        return False

    if time.time() > exp:
        return False

    data = f"{task_id}:{exp}"
    expected = hmac.new(
        settings.signing_secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(sig, expected)
