"""Renders the internship completion certificate the coordinator signs.

The companion to :mod:`app.services.contract_service`: that one issues the
agreement at the start of a placement, this one certifies it was completed. The
layout follows the same UTA house style so the two documents look like they came
from the same office.

Two details carry the weight.

**The package hash.** The certificate prints the SHA-256 of the three
attachments as received. A certificate detached from its documents attests to
nothing — anyone holding it could pair it with a different report. With the hash
on the face of the document the claim is checkable: rehash the three files and
compare. :func:`compute_package_hash` is the single definition of how that hash
is formed, and it is order-independent so attachment order cannot change it.

**The named coordinator.** The certificate carries a person's name, not a
system's. Somebody is accountable for the decision.

Fonts: unlike :mod:`app.services.contract_service`, this module registers a
TrueType face when one is available. Helvetica's WinAnsi encoding has no glyphs
for ł, ą, ę, ś, ż, ń or ğ, ş, ı, and this document prints a real student's name
and their host organisation. A name with holes in it on a certificate the
registrar files is not acceptable; transliteration is the fallback, and plain
Helvetica the last resort.

Signature placement contract: the coordinator's signature is embedded at
:data:`CertificateService.SIGNATURE_BOX` in PDF points with a TOP-LEFT origin
(the convention :mod:`app.services.pdf_service` uses). The signature rule and
the coordinator's printed name below it are positioned to sit under that ink.
Keep them in sync.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

_BEAR_BROWN = HexColor("#7A5A2E")
_PAGE_W, _PAGE_H = A4

# Candidate TrueType faces, in preference order. The first that loads wins.
_FONT_CANDIDATES = (
    ("DejaVuSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
    ("CertArial", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    (
        "LiberationSans",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
)

_TRANSLITERATE = str.maketrans({
    "ł": "l", "Ł": "L", "ą": "a", "Ą": "A", "ę": "e", "Ę": "E",
    "ś": "s", "Ś": "S", "ż": "z", "Ż": "Z", "ź": "z", "Ź": "Z",
    "ń": "n", "Ń": "N", "ć": "c", "Ć": "C",
    "ğ": "g", "Ğ": "G", "ı": "i", "İ": "I", "ş": "s", "Ş": "S",
    "ç": "c", "Ç": "C", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
    "ó": "o", "Ó": "O",
})

_fonts_cache: tuple[str, str, bool] | None = None


def _fonts() -> tuple[str, str, bool]:
    """Return ``(regular, bold, unicode_ok)``, registering a TTF once per process."""
    global _fonts_cache
    if _fonts_cache is not None:
        return _fonts_cache

    for family, regular_path, bold_path in _FONT_CANDIDATES:
        try:
            pdfmetrics.registerFont(TTFont(family, regular_path))
            pdfmetrics.registerFont(TTFont(f"{family}-Bold", bold_path))
            _fonts_cache = (family, f"{family}-Bold", True)
            return _fonts_cache
        except Exception:  # noqa: BLE001 — any font failure falls through
            continue

    logger.warning(
        "No TrueType font available for certificates; falling back to Helvetica with "
        "transliteration. Polish and Turkish characters will be rendered as their "
        "ASCII equivalents. Install DejaVu Sans in the image to fix this."
    )
    _fonts_cache = ("Helvetica", "Helvetica-Bold", False)
    return _fonts_cache


def compute_package_hash(document_hashes: list[str]) -> str:
    """Combine per-document hashes into one order-independent package hash.

    Sorted before hashing so the same three attachments produce the same value
    regardless of the order the mail client happened to present them in.
    """
    return hashlib.sha256("\n".join(sorted(document_hashes)).encode("utf-8")).hexdigest()


class CertificateService:
    """Renders a completion certificate for a verified submission."""

    LEFT = 22 * mm
    RIGHT = 22 * mm

    # Where the coordinator's signature image lands, in PDF points with a
    # TOP-LEFT origin. On A4 this band sits ~153–215 pt above the page bottom.
    SIGNATURE_BOX = (60.0, 627.0, 240.0, 62.0)

    @staticmethod
    def create_certificate_pdf(
        submission,
        output_path: Path,
        *,
        coordinator_name: str,
        note: str | None = None,
        issued_at: datetime | None = None,
    ) -> Path:
        """Write the certificate for *submission* to *output_path*.

        Refuses to render a certificate that would state nothing. The caller
        already declines to reach this point for an unverified package;
        printing a blank student name onto a document the coordinator then
        signs would be worse than failing loudly. Mirrors the same guard in
        :meth:`app.services.contract_service.ContractService.create_contract_pdf`.
        """
        blank = [
            label
            for label, value in (
                ("student name", submission.student_name),
                ("host organisation", submission.company),
                ("coordinator name", coordinator_name),
            )
            if not (value or "").strip()
        ]
        if blank:
            raise ValueError(
                "Cannot generate a completion certificate without: " + ", ".join(blank)
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        regular, bold, unicode_ok = _fonts()
        issued_at = issued_at or datetime.now(timezone.utc)

        def t(value: object) -> str:
            """Render a value as text the chosen font can actually draw."""
            text = "-" if value is None else str(value)
            return text if unicode_ok else text.translate(_TRANSLITERATE)

        c = canvas.Canvas(str(output_path), pagesize=A4)
        c.setTitle("Internship Completion Certificate")
        c.setAuthor("Agentic Internship Coordinator")

        left = CertificateService.LEFT
        right_edge = _PAGE_W - CertificateService.RIGHT
        y = _PAGE_H - 24 * mm

        # -- university header ------------------------------------------
        c.setFillColor(_BEAR_BROWN)
        c.setFont(bold, 11)
        c.drawString(left, y, t("Akademia Techniczno-Artystyczna Nauk Stosowanych"))
        y -= 12
        c.setFont(regular, 8)
        c.drawString(left, y, t("w Warszawie  ·  Internship Coordination Office"))
        c.setFillColor(black)
        y -= 26

        c.setFont(bold, 16)
        c.drawString(left, y, t("Internship Completion Certificate"))
        y -= 14

        c.setFont(regular, 8)
        c.setFillGray(0.35)
        c.drawString(
            left,
            y,
            t(
                f"Issued {issued_at.strftime('%Y-%m-%d %H:%M UTC')}  ·  "
                f"Reference {submission.id}"
            ),
        )
        c.setFillGray(0)
        y -= 10

        c.setStrokeColor(_BEAR_BROWN)
        c.setLineWidth(1.2)
        c.line(left, y, right_edge, y)
        c.setStrokeColor(black)
        y -= 26

        def field(label: str, value: str) -> None:
            nonlocal y
            c.setFont(regular, 9)
            c.setFillGray(0.4)
            c.drawString(left, y, label)
            c.setFillGray(0)
            c.setFont(regular, 10)
            c.drawString(left + 52 * mm, y, value)
            y -= 15

        def section(title: str) -> None:
            nonlocal y
            c.setFont(bold, 10.5)
            c.drawString(left, y, title)
            y -= 16

        section(t("Intern"))
        field(t("Name"), t(submission.student_name))
        field(t("Student ID"), t(submission.student_id))
        field(t("Host organisation"), t(submission.company))
        y -= 8

        section(t("Verified"))
        field(t("Internship period"), t(f"{submission.start_date} to {submission.end_date}"))
        field(
            t("Attended working days"),
            t(f"{submission.counted_working_days} days ({submission.total_hours:g} hours)"),
        )
        field(
            t("Employer evaluation"),
            t(f"{submission.evaluation_score}/100" if submission.evaluation_score is not None else "-"),
        )
        field(t("Report length"), t(f"{submission.report_word_count} words"))
        field(
            t("Originality"),
            t(f"{submission.max_similarity:.0%} peak similarity to prior submissions"),
        )
        y -= 8

        # -- the documents this certificate is about --------------------
        section(t("Attested documents"))
        for doc in submission.documents:
            c.setFont(regular, 9)
            c.setFillGray(0.4)
            c.drawString(left, y, t(doc.role.value.title()))
            c.setFillGray(0)
            c.setFont(regular, 10)
            c.drawString(left + 52 * mm, y, t(f"{doc.filename}  ({doc.page_count} pp)"))
            y -= 10
            c.setFont(regular, 7)
            c.setFillGray(0.45)
            c.drawString(left + 52 * mm, y, t(f"sha256 {doc.sha256}"))
            c.setFillGray(0)
            y -= 16

        y -= 4
        c.setFont(bold, 9)
        c.drawString(left, y, t("Package hash (SHA-256)"))
        y -= 12
        c.setFont(regular, 7.5)
        c.drawString(left, y, t(submission.package_sha256))
        y -= 10
        c.setFillGray(0.45)
        c.setFont(regular, 7)
        c.drawString(left, y, t("This certificate attests only to the documents hashed above."))
        c.setFillGray(0)
        y -= 22

        # -- what this does and does not claim --------------------------
        y = _paragraph(
            c, left, y, regular, right_edge - left,
            "This certificate records that the three documents identified above were "
            "received, that every automated verification check was applied to them, and "
            "that the coordinator named below reviewed the result and approved it. It "
            "attests to the completeness and internal consistency of the submitted "
            "record. It is not an assessment of the quality of the work performed.",
        )

        acknowledged = [f for f in submission.findings if f.severity.value == "warning"]
        if acknowledged:
            y -= 6
            y = _paragraph(
                c, left, y, regular, right_edge - left,
                t(
                    f"Signed with {len(acknowledged)} open point(s) explicitly acknowledged "
                    "by the coordinator: " + "; ".join(f.code for f in acknowledged) + "."
                ),
            )

        if note:
            y -= 6
            y = _paragraph(
                c, left, y, regular, right_edge - left, t(f"Coordinator note: {note}")
            )

        # -- signature block --------------------------------------------
        # Positioned from the page bottom so it stays clear of SIGNATURE_BOX,
        # where the signature image lands (153–215 pt from the bottom).
        c.setFont(bold, 10)
        c.drawString(left, 225, t("Approved and signed by"))

        c.setLineWidth(0.8)
        c.line(left, 145, left + 240, 145)

        c.setFont(regular, 10)
        c.drawString(left, 128, t(coordinator_name))
        c.setFont(regular, 8)
        c.setFillGray(0.4)
        c.drawString(left, 114, t(f"Internship Coordinator  ·  {date.today().isoformat()}"))
        c.setFillGray(0)

        c.setFont(regular, 6.5)
        c.setFillGray(0.5)
        c.drawCentredString(
            _PAGE_W / 2,
            30,
            t(
                "Generated by the Agentic Internship Coordinator. Verify by rehashing the "
                "three attached documents against the package hash above."
            ),
        )
        c.setFillGray(0)

        c.showPage()
        c.save()
        logger.info(
            "Completion certificate written for submission %s (%d documents)",
            submission.id,
            len(submission.documents),
        )
        return output_path


def _paragraph(
    c: canvas.Canvas,
    left: float,
    y: float,
    font: str,
    max_width: float,
    text: str,
    size: float = 8.5,
) -> float:
    """Draw wrapped body text and return the new y position."""
    c.setFont(font, size)
    line = ""

    for word in text.split():
        candidate = f"{line} {word}".strip()
        if c.stringWidth(candidate, font, size) > max_width:
            c.drawString(left, y, line)
            y -= 11
            line = word
        else:
            line = candidate

    if line:
        c.drawString(left, y, line)
        y -= 11

    return y
