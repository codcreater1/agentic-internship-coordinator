"""ContractService — renders the internship-decision form the coordinator signs.

The layout mirrors the official UTA (Akademia Techniczno-Artystyczna Nauk
Stosowanych w Warszawie) internship form — *Appendix No. 3*, "Decision of the
Dean's Internship Supervisor" — so the signed output looks like the school's
real paperwork, since the tool is used at the university.

Signature placement contract: the frontend embeds the coordinator's signature at
a FIXED box (x=70, y=600, w=220, h=70) in PDF points with a top-left origin. On
A4 (842 pt tall) that box spans ~172–242 pt from the bottom, so the signature
line below is drawn at reportlab y≈170 to sit directly under the ink. Keep these
in sync if the signing coordinates in the frontend/model ever change.
"""

from datetime import date
from pathlib import Path

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

_BEAR_BROWN = HexColor("#7A5A2E")
_PAGE_W, _PAGE_H = A4

# Where the signing date is stamped, in PDF points with a TOP-LEFT origin (the
# convention pdf_service uses). Mirrors the reportlab position of the date line
# below, which is drawn at 61 mm from the bottom.
SIGNATURE_DATE_POS = (_PAGE_W - 73 * mm, _PAGE_H - 63 * mm)


class ContractService:
    @staticmethod
    def create_contract_pdf(
        name: str,
        email: str,
        recommended_role: str,
        candidate_score: int,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        c = canvas.Canvas(str(output_path), pagesize=A4)
        left = 20 * mm

        # ---- Header (UTA identity + appendix reference) -------------------
        c.setFillColor(_BEAR_BROWN)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, _PAGE_H - 25 * mm, "Akademia")
        c.drawString(left, _PAGE_H - 30 * mm, "Techniczno-Artystyczna")
        c.setFont("Helvetica-Bold", 8)
        c.drawString(left, _PAGE_H - 34 * mm, "Nauk Stosowanych w Warszawie")

        c.setFillColor(black)
        c.setFont("Helvetica-Oblique", 8)
        c.drawRightString(_PAGE_W - left, _PAGE_H - 22 * mm, "Appendix No. 3")
        c.drawRightString(_PAGE_W - left, _PAGE_H - 26 * mm,
                          "to the Student Vocational Internship Regulations at UTA")
        c.drawRightString(_PAGE_W - left, _PAGE_H - 30 * mm,
                          "(Direction No. 29/2023 of September 15, 2023 of the Rector of UTA)")

        # ---- Title --------------------------------------------------------
        y = _PAGE_H - 52 * mm
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(_PAGE_W / 2, y, "STUDENT INTERNSHIP AGREEMENT")
        y -= 6 * mm
        c.setFont("Helvetica", 9)
        c.drawCentredString(
            _PAGE_W / 2, y,
            "for completing student internship at the place of employment, traineeship or volunteering",
        )
        y -= 14 * mm

        # ---- Candidate / placement details -------------------------------
        def field(label: str, value: str):
            nonlocal y
            c.setFont("Helvetica-Bold", 10)
            c.drawString(left, y, label)
            c.setFont("Helvetica", 10)
            c.drawString(left + 55 * mm, y, value)
            y -= 9 * mm

        field("Student's name and surname:", name)
        field("Contact e-mail:", email)
        field("Recommended role:", recommended_role)
        field("Evaluation score:", f"{candidate_score}/100")
        field("Date:", date.today().isoformat())
        y -= 4 * mm

        c.setFont("Helvetica", 9)
        for line in [
            "The above applicant has been evaluated by the Internship Coordination system based on the",
            "submitted application and CV. Based on the assessment, the candidate is recommended to",
            "proceed to the internship coordination process for the role indicated above.",
        ]:
            c.drawString(left, y, line)
            y -= 5 * mm
        y -= 8 * mm

        # ---- Decision of the Dean's Internship Supervisor ----------------
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(_PAGE_W / 2, y, "DECISION OF THE DEAN'S INTERNSHIP SUPERVISOR")
        y -= 9 * mm
        c.setFont("Helvetica", 9)
        c.drawString(left, y, "[X]  I consent to the internship implementation for the student named above.")
        y -= 6 * mm
        c.drawString(left, y, "[  ]  I do not consent to the internship implementation.")

        # ---- Signature block ---------------------------------------------
        # The frontend embeds the signature in the fixed box (70, 600, 220, 70)
        # from the top, which on A4 lands ~61–85 mm from the bottom. The line is
        # drawn at y=61 mm so the ink rests directly on it.
        c.setFont("Helvetica", 10)
        c.line(left, 61 * mm, left + 70 * mm, 61 * mm)          # signature line
        c.drawString(left, 55 * mm, "Signature of the Dean's Internship Supervisor")

        # The date beside the signature is intentionally left blank here: it is
        # the date the coordinator signs, which happens later (often days after
        # the contract is generated). It is stamped during signing, at
        # SIGNATURE_DATE_POS below.
        c.drawString(_PAGE_W - 85 * mm, 61 * mm, "Date:")
        c.line(_PAGE_W - 73 * mm, 61 * mm, _PAGE_W - 20 * mm, 61 * mm)

        c.setFont("Helvetica-Oblique", 7)
        c.drawString(left, 15 * mm,
                     "Generated by the Agentic Internship Coordinator and signed electronically.")

        c.save()
        return output_path
