"""End-of-internship report review — gate and API tests (offline, see conftest).

Two layers:

  * gate tests build field objects directly, break exactly one property of a
    valid package, and assert the finding **and its severity**. Severity is the
    part worth asserting: this system's whole contract is that a fixable
    omission holds a package for clarification rather than rejecting a student,
    so a check that rejects where it should clarify is a real defect that a
    "some finding fired" assertion would miss.

  * API tests run real generated PDFs through the full HTTP surface — real text
    extraction, real certificate rendering, real signature embedding. The ones
    that matter most are the refusals.
"""

from __future__ import annotations

import base64
import io
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.report_constants import (
    STATUS_APPROVED,
    STATUS_CLARIFICATION,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_SIGNED,
)
from app.main import app
from app.models.report import (
    AttendanceEntry,
    EvaluationFields,
    Finding,
    ReportFields,
    Severity,
    TimesheetFields,
)
from app.routers.reports import get_report_service
from app.services.report_service import ReportService
from app.services.report_similarity import SimilarityIndex
from app.services.report_verification import (
    ReportVerificationService,
    decide_status,
    normalize_id,
    normalize_name,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ata-test-docs" / "tool"))
from completion_docs import Package, generate, write_attendance  # noqa: E402

client = TestClient(app)

COORDINATOR = "dr Anna Zielińska"

START = date(2026, 6, 29)
END = date(2026, 8, 7)
TODAY = date(2026, 8, 12)


# --------------------------------------------------------------------------- #
# Builders — a valid package, which each test then breaks in one way
# --------------------------------------------------------------------------- #


def working_days(count: int, start: date = START, hours: float = 8.0) -> list[AttendanceEntry]:
    entries: list[AttendanceEntry] = []
    cursor = start
    while len(entries) < count:
        if cursor.weekday() < 5:
            entries.append(AttendanceEntry(day=cursor, hours=hours, status="present"))
        cursor += timedelta(days=1)
    return entries


@pytest.fixture
def verifier() -> ReportVerificationService:
    """A verifier with a private corpus, so one test cannot make another fail
    later with a plagiarism finding."""
    return ReportVerificationService(index=SimilarityIndex())


@pytest.fixture
def report() -> ReportFields:
    return ReportFields(
        student_name="Zofia Wiśniewska",
        student_id="s24187",
        company="Nova Logistics Software",
        department="Backend Platform Team",
        start_date=START,
        end_date=END,
        declared_working_days=30,
        supervisor="Marcin Kowalczyk",
        sections_found=[
            "1. introduction",
            "2. company overview",
            "3. work performed",
            "4. technologies used",
            "5. challenges and solutions",
            "6. conclusion",
        ],
        word_count=640,
        body_text=" ".join(f"paragraph{i} about caching and postgres" for i in range(160)),
    )


@pytest.fixture
def evaluation() -> EvaluationFields:
    return EvaluationFields(
        student_name="Zofia Wiśniewska",
        student_id="s24187",
        company="Nova Logistics Software",
        supervisor_name="Marcin Kowalczyk",
        supervisor_title="Senior Backend Engineer",
        evaluation_date=date(2026, 8, 10),
        scores={"technical_competence": 86},
        overall_score=84,
        signed=True,
        stamped=True,
    )


@pytest.fixture
def timesheet() -> TimesheetFields:
    entries = working_days(30)
    return TimesheetFields(
        student_name="Zofia Wiśniewska",
        student_id="s24187",
        company="Nova Logistics Software",
        period_start=START,
        period_end=END,
        entries=entries,
        declared_total_days=len(entries),
        declared_total_hours=sum(e.hours for e in entries),
    )


def run(verifier, report, evaluation, timesheet, today=TODAY) -> dict:
    return verifier.verify(report, evaluation, timesheet, today=today)


def codes(verdict) -> set[str]:
    return {f.code for f in verdict["findings"]}


def severity_of(verdict, code: str) -> Severity:
    return next(f.severity for f in verdict["findings"] if f.code == code)


# --------------------------------------------------------------------------- #
# Baseline
# --------------------------------------------------------------------------- #


def test_valid_package_produces_no_findings(verifier, report, evaluation, timesheet):
    """If this fails, every other gate test in this file is meaningless."""
    verdict = run(verifier, report, evaluation, timesheet)

    assert verdict["findings"] == []
    assert decide_status(verdict["findings"]) == STATUS_APPROVED
    assert verdict["counted_working_days"] == 30
    assert verdict["evaluation_score"] == 84


# --------------------------------------------------------------------------- #
# The severity contract — fixable things must not reject anyone
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "break_it,expected_code",
    [
        (lambda r, e, t: setattr(e, "signed", False), "EVAL_UNSIGNED"),
        (lambda r, e, t: setattr(e, "stamped", False), "EVAL_UNSTAMPED"),
        (lambda r, e, t: setattr(e, "supervisor_name", None), "SUPERVISOR_MISSING"),
        (lambda r, e, t: setattr(e, "overall_score", None), "EVAL_SCORE_MISSING"),
        (lambda r, e, t: setattr(e, "student_name", "Someone Else"), "NAME_MISMATCH"),
        (lambda r, e, t: setattr(t, "student_id", "s99999"), "STUDENT_ID_MISMATCH"),
        (lambda r, e, t: setattr(e, "company", "Other Company"), "COMPANY_MISMATCH"),
        (lambda r, e, t: setattr(r, "word_count", 90), "REPORT_SHORT"),
        (lambda r, e, t: setattr(r, "sections_found", []), "SECTIONS_MISSING"),
        (lambda r, e, t: setattr(t, "entries", working_days(18)), "DAYS_SHORT"),
        (lambda r, e, t: setattr(t, "entries", []), "ATTENDANCE_EMPTY"),
    ],
)
def test_fixable_problems_ask_for_a_correction_rather_than_rejecting(
    verifier, report, evaluation, timesheet, break_it, expected_code
):
    """Nobody is refused for something a resubmission would fix.

    This is the principle the application flow already follows for incomplete
    applications, applied at the other end of the internship.
    """
    break_it(report, evaluation, timesheet)
    verdict = run(verifier, report, evaluation, timesheet)

    assert expected_code in codes(verdict)
    assert severity_of(verdict, expected_code) is Severity.CLARIFY
    assert decide_status(verdict["findings"]) == STATUS_CLARIFICATION


