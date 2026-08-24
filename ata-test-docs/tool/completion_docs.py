"""Generate the three documents an intern emails at the end of a placement.

The companion to :mod:`generate` in this directory. That one produces the
*application* corpus — UTA Appendix No. 3 forms for the CV-screening flow. This
one produces the *completion* package the report reviewer consumes: the
student's report, the employer evaluation form, and the attendance record.

Without it there is nothing to test against, and a verification system whose
only inputs are the documents it was designed around has never been shown one
nobody intended to send — which is exactly what the gates exist for. So the
failures are first-class output here, not an afterthought.

Each scenario perturbs one thing and leaves everything else valid, which makes a
firing gate diagnostic: ``--scenario short-days`` should produce DAYS_SHORT and
nothing else.

    python tool/completion_docs.py --scenario clean --out completion/clean
    python tool/completion_docs.py --all --out completion

All data is synthetic — invented names, IDs and companies. No real person or
placement is referenced.

Scenarios, and what the reviewer should do with each:

    clean          approved             every gate passes
    short-days     request_clarification 18 attended days against a required 20
    name-mismatch  request_clarification the evaluation form names another student
    unsigned       request_clarification the supervisor never signed the form
    thin-report    request_clarification the report is a few sentences long
    weekend-pad    request_clarification the day count only reaches 20 with weekends
    future-dates   request_clarification attendance claims days not yet happened
    scan           request_clarification the report is an image with no text
    copied         rejected             the report is lifted from another student

Note the column: only ``copied`` is a rejection. Everything else is something
the student can correct and resend, and this system does not refuse people for
that — see :mod:`app.core.report_constants`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

_FONT_CANDIDATES = (
    ("Arial", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("DejaVuSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
)

_TRANSLITERATE = str.maketrans({
    "ğ": "g", "Ğ": "G", "ı": "i", "İ": "I", "ş": "s", "Ş": "S",
    "ç": "c", "Ç": "C", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
})


def _fonts() -> tuple[str, str, bool]:
    for family, regular, bold in _FONT_CANDIDATES:
        try:
            pdfmetrics.registerFont(TTFont(family, regular))
            pdfmetrics.registerFont(TTFont(f"{family}-Bold", bold))
            return family, f"{family}-Bold", True
        except Exception:  # noqa: BLE001
            continue
    return "Helvetica", "Helvetica-Bold", False


REGULAR, BOLD, UNICODE_OK = _fonts()


def _t(value: object) -> str:
    text = "" if value is None else str(value)
    return text if UNICODE_OK else text.translate(_TRANSLITERATE)


# ---------------------------------------------------------------------------
# Package data
# ---------------------------------------------------------------------------

REPORT_SECTIONS: list[tuple[str, str]] = [
    (
        "1. Introduction",
        "This report covers my forty-day summer internship in the backend platform "
        "team. I joined at the start of the summer with some university experience "
        "in Python and almost none in running services that other people depend on. "
        "The purpose of this report is to describe the work I was given, the "
        "decisions I had to make, and what I would do differently now.",
    ),
    (
        "2. Company Overview",
        "The company builds logistics software for regional distributors. The "
        "engineering organisation is split into four teams; I sat with the backend "
        "platform team, which owns the internal service that every customer-facing "
        "product calls for address validation and route estimates. The team runs "
        "two-week iterations with a Monday planning session and a Friday review, "
        "and every change ships behind a feature flag.",
    ),
    (
        "3. Work Performed",
        "My first two weeks were spent on the test suite. The address validation "
        "service had a set of integration tests that took eleven minutes to run "
        "because each one started a fresh Postgres container. I rewrote them to "
        "share a single container and roll back a transaction after each test, "
        "which brought the suite down to just under ninety seconds. The change was "
        "not complicated but it taught me how much of the team's day was being "
        "spent waiting. "
        "For the remainder of the internship I worked on a caching layer in front "
        "of the route estimate endpoint. Estimates are expensive to compute and are "
        "requested repeatedly for the same origin and destination pairs within a "
        "planning session. I implemented a Redis-backed cache keyed on a normalised "
        "form of the request, with a fifteen-minute expiry agreed with the team "
        "after we looked at how often underlying road data actually changes. "
        "I also wrote the metrics for it, and a small admin endpoint that reports "
        "the hit rate so the team could see whether the cache was earning its "
        "complexity. In the last week it was serving about sixty-one percent of "
        "estimate requests without recomputation.",
    ),
    (
        "4. Technologies Used",
        "The service is written in Python using FastAPI, backed by PostgreSQL, with "
        "Redis for caching and RabbitMQ for asynchronous jobs. Everything runs in "
        "Docker containers orchestrated with Kubernetes in staging and production. "
        "I used pytest for testing, Git and GitHub for version control with pull "
        "request review, and Grafana to read the metrics I had added. I had not "
        "used Redis, RabbitMQ, or Kubernetes before this internship.",
    ),
    (
        "5. Challenges and Solutions",
        "The hardest problem was cache invalidation, which I had heard was hard and "
        "then found out why. My first implementation keyed the cache on the raw "
        "request body, so two logically identical requests that differed in "
        "coordinate precision or field order produced separate entries and the hit "
        "rate sat near twelve percent. My mentor suggested I look at what the "
        "requests actually contained rather than assuming, so I logged a day of "
        "traffic and found that most repeats differed only in trailing decimal "
        "places. Rounding coordinates to five decimal places before building the "
        "key, and sorting the fields, took the hit rate from twelve percent to the "
        "low sixties. "
        "The second difficulty was less technical. I spent most of a week on a "
        "refactor nobody had asked for, because I thought the existing code was "
        "untidy. It was reviewed, discussed, and largely rejected, which was "
        "uncomfortable but fair: it made the module harder to follow for the people "
        "who maintain it. I learned to raise an intention before spending days on "
        "it.",
    ),
    (
        "6. Conclusion",
        "I finished the internship able to work in a codebase far larger than "
        "anything I had seen at university, and more importantly able to admit when "
        "I did not understand something. The specific technologies mattered less "
        "than learning how a change gets from an idea to production: written down, "
        "reviewed, measured, and reverted if the numbers do not support it. I would "
        "like to keep working on backend systems.",
    ),
]


def default_end_date(today: date | None = None) -> date:
    """The most recent Friday strictly before *today*.

    The sample period is computed rather than hard-coded so the generated
    package is always in the past. A fixed date would be fine today and would
    silently start failing the future-date gate for anyone who ran the
    generator before it - a confusing way to meet a working system.
    """
    today = today or date.today()
    # weekday(): Monday is 0, Friday is 4.
    return today - timedelta(days=((today.weekday() - 4) % 7) or 7)


def default_start_date(end: date) -> date:
    """The Monday exactly 30 working days before *end* inclusive.

    Thirty weekdays ending on a Friday begin on a Monday 39 calendar days
    earlier, so the window contains the attendance rows exactly.
    """
    return end - timedelta(days=39)


@dataclass
class Package:
    """The facts the three documents are rendered from."""

    student_name: str = "Zofia Wiśniewska"
    student_id: str = "s24187"
    company: str = "Nova Logistics Software Sp. z o.o."
    department: str = "Backend Platform Team"
    supervisor_name: str = "Marcin Kowalczyk"
    supervisor_title: str = "Senior Backend Engineer"
    end_date: date = field(default_factory=default_end_date)
    start_date: date = field(default=None)  # type: ignore[assignment]

    working_days: int = 30
    daily_hours: float = 8.0
    include_weekends: bool = False
    day_offset: int = 0

    evaluation_student_name: str | None = None
    evaluation_date: date = field(default=None)  # type: ignore[assignment]
    scores: dict[str, int] = field(
        default_factory=lambda: {
            "Technical Competence": 86,
            "Communication": 79,
            "Punctuality": 92,
            "Initiative": 81,
            "Teamwork": 84,
        }
    )
    overall_score: int = 84
    signed: bool = True
    stamped: bool = True

    sections: list[tuple[str, str]] = field(default_factory=lambda: list(REPORT_SECTIONS))
    report_as_image: bool = False

    def __post_init__(self) -> None:
        """Derive the dates that depend on the end date, when not given.

        Left as None by default rather than computed in the field default so
        that dataclasses.replace() can override either one independently.
        """
        if self.start_date is None:
            self.start_date = default_start_date(self.end_date)
        if self.evaluation_date is None:
            self.evaluation_date = self.end_date + timedelta(days=3)

    def attendance(self) -> list[tuple[date, float, str]]:
        """Build the day-by-day rows the attendance record will show."""
        rows: list[tuple[date, float, str]] = []
        cursor = self.start_date + timedelta(days=self.day_offset)

        while len(rows) < self.working_days:
            is_weekend = cursor.weekday() >= 5
            if is_weekend and not self.include_weekends:
                cursor += timedelta(days=1)
                continue
            rows.append((cursor, self.daily_hours, "Present"))
            cursor += timedelta(days=1)

        return rows


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _header(c: canvas.Canvas, title: str, y: float) -> float:
    c.setFont(BOLD, 16)
    c.drawString(60, y, _t(title))
    y -= 10
    c.setLineWidth(1)
    c.line(60, y, A4[0] - 60, y)
    return y - 24


def _label(c: canvas.Canvas, y: float, label: str, value: object) -> float:
    c.setFont(REGULAR, 10)
    c.drawString(60, y, _t(f"{label}: {value}"))
    return y - 16


def _wrap(c: canvas.Canvas, y: float, text: str, size: float = 10, leading: float = 14) -> float:
    c.setFont(REGULAR, size)
    max_width = A4[0] - 120
    line = ""

    for word in text.split():
        candidate = f"{line} {word}".strip()
        if c.stringWidth(_t(candidate), REGULAR, size) > max_width:
            c.drawString(60, y, _t(line))
            y -= leading
            line = word
            if y < 70:
                c.showPage()
                c.setFont(REGULAR, size)
                y = A4[1] - 70
        else:
            line = candidate

    if line:
        c.drawString(60, y, _t(line))
        y -= leading

    return y


# ---------------------------------------------------------------------------
# The three documents
# ---------------------------------------------------------------------------


def write_report(pkg: Package, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)

    if pkg.report_as_image:
        # A scan: a picture of a page, carrying no extractable text. Drawn as
        # vector marks so the file is a real PDF that simply has nothing to read.
        c.setFont(BOLD, 16)
        y = A4[1] - 90
        for row in range(40):
            c.setLineWidth(2.2)
            width = 420 if row % 4 else 260
            c.line(70, y, 70 + width, y)
            y -= 16
        c.showPage()
        c.save()
        return

    y = A4[1] - 70
    y = _header(c, "Internship Report", y)

    y = _label(c, y, "Student Name", pkg.student_name)
    y = _label(c, y, "Student ID", pkg.student_id)
    y = _label(c, y, "Company", pkg.company)
    y = _label(c, y, "Department", pkg.department)
    y = _label(c, y, "Supervisor", pkg.supervisor_name)
    y = _label(c, y, "Internship Start Date", pkg.start_date.isoformat())
    y = _label(c, y, "Internship End Date", pkg.end_date.isoformat())
    y = _label(c, y, "Total Working Days", pkg.working_days)
    y -= 14

    for heading, body in pkg.sections:
        if y < 130:
            c.showPage()
            y = A4[1] - 70

        c.setFont(BOLD, 11)
        c.drawString(60, y, _t(heading))
        y -= 18
        y = _wrap(c, y, body)
        y -= 12

    c.save()


def write_evaluation(pkg: Package, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    y = A4[1] - 70
    y = _header(c, "Employer Evaluation Form", y)

    y = _label(c, y, "Student Name", pkg.evaluation_student_name or pkg.student_name)
    y = _label(c, y, "Student ID", pkg.student_id)
    y = _label(c, y, "Company", pkg.company)
    y = _label(c, y, "Supervisor Name", pkg.supervisor_name)
    y = _label(c, y, "Supervisor Title", pkg.supervisor_title)
    y = _label(c, y, "Evaluation Date", pkg.evaluation_date.isoformat())
    y -= 18

    c.setFont(BOLD, 11)
    c.drawString(60, y, _t("Assessment"))
    y -= 20

    for criterion, score in pkg.scores.items():
        y = _label(c, y, criterion, f"{score} / 100")

    y -= 10
    c.setFont(BOLD, 11)
    c.drawString(60, y, _t(f"Overall Score: {pkg.overall_score} / 100"))
    y -= 26

    c.setFont(REGULAR, 10)
    y = _wrap(
        c, y,
        "The intern joined the backend platform team and contributed to the test "
        "infrastructure and the route estimate caching layer. Work was delivered on "
        "time and to the standard expected. Took feedback well, including on a "
        "refactor that was not accepted. We would be glad to have them back.",
    )
    y -= 20

    y = _label(c, y, "Signed", "Yes" if pkg.signed else "No")
    y = _label(c, y, "Company Stamp", "Yes" if pkg.stamped else "No")

    c.setFont(REGULAR, 10)
    c.drawString(60, 150, _t("Supervisor Signature"))
    c.line(60, 140, 260, 140)
    if pkg.signed:
        c.setFont(BOLD, 13)
        c.drawString(70, 146, _t(pkg.supervisor_name))

    c.save()


def write_attendance(pkg: Package, path: Path) -> None:
    rows = pkg.attendance()

    c = canvas.Canvas(str(path), pagesize=A4)
    y = A4[1] - 70
    y = _header(c, "Attendance Record", y)

    y = _label(c, y, "Student Name", pkg.student_name)
    y = _label(c, y, "Student ID", pkg.student_id)
    y = _label(c, y, "Company", pkg.company)
    y = _label(c, y, "Period", f"{pkg.start_date.isoformat()} - {pkg.end_date.isoformat()}")
    y -= 18

    c.setFont(BOLD, 10)
    c.drawString(60, y, _t("Date          Day             Hours   Status"))
    y -= 16

    c.setFont(REGULAR, 10)
    for day, hours, status in rows:
        if y < 110:
            c.showPage()
            c.setFont(REGULAR, 10)
            y = A4[1] - 70

        # Column layout is padded rather than tabulated so the extracted text
        # keeps one row per line, which is what the parser reads.
        line = f"{day.isoformat()}    {day.strftime('%A'):<12} {hours:<6.1f} {status}"
        c.drawString(60, y, _t(line))
        y -= 14

    y -= 12
    total_hours = sum(hours for _, hours, _ in rows)
    c.setFont(BOLD, 10)
    c.drawString(60, y, _t(f"Total Days Recorded: {len(rows)}"))
    y -= 16
    c.drawString(60, y, _t(f"Total Hours: {total_hours:.1f}"))

    c.save()


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def build_scenario(name: str) -> Package:
    base = Package()

    if name == "clean":
        return base

    if name == "short-days":
        return replace(base, working_days=18)

    if name == "name-mismatch":
        return replace(base, evaluation_student_name="Jakub Nowak")

    if name == "unsigned":
        return replace(base, signed=False, stamped=False)

    if name == "thin-report":
        return replace(
            base,
            sections=[
                ("1. Introduction", "I did an internship at a software company."),
                ("2. Company Overview", "It is a logistics company."),
                ("3. Work Performed", "I wrote some code and fixed some bugs."),
                ("4. Technologies Used", "Python."),
                ("5. Challenges and Solutions", "It was hard at first."),
                ("6. Conclusion", "I learned a lot. Thank you."),
            ],
        )

    if name == "weekend-pad":
        # Exactly the required number of days only if weekends are counted.
        return replace(base, working_days=20, include_weekends=True, day_offset=4)

    if name == "future-dates":
        today = date.today()
        return replace(
            base,
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=40),
            evaluation_date=today + timedelta(days=43),
            day_offset=0,
        )

    if name == "scan":
        return replace(base, report_as_image=True)

    if name == "copied":
        # Same report text, different student. This is only detectable against
        # a corpus, which is the point of the originality gate.
        return replace(
            base,
            student_name="Tomasz Lewandowski",
            student_id="s24902",
        )

    raise SystemExit(f"Unknown scenario: {name}")


# Expected outcome per scenario: (status, the finding code that should fire).
# The reviewer's own tests assert these; keeping them here means the generator
# and the expectation live in one place rather than drifting apart.
EXPECTED = {
    "clean": ("approved", None),
    "short-days": ("request_clarification", "DAYS_SHORT"),
    "name-mismatch": ("request_clarification", "NAME_MISMATCH"),
    "unsigned": ("request_clarification", "EVAL_UNSIGNED"),
    "thin-report": ("request_clarification", "REPORT_SHORT"),
    "weekend-pad": ("request_clarification", "DAYS_SHORT"),
    "future-dates": ("request_clarification", "FUTURE_DATES"),
    "scan": ("request_clarification", "ATTACHMENT_NOT_TEXT"),
    "copied": ("rejected", "REPORT_NOT_ORIGINAL"),
}

SCENARIOS = [
    "clean",
    "short-days",
    "name-mismatch",
    "unsigned",
    "thin-report",
    "weekend-pad",
    "future-dates",
    "scan",
    "copied",
]


def generate(scenario: str, out_dir: Path) -> list[Path]:
    """Write the three attachments for *scenario* into *out_dir*."""
    pkg = build_scenario(scenario)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = out_dir / "internship_report.pdf"
    evaluation = out_dir / "evaluation_form.pdf"
    attendance = out_dir / "attendance_record.pdf"

    write_report(pkg, report)
    write_evaluation(pkg, evaluation)
    write_attendance(pkg, attendance)

    return [report, evaluation, attendance]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="clean")
    parser.add_argument("--all", action="store_true", help="Generate every scenario.")
    parser.add_argument("--out", type=Path, default=Path("samples"))
    args = parser.parse_args()

    targets = SCENARIOS if args.all else [args.scenario]

    for scenario in targets:
        directory = args.out / scenario if args.all or len(targets) > 1 else args.out
        paths = generate(scenario, directory)
        print(f"{scenario:14} -> {directory}")
        for path in paths:
            print(f"                 {path.name}  ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
