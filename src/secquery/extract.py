from __future__ import annotations
import hashlib
from collections.abc import Sequence
from secquery.lexical import BM25Index
from secquery.llm import OllamaClient
from secquery.models import Chunk, FieldResult
from secquery.prompts import extract_prompt
from secquery.store import SQLiteStore
from secquery.verify import verified


def _cache_key(document_id: str, field_name: str, chunks: Sequence[Chunk]) -> str:
    material = "|".join([document_id, field_name, *(chunk.chunk_id for chunk in chunks)])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def extract_field(
    field_name: str,
    chunks: Sequence[Chunk],
    *,
    llm: OllamaClient,
    store: SQLiteStore | None = None,
) -> FieldResult:
    if not chunks:
        return FieldResult(field=field_name, value="not stated")
    document_id = chunks[0].document_id
    ranked = BM25Index(list(chunks)).search(field_name, top_k=10)
    candidates = [chunk for chunk, _ in ranked] or list(chunks[:10])
    key = _cache_key(document_id, field_name, candidates)
    if store:
        cached = store.get_extraction(key)
        if cached:
            return cached
    payload = llm.generate_json(extract_prompt(field_name, candidates))
    quote = str(payload.get("quote", ""))
    cited_id = str(payload.get("document_id", ""))
    cited_page = payload.get("page_number")
    source = next(
        (
            chunk
            for chunk in candidates
            if (not cited_id or chunk.document_id == cited_id)
            and (cited_page is None or chunk.page_number == cited_page)
            and verified(quote, chunk)
        ),
        None,
    )
    if source is None:
        result = FieldResult(field=field_name, value="not stated", document_id=document_id)
    else:
        result = FieldResult(
            field=field_name,
            value=str(payload.get("value") or "not stated"),
            quote=quote,
            document_id=source.document_id,
            document_name=source.document_name,
            page_number=source.page_number,
            verified=True,
        )
    if store:
        store.save_extraction(key, document_id, field_name, result)
    return result


def extract_document(
    document_id: str,
    fields: list[str],
    *,
    chunks: list[Chunk],
    llm: OllamaClient,
    store: SQLiteStore | None = None,
) -> dict[str, FieldResult]:
    scoped = [chunk for chunk in chunks if chunk.document_id == document_id]
    return {field: extract_field(field, scoped, llm=llm, store=store) for field in fields}