def test_a_failing_employer_score_is_a_rejection_not_a_correction(
    verifier, report, evaluation, timesheet
):
    """The supervisor's judgement is not paperwork; resending cannot change it."""
    evaluation.overall_score = 41
    verdict = run(verifier, report, evaluation, timesheet)

    assert severity_of(verdict, "EVAL_SCORE_LOW") is Severity.REJECT
    assert decide_status(verdict["findings"]) == STATUS_REJECTED


def test_a_copied_report_is_a_rejection_not_a_correction(
    verifier, report, evaluation, timesheet
):
    verifier.index.add("earlier-submission", report.body_text)
    verdict = run(verifier, report, evaluation, timesheet)

    assert severity_of(verdict, "REPORT_NOT_ORIGINAL") is Severity.REJECT
    assert verdict["max_similarity"] > 0.99
    assert verdict["similarity_match"] == "earlier-submission"


def test_a_rejection_outranks_a_clarification(verifier, report, evaluation, timesheet):
    """A student whose employer failed them is not also told to chase a stamp."""
    evaluation.overall_score = 30
    evaluation.stamped = False

    verdict = run(verifier, report, evaluation, timesheet)

    assert {"EVAL_SCORE_LOW", "EVAL_UNSTAMPED"} <= codes(verdict)
    assert decide_status(verdict["findings"]) == STATUS_REJECTED


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Zofia Wiśniewska", "zofia wisniewska"),
        ("ZOFIA WIŚNIEWSKA", "zofia wisniewska"),
        ("  zofia   wiśniewska ", "zofia wisniewska"),
        ("Michał Łukasiewicz", "michal lukasiewicz"),
        ("Elif Şahin", "elif sahin"),
        ("ELİF ŞAHİN", "elif sahin"),
    ],
)
def test_names_fold_for_comparison(raw, expected):
    """Polish ł and Turkish dotted I do not survive naive case folding.

    A package must not be held because the company typed a name in capitals.
    """
    assert normalize_name(raw) == expected


