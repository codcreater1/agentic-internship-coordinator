"""The gates. Decides what happens to a completed-internship package.

Everything here is deterministic. Given the same three documents it returns the
same findings, and every finding can be explained to a student in one sentence
without reference to a model.

That is the design argument. A completion certificate is an institutional claim
about a real person — that they attended twenty days at a named company. The
evidence for it is countable: dates, hours, a supervisor's signature, a score.
Counting is what computers are trustworthy at, so counting decides, and the
model is left to the one job it suits — reading prose and raising questions for
a human (see :mod:`app.services.report_service`).

**Severity is the whole contract.** This project does not refuse people for
omissions they can correct, at application time or here. So almost everything
wrong with a package is :attr:`~app.models.report.Severity.CLARIFY`: the student
is told exactly what to fix and the package waits. Only two failures are
:attr:`~app.models.report.Severity.REJECT`, because resending cannot fix either
of them:

  * the employer scored the internship below the pass mark;
  * the report was copied from another accepted submission.

Both of those need a conversation with the coordinator, not a new attachment.

Rules for adding a gate:

  * Ask whether a corrected resubmission would clear it. If yes, it is CLARIFY.
  * Every CLARIFY finding carries a ``remedy``. The clarification email is
    assembled from them, and a request the student cannot answer is a bug.
  * Ambiguity resolves against the submission. A field that will not parse is
    missing, not assumed.
"""

from __future__ import annotations

import logging
import unicodedata
from datetime import date

from app.core.report_constants import (
    COUNT_WEEKEND_DAYS,
    MAX_DAILY_HOURS,
    MIN_DAILY_HOURS,
    MIN_EVALUATION_SCORE,
    MIN_REPORT_WORDS,
    MIN_WORKING_DAYS,
    REQUIRED_REPORT_SECTIONS,
    SIMILARITY_REJECT_THRESHOLD,
    SIMILARITY_WARN_THRESHOLD,
    STATUS_APPROVED,
    STATUS_CLARIFICATION,
    STATUS_PENDING,
    STATUS_REJECTED,
)
from app.models.report import (
    DocumentRole,
    EvaluationFields,
    Finding,
    ReportFields,
    Severity,
    TimesheetFields,
)
from app.services.report_similarity import SimilarityIndex, similarity_index

logger = logging.getLogger(__name__)

_WEEKEND = {5, 6}  # Saturday, Sunday


# --------------------------------------------------------------------------- #
# Name normalisation
# --------------------------------------------------------------------------- #

# Neither Turkish dotted/dotless I nor Polish crossed L survives ASCII case
# folding, and this university's intake is full of both. Fold them explicitly:
# without it, "İNCİ" and "inci" read as two different students, and a package
# gets held because a company typed a name in capitals.
_FOLD = str.maketrans({
    "İ": "i", "I": "i", "ı": "i",
    "Ş": "s", "ş": "s",
    "Ğ": "g", "ğ": "g",
    "Ü": "u", "ü": "u",
    "Ö": "o", "ö": "o",
    "Ç": "c", "ç": "c",
    "Ł": "l", "ł": "l",
})


def normalize_name(value: str | None) -> str:
    """Fold a name for comparison: lowercase, unaccented, single-spaced.

    Used only to compare documents against each other, never for display.
    """
    if not value:
        return ""
    folded = value.translate(_FOLD)
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFKD", folded) if not unicodedata.combining(ch)
    )
    return " ".join(stripped.lower().split())


def normalize_id(value: str | None) -> str:
    """Reduce a student ID to its alphanumerics, lowercased.

    Not digits-only: this university issues album numbers like ``s123456``,
    and stripping the letter would collide two different students.
    """
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isalnum()).lower()


# --------------------------------------------------------------------------- #
# The service
# --------------------------------------------------------------------------- #


