"""ATA internship-application form renderer (UTA Appendix No. 3).

Recreates the University of Technology and Arts (Akademia Techniczno-Artystyczna
Nauk Stosowanych w Warszawie) student vocational internship application form as a
digital, text-selectable PDF so downstream PDF-text extraction works.

The public entry point is :func:`render_form`, which takes a ``FormData`` record
and writes a multi-page PDF. Category-specific quirks (missing fields, injected
text, broken layout, handwriting style) are all expressed through ``FormData`` and
a few render flags — the layout itself stays faithful to the real form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4

# Fonts: Helvetica for printed labels; a script-ish face for "handwritten" entries.
LABEL_FONT = "Helvetica"
LABEL_BOLD = "Helvetica-Bold"
ENTRY_FONT = "Helvetica"           # typed applicant entries
HAND_FONT = "Times-Italic"         # stand-in for handwriting (built-in, always available)

BEAR_BROWN = HexColor("#7A5A2E")


@dataclass
class FormData:
    """Everything an ATA form can carry. Empty string = field left blank."""

    student_name: str = ""
    student_id: str = ""
    field_of_study: str = "Computer Engineering"
    cycle_of_study: str = "I"
    semester: str = ""
    date: str = ""

    company_name_address: str = ""
    internship_period: str = ""
    internship_months: str = ""
    company_scope: str = ""
    company_website: str = ""
    manager_contact: str = ""

    # Page 2 — company confirmation + dean decision
    manager_name: str = ""
    manager_comments: str = ""
    manager_date: str = ""
    dean_decision: str = ""        # "consent" | "no_consent" | ""
    dean_comments: str = ""
    dean_date: str = ""

    # Page 3 — statement
    statement_field: str = "Computer Engineering"
    statement_cycle: str = "I"
    statement_date: str = ""

    # Render behaviour flags
    handwritten: bool = False       # render applicant entries in script font
    broken: bool = False            # corrupt layout / garbage
    extra_blocks: list[str] = field(default_factory=list)  # free extra paragraphs (injection etc.)


def _wrap(text: str, max_chars: int) -> list[str]:
    """Naive width wrap by character budget (entries are short)."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _draw_header(c: canvas.Canvas):
    # Bear logo stand-in
    c.setFillColor(BEAR_BROWN)
    c.setFont(LABEL_BOLD, 11)
    c.drawString(20 * mm, PAGE_H - 25 * mm, "Akademia")
    c.drawString(20 * mm, PAGE_H - 30 * mm, "Techniczno-Artystyczna")
    c.setFont(LABEL_BOLD, 8)
    c.drawString(20 * mm, PAGE_H - 34 * mm, "Nauk Stosowanych w Warszawie")

    c.setFillColor(black)
    c.setFont("Helvetica-Oblique", 8)
    c.drawRightString(PAGE_W - 20 * mm, PAGE_H - 22 * mm, "Appendix No. 3")
    c.drawRightString(PAGE_W - 20 * mm, PAGE_H - 26 * mm,
                      "to the Student Vocational Internship Regulations at UTA")
    c.drawRightString(PAGE_W - 20 * mm, PAGE_H - 30 * mm,
                      "(Direction No. 29/2023 of September 15, 2023 of the Rector of UTA)")


def _entry(c: canvas.Canvas, x: float, y: float, text: str, hand: bool, size: int = 10):
    c.setFont(HAND_FONT if hand else ENTRY_FONT, size)
    c.setFillColor(HexColor("#1a1a6e") if hand else black)
    c.drawString(x, y, text)
    c.setFillColor(black)


def _label(c: canvas.Canvas, x: float, y: float, text: str, bold: bool = True, size: int = 10):
    c.setFont(LABEL_BOLD if bold else LABEL_FONT, size)
    c.drawString(x, y, text)


def _dots(c: canvas.Canvas, x1: float, y: float, x2: float):
    c.setFont(LABEL_FONT, 10)
    c.drawString(x1, y, "." * int((x2 - x1) / 1.6))


