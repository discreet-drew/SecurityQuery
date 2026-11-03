from __future__ import annotations
import math
import re
from collections import Counter
from secquery.models import Chunk

TOKEN_RE = re.compile(
    r"CVE-\d{4}-\d{4,}|CWE-\d+|T\d{4}(?:\.\d{3})?|\b\d+(?:\.\d+){1,3}(?:[-+][\w.-]+)?\b|[a-zA-Z][a-zA-Z0-9_+#.-]*",
    re.IGNORECASE,
)


def tokenize(text: str) -> list[str]:
    """Keep CVE/CWE/ATT&CK IDs and dotted version numbers intact."""
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(chunk.text) for chunk in chunks]
        self.term_frequencies = [Counter(tokens) for tokens in self.tokens]
        self.doc_freq: Counter[str] = Counter()
        for tokens in self.tokens:
            self.doc_freq.update(set(tokens))
        self.avgdl = sum(map(len, self.tokens)) / max(1, len(self.tokens))

    def search(
        self, query: str, top_k: int = 10, document_ids: set[str] | None = None
    ) -> list[tuple[Chunk, float]]:
        if top_k <= 0 or not self.chunks:
            return []
        query_terms = tokenize(query)
        if not query_terms:
            return []
        total_docs = len(self.chunks)
        results: list[tuple[Chunk, float]] = []
        for chunk, tf, tokens in zip(self.chunks, self.term_frequencies, self.tokens, strict=True):
            if document_ids is not None and chunk.document_id not in document_ids:
                continue
            score = 0.0
            doc_len = len(tokens)
            for term in query_terms:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
                denom = freq + self.k1 * (1 - self.b + self.b * doc_len / max(self.avgdl, 1e-9))
                score += idf * freq * (self.k1 + 1) / denom
            if score > 0:
                results.append((chunk, score))
        return sorted(results, key=lambda item: item[1], reverse=True)[:top_k]
