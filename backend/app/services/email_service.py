"""Outbound email for signed contracts — delegated to n8n.

The backend does not hold SMTP credentials. Instead it POSTs to an n8n webhook
(``PDFSIGN_N8N_EMAIL_WEBHOOK_URL``) which reuses the Gmail OAuth connection
already configured there for the candidate-reply flow.

The PDF travels as base64 in the payload so n8n needs nothing but the webhook:
no public download URL, no signed token, no callback into this service.
On the n8n side: Webhook -> Convert to File (base64 -> binary) -> Gmail (send
with attachment).
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 20


class EmailNotConfiguredError(RuntimeError):
    """Raised when no n8n email webhook is configured."""


class EmailSendError(RuntimeError):
    """Raised when the n8n webhook rejects or fails to deliver the message."""


def is_enabled() -> bool:
    return bool(settings.n8n_email_webhook_url)


def send_signed_contract(
    *,
    to: str,
    subject: str,
    body: str,
    pdf_path: Path,
    candidate_name: str,
) -> None:
    """Ask n8n to email *pdf_path* to *to*. Raises on any failure."""
    if not is_enabled():
        raise EmailNotConfiguredError(
            "No n8n email webhook configured (PDFSIGN_N8N_EMAIL_WEBHOOK_URL)."
        )

    if not pdf_path.is_file():
        raise EmailSendError(f"Signed contract file is missing: {pdf_path}")

    pdf_b64 = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
    filename = f"internship-agreement-{candidate_name.replace(' ', '-').lower()}.pdf"

    payload = {
        "to": to,
        "subject": subject,
        "body": body,
        "filename": filename,
        "pdf_base64": pdf_b64,
    }

    try:
        response = httpx.post(
            settings.n8n_email_webhook_url,
            json=payload,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        message = (
            f"n8n webhook returned {exc.response.status_code}: {exc.response.text[:200]}"
        )
        logger.error("Contract email failed — %s", message)
        raise EmailSendError(message) from exc
    except httpx.HTTPError as exc:
        # Log the exception type too: a bare message like "" is common for
        # connect/DNS errors and tells the operator nothing on its own.
        message = f"Could not reach the n8n webhook ({type(exc).__name__}): {exc}"
        logger.error("Contract email failed — %s", message)
        raise EmailSendError(message) from exc

    logger.info("Signed contract emailed via n8n to %s", to)