def _render_page1(c: canvas.Canvas, d: FormData):
    _draw_header(c)
    left = 20 * mm
    y = PAGE_H - 48 * mm

    _label(c, left, y, "Student's name and surname:")
    _entry(c, left + 52 * mm, y, d.student_name, d.handwritten)
    _label(c, PAGE_W - 62 * mm, y, "Date:", size=10)
    _entry(c, PAGE_W - 50 * mm, y, d.date, d.handwritten)
    y -= 9 * mm

    _label(c, left, y, "Student ID number:")
    _entry(c, left + 38 * mm, y, d.student_id, d.handwritten)
    _label(c, PAGE_W - 100 * mm, y, "Field of study:")
    _entry(c, PAGE_W - 72 * mm, y, d.field_of_study, d.handwritten)
    y -= 9 * mm

    _label(c, left, y, "Cycle of study: I/II*")
    _label(c, PAGE_W - 100 * mm, y, "Semester:")
    _entry(c, PAGE_W - 78 * mm, y, d.semester, d.handwritten)
    y -= 14 * mm

    c.setFont(LABEL_BOLD, 12)
    c.drawCentredString(PAGE_W / 2, y, "APPLICATION")
    y -= 6 * mm
    c.setFont(LABEL_BOLD, 10)
    c.drawCentredString(PAGE_W / 2, y, "for completing student internship at the place of employment,")
    y -= 5 * mm
    c.drawCentredString(PAGE_W / 2, y, "traineeship or volunteering")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(PAGE_W / 2, y,
                        "(pursuant to art. 67 item 7 of the Act of 20 July 2018 - Law on Higher Education and Science)")
    y -= 10 * mm

    c.setFont(LABEL_FONT, 9)
    intro = _wrap(
        "After reading the rules for organizing and passing student internship and learning "
        "outcomes to be achieved as a result of its implementation, I hereby request for consent "
        "to carry out the internship in the company where I carry out my professional activity:",
        110,
    )
    for line in intro:
        c.drawString(left, y, line)
        y -= 5 * mm
    y -= 4 * mm

    def block(label_text: str, value: str, lines: int = 1):
        nonlocal y
        _label(c, left, y, label_text, bold=False)
        y -= 6 * mm
        vals = _wrap(value, 95) if value else [""]
        for i in range(max(lines, len(vals))):
            v = vals[i] if i < len(vals) else ""
            _entry(c, left, y, v, d.handwritten)
            y -= 6 * mm
        y -= 2 * mm

    block("Full name and address of the company:", d.company_name_address, lines=2)
    block("Internship period ( from, to ):", d.internship_period)
    block("Internship duration (specify the duration in months ):", d.internship_months)
    block("Description of the company's scope of activity:", d.company_scope, lines=2)
    block("Website address of the company or other source of information about the company:",
          d.company_website)
    block("Immediate manager in the company (name and surname, function, e-mail address, phone number ):",
          d.manager_contact, lines=2)

    # Extra free blocks (used by injection / clarification categories)
    for extra in d.extra_blocks:
        for line in _wrap(extra, 100):
            _entry(c, left, y, line, d.handwritten, size=9)
            y -= 5 * mm
        y -= 2 * mm

    c.setFont("Helvetica", 8)
    c.drawString(left, 15 * mm, "*- cross out what is not necessary")


def _render_page2(c: canvas.Canvas, d: FormData):
    left = 20 * mm
    y = PAGE_H - 30 * mm
    c.setFont(LABEL_FONT, 9)
    for line in _wrap(
        "The application must be accompanied by a list of learning outcomes for the student "
        "vocational internship that the student intends to complete at the entity where he/she "
        "pursues professional activity.", 110):
        c.drawString(left, y, line)
        y -= 5 * mm
    y -= 8 * mm

    _label(c, left, y, "Date:", bold=False)
    _entry(c, left + 12 * mm, y, d.date, d.handwritten)
    _label(c, PAGE_W / 2, y, "Student's signature:", bold=False)
    _entry(c, PAGE_W / 2 + 34 * mm, y, d.student_name.split()[0] if d.student_name else "",
           True)
    y -= 14 * mm

    c.setFont(LABEL_BOLD, 11)
    c.drawCentredString(PAGE_W / 2, y, "Confirmation of the receiving company")
    y -= 10 * mm

    _label(c, left, y, "Name and surname of the manager", bold=False)
    y -= 6 * mm
    _entry(c, left, y, d.manager_name, d.handwritten)
    y -= 10 * mm

    _label(c, left, y, "Comments:", bold=False)
    y -= 6 * mm
    for line in _wrap(d.manager_comments, 100):
        _entry(c, left, y, line, d.handwritten)
        y -= 6 * mm
    y -= 6 * mm

    _label(c, left, y, "Date:", bold=False)
    _entry(c, left + 12 * mm, y, d.manager_date, d.handwritten)
    _label(c, PAGE_W / 2, y, "Manager's signature:", bold=False)
    y -= 16 * mm
    _label(c, left, y, "Stamp of the receiving company", bold=False)
    y -= 16 * mm

    c.setFont(LABEL_BOLD, 10)
    c.drawCentredString(PAGE_W / 2, y, "DECISION OF THE DEAN'S INTERNSHIP SUPERVISOR")
    y -= 10 * mm

    box1 = "X" if d.dean_decision == "consent" else " "
    box2 = "X" if d.dean_decision == "no_consent" else " "
    c.setFont(LABEL_FONT, 9)
    c.drawString(left, y, f"[{box1}]  I consent to the internship implementation in the company where the")
    y -= 5 * mm
    c.drawString(left, y, "student carries out his/her professional activity.")
    y -= 7 * mm
    c.drawString(left, y, f"[{box2}]  I do not consent to the internship implementation in the company where the")
    y -= 5 * mm
    c.drawString(left, y, "student carries out his/her professional activity.")
    y -= 9 * mm

    _label(c, left, y, "Comments:", bold=False)
    y -= 6 * mm
    for line in _wrap(d.dean_comments, 100):
        _entry(c, left, y, line, d.handwritten)
        y -= 6 * mm
    y -= 6 * mm
    _label(c, left, y, "Date:", bold=False)
    _entry(c, left + 12 * mm, y, d.dean_date, d.handwritten)


