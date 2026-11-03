"""Vector index wrapper with an optional FAISS backend and NumPy fallback."""

from __future__ import annotations
import faiss
import json
from pathlib import Path

import numpy as np


class VectorIndex:
    def __init__(self, dimension: int, path: str | Path) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.dimension = dimension
        self.path = Path(path)
        self.ids_path = self.path.with_suffix(self.path.suffix + ".ids.json")
        self.chunk_ids: list[str] = []
        self._vectors = np.empty((0, dimension), dtype=np.float32)
        self._faiss = None
        self._index = None
        try:
            self._faiss = faiss
            self._index = faiss.IndexFlatIP(dimension)
        except ImportError:
            self._faiss = None

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.maximum(norms, 1e-12)

    def add(self, chunk_ids: list[str], vectors: np.ndarray) -> None:
        matrix = self._normalize(vectors)
        if matrix.shape != (len(chunk_ids), self.dimension):
            raise ValueError(f"Expected vectors shape ({len(chunk_ids)}, {self.dimension}), got {matrix.shape}")
        existing = set(self.chunk_ids)
        keep = [(cid, vec) for cid, vec in zip(chunk_ids, matrix, strict=True) if cid not in existing]
        if not keep:
            return
        new_ids = [item[0] for item in keep]
        new_vectors = np.stack([item[1] for item in keep]).astype(np.float32)
        self.chunk_ids.extend(new_ids)
        if self._faiss is not None:
            self._index.add(new_vectors)
        else:
            self._vectors = np.vstack([self._vectors, new_vectors])

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        if top_k <= 0 or not self.chunk_ids:
            return []
        vector = self._normalize(query_vector)
        if vector.shape[1] != self.dimension:
            raise ValueError("Query vector dimension does not match index dimension")
        k = min(top_k, len(self.chunk_ids))
        if self._faiss is not None:
            scores, positions = self._index.search(vector, k)
            return [
                (self.chunk_ids[int(pos)], float(score))
                for pos, score in zip(positions[0], scores[0], strict=True)
                if 0 <= int(pos) < len(self.chunk_ids)
            ]
        scores = (self._vectors @ vector[0]).astype(float)
        positions = np.argsort(scores)[::-1][:k]
        return [(self.chunk_ids[int(i)], float(scores[int(i)])) for i in positions]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self._faiss is not None:
            self._faiss.write_index(self._index, str(self.path))
        else:
            with self.path.open("wb") as handle:
                np.save(handle, self._vectors)
        self.ids_path.write_text(json.dumps(self.chunk_ids, indent=2), encoding="utf-8")

    def load(self) -> bool:
        if not self.path.exists() or not self.ids_path.exists():
            return False
        self.chunk_ids = json.loads(self.ids_path.read_text(encoding="utf-8"))
        if self._faiss is not None:
            self._index = self._faiss.read_index(str(self.path))
            if int(self._index.d) != self.dimension or int(self._index.ntotal) != len(self.chunk_ids):
                raise ValueError("FAISS index dimension or item count does not match its ID sidecar")
        else:
            with self.path.open("rb") as handle:
                self._vectors = np.load(handle).astype(np.float32)
            if self._vectors.shape != (len(self.chunk_ids), self.dimension):
                raise ValueError("Vector file shape does not match its ID sidecar")
        return True

    def rebuild(self, chunk_ids: list[str], vectors: np.ndarray) -> None:
        self.chunk_ids = []
        self._vectors = np.empty((0, self.dimension), dtype=np.float32)
        if self._faiss is not None:
            self._index = self._faiss.IndexFlatIP(self.dimension)
        self.add(chunk_ids, vectors)
        self.save()
