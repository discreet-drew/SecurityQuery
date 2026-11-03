from secquery.extract import extract_field
from secquery.models import Chunk
from secquery.store import SQLiteStore
from conftest import FakeLLM

def test_field_extraction_requires_supported_quote_and_caches(tmp_path):
    chunk = Chunk("d1", "advisory.pdf", 2, "c1", "The vendor recommends upgrading to version 4.2.8.")
    llm = FakeLLM({
        "value": "4.2.8", "quote": "upgrading to version 4.2.8", "document_id": "d1",
        "document_name": "advisory.pdf", "page_number": 2,
    })
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.upsert_document("d1", "advisory.pdf")
    first = extract_field("fixed version", [chunk], llm=llm, store=store)
    second = extract_field("fixed version", [chunk], llm=llm, store=store)
    assert first.verified and first.value == "4.2.8"
    assert second.cached
    assert llm.json_calls == 1


def test_unverifiable_extraction_returns_not_stated():
    chunk = Chunk("d1", "advisory.pdf", 1, "c1", "This page does not mention a fixed version.")
    llm = FakeLLM({"value": "9.9.9", "quote": "Fixed version is 9.9.9", "document_id": "d1", "page_number": 1})
    result = extract_field("fixed version", [chunk], llm=llm)
    assert result.value == "not stated"
    assert not result.verified
