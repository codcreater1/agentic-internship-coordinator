"""Turn three PDFs into structured fields, without trusting anything about them.

Two rules govern this module.

**Filenames are not evidence.** An attachment called ``attendance.pdf`` is
classified by what its text says, not by what it is called. Interns rename
files; senders reorder attachments; neither should change what the system
believes it is looking at. :func:`classify_document` reads the content.

**A scan is not a document.** A PDF containing only a photograph of a signed
form yields almost no extractable text. Rather than let such a file sail
through every text-based check vacuously satisfied, the caller refuses it
(see ``min_extractable_chars``). Vacuous passes are the dangerous kind.

This module is framework-agnostic: it imports nothing from FastAPI and raises
only domain exceptions from :mod:`app.core.exceptions`.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - older PyMuPDF, or not installed
    try:
        import fitz  # noqa: F401 - legacy module name, deprecated upstream
    except ImportError:
        fitz = None  # type: ignore[assignment]

from app.core.exceptions import CorruptedPdfError, EncryptedPdfError
from app.models.report import (
    AttendanceEntry,
    DocumentRole,
    EvaluationFields,
    ReportFields,
    TimesheetFields,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def extract_text(pdf_bytes: bytes) -> tuple[str, int]:
    """Return ``(text, page_count)`` for *pdf_bytes*.

    Raises:
        CorruptedPdfError: the bytes are not a parseable PDF.
        EncryptedPdfError: the PDF is password-protected. We refuse these
            rather than attempting an empty-password open, because a document
            we had to break into is not a document we should attest to.
    """
    if fitz is None:  # pragma: no cover
        raise CorruptedPdfError("PyMuPDF is not installed; cannot read PDFs.")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise CorruptedPdfError(f"PDF could not be parsed: {exc}") from exc

    try:
        if doc.needs_pass or doc.is_encrypted:
            raise EncryptedPdfError()

        if doc.page_count < 1:
            raise CorruptedPdfError("PDF contains no pages.")

        pages = [doc[i].get_text("text") for i in range(doc.page_count)]
        return "\n".join(pages), doc.page_count
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

# Markers are weighted by how strongly they identify a role. A phrase that
# could plausibly appear in any of the three documents earns a low weight;
# a phrase that belongs to exactly one document earns a high one.
_MARKERS: dict[DocumentRole, list[tuple[str, int]]] = {
    DocumentRole.REPORT: [
        ("internship report", 5),
        ("work performed", 3),
        ("technologies used", 3),
        ("challenges and solutions", 3),
        ("company overview", 2),
        ("introduction", 1),
        ("conclusion", 1),
    ],
    DocumentRole.EVALUATION: [
        ("employer evaluation form", 5),
        ("evaluation form", 4),
        ("overall score", 3),
        ("technical competence", 3),
        ("company stamp", 2),
        ("supervisor title", 2),
        ("punctuality", 2),
    ],
    DocumentRole.TIMESHEET: [
        ("attendance record", 5),
        ("total days recorded", 4),
        ("attendance sheet", 4),
        ("total hours", 2),
        ("daily attendance", 3),
    ],
}

# Below this score we decline to guess. An unrecognised attachment is reported
# as UNKNOWN and blocks the package, which is the honest outcome - guessing
# would mean running a timesheet parser over a report and reporting nonsense.
_MIN_CLASSIFY_SCORE = 4


def classify_document(text: str) -> tuple[DocumentRole, int]:
    """Identify which of the three documents *text* is.

    Returns ``(role, confidence)`` where confidence is the winning marker
    score. Role is :attr:`DocumentRole.UNKNOWN` when no role clears
    ``_MIN_CLASSIFY_SCORE`` or when the top two roles tie.
    """
    lowered = text.lower()

    scores: dict[DocumentRole, int] = {}
    for role, markers in _MARKERS.items():
        scores[role] = sum(weight for phrase, weight in markers if phrase in lowered)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_role, best_score = ranked[0]
    runner_up_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score < _MIN_CLASSIFY_SCORE or best_score == runner_up_score:
        return DocumentRole.UNKNOWN, best_score

    # A timesheet is mostly dated rows. If a document scores as a report but is
    # dominated by attendance rows, believe the rows over the vocabulary.
    if best_role is DocumentRole.REPORT and _dated_row_ratio(text) > 0.5:
        return DocumentRole.TIMESHEET, best_score

    return best_role, best_score


def _dated_row_ratio(text: str) -> float:
    """Fraction of non-empty lines that look like an attendance row."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0.0
    dated = sum(1 for ln in lines if _ROW_RE.match(ln.strip()))
    return dated / len(lines)


