from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return default if raw is None or not raw.strip() else int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _as_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return default if raw is None or not raw.strip() else float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean, got {raw!r}")


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    db_path: Path
    faiss_path: Path
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedder_backend: str = "sentence-transformers"
    embedding_dim: int = 384
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = 90
    top_k_vector: int = 12
    top_k_lexical: int = 12
    top_k_final: int = 6
    rrf_k: int = 60
    exact_id_boost: float = 0.08
    min_retrieval_score: float = 0.015
    max_pdf_bytes: int = 25_000_000
    max_pdf_pages: int = 500
    chunk_size: int = 800
    chunk_overlap: int = 150
    max_upload_bytes: int = 25_000_000
    allow_synthetic: bool = True

    @classmethod
    def load(cls, env_file: str | Path | None = ".env") -> "Settings":
        if env_file:
            load_dotenv(Path(env_file), override=False)
        data_dir = Path(os.getenv("SECQUERY_DATA_DIR", "data"))
        db_path = Path(os.getenv("SECQUERY_DB_PATH", str(data_dir / "index" / "secquery.db")))
        faiss_path = Path(os.getenv("SECQUERY_FAISS_PATH", str(data_dir / "index" / "faiss.index")))
        settings = cls(
            data_dir=data_dir,
            db_path=db_path,
            faiss_path=faiss_path,
            embedding_model=os.getenv("SECQUERY_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            embedder_backend=os.getenv("SECQUERY_EMBEDDER_BACKEND", "sentence-transformers").lower(),
            embedding_dim=_as_int("SECQUERY_EMBEDDING_DIM", 384),
            ollama_url=os.getenv("SECQUERY_OLLAMA_URL", "http://localhost:11434").rstrip("/"),
            ollama_model=os.getenv("SECQUERY_OLLAMA_MODEL", "llama3.1:8b"),
            ollama_timeout_seconds=_as_int("SECQUERY_OLLAMA_TIMEOUT_SECONDS", 90),
            top_k_vector=_as_int("SECQUERY_TOP_K_VECTOR", 12),
            top_k_lexical=_as_int("SECQUERY_TOP_K_LEXICAL", 12),
            top_k_final=_as_int("SECQUERY_TOP_K_FINAL", 6),
            rrf_k=_as_int("SECQUERY_RRF_K", 60),
            exact_id_boost=_as_float("SECQUERY_EXACT_ID_BOOST", 0.08),
            min_retrieval_score=_as_float("SECQUERY_MIN_RETRIEVAL_SCORE", 0.015),
            max_pdf_bytes=_as_int("SECQUERY_MAX_PDF_BYTES", 25_000_000),
            max_pdf_pages=_as_int("SECQUERY_MAX_PDF_PAGES", 500),
            chunk_size=_as_int("SECQUERY_CHUNK_SIZE", 800),
            chunk_overlap=_as_int("SECQUERY_CHUNK_OVERLAP", 150),
            max_upload_bytes=_as_int("SECQUERY_MAX_UPLOAD_BYTES", 25_000_000),
            allow_synthetic=_as_bool("SECQUERY_ALLOW_SYNTHETIC", True),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        positive_ints = {
            "embedding_dim": self.embedding_dim,
            "ollama_timeout_seconds": self.ollama_timeout_seconds,
            "top_k_vector": self.top_k_vector,
            "top_k_lexical": self.top_k_lexical,
            "top_k_final": self.top_k_final,
            "rrf_k": self.rrf_k,
            "max_pdf_bytes": self.max_pdf_bytes,
            "max_pdf_pages": self.max_pdf_pages,
            "chunk_size": self.chunk_size,
            "max_upload_bytes": self.max_upload_bytes,
        }
        for name, value in positive_ints.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("chunk_overlap must satisfy 0 <= overlap < chunk_size")
        if self.top_k_final > max(self.top_k_vector, self.top_k_lexical) * 2:
            raise ValueError("top_k_final is implausibly large relative to retrieval candidate limits")
        if self.exact_id_boost < 0:
            raise ValueError("exact_id_boost cannot be negative")
        if self.min_retrieval_score < 0:
            raise ValueError("min_retrieval_score cannot be negative")
        if self.embedder_backend not in {"sentence-transformers", "offline"}:
            raise ValueError("embedder_backend must be 'sentence-transformers' or 'offline'")
