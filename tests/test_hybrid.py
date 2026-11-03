from secquery.embeddings import OfflineHashEmbedder
from secquery.hybrid import hybrid_search
from secquery.index import VectorIndex
from secquery.models import Chunk
from secquery.store import SQLiteStore

def test_hybrid_retrieval_boosts_exact_id_and_respects_document_scope(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.upsert_document("d1", "a.pdf")
    store.upsert_document("d2", "b.pdf")
    chunks = [
        Chunk("d1", "a.pdf", 1, "c1", "CVE-2024-12345 mitigation: upgrade to version 4.2.8."),
        Chunk("d2", "b.pdf", 1, "c2", "CVE-2024-99999 unrelated entry."),
    ]
    store.replace_chunks("d1", [chunks[0]])
    store.replace_chunks("d2", [chunks[1]])
    embedder = OfflineHashEmbedder(32)
    index = VectorIndex(32, tmp_path / "vectors.index")
    index.add([chunk.chunk_id for chunk in chunks], embedder.embed([chunk.text for chunk in chunks]))
    hits = hybrid_search(
        "What affects CVE-2024-12345?", embedder=embedder, vector_index=index, store=store,
        top_k_vector=2, top_k_lexical=2, top_k_final=2, exact_id_boost=0.5,
    )
    assert hits[0].chunk.chunk_id == "c1"
    scoped = hybrid_search(
        "CVE-2024-12345", embedder=embedder, vector_index=index, store=store,
        top_k_vector=2, top_k_lexical=2, top_k_final=2, document_ids={"d2"},
    )
    assert all(hit.chunk.document_id == "d2" for hit in scoped)
