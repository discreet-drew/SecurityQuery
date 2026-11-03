from __future__ import annotations
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any
from secquery.models import Chunk, FieldResult


class SQLiteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    document_name TEXT NOT NULL,
                    source_path TEXT NOT NULL DEFAULT '',
                    trust_level TEXT NOT NULL DEFAULT 'unreviewed',
                    sha256 TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    page_count INTEGER NOT NULL DEFAULT 0,
                    chunk_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                    document_name TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_page ON chunks(document_id, page_number);
                CREATE TABLE IF NOT EXISTS entities (
                    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                    entity_type TEXT NOT NULL,
                    entity_value TEXT NOT NULL,
                    chunk_id TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(document_id, entity_type, entity_value, chunk_id)
                );
                CREATE TABLE IF NOT EXISTS extractions (
                    cache_key TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                    field_name TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def upsert_document(
        self,
        document_id: str,
        document_name: str,
        source_path: str = "",
        trust_level: str = "unreviewed",
        sha256: str = "",
        page_count: int = 0,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO documents(document_id,document_name,source_path,trust_level,sha256,page_count)
                VALUES(?,?,?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET
                document_name=excluded.document_name, source_path=excluded.source_path,
                trust_level=excluded.trust_level, sha256=excluded.sha256, page_count=excluded.page_count""",
                (document_id, document_name, source_path, trust_level, sha256, page_count),
            )

    def replace_chunks(self, document_id: str, chunks: list[Chunk]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            conn.executemany(
                """INSERT INTO chunks(chunk_id,document_id,document_name,page_number,text,metadata_json)
                VALUES(?,?,?,?,?,?)""",
                [
                    (
                        chunk.chunk_id,
                        document_id,
                        chunk.document_name,
                        chunk.page_number,
                        chunk.text,
                        json.dumps(chunk.metadata, ensure_ascii=False),
                    )
                    for chunk in chunks
                ],
            )
            conn.execute("UPDATE documents SET chunk_count=? WHERE document_id=?", (len(chunks), document_id))

    def add_entities(self, document_id: str, entities: dict[str, list[str]], chunk_id: str = "") -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO entities(document_id,entity_type,entity_value,chunk_id) VALUES(?,?,?,?)",
                [(document_id, kind, value, chunk_id) for kind, values in entities.items() for value in values],
            )

    def list_documents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC, document_name").fetchall()
            return [dict(row) for row in rows]

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
            return dict(row) if row else None

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
        return self._row_to_chunk(row) if row else None

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row | dict[str, Any]) -> Chunk:
        return Chunk(
            document_id=row["document_id"],
            document_name=row["document_name"],
            page_number=int(row["page_number"]),
            chunk_id=row["chunk_id"],
            text=row["text"],
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    def list_chunks(self, document_id: str | None = None) -> list[Chunk]:
        with self._connect() as conn:
            if document_id:
                rows = conn.execute(
                    "SELECT * FROM chunks WHERE document_id=? ORDER BY page_number, chunk_id", (document_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM chunks ORDER BY document_id, page_number, chunk_id").fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def get_chunks_by_ids(self, ids: list[str]) -> list[Chunk]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})", ids).fetchall()
        mapped = {row["chunk_id"]: self._row_to_chunk(row) for row in rows}
        return [mapped[item] for item in ids if item in mapped]

    def save_extraction(self, cache_key: str, document_id: str, field_name: str, result: FieldResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO extractions(cache_key,document_id,field_name,result_json) VALUES(?,?,?,?)
                ON CONFLICT(cache_key) DO UPDATE SET result_json=excluded.result_json""",
                (cache_key, document_id, field_name, json.dumps(asdict(result), ensure_ascii=False)),
            )

    def get_extraction(self, cache_key: str) -> FieldResult | None:
        with self._connect() as conn:
            row = conn.execute("SELECT result_json FROM extractions WHERE cache_key=?", (cache_key,)).fetchone()
        if not row:
            return None
        data = json.loads(row["result_json"])
        data["cached"] = True
        return FieldResult(**data)

    def set_meta(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_meta(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def delete_document(self, document_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM documents WHERE document_id=?", (document_id,))