def _render_page3(c: canvas.Canvas, d: FormData):
    left = 20 * mm
    y = PAGE_H - 30 * mm
    c.setFont(LABEL_BOLD, 11)
    c.drawCentredString(PAGE_W / 2, y, "STATEMENT")
    y -= 12 * mm
    c.setFont(LABEL_FONT, 9)
    c.drawString(left, y, "I declare that:")
    y -= 7 * mm
    for txt in [
        "1)  I know the learning outcomes appropriate to the field and level (cycle) of study that",
        "     must be achieved as a result of completing the student internship,",
        "2)  I know that as a result of completing the entire student internship (both parts in the",
        "     fields of study where the internship is divided into parts) I must achieve all the",
        "     learning outcomes.",
    ]:
        c.drawString(left, y, txt)
        y -= 5 * mm
    y -= 8 * mm

    _label(c, left, y, "Field of study:", bold=True)
    _entry(c, left + 28 * mm, y, d.statement_field, d.handwritten)
    _label(c, PAGE_W / 2 + 10 * mm, y, "Cycle of study:", bold=True)
    _entry(c, PAGE_W / 2 + 42 * mm, y, d.statement_cycle, d.handwritten)
    y -= 16 * mm
    _label(c, left, y, "Date:", bold=False)
    _entry(c, left + 12 * mm, y, d.statement_date, d.handwritten)
    _label(c, PAGE_V := PAGE_W / 2, y, "Student's signature:", bold=False)
    _entry(c, PAGE_V + 34 * mm, y, d.student_name.split()[0] if d.student_name else "", True)


def render_form(d: FormData, out_path: Path):
    """Render *d* to a multi-page ATA-form PDF at *out_path*."""
    c = canvas.Canvas(str(out_path), pagesize=A4)

    if d.broken:
        _render_broken(c, d)
    else:
        _render_page1(c, d)
        c.showPage()
        _render_page2(c, d)
        c.showPage()
        _render_page3(c, d)

    c.showPage()
    c.save()


def _render_broken(c: canvas.Canvas, d: FormData):
    """A corrupted / unusable submission: garbled text, wrong layout, no real data."""
    import random
    rng = random.Random(d.student_id or d.date or "broken")
    c.setFont("Helvetica", 8)
    # Scatter garbage so text extraction yields noise, not a valid form.
    garbage = [
        "��� corrupted stream ��", "%PDF-1.4 broken xref",
        "ï¿½ï¿½ï¿½ encoding error ï¿½", "������ scan failed ������",
        "Lorem ipsum dolor sit amet 0x00 0xFF", "[[ OCR CONFIDENCE 0.02 ]]",
    ]
    for _ in range(60):
        c.saveState()
        c.translate(rng.randint(10, 180) * mm, rng.randint(10, 280) * mm)
        c.rotate(rng.randint(-25, 25))
        c.drawString(0, 0, rng.choice(garbage))
        c.restoreState()
    if d.extra_blocks:
        for i, b in enumerate(d.extra_blocks):
            c.drawString(20 * mm, (250 - i * 6) * mm, b[:90])
