import hmac
import hashlib
import time
from app.core.config import settings


def _secret() -> bytes:
    return settings.signing_secret.encode()


def create_download_token(task_id: str, ttl: int = 600) -> str:
    exp = int(time.time()) + ttl
    data = f"{task_id}:{exp}"
    sig = hmac.new(_secret(), data.encode(), hashlib.sha256).hexdigest()
    return f"{task_id}:{exp}:{sig}"


def verify_download_token(token: str) -> str:
    try:
        task_id, exp, sig = token.split(":")
        exp = int(exp)
    except Exception:
        raise ValueError("Invalid token")

    if time.time() > exp:
        raise ValueError("Token expired")

    data = f"{task_id}:{exp}"
    expected = hmac.new(_secret(), data.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(sig, expected):
        raise ValueError("Invalid token")

    return task_id
