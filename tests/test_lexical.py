from secquery.lexical import BM25Index, tokenize
from secquery.models import Chunk

def test_tokenizer_preserves_security_ids_versions_and_dotted_attack_ids():
    tokens = tokenize("CVE-2024-12345 CWE-79 version 4.2.8 technique T1059.001")
    assert "cve-2024-12345" in tokens
    assert "cwe-79" in tokens
    assert "4.2.8" in tokens
    assert "t1059.001" in tokens


def test_bm25_retrieves_exact_identifier_match():
    chunks = [
        Chunk("d1", "one.pdf", 1, "c1", "Affected by CVE-2024-12345 and fixed in 4.2.8."),
        Chunk("d2", "two.pdf", 1, "c2", "A general security note about least privilege."),
    ]
    hits = BM25Index(chunks).search("CVE-2024-12345", 2)
    assert hits[0][0].chunk_id == "c1"
