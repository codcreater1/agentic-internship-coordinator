from io import BytesIO

from pypdf import PdfReader


class CVPDFService:
    @staticmethod
    async def extract_text_from_pdf(file):
        contents = await file.read()

        reader = PdfReader(BytesIO(contents))

        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        return text.strip()
