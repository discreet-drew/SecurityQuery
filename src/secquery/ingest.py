from __future__ import annotations
import hashlib
from pathlib import Path
import fitz
from secquery.models import Page

class PDFIngestError(ValueError):
    """Raised when a PDF is invalid or violates configured resource limits."""

def stable_document_id(path: str | Path, content: bytes | None = None) -> str:
    """Return a stable content-derived ID; duplicate identical PDFs share an ID."""
    raw = content if content is not None else Path(path).read_bytes()
    return hashlib.sha256(raw).hexdigest()[:24]


def pdf_to_pages(
    path: str | Path,
    *,
    document_id: str | None = None,
    document_name: str | None = None,
    max_bytes: int = 25_000_000,
    max_pages: int = 500,
) -> list[Page]:
    """Extract one Page per physical PDF page, retaining blank pages in the result."""
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise PDFIngestError(f"PDF does not exist: {pdf_path}")
    size = pdf_path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise PDFIngestError(f"PDF size {size} bytes is outside allowed range 1..{max_bytes}")
    try:
        with fitz.open(pdf_path) as doc:
            if doc.is_encrypted:
                raise PDFIngestError("Encrypted PDFs are not supported; provide an authorized, readable copy")
            if len(doc) > max_pages:
                raise PDFIngestError(f"PDF has {len(doc)} pages; maximum is {max_pages}")
            doc_id = document_id or stable_document_id(pdf_path)
            name = document_name or pdf_path.name
            return [
                Page(
                    document_id=doc_id,
                    document_name=name,
                    page_number=number,
                    text=page.get_text("text", sort=True).replace("\x00", "").strip(),
                )
                for number, page in enumerate(doc, start=1)
            ]
    except PDFIngestError:
        raise
    except Exception as exc:  
        raise PDFIngestError(f"Could not read PDF {pdf_path.name}: {exc}") from exc
