import fitz  # PyMuPDF


class PDFService:
    @staticmethod
    async def extract_text_from_pdf(file):
        content = await file.read()

        pdf = fitz.open(stream=content, filetype="pdf")
        text = ""

        for page in pdf:
            text += page.get_text()

        pdf.close()

        return text.strip()