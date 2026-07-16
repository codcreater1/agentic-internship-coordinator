from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


def _new_id() -> str:
    return uuid4().hex


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Application(BaseModel):
    name: str
    email: EmailStr
    cv_text: str


class SignApplicationRequest(BaseModel):
    signature_image_base64: str
    x: float = 70
    y: float = 600
    w: float = 220
    h: float = 70


class SendContractRequest(BaseModel):
    """Coordinator-composed delivery of the signed contract."""

    to: EmailStr
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)


class ApplicationResponse(BaseModel):
    id: str = Field(default_factory=_new_id)
    created_at: str = Field(default_factory=_now_iso)
    name: str
    email: EmailStr
    candidate_score: int
    recommended_role: str
    status: str
    report: str
    email_subject: str
    email_body: str
    contract_pdf_path: str | None = None
    signed_contract_path: str | None = None
    contract_task_id: str | None = None
    signed_contract_download_url: str | None = None
    # Delivery audit trail — who the signed contract went to, and when.
    contract_sent_to: str | None = None
    contract_sent_at: str | None = None