def test_student_ids_keep_their_letter():
    """This university issues album numbers like s24187.

    Comparison strips punctuation and spacing but not letters: dropping the
    prefix would make s24187 and 24187 the same student, and transposed digits
    must stay different.
    """
    assert normalize_id("S-24187") == normalize_id("s24187") == "s24187"
    assert normalize_id("s 24187") == "s24187"
    assert normalize_id("s24187") != normalize_id("s24178")


def test_case_difference_alone_is_not_a_mismatch(verifier, report, evaluation, timesheet):
    evaluation.student_name = "ZOFIA WIŚNIEWSKA"
    timesheet.student_name = "zofia wiśniewska"

    assert "NAME_MISMATCH" not in codes(run(verifier, report, evaluation, timesheet))


# --------------------------------------------------------------------------- #
# Attendance arithmetic
# --------------------------------------------------------------------------- #


def test_exactly_the_minimum_passes(verifier, report, evaluation, timesheet):
    """A boundary that rejects the compliant case is worse than no boundary."""
    timesheet.entries = working_days(20)
    timesheet.declared_total_days = 20
    report.declared_working_days = 20

    verdict = run(verifier, report, evaluation, timesheet)

    assert "DAYS_SHORT" not in codes(verdict)
    assert verdict["counted_working_days"] == 20


def test_weekend_days_do_not_pad_the_count(verifier, report, evaluation, timesheet):
    """Twenty weekdays plus the weekends between them is not twenty-six days."""
    saturday = date(2026, 7, 4)
    timesheet.entries = working_days(20) + [
        AttendanceEntry(day=saturday, hours=8.0, status="present"),
        AttendanceEntry(day=saturday + timedelta(days=1), hours=8.0, status="present"),
    ]

    verdict = run(verifier, report, evaluation, timesheet)

    assert verdict["counted_working_days"] == 20
    assert severity_of(verdict, "WEEKEND_DAYS") is Severity.WARNING


def test_duplicate_dates_are_counted_once(verifier, report, evaluation, timesheet):
    entries = working_days(21)
    timesheet.entries = entries + [entries[0], entries[1]]

    verdict = run(verifier, report, evaluation, timesheet)

    assert "DUPLICATE_DATES" in codes(verdict)
    assert verdict["counted_working_days"] == 21


def test_future_dates_are_not_counted(verifier, report, evaluation, timesheet):
    report.end_date = TODAY + timedelta(days=30)
    timesheet.period_end = report.end_date
    timesheet.entries = working_days(30, start=TODAY - timedelta(days=2))

    verdict = run(verifier, report, evaluation, timesheet)

    assert "FUTURE_DATES" in codes(verdict)
    assert verdict["counted_working_days"] < 30


def test_days_before_the_period_are_excluded(verifier, report, evaluation, timesheet):
    """Ordered so a date both future and out-of-period reports as future — the
    more specific and more actionable of the two — so this uses a past date."""
    timesheet.entries = working_days(30) + [
        AttendanceEntry(day=START - timedelta(days=7), hours=8.0, status="present")
    ]

    verdict = run(verifier, report, evaluation, timesheet)

    assert "DATES_OUTSIDE_PERIOD" in codes(verdict)
    assert verdict["counted_working_days"] == 30


