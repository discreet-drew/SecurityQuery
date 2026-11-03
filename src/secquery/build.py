from __future__ import annotations
import hashlib
from dataclasses import replace
from pathlib import Path
from secquery.chunking import chunk_pages
from secquery.config import Settings
from secquery.embeddings import Embedder, create_embedder
from secquery.entities import extract_entities
from secquery.index import VectorIndex
from secquery.ingest import pdf_to_pages, stable_document_id
from secquery.store import SQLiteStore
from secquery.tables import extract_table_chunks


class IndexBuilder:
    def __init__(self, settings: Settings, embedder: Embedder | None = None) -> None:
        self.settings = settings
        self.store = SQLiteStore(settings.db_path)
        self.embedder = embedder or create_embedder(
            settings.embedder_backend, settings.embedding_dim, settings.embedding_model
        )
        if self.embedder.dimension != settings.embedding_dim:
            self.settings = replace(settings, embedding_dim=self.embedder.dimension)
        self.index = VectorIndex(self.embedder.dimension, settings.faiss_path)

    def add_document(
        self,
        path: str | Path,
        *,
        trust_level: str = "unreviewed",
        document_name: str | None = None,
    ) -> str:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"PDF does not exist: {source}")
        if source.stat().st_size > self.settings.max_pdf_bytes:
            raise ValueError(f"PDF exceeds configured maximum of {self.settings.max_pdf_bytes} bytes")
        content = source.read_bytes()
        document_id = stable_document_id(source, content)
        pages = pdf_to_pages(
            source,
            document_id=document_id,
            document_name=document_name or source.name,
            max_bytes=self.settings.max_pdf_bytes,
            max_pages=self.settings.max_pdf_pages,
        )
        chunks = chunk_pages(pages, self.settings.chunk_size, self.settings.chunk_overlap)
        # Keep table rows independently searchable instead of flattening table cells into prose.
        table_chunks = extract_table_chunks(
            source,
            document_id=document_id,
            document_name=document_name or source.name,
            chunk_size=self.settings.chunk_size,
            overlap=self.settings.chunk_overlap,
        )
        chunks.extend(table_chunks)
        self.store.upsert_document(
            document_id=document_id,
            document_name=document_name or source.name,
            source_path=str(source.resolve()),
            trust_level=trust_level,
            sha256=hashlib.sha256(content).hexdigest(),
            page_count=len(pages),
        )
        self.store.replace_chunks(document_id, chunks)
        for chunk in chunks:
            self.store.add_entities(document_id, extract_entities(chunk.text), chunk.chunk_id)
        self._sync_index()
        return document_id

    def rebuild(self) -> None:
        chunks = self.store.list_chunks()
        self.index.rebuild(
            [chunk.chunk_id for chunk in chunks],
            self.embedder.embed([chunk.text for chunk in chunks]),
        )
        self.store.set_meta("embedding_dimension", str(self.embedder.dimension))
        self.store.set_meta("chunk_count", str(len(chunks)))

    def _sync_index(self) -> None:
        chunks = self.store.list_chunks()
        loaded = self.index.load()
        db_ids = [chunk.chunk_id for chunk in chunks]
        if not loaded or not set(self.index.chunk_ids).issubset(set(db_ids)):
            self.rebuild()
            return
        missing = [chunk for chunk in chunks if chunk.chunk_id not in set(self.index.chunk_ids)]
        if missing:
            self.index.add([chunk.chunk_id for chunk in missing], self.embedder.embed([c.text for c in missing]))
            self.index.save()
        self.store.set_meta("embedding_dimension", str(self.embedder.dimension))
        self.store.set_meta("chunk_count", str(len(chunks)))

    def load_consistent(self) -> VectorIndex:
        chunks = self.store.list_chunks()
        if not self.index.load():
            self.rebuild()
            return self.index
        db_ids = {chunk.chunk_id for chunk in chunks}
        index_ids = set(self.index.chunk_ids)
        if index_ids != db_ids:
            self.rebuild()
        elif self.store.get_meta("embedding_dimension") not in (None, str(self.embedder.dimension)):
            self.rebuild()
        return self.index


def add_document(path: str | Path, settings: Settings | None = None) -> str:
    """Convenience API requested by the CLI and app."""
    return IndexBuilder(settings or Settings.load()).add_document(path)
