"""CV PDF text extraction.

The uploaded CV is attacker-supplied: it arrives from a public endpoint and
from candidate email via n8n. It is therefore validated the same way the
signing endpoints validate their uploads — size-capped before it reaches
memory, identified by magic bytes rather than by filename, and parsed inside
a guard so a malformed document is a clear 400 rather than a 500.
"""

from io import BytesIO

from pypdf import PdfReader

from app.core.config import settings
from app.core.exceptions import (
    EmptyUploadError,
    InvalidPdfError,
    PayloadTooLargeError,
)
from app.core.validators import human_readable_size, is_pdf


class CVPDFService:
    @staticmethod
    async def extract_text_from_pdf(file):
        limit = settings.max_pdf_bytes

        # Reject on the declared size first, then read one byte past the limit
        # so an oversized upload is detected without allocating all of it.
        if file.size is not None and file.size > limit:
            raise PayloadTooLargeError(
                f"CV exceeds the {human_readable_size(limit)} limit."
            )

        contents = await file.read(limit + 1)
        await file.close()

        if not contents:
            raise EmptyUploadError()

        if len(contents) > limit:
            raise PayloadTooLargeError(
                f"CV exceeds the {human_readable_size(limit)} limit."
            )

        # The filename extension is attacker-controlled; the magic number is
        # what actually decides whether pypdf should be handed these bytes.
        if not is_pdf(contents[:5]):
            raise InvalidPdfError(
                "Uploaded file is not a valid PDF (magic-byte check failed)."
            )

        try:
            reader = PdfReader(BytesIO(contents))
            text = "".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise InvalidPdfError(
                "The PDF could not be read — it may be corrupt or encrypted."
            ) from exc

        return text.strip()
