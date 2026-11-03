from secquery.models import Chunk, FieldResult
from secquery.store import SQLiteStore

def test_store_round_trip_document_chunks_entities_and_extraction(tmp_path):
    store = SQLiteStore(tmp_path / "secquery.db")
    store.upsert_document("d1", "a.pdf", page_count=1)
    chunk = Chunk("d1", "a.pdf", 1, "d1:p1:c0", "The fix is version 4.2.8.", {"start_char": 0})
    store.replace_chunks("d1", [chunk])
    store.add_entities("d1", {"cve_ids": ["CVE-2024-12345"]}, chunk.chunk_id)
    assert store.get_chunk(chunk.chunk_id).text == chunk.text
    assert store.get_document("d1")["chunk_count"] == 1
    result = FieldResult("fixed version", "4.2.8", "version 4.2.8.", "d1", "a.pdf", 1, True)
    store.save_extraction("cache", "d1", result.field, result)
    cached = store.get_extraction("cache")
    assert cached is not None and cached.value == "4.2.8" and cached.cached