# ---------------------------------------------------------------------------
# Primitive parsers
# ---------------------------------------------------------------------------

_DATE_PATTERNS = (
    ("%Y-%m-%d", re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")),
    ("%d.%m.%Y", re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")),
    ("%d/%m/%Y", re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")),
)

# An attendance row: a date, then anything, then hours, then a status word.
_ROW_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4})\s+"
    r"(?P<rest>.*?)"
    r"(?P<hours>\d{1,2}(?:[.,]\d{1,2})?)\s+"
    r"(?P<status>[A-Za-zÇĞİÖŞÜçğıöşü]+)\s*$"
)


def parse_date(value: str | None) -> date | None:
    """Parse the first date found in *value*, in any of the accepted formats.

    Accepts ISO (2026-06-29), Turkish dotted (29.06.2026), and slashed
    (29/06/2026). Returns None when nothing parses - callers treat a missing
    date as a finding, never as today.
    """
    if not value:
        return None

    for fmt, pattern in _DATE_PATTERNS:
        match = pattern.search(value)
        if match:
            try:
                return datetime.strptime(match.group(1), fmt).date()
            except ValueError:
                continue
    return None


def find_label(text: str, *labels: str) -> str | None:
    """Return the value of the first ``Label: value`` line matching *labels*.

    Matching is case-insensitive and tolerant of the spacing and punctuation
    variations that survive a round-trip through PDF text extraction.
    """
    for label in labels:
        pattern = re.compile(
            rf"^\s*{re.escape(label)}\s*[:\-]\s*(.+?)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", value)
    return float(match.group(0).replace(",", ".")) if match else None


def _parse_bool(value: str | None) -> bool:
    """Interpret a yes/no field, defaulting to False.

    Defaulting to False matters: an unparseable ``Signed:`` field must not read
    as signed. Every ambiguity in this module resolves against the submission.
    """
    if not value:
        return False
    return value.strip().lower() in {"yes", "y", "true", "evet", "var", "signed", "1"}


# ---------------------------------------------------------------------------
# Document parsers
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^\s*(?:\d+[.)]\s*)?([A-Za-zÇĞİÖŞÜçğıöşü][\w \-/&]{3,60})\s*$")


def parse_report(text: str) -> ReportFields:
    """Extract identity, period, sections and prose from the written report."""
    body = _strip_label_lines(text)

    return ReportFields(
        student_name=find_label(text, "Student Name", "Name", "Ad Soyad"),
        student_id=find_label(text, "Student ID", "Student Number", "Student No", "Album Number"),
        company=find_label(text, "Company", "Company Name", "Firma"),
        department=find_label(text, "Department", "Unit"),
        start_date=parse_date(find_label(text, "Internship Start Date", "Start Date")),
        end_date=parse_date(find_label(text, "Internship End Date", "End Date")),
        declared_working_days=_parse_int(
            find_label(text, "Total Working Days", "Working Days")
        ),
        supervisor=find_label(text, "Supervisor", "Supervisor Name"),
        sections_found=_find_sections(text),
        word_count=len(body.split()),
        body_text=body,
    )


