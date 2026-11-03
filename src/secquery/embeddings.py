from __future__ import annotations
import hashlib
import re
from typing import Protocol
import numpy as np


class Embedder(Protocol):
    dimension: int

    def embed(self, texts: list[str]) -> np.ndarray: ...


class OfflineHashEmbedder:
    """Dependency-light feature hashing embedder for tests and offline smoke tests only."""

    def __init__(self, dimension: int = 384) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.dimension = dimension

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = re.findall(r"[a-zA-Z0-9]+(?:[-_.][a-zA-Z0-9]+)*", text.lower())
            for token in tokens:
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                number = int.from_bytes(digest, "big")
                index = number % self.dimension
                sign = 1.0 if (number >> 8) & 1 else -1.0
                matrix[row, index] += sign
            norm = np.linalg.norm(matrix[row])
            if norm:
                matrix[row] /= norm
        return matrix


class SentenceTransformerEmbedder:
    """Production embedding backend; model is downloaded by sentence-transformers as needed."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install sentence-transformers to use this embedding backend") from exc
        self.model = SentenceTransformer(model_name)
        self.dimension = int(self.model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        values = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(values, dtype=np.float32)


def create_embedder(backend: str, dimension: int, model_name: str) -> Embedder:
    if backend == "offline":
        return OfflineHashEmbedder(dimension)
    if backend == "sentence-transformers":
        return SentenceTransformerEmbedder(model_name)
    raise ValueError(f"Unsupported embedding backend: {backend}")