class ReportVerificationService:
    """Runs every gate over one package and returns the findings."""

    def __init__(self, index: SimilarityIndex | None = None) -> None:
        # Injectable so tests use an isolated corpus rather than mutating the
        # process-wide index and making a later test fail as plagiarism.
        self.index = index if index is not None else similarity_index

    def verify(
        self,
        report: ReportFields,
        evaluation: EvaluationFields,
        timesheet: TimesheetFields,
        *,
        today: date | None = None,
    ) -> dict:
        """Run all gates. Returns the findings plus the figures they produced."""
        today = today or date.today()
        findings: list[Finding] = []

        findings += self._check_identity(report, evaluation, timesheet)
        findings += self._check_company(report, evaluation, timesheet)

        start, end, period_findings = self._resolve_period(report, timesheet)
        findings += period_findings

        counted, hours, attendance_findings = self._check_attendance(
            timesheet, start, end, today
        )
        findings += attendance_findings

        findings += self._check_declared_totals(timesheet, report, counted)
        findings += self._check_evaluation(evaluation, end)
        findings += self._check_report_substance(report)

        similarity, match_id, similarity_findings = self._check_originality(report)
        findings += similarity_findings

        return {
            "findings": findings,
            "student_name": report.student_name or evaluation.student_name,
            "student_id": report.student_id or evaluation.student_id,
            "company": report.company or evaluation.company,
            "start_date": start,
            "end_date": end,
            "counted_working_days": counted,
            "total_hours": hours,
            "evaluation_score": evaluation.overall_score,
            "report_word_count": report.word_count,
            "max_similarity": similarity,
            "similarity_match": match_id,
        }

    # ------------------------------------------------------------------ #
    # Identity
    # ------------------------------------------------------------------ #

    def _check_identity(
        self,
        report: ReportFields,
        evaluation: EvaluationFields,
        timesheet: TimesheetFields,
    ) -> list[Finding]:
        """The three documents must be about the same student.

        This catches the most common real problem: a student attaching a
        classmate's form, or reusing a template and forgetting a name.
        """
        findings: list[Finding] = []

        names = {
            DocumentRole.REPORT: report.student_name,
            DocumentRole.EVALUATION: evaluation.student_name,
            DocumentRole.TIMESHEET: timesheet.student_name,
        }
        ids = {
            DocumentRole.REPORT: report.student_id,
            DocumentRole.EVALUATION: evaluation.student_id,
            DocumentRole.TIMESHEET: timesheet.student_id,
        }

        for role, value in names.items():
            if not value:
                findings.append(
                    Finding(
                        code="NAME_MISSING",
                        severity=Severity.CLARIFY,
                        message=f"The {role.value} does not state a student name.",
                        remedy=f"Add a 'Student Name:' line to your {role.value}.",
                        document=role,
                    )
                )

        if len({normalize_name(v) for v in names.values() if v}) > 1:
            listed = ", ".join(f"{r.value}: {v}" for r, v in names.items() if v)
            findings.append(
                Finding(
                    code="NAME_MISMATCH",
                    severity=Severity.CLARIFY,
                    message=f"The three documents name different students ({listed}).",
                    remedy=(
                        "All three documents must belong to the same student. Check "
                        "that you attached your own evaluation form and attendance "
                        "record, then resend all three."
                    ),
                )
            )

        distinct_ids = {normalize_id(v) for v in ids.values() if v}
        if len(distinct_ids) > 1:
            listed = ", ".join(f"{r.value}: {v}" for r, v in ids.items() if v)
            findings.append(
                Finding(
                    code="STUDENT_ID_MISMATCH",
                    severity=Severity.CLARIFY,
                    message=f"The documents carry different student IDs ({listed}).",
                    remedy="Correct the student ID so it matches on all three documents.",
                )
            )
        elif not distinct_ids:
            findings.append(
                Finding(
                    code="STUDENT_ID_MISSING",
                    severity=Severity.CLARIFY,
                    message="No student ID appears on any document.",
                    remedy="Add your student ID number to all three documents.",
                )
            )

        return findings

    # ------------------------------------------------------------------ #
    # Company
    # ------------------------------------------------------------------ #

    def _check_company(
        self,
        report: ReportFields,
        evaluation: EvaluationFields,
        timesheet: TimesheetFields,
    ) -> list[Finding]:
        companies = {
            DocumentRole.REPORT: report.company,
            DocumentRole.EVALUATION: evaluation.company,
            DocumentRole.TIMESHEET: timesheet.company,
        }
        present = {normalize_name(v) for v in companies.values() if v}

        if not present:
            return [
                Finding(
                    code="COMPANY_MISSING",
                    severity=Severity.CLARIFY,
                    message="No host organisation is named on any document.",
                    remedy="Add a 'Company:' line naming your host organisation.",
                )
            ]

        if len(present) > 1:
            listed = ", ".join(f"{r.value}: {v}" for r, v in companies.items() if v)
            return [
                Finding(
                    code="COMPANY_MISMATCH",
                    severity=Severity.CLARIFY,
                    message=f"The documents name different host organisations ({listed}).",
                    remedy="All three documents must name the same host organisation.",
                )
            ]

        return []

    # ------------------------------------------------------------------ #
    # Period
    # ------------------------------------------------------------------ #

    def _resolve_period(
        self,
        report: ReportFields,
        timesheet: TimesheetFields,
    ) -> tuple[date | None, date | None, list[Finding]]:
        """Establish the window every attendance date is judged against.

        The report declares it and the attendance record repeats it. They must
        agree: a system that silently picks one of two conflicting windows is
        deciding something it should be reporting.
        """
        findings: list[Finding] = []
        start = report.start_date or timesheet.period_start
        end = report.end_date or timesheet.period_end

        if start is None or end is None:
            findings.append(
                Finding(
                    code="PERIOD_MISSING",
                    severity=Severity.CLARIFY,
                    message="The internship start and end dates could not be read.",
                    remedy=(
                        "State the period on the report as 'Internship Start Date: "
                        "YYYY-MM-DD' and 'Internship End Date: YYYY-MM-DD'."
                    ),
                    document=DocumentRole.REPORT,
                )
            )
            return start, end, findings

        if end < start:
            findings.append(
                Finding(
                    code="PERIOD_INVALID",
                    severity=Severity.CLARIFY,
                    message=f"The end date ({end}) precedes the start date ({start}).",
                    remedy="Correct the internship start and end dates.",
                    document=DocumentRole.REPORT,
                )
            )

        report_period = (report.start_date, report.end_date)
        sheet_period = (timesheet.period_start, timesheet.period_end)
        if all(report_period) and all(sheet_period) and report_period != sheet_period:
            findings.append(
                Finding(
                    code="PERIOD_MISMATCH",
                    severity=Severity.CLARIFY,
                    message=(
                        f"The report declares {report.start_date} to {report.end_date}, "
                        f"but the attendance record covers {timesheet.period_start} to "
                        f"{timesheet.period_end}."
                    ),
                    remedy="Make the internship period identical on both documents.",
                )
            )

        return start, end, findings

    # ------------------------------------------------------------------ #
    # Attendance
    # ------------------------------------------------------------------ #

    def _check_attendance(
        self,
        timesheet: TimesheetFields,
        start: date | None,
        end: date | None,
        today: date,
    ) -> tuple[int, float, list[Finding]]:
        """Count the days that genuinely count, and report what did not.

        A day counts when it is inside the declared period, marked present,
        carries at least MIN_DAILY_HOURS, is not a duplicate, and is not a
        weekend unless weekends are configured to count.
        """
        findings: list[Finding] = []

        if not timesheet.entries:
            findings.append(
                Finding(
                    code="ATTENDANCE_EMPTY",
                    severity=Severity.CLARIFY,
                    message="The attendance record contains no readable daily entries.",
                    remedy=(
                        "Submit an attendance record listing one row per day as "
                        "'YYYY-MM-DD  Day  Hours  Present'."
                    ),
                    document=DocumentRole.TIMESHEET,
                )
            )
            return 0, 0.0, findings

        seen: set[date] = set()
        buckets: dict[str, list[date]] = {
            key: [] for key in
            ("duplicate", "outside", "future", "weekend", "short", "long", "absent")
        }

        counted = 0
        total_hours = 0.0

        for entry in sorted(timesheet.entries, key=lambda e: e.day):
            if entry.day in seen:
                buckets["duplicate"].append(entry.day)
                continue
            seen.add(entry.day)

            if entry.day > today:
                buckets["future"].append(entry.day)
                continue

            if start and end and not (start <= entry.day <= end):
                buckets["outside"].append(entry.day)
                continue

            if entry.status not in {"present", "p", "attended", "obecny"}:
                buckets["absent"].append(entry.day)
                continue

            if entry.hours > MAX_DAILY_HOURS:
                buckets["long"].append(entry.day)

            if entry.hours < MIN_DAILY_HOURS:
                buckets["short"].append(entry.day)
                continue

            if entry.day.weekday() in _WEEKEND:
                buckets["weekend"].append(entry.day)
                if not COUNT_WEEKEND_DAYS:
                    continue

            counted += 1
            total_hours += entry.hours

        findings += self._attendance_findings(buckets)

        if counted < MIN_WORKING_DAYS:
            findings.append(
                Finding(
                    code="DAYS_SHORT",
                    severity=Severity.CLARIFY,
                    message=(
                        f"Only {counted} attended working days could be verified; "
                        f"{MIN_WORKING_DAYS} are required."
                    ),
                    remedy=(
                        f"Submit an attendance record showing at least {MIN_WORKING_DAYS} "
                        f"attended working days of at least {MIN_DAILY_HOURS:g} hours "
                        "each, inside the declared internship period. If you did work "
                        "those days, ask the company to reissue the record."
                    ),
                    document=DocumentRole.TIMESHEET,
                )
            )

        return counted, round(total_hours, 2), findings

    def _attendance_findings(self, buckets: dict[str, list[date]]) -> list[Finding]:
        """Turn the excluded-day buckets into findings.

        Split out from the counting loop so the loop reads as arithmetic and
        this reads as reporting.
        """
        findings: list[Finding] = []

        if buckets["duplicate"]:
            findings.append(
                Finding(
                    code="DUPLICATE_DATES",
                    severity=Severity.CLARIFY,
                    message=(
                        f"{len(buckets['duplicate'])} date(s) appear more than once: "
                        f"{_list_dates(buckets['duplicate'])}."
                    ),
                    remedy="Remove the duplicated rows; each day may appear only once.",
                    document=DocumentRole.TIMESHEET,
                )
            )

        if buckets["future"]:
            findings.append(
                Finding(
                    code="FUTURE_DATES",
                    severity=Severity.CLARIFY,
                    message=(
                        f"The record claims {len(buckets['future'])} day(s) that have "
                        f"not happened yet: {_list_dates(buckets['future'])}."
                    ),
                    remedy="Submit the attendance record after the internship has ended.",
                    document=DocumentRole.TIMESHEET,
                )
            )

        if buckets["outside"]:
            findings.append(
                Finding(
                    code="DATES_OUTSIDE_PERIOD",
                    severity=Severity.CLARIFY,
                    message=(
                        f"{len(buckets['outside'])} attendance date(s) fall outside the "
                        f"declared period: {_list_dates(buckets['outside'])}."
                    ),
                    remedy=(
                        "Either correct the declared internship period or remove the "
                        "days outside it."
                    ),
                    document=DocumentRole.TIMESHEET,
                )
            )

        if buckets["long"]:
            findings.append(
                Finding(
                    code="HOURS_IMPLAUSIBLE",
                    severity=Severity.WARNING,
                    message=(
                        f"{len(buckets['long'])} day(s) log more than {MAX_DAILY_HOURS:g} "
                        f"hours: {_list_dates(buckets['long'])}."
                    ),
                    remedy="A coordinator should confirm these hours with the supervisor.",
                    document=DocumentRole.TIMESHEET,
                )
            )

        if buckets["short"]:
            findings.append(
                Finding(
                    code="HOURS_SHORT",
                    severity=Severity.WARNING,
                    message=(
                        f"{len(buckets['short'])} day(s) log fewer than "
                        f"{MIN_DAILY_HOURS:g} hours and were not counted: "
                        f"{_list_dates(buckets['short'])}."
                    ),
                    remedy="Half days do not count toward the required total.",
                    document=DocumentRole.TIMESHEET,
                )
            )

        if buckets["weekend"] and not COUNT_WEEKEND_DAYS:
            findings.append(
                Finding(
                    code="WEEKEND_DAYS",
                    severity=Severity.WARNING,
                    message=(
                        f"{len(buckets['weekend'])} weekend day(s) were listed and not "
                        f"counted: {_list_dates(buckets['weekend'])}."
                    ),
                    remedy=(
                        "Weekend work counts only where the coordinator approved it in "
                        "advance."
                    ),
                    document=DocumentRole.TIMESHEET,
                )
            )

        if buckets["absent"]:
            findings.append(
                Finding(
                    code="ABSENT_DAYS",
                    severity=Severity.INFO,
                    message=(
                        f"{len(buckets['absent'])} day(s) are marked absent and were "
                        "not counted."
                    ),
                    document=DocumentRole.TIMESHEET,
                )
            )

        return findings

    # ------------------------------------------------------------------ #
    # Declared totals
    # ------------------------------------------------------------------ #

    def _check_declared_totals(
        self,
        timesheet: TimesheetFields,
        report: ReportFields,
        counted: int,
    ) -> list[Finding]:
        """Compare what the documents claim against the rows they show.

        A summary line saying 30 days above a table containing 18 is either a
        clerical error or an attempt to pass one. Either way a coordinator
        should see it rather than the system quietly believing the table.
        """
        findings: list[Finding] = []

        if timesheet.declared_total_days is not None and timesheet.declared_total_days != counted:
            findings.append(
                Finding(
                    code="TOTAL_DAYS_MISMATCH",
                    severity=Severity.WARNING,
                    message=(
                        f"The attendance record claims {timesheet.declared_total_days} "
                        f"total days, but {counted} verified working day(s) could be "
                        "counted from its own rows."
                    ),
                    remedy="Make the stated total match the days actually listed.",
                    document=DocumentRole.TIMESHEET,
                )
            )

        if (
            report.declared_working_days is not None
            and timesheet.declared_total_days is not None
            and report.declared_working_days != timesheet.declared_total_days
        ):
            findings.append(
                Finding(
                    code="DECLARED_DAYS_MISMATCH",
                    severity=Severity.WARNING,
                    message=(
                        f"The report states {report.declared_working_days} working days; "
                        f"the attendance record states {timesheet.declared_total_days}."
                    ),
                    remedy="State the same number of working days on both documents.",
                )
            )

        return findings

    # ------------------------------------------------------------------ #
    # Employer endorsement
    # ------------------------------------------------------------------ #

    def _check_evaluation(
        self,
        evaluation: EvaluationFields,
        end: date | None,
    ) -> list[Finding]:
        """The employer must actually have endorsed the internship.

        This is the only external attestation in the package — the report is
        written by the student and the attendance record is easy to fill in — so
        an unsigned form removes the one independent voice.

        A *low* score is the one finding here that rejects. Everything else is
        paperwork the student can chase; a supervisor who assessed the work as
        failing is a judgement, and no resubmission changes it.
        """
        findings: list[Finding] = []

        if evaluation.overall_score is None:
            findings.append(
                Finding(
                    code="EVAL_SCORE_MISSING",
                    severity=Severity.CLARIFY,
                    message="The evaluation form does not carry an overall score.",
                    remedy=(
                        "Ask your supervisor to complete the 'Overall Score:' field and "
                        "resend the form."
                    ),
                    document=DocumentRole.EVALUATION,
                )
            )
        elif evaluation.overall_score < MIN_EVALUATION_SCORE:
            findings.append(
                Finding(
                    code="EVAL_SCORE_LOW",
                    severity=Severity.REJECT,
                    message=(
                        f"The employer scored the internship {evaluation.overall_score}/100, "
                        f"below the passing mark of {MIN_EVALUATION_SCORE}."
                    ),
                    remedy=(
                        "An internship the host organisation assessed as failing cannot "
                        "be approved automatically. Contact the internship coordinator "
                        "directly to discuss your options."
                    ),
                    document=DocumentRole.EVALUATION,
                )
            )

        if not evaluation.signed:
            findings.append(
                Finding(
                    code="EVAL_UNSIGNED",
                    severity=Severity.CLARIFY,
                    message="The evaluation form is not marked as signed by the supervisor.",
                    remedy="Return the evaluation form to your supervisor to be signed.",
                    document=DocumentRole.EVALUATION,
                )
            )

        if not evaluation.stamped:
            findings.append(
                Finding(
                    code="EVAL_UNSTAMPED",
                    severity=Severity.CLARIFY,
                    message="The evaluation form does not carry a company stamp.",
                    remedy="Ask the host organisation to stamp the evaluation form.",
                    document=DocumentRole.EVALUATION,
                )
            )

        if not evaluation.supervisor_name:
            findings.append(
                Finding(
                    code="SUPERVISOR_MISSING",
                    severity=Severity.CLARIFY,
                    message="The evaluation form does not name the supervisor who signed it.",
                    remedy="Ask your supervisor to add their name and title to the form.",
                    document=DocumentRole.EVALUATION,
                )
            )

        if evaluation.evaluation_date and end and evaluation.evaluation_date < end:
            findings.append(
                Finding(
                    code="EVAL_DATED_EARLY",
                    severity=Severity.WARNING,
                    message=(
                        f"The evaluation form is dated {evaluation.evaluation_date}, before "
                        f"the internship ended on {end}."
                    ),
                    remedy=(
                        "An evaluation signed before the internship ended cannot cover the "
                        "whole period."
                    ),
                    document=DocumentRole.EVALUATION,
                )
            )

        return findings

    # ------------------------------------------------------------------ #
    # Report substance
    # ------------------------------------------------------------------ #

    def _check_report_substance(self, report: ReportFields) -> list[Finding]:
        """Structural checks on the written report — not a judgement of quality.

        Word count and section presence are weak proxies, deliberately. They
        catch the empty submission. Judging whether the report is any good is a
        coordinator's job, informed by the advisory review.
        """
        findings: list[Finding] = []

        if report.word_count < MIN_REPORT_WORDS:
            findings.append(
                Finding(
                    code="REPORT_SHORT",
                    severity=Severity.CLARIFY,
                    message=(
                        f"The report body is {report.word_count} words; at least "
                        f"{MIN_REPORT_WORDS} are required."
                    ),
                    remedy=(
                        f"Expand the report to at least {MIN_REPORT_WORDS} words "
                        "describing the work you actually did."
                    ),
                    document=DocumentRole.REPORT,
                )
            )

        found = " | ".join(report.sections_found).lower()
        missing = [s for s in REQUIRED_REPORT_SECTIONS if s not in found]
        if missing:
            findings.append(
                Finding(
                    code="SECTIONS_MISSING",
                    severity=Severity.CLARIFY,
                    message=f"The report is missing required section(s): {', '.join(missing)}.",
                    remedy=(
                        "Add the missing sections as headings. Required sections: "
                        f"{', '.join(REQUIRED_REPORT_SECTIONS)}."
                    ),
                    document=DocumentRole.REPORT,
                )
            )

        return findings

    # ------------------------------------------------------------------ #
    # Originality
    # ------------------------------------------------------------------ #

    def _check_originality(
        self,
        report: ReportFields,
    ) -> tuple[float, str | None, list[Finding]]:
        """Compare this report against every previously accepted one."""
        if not report.body_text.strip():
            return 0.0, None, []

        score, match_id = self.index.most_similar(report.body_text)

        if score >= SIMILARITY_REJECT_THRESHOLD:
            return score, match_id, [
                Finding(
                    code="REPORT_NOT_ORIGINAL",
                    severity=Severity.REJECT,
                    message=(
                        f"The report is {score:.0%} similar to a previously accepted "
                        f"submission ({match_id})."
                    ),
                    remedy=(
                        "Contact the internship coordinator. If you believe this is an "
                        "error — for example you and a teammate documented the same "
                        "project — say so and it will be reviewed by a person."
                    ),
                    document=DocumentRole.REPORT,
                )
            ]

        if score >= SIMILARITY_WARN_THRESHOLD:
            return score, match_id, [
                Finding(
                    code="REPORT_SIMILARITY_ELEVATED",
                    severity=Severity.WARNING,
                    message=(
                        f"The report is {score:.0%} similar to a previously accepted "
                        f"submission ({match_id}). This is legitimate for two interns on "
                        "the same team and needs a human to judge."
                    ),
                    document=DocumentRole.REPORT,
                )
            ]

        return score, match_id, []


# --------------------------------------------------------------------------- #
# Decision
# --------------------------------------------------------------------------- #


def decide_status(findings: list[Finding]) -> str:
    """Map findings to a status.

    Deliberately trivial, and deliberately the only place the mapping exists.
    Note the order: a rejection outranks a clarification, so a student whose
    employer failed them is not also asked to chase a missing stamp.

    ``approved`` means the package is sound and is *waiting* for a signature.
    Passing every gate is necessary for a certificate, never sufficient.
    """
    if any(f.severity is Severity.REJECT for f in findings):
        return STATUS_REJECTED
    if any(f.severity is Severity.CLARIFY for f in findings):
        return STATUS_CLARIFICATION
    if any(f.severity is Severity.WARNING for f in findings):
        return STATUS_PENDING
    return STATUS_APPROVED


def _list_dates(days: list[date], limit: int = 5) -> str:
    """Format a date list for a message, truncating politely."""
    shown = [d.isoformat() for d in days[:limit]]
    if len(days) > limit:
        shown.append(f"and {len(days) - limit} more")
    return ", ".join(shown)


# Module-level singleton, matching the other services in this package.
report_verification_service = ReportVerificationService()