def test_implausible_hours_warn_but_still_count(verifier, report, evaluation, timesheet):
    """A fourteen-hour day warrants asking the supervisor, not refusing a student."""
    entries = working_days(30)
    entries[0] = AttendanceEntry(day=entries[0].day, hours=14.0, status="present")
    timesheet.entries = entries

    verdict = run(verifier, report, evaluation, timesheet)

    assert severity_of(verdict, "HOURS_IMPLAUSIBLE") is Severity.WARNING
    assert verdict["counted_working_days"] == 30
    assert decide_status(verdict["findings"]) == STATUS_PENDING


def test_a_declared_total_that_contradicts_the_rows_warns(
    verifier, report, evaluation, timesheet
):
    timesheet.declared_total_days = 45
    verdict = run(verifier, report, evaluation, timesheet)

    assert severity_of(verdict, "TOTAL_DAYS_MISMATCH") is Severity.WARNING


def test_period_disagreement_between_documents_is_flagged(
    verifier, report, evaluation, timesheet
):
    timesheet.period_end = END + timedelta(days=14)
    assert "PERIOD_MISMATCH" in codes(run(verifier, report, evaluation, timesheet))


# --------------------------------------------------------------------------- #
# Decision mapping
# --------------------------------------------------------------------------- #


def test_decision_order():
    reject = Finding(code="R", severity=Severity.REJECT, message="r")
    clarify = Finding(code="C", severity=Severity.CLARIFY, message="c")
    warn = Finding(code="W", severity=Severity.WARNING, message="w")
    info = Finding(code="I", severity=Severity.INFO, message="i")

    assert decide_status([reject, clarify, warn]) == STATUS_REJECTED
    assert decide_status([clarify, warn]) == STATUS_CLARIFICATION
    assert decide_status([warn, info]) == STATUS_PENDING
    assert decide_status([info]) == STATUS_APPROVED
    assert decide_status([]) == STATUS_APPROVED


def test_every_actionable_finding_carries_a_remedy(verifier, report, evaluation, timesheet):
    """The student's email is assembled from remedies.

    A finding without one produces a message the student cannot act on, so this
    asserts the property across a package broken in many ways at once.
    """
    evaluation.student_name = "Someone Else"
    evaluation.signed = False
    evaluation.stamped = False
    evaluation.overall_score = None
    evaluation.supervisor_name = None
    report.word_count = 10
    report.sections_found = []
    timesheet.entries = working_days(3)

    verdict = run(verifier, report, evaluation, timesheet)
    actionable = [
        f for f in verdict["findings"]
        if f.severity in (Severity.CLARIFY, Severity.REJECT)
    ]

    assert actionable
    assert [f.code for f in actionable if not f.remedy] == []


# --------------------------------------------------------------------------- #
# API — real PDFs through the full surface
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def packages(tmp_path_factory) -> dict[str, list[Path]]:
    base = tmp_path_factory.mktemp("completion")
    return {
        name: generate(name, base / name)
        for name in ("clean", "short-days", "unsigned", "name-mismatch")
    }


