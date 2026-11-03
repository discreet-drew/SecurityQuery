from __future__ import annotations
from secquery.models import Chunk, Page


def chunk_pages(
    pages: list[Page], chunk_size: int = 800, overlap: int = 150
) -> list[Chunk]:
    """Chunk non-empty pages independently, preserving every character and overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
    chunks: list[Chunk] = []
    for page in pages:
        if not page.text.strip():
            continue
        text = page.text
        start = 0
        sequence = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            piece = text[start:end]
            if piece:
                chunk_id = f"{page.document_id}:p{page.page_number}:c{sequence}"
                chunks.append(
                    Chunk(
                        document_id=page.document_id,
                        document_name=page.document_name,
                        page_number=page.page_number,
                        chunk_id=chunk_id,
                        text=piece,
                        metadata={"start_char": start, "end_char": end},
                    )
                )
            if end >= len(text):
                break
            next_start = end - overlap
            if next_start <= start:
                raise RuntimeError("Chunker failed to advance; check chunk_size/overlap")
            start = next_start
            sequence += 1
    return chunks
