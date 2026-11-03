from __future__ import annotations
from pathlib import Path
import pdfplumber
from secquery.models import Chunk, Page


def row_to_text(row: list[object] | tuple[object, ...]) -> str:
    """Convert a table row to a stable one-line representation."""
    cells = [" ".join(str(cell or "").split()) for cell in row]
    cells = [cell for cell in cells if cell]
    return " | ".join(cells)


def rows_to_chunks(
    rows: list[tuple[int, list[object] | tuple[object, ...]]],
    *,
    document_id: str,
    document_name: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[Chunk]:
    """Build table-row chunks; each logical row has its own chunk ID and is page scoped."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= overlap < chunk_size")
    chunks: list[Chunk] = []
    page_row_counts: dict[int, int] = {}
    for page_number, row in rows:
        text = row_to_text(row)
        if not text:
            continue
        row_id = page_row_counts.get(page_number, 0)
        page_row_counts[page_number] = row_id + 1
        start = 0
        part = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(
                Chunk(
                    document_id=document_id,
                    document_name=document_name,
                    page_number=page_number,
                    chunk_id=f"{document_id}:p{page_number}:table{row_id}:c{part}",
                    text=text[start:end],
                    metadata={"kind": "table_row", "row_index": row_id, "start_char": start, "end_char": end},
                )
            )
            if end == len(text):
                break
            start = end - overlap
            part += 1
    return chunks


def extract_table_chunks(
    path: str | Path,
    *,
    document_id: str,
    document_name: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[Chunk]:
    """Extract table rows with pdfplumber, with one logical row per table chunk."""
    rows: list[tuple[int, list[object] | tuple[object, ...]]] = []
    with pdfplumber.open(Path(path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables() or []:
                rows.extend((page_number, row or []) for row in table)
    return rows_to_chunks(
        rows,
        document_id=document_id,
        document_name=document_name,
        chunk_size=chunk_size,
        overlap=overlap,
    )


def extract_table_pages(path: str | Path, pages: list[Page] | None = None) -> list[Page]:
    """Compatibility helper returning one text page per page with extracted table rows."""
    source = Path(path)
    document_id = pages[0].document_id if pages else source.stem
    name = pages[0].document_name if pages else source.name
    results: list[Page] = []
    with pdfplumber.open(source) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            lines: list[str] = []
            for table in page.extract_tables() or []:
                for row in table:
                    line = row_to_text(row or [])
                    if line:
                        lines.append(line)
            if lines:
                results.append(Page(document_id, name, page_number, "\n".join(lines)))
    return results