@pytest.fixture(autouse=True)
def isolated_service():
    """Give each API test a private originality corpus.

    Every generated sample shares the same report prose by construction, so a
    shared corpus would reject the second test to run as plagiarism.
    """
    index = SimilarityIndex()
    service = ReportService(
        verifier=ReportVerificationService(index=index),
        index=index,
    )
    app.dependency_overrides[get_report_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


def submit(paths, email="zofia@example.edu"):
    files = [
        ("files", (p.name, io.BytesIO(p.read_bytes()), "application/pdf")) for p in paths
    ]
    return client.post("/reports/", data={"intern_email": email}, files=files)


def sign(submission_id: str, **payload):
    payload.setdefault("coordinator_name", COORDINATOR)
    return client.post(f"/reports/by-id/{submission_id}/sign", json=payload)


def test_a_clean_package_is_approved_but_not_signed(packages):
    """The happy path stops one step short of a certificate, on purpose."""
    body = submit(packages["clean"]).json()

    assert body["status"] == STATUS_APPROVED
    assert body["findings"] == []
    assert body["counted_working_days"] == 30
    assert body["signed_by"] is None
    assert body["signed_certificate_download_url"] is None


def test_documents_are_classified_from_content_not_filename(packages, tmp_path):
    """Filenames are sender-controlled and must not steer classification."""
    renamed = []
    for n, path in enumerate(packages["clean"]):
        target = tmp_path / f"scan_{n}.pdf"
        target.write_bytes(path.read_bytes())
        renamed.append(target)

    body = submit(renamed).json()

    assert body["status"] == STATUS_APPROVED
    assert {d["role"] for d in body["documents"]} == {"report", "evaluation", "timesheet"}


def test_two_attachments_asks_for_the_third(packages):
    body = submit(packages["clean"][:2]).json()

    assert body["status"] == STATUS_CLARIFICATION
    assert "ATTACHMENT_COUNT" in {f["code"] for f in body["findings"]}
    assert "three PDF attachments" in body["email_body"]


def test_a_duplicated_document_is_reported(packages):
    report_pdf = packages["clean"][0]
    body = submit([report_pdf, report_pdf, packages["clean"][1]]).json()

    assert "DOCUMENT_DUPLICATED" in {f["code"] for f in body["findings"]}


def test_a_non_pdf_attachment_is_refused(packages, tmp_path):
    fake = tmp_path / "report.pdf"
    fake.write_bytes(b"A text file wearing a PDF extension.")

    body = submit([fake, *packages["clean"][1:]]).json()

    assert "ATTACHMENT_NOT_PDF" in {f["code"] for f in body["findings"]}


def test_the_package_hash_is_order_independent(packages):
    first = submit(packages["clean"]).json()
    second = submit(list(reversed(packages["clean"]))).json()

    assert first["package_sha256"] == second["package_sha256"]
    assert len(first["package_sha256"]) == 64


def test_the_clarification_email_says_what_to_fix(packages):
    body = submit(packages["short-days"]).json()

    assert body["status"] == STATUS_CLARIFICATION
    assert "What to do:" in body["email_body"]
    assert "20" in body["email_body"]


def test_a_submission_links_to_the_students_application(packages):
    """Placement approval and completion are two ends of one candidate's arc."""
    created = client.post(
        "/applications/",
        json={"name": "Zofia", "email": "linked@example.edu", "cv_text": "python fastapi"},
    ).json()

    body = submit(packages["clean"], email="linked@example.edu").json()

    assert body["application_id"] == created["id"]
    linked = client.get(f"/reports/for-application/{created['id']}").json()
    assert [s["id"] for s in linked] == [body["id"]]


def test_an_unmatched_email_is_still_reviewed(packages):
    """A student who applied before this system existed still gets reviewed."""
    body = submit(packages["clean"], email="nobody-on-file@example.edu").json()

    assert body["application_id"] is None
    assert body["status"] == STATUS_APPROVED


# --------------------------------------------------------------------------- #
# The signature gate
# --------------------------------------------------------------------------- #


def test_a_package_awaiting_the_student_cannot_be_signed(packages):
    """Signing here would certify a record that is still incomplete."""
    submission_id = submit(packages["unsigned"]).json()["id"]

    response = sign(submission_id, acknowledge_warnings=True)

    assert response.status_code == 409
    assert "waiting on the student" in response.json()["detail"]


def test_signing_requires_a_coordinator_name(packages):
    submission_id = submit(packages["clean"]).json()["id"]

    assert client.post(f"/reports/by-id/{submission_id}/sign", json={}).status_code == 422


def test_signing_an_approved_package_issues_a_certificate(packages):
    submission_id = submit(packages["clean"]).json()["id"]

    body = sign(submission_id).json()

    assert body["status"] == STATUS_SIGNED
    assert body["signed_by"] == COORDINATOR
    assert body["signed_certificate_download_url"]
    assert "Completion Certificate" in body["email_subject"]


def test_the_certificate_downloads_as_a_pdf_and_survives_a_second_read(packages):
    submission_id = submit(packages["clean"]).json()["id"]
    url = sign(submission_id).json()["signed_certificate_download_url"]

    first = client.get(url)
    assert first.status_code == 200
    assert first.content.startswith(b"%PDF-")
    assert client.get(url).status_code == 200


def test_a_forged_token_does_not_open_a_certificate(packages):
    submission_id = submit(packages["clean"]).json()["id"]
    sign(submission_id)

    response = client.get(
        f"/reports/by-id/{submission_id}/certificate?token=abc:99999999999:deadbeef"
    )
    assert response.status_code == 403


def test_signing_twice_is_refused(packages):
    submission_id = submit(packages["clean"]).json()["id"]
    sign(submission_id)

    response = sign(submission_id)

    assert response.status_code == 409
    assert "Already signed" in response.json()["detail"]


def test_open_points_must_be_acknowledged_before_signing(packages, tmp_path):
    submission_id = _pending_submission(packages, tmp_path)

    response = sign(submission_id)

    assert response.status_code == 409
    assert "acknowledge_warnings=true" in response.json()["detail"]


def test_open_points_can_be_acknowledged_deliberately(packages, tmp_path):
    submission_id = _pending_submission(packages, tmp_path)

    body = sign(
        submission_id,
        acknowledge_warnings=True,
        note="Confirmed the hours with the supervisor by phone.",
    ).json()

    assert body["status"] == STATUS_SIGNED


def _pending_submission(packages, tmp_path) -> str:
    """A package with open points but nothing blocking.

    Thirteen-hour days are implausible but not disqualifying: every required
    day is attended, so nothing holds it, but a coordinator should ask.
    """
    attendance = tmp_path / "attendance_long_hours.pdf"
    write_attendance(replace(Package(), daily_hours=13.0), attendance)

    body = submit([packages["clean"][0], packages["clean"][1], attendance]).json()
    assert body["status"] == STATUS_PENDING, body["findings"]
    return body["id"]


def test_a_custom_signature_image_is_accepted(packages):
    from app.services.signature_image_service import SignatureImageService

    png = base64.b64encode(SignatureImageService.create_company_signature()).decode()
    submission_id = submit(packages["clean"]).json()["id"]

    response = sign(submission_id, signature_image_base64=f"data:image/png;base64,{png}")

    assert response.status_code == 200


def test_a_corrupt_signature_image_is_refused(packages):
    submission_id = submit(packages["clean"]).json()["id"]

    assert sign(submission_id, signature_image_base64="not-base64!!").status_code == 400


def test_the_queue_can_be_filtered_by_status(packages):
    # Order matters, and demonstrates the corpus rule: every generated sample
    # shares the same report prose, so if `clean` were submitted first it would
    # be indexed as accepted and `short-days` would come back as a copy. A
    # clarification-held package is never indexed, so this order is clean.
    held_id = submit(packages["short-days"]).json()["id"]
    approved_id = submit(packages["clean"]).json()["id"]

    approved = client.get("/reports/", params={"status": STATUS_APPROVED}).json()
    held = client.get("/reports/", params={"status": STATUS_CLARIFICATION}).json()

    assert approved_id in {row["id"] for row in approved}
    assert held_id in {row["id"] for row in held}
    assert approved_id not in {row["id"] for row in held}


def test_submitted_documents_can_be_read_back(packages):
    submission_id = submit(packages["clean"]).json()["id"]

    response = client.get(f"/reports/by-id/{submission_id}/attachments/evaluation")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_an_unknown_submission_is_a_404():
    assert client.get("/reports/by-id/does-not-exist").status_code == 404