def parse_evaluation(text: str) -> EvaluationFields:
    """Extract scores and endorsement flags from the employer evaluation form."""
    scores: dict[str, int] = {}
    for criterion in (
        "Technical Competence",
        "Communication",
        "Punctuality",
        "Initiative",
        "Teamwork",
    ):
        value = _parse_int(find_label(text, criterion))
        if value is not None:
            scores[criterion.lower().replace(" ", "_")] = value

    return EvaluationFields(
        student_name=find_label(text, "Student Name", "Name", "Ad Soyad"),
        student_id=find_label(text, "Student ID", "Student Number", "Student No", "Album Number"),
        company=find_label(text, "Company", "Company Name", "Firma"),
        supervisor_name=find_label(text, "Supervisor Name", "Supervisor"),
        supervisor_title=find_label(text, "Supervisor Title", "Title"),
        evaluation_date=parse_date(find_label(text, "Evaluation Date", "Date")),
        scores=scores,
        overall_score=_parse_int(find_label(text, "Overall Score", "Total Score")),
        signed=_parse_bool(find_label(text, "Signed", "Signature")),
        stamped=_parse_bool(find_label(text, "Company Stamp", "Stamp")),
    )


def parse_timesheet(text: str) -> TimesheetFields:
    """Extract the dated attendance rows and the totals the document claims.

    Both are kept. The declared totals are what the company says; the parsed
    rows are what the document actually contains. The verification stage
    compares them, because a mismatch is exactly the kind of thing worth
    catching.
    """
    period = find_label(text, "Period", "Internship Period") or ""
    period_dates = _all_dates(period)

    entries: list[AttendanceEntry] = []
    for line in text.splitlines():
        match = _ROW_RE.match(line.strip())
        if not match:
            continue

        day = parse_date(match.group("date"))
        if day is None:
            continue

        entries.append(
            AttendanceEntry(
                day=day,
                hours=float(match.group("hours").replace(",", ".")),
                status=match.group("status").strip().lower(),
            )
        )

    return TimesheetFields(
        student_name=find_label(text, "Student Name", "Name", "Ad Soyad"),
        student_id=find_label(text, "Student ID", "Student Number", "Student No", "Album Number"),
        company=find_label(text, "Company", "Company Name", "Firma"),
        period_start=period_dates[0] if period_dates else None,
        period_end=period_dates[1] if len(period_dates) > 1 else None,
        entries=entries,
        declared_total_days=_parse_int(find_label(text, "Total Days Recorded", "Total Days")),
        declared_total_hours=_parse_float(find_label(text, "Total Hours")),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_dates(value: str) -> list[date]:
    """Every date in *value*, in order of appearance."""
    found: list[date] = []
    for fmt, pattern in _DATE_PATTERNS:
        for raw in pattern.findall(value):
            try:
                found.append((datetime.strptime(raw, fmt).date(), value.index(raw)))  # type: ignore[arg-type]
            except ValueError:
                continue
    # Sort by position in the string so "start - end" keeps its order.
    return [d for d, _ in sorted(found, key=lambda pair: pair[1])]  # type: ignore[misc]


def _strip_label_lines(text: str) -> str:
    """Drop ``Label: value`` header lines, keeping the prose.

    The originality check runs on prose only. Header lines are near-identical
    across every submission by construction, and including them would inflate
    similarity between two entirely unrelated reports.
    """
    kept = [
        line
        for line in text.splitlines()
        if not re.match(r"^\s*[A-Za-zÇĞİÖŞÜçğıöşü ]{3,40}\s*:\s*\S", line)
    ]
    return "\n".join(kept).strip()


def _find_sections(text: str) -> list[str]:
    """Return the lowercase headings that look like section titles."""
    sections: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or ":" in stripped or len(stripped.split()) > 6:
            continue
        match = _SECTION_RE.match(stripped)
        if match:
            sections.append(match.group(1).strip().lower())
    return sections
