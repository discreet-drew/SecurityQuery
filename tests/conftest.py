from __future__ import annotations
from pathlib import Path
from typing import Any
import fitz
import pytest
from secquery.config import Settings
from secquery.embeddings import OfflineHashEmbedder


class FakeLLM:
    def __init__(self, payload: dict[str, Any] | None = None, text: str = "test response") -> None:
        self.payload = payload or {}
        self.text = text
        self.json_calls = 0
        self.text_calls = 0

    def generate_json(self, prompt: str) -> dict[str, Any]:
        self.json_calls += 1
        return self.payload

    def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        self.text_calls += 1
        return self.text


@pytest.fixture
def fake_embedder() -> OfflineHashEmbedder:
    return OfflineHashEmbedder(dimension=32)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def make_pdf(tmp_path: Path):
    def _make(path: Path, page_texts: list[str]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = fitz.open()
        for text in page_texts:
            page = document.new_page()
            if text:
                page.insert_text((72, 72), text)
        document.save(path)
        document.close()
        return path

    return _make


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "index" / "secquery.db",
        faiss_path=tmp_path / "data" / "index" / "faiss.index",
        embedder_backend="offline",
        embedding_dim=32,
        top_k_vector=8,
        top_k_lexical=8,
        top_k_final=4,
        chunk_size=80,
        chunk_overlap=10,
        min_retrieval_score=0.005,
    )
