from pathlib import Path
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


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
        width, height = A4

        y = height - 80

        c.setFont("Helvetica-Bold", 18)
        c.drawString(70, y, "Internship Agreement")
        y -= 50

        c.setFont("Helvetica", 11)
        c.drawString(70, y, f"Date: {date.today().isoformat()}")
        y -= 30

        c.drawString(70, y, f"Candidate Name: {name}")
        y -= 25

        c.drawString(70, y, f"Candidate Email: {email}")
        y -= 25

        c.drawString(70, y, f"Recommended Role: {recommended_role}")
        y -= 25

        c.drawString(70, y, f"Candidate Score: {candidate_score}/100")
        y -= 50

        text = c.beginText(70, y)
        text.setFont("Helvetica", 11)
        text.setLeading(18)

        lines = [
            "This document confirms that the candidate has been evaluated by the",
            "Agentic Internship Coordinator system.",
            "",
            "Based on the automated CV analysis and matching workflow, the candidate",
            "is eligible to proceed to the internship coordination process.",
            "",
            "The recommended internship role has been selected according to the",
            "candidate's skills, project experience, and technical background.",
            "",
            "This agreement is generated automatically by the system and may be",
            "signed electronically by the internship coordinator.",
        ]

        for line in lines:
            text.textLine(line)

        c.drawText(text)

        c.setFont("Helvetica", 11)
        c.drawString(70, 160, "Coordinator Signature:")
        c.line(70, 135, 260, 135)

        c.drawString(330, 160, "Candidate Signature:")
        c.line(330, 135, 520, 135)

        c.save()
        return output_path