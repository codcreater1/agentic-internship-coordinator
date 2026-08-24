"""Schemas for the end-of-internship report package.

Mirrors :mod:`app.models.application`: a stable ``id``, a ``created_at``, and a
response model persisted whole as JSON by the repository.

The vocabulary is small on purpose:

  * a **submission** is one email — three PDFs plus the address they came from;
  * a **finding** is one thing wrong with it, at one severity;
  * the **severity** decides the status, and nothing else does.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


def _new_id() -> str:
    return uuid4().hex


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #


class DocumentRole(str, Enum):
    """What an attachment turned out to be.

    Determined by reading the document, never by trusting its filename.
    """

    REPORT = "report"
    EVALUATION = "evaluation"
    TIMESHEET = "timesheet"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """How much a finding matters — and therefore what happens to the package.

    The split between REJECT and CLARIFY is the important one. Almost
    everything wrong with a submission is fixable by the student, and this
    project does not refuse people for omissions they can correct. Only two
    failures are genuinely final: an employer score below the pass mark, and a
    report copied from someone else's accepted submission.
    """

    REJECT = "reject"
    CLARIFY = "clarify"
    WARNING = "warning"
    INFO = "info"


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #


class Finding(BaseModel):
    """One specific problem, phrased so the student can act on it.

    ``remedy`` is load-bearing, not decoration: the clarification email is
    assembled from the remedies of the CLARIFY findings. A finding without one
    produces a request the student cannot answer, which a test forbids.
    """

    code: str = Field(..., description="Stable machine-readable identifier, e.g. DAYS_SHORT.")
    severity: Severity
    message: str = Field(..., description="What is wrong, stated as fact.")
    remedy: str | None = Field(
        default=None,
        description="What the student must do to clear this finding.",
    )
    document: DocumentRole | None = Field(
        default=None,
        description="Which attachment it concerns; None if it spans documents.",
    )


# --------------------------------------------------------------------------- #
# Extracted document contents
# --------------------------------------------------------------------------- #


class AttendanceEntry(BaseModel):
    day: date
    hours: float
    status: str = "present"


class ReportFields(BaseModel):
    """Parsed out of the student's written report."""

    student_name: str | None = None
    student_id: str | None = None
    company: str | None = None
    department: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    declared_working_days: int | None = None
    supervisor: str | None = None
    sections_found: list[str] = Field(default_factory=list)
    word_count: int = 0
    body_text: str = Field(
        default="",
        description="Prose body used for the originality check, header lines excluded.",
    )


class EvaluationFields(BaseModel):
    """Parsed out of the employer's evaluation form."""

    student_name: str | None = None
    student_id: str | None = None
    company: str | None = None
    supervisor_name: str | None = None
    supervisor_title: str | None = None
    evaluation_date: date | None = None
    scores: dict[str, int] = Field(default_factory=dict)
    overall_score: int | None = None
    signed: bool = False
    stamped: bool = False


class TimesheetFields(BaseModel):
    """Parsed out of the attendance record."""

    student_name: str | None = None
    student_id: str | None = None
    company: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    entries: list[AttendanceEntry] = Field(default_factory=list)
    declared_total_days: int | None = None
    declared_total_hours: float | None = None


class DocumentSummary(BaseModel):
    """What intake learned about one attachment."""

    filename: str = Field(..., description="As supplied by the sender. Untrusted.")
    role: DocumentRole
    page_count: int
    char_count: int
    sha256: str = Field(..., description="Hash of the bytes as received.")
    size_bytes: int


# --------------------------------------------------------------------------- #
# Advisory review
# --------------------------------------------------------------------------- #


class AdvisoryReview(BaseModel):
    """The model's reading of the report. Advisory only.

    Nothing in the decision path consults it: the status is fixed before this
    runs. It exists so a coordinator opening the queue has a starting point and
    a few specific questions, not so a model can grade anybody.
    """

    available: bool = Field(
        ...,
        description="False when no model is configured or the call failed.",
    )
    summary: str = ""
    depth_rating: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="The model's view of technical specificity. Never gates a decision.",
    )
    role_alignment: str = ""
    questions_for_coordinator: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Persisted response
# --------------------------------------------------------------------------- #


class ReportSubmissionResponse(BaseModel):
    """One reviewed submission — the row the repository stores whole."""

    id: str = Field(default_factory=_new_id)
    created_at: str = Field(default_factory=_now_iso)

    intern_email: EmailStr
    application_id: str | None = Field(
        default=None,
        description=(
            "The application this student's placement was approved under, matched "
            "by email. None when no application is on file — a student whose "
            "application predates this system still gets reviewed."
        ),
    )

    status: str
    findings: list[Finding] = Field(default_factory=list)

    student_name: str | None = None
    student_id: str | None = None
    company: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    counted_working_days: int = 0
    total_hours: float = 0.0
    evaluation_score: int | None = None
    report_word_count: int = 0
    max_similarity: float = 0.0
    similarity_match: str | None = None

    documents: list[DocumentSummary] = Field(default_factory=list)
    package_sha256: str = Field(
        default="",
        description=(
            "Hash binding the three attachments together, printed on the "
            "certificate so it cannot be detached from what it attests to."
        ),
    )

    report: str = Field(default="", description="Coordinator-facing summary.")
    email_subject: str = ""
    email_body: str = ""
    advisory: AdvisoryReview | None = None

    certificate_task_id: str | None = None
    certificate_pdf_path: str | None = None
    signed_certificate_path: str | None = None
    signed_certificate_download_url: str | None = None
    signed_by: str | None = None
    signed_at: str | None = None
    coordinator_note: str | None = None

    @property
    def rejections(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.REJECT]

    @property
    def clarifications(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.CLARIFY]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #


class SignCertificateRequest(BaseModel):
    """Body for POST /reports/by-id/{id}/sign.

    ``coordinator_name`` is required and printed on the certificate. A
    signature with nobody's name on it is not a signature.
    """

    coordinator_name: str = Field(..., min_length=2, max_length=120)
    signature_image_base64: str | None = Field(
        default=None,
        description="Coordinator's drawn signature; falls back to the generated mark.",
    )
    acknowledge_warnings: bool = Field(
        default=False,
        description=(
            "Sign a package held at 'pending' for warnings. Rejected and "
            "clarification-held packages can never be signed."
        ),
    )
    note: str | None = Field(default=None, max_length=500)


class ReportListItem(BaseModel):
    """Compact row for the coordinator queue."""

    id: str
    created_at: str
    student_name: str | None
    student_id: str | None
    company: str | None
    status: str
    counted_working_days: int
    evaluation_score: int | None
    clarification_count: int
    warning_count: int
    signed_by: str | None = None
