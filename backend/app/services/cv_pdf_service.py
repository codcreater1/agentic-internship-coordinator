from pypdf import PdfReader


class CVPDFService:
    @staticmethod
    async def extract_text_from_pdf(file):
        contents = await file.read()

        temp_path = "temp_cv.pdf"

        with open(temp_path, "wb") as f:
            f.write(contents)

        reader = PdfReader(temp_path)

        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        return text.strip()