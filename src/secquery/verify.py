from __future__ import annotations
import re
import unicodedata
from secquery.models import Chunk

def normalize(text: str) -> str:
    """Normalize Unicode and whitespace while retaining punctuation and identifiers."""
    value = unicodedata.normalize("NFKC", text or "").casefold()
    return re.sub(r"\s+", " ", value).strip()


def verified(quote: str, chunk: Chunk | str) -> bool:
    """True only when a non-empty normalized quote is present in the source chunk."""
    source_text = chunk.text if isinstance(chunk, Chunk) else chunk
    needle = normalize(quote)
    haystack = normalize(source_text)
    return bool(needle) and needle in haystack
