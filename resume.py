"""Resume/CV text extraction for profile onboarding."""

import io
from pathlib import Path

from docx import Document
from pypdf import PdfReader

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 30_000
MIN_TEXT_CHARS = 40

ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt"}


def _normalize(text: str) -> str:
    lines = [
        " ".join(line.split())
        for line in (text or "").replace("\x00", " ").splitlines()
    ]
    return "\n".join(line for line in lines if line).strip()


def extract_resume_text(
    filename: str,
    data: bytes,
) -> str:
    """Extract readable text from PDF, DOCX, or TXT without saving it."""
    if not data:
        raise ValueError("The uploaded file is empty.")

    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("The file is larger than the 5 MB limit.")

    suffix = Path(filename or "").suffix.lower()

    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Upload a PDF, DOCX, or TXT file.")

    try:
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(data))

            if reader.is_encrypted:
                raise ValueError("Password-protected PDFs are not supported.")

            text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages[:20]
            )
        elif suffix == ".docx":
            document = Document(io.BytesIO(data))
            parts = [paragraph.text for paragraph in document.paragraphs]

            for table in document.tables:
                for row in table.rows:
                    parts.extend(cell.text for cell in row.cells)

            text = "\n".join(parts)
        else:
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = data.decode("latin-1", errors="ignore")
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(
            "The resume could not be read. Try another PDF, DOCX, or TXT file."
        ) from error

    normalized = _normalize(text)

    if len(normalized) < MIN_TEXT_CHARS:
        raise ValueError(
            "The resume did not contain enough readable text. "
            "A scanned image-only PDF may need a text-based version."
        )

    return normalized[:MAX_TEXT_CHARS]