from __future__ import annotations
import re
from secquery.embeddings import Embedder
from secquery.index import VectorIndex
from secquery.lexical import BM25Index
from secquery.models import Hit
from secquery.store import SQLiteStore

ID_RE = re.compile(r"\b(?:CVE-\d{4}-\d{4,}|CWE-\d+|T\d{4}(?:\.\d{3})?)\b", re.IGNORECASE)


def hybrid_search(
    query: str,
    *,
    embedder: Embedder,
    vector_index: VectorIndex,
    store: SQLiteStore,
    top_k_vector: int = 12,
    top_k_lexical: int = 12,
    top_k_final: int = 6,
    rrf_k: int = 60,
    exact_id_boost: float = 0.08,
    document_ids: set[str] | None = None,
) -> list[Hit]:
    """Fuse retrievers while enforcing document scope before final ranking."""
    if not query.strip() or top_k_final <= 0:
        return []
    all_chunks = store.list_chunks()
    if document_ids is not None:
        all_chunks = [chunk for chunk in all_chunks if chunk.document_id in document_ids]
    if not all_chunks:
        return []
    chunk_by_id = {chunk.chunk_id: chunk for chunk in all_chunks}
    allowed_ids = set(chunk_by_id)

    vector_candidate_k = len(vector_index.chunk_ids) if document_ids is not None else top_k_vector
    vector_results = [
        (cid, score)
        for cid, score in vector_index.search(embedder.embed([query]), vector_candidate_k)
        if cid in allowed_ids
    ][:top_k_vector]
    lexical_results = BM25Index(all_chunks).search(query, top_k_lexical)

    fused: dict[str, float] = {}
    sources: dict[str, set[str]] = {}
    for rank, (chunk_id, _) in enumerate(vector_results, start=1):
        fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        sources.setdefault(chunk_id, set()).add("vector")
    for rank, (chunk, _) in enumerate(lexical_results, start=1):
        fused[chunk.chunk_id] = fused.get(chunk.chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        sources.setdefault(chunk.chunk_id, set()).add("lexical")

    query_ids = {item.upper() for item in ID_RE.findall(query)}
    results: list[Hit] = []
    for chunk_id, score in fused.items():
        chunk = chunk_by_id.get(chunk_id)
        if not chunk:
            continue
        if query_ids and any(
            re.search(rf"(?<![A-Z0-9-]){re.escape(identifier)}(?![A-Z0-9-])", chunk.text.upper())
            for identifier in query_ids
        ):
            score += exact_id_boost
        results.append(
            Hit(chunk=chunk, score=score, source="+".join(sorted(sources[chunk_id])), rank=0)
        )
    results.sort(key=lambda hit: hit.score, reverse=True)
    final = results[:top_k_final]
    for rank, hit in enumerate(final, start=1):
        hit.rank = rank
    return final
