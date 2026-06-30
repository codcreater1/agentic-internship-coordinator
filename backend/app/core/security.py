import hmac
import hashlib
import time
from app.core.config import settings


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
        settings.secret_key.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(sig, expected)
