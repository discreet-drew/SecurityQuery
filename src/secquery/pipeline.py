from __future__ import annotations
from pathlib import Path
from typing import Any
from secquery.build import IndexBuilder
from secquery.compare import compare_documents
from secquery.config import Settings
from secquery.embeddings import Embedder, create_embedder
from secquery.extract import extract_document as extract_document_fields
from secquery.hybrid import hybrid_search
from secquery.llm import OllamaClient
from secquery.models import AskResult, Claim, FieldResult, Hit
from secquery.prompts import answer_prompt
from secquery.store import SQLiteStore
from secquery.verify import verified


class SecQuery:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        embedder: Embedder | None = None,
        llm: Any | None = None,
    ) -> None:
        self.settings = settings or Settings.load()
        self.store = SQLiteStore(self.settings.db_path)
        self.embedder = embedder or create_embedder(
            self.settings.embedder_backend,
            self.settings.embedding_dim,
            self.settings.embedding_model,
        )
        self.builder = IndexBuilder(self.settings, self.embedder)
        self.index = self.builder.load_consistent()
        self.llm = llm or OllamaClient(
            self.settings.ollama_url,
            self.settings.ollama_model,
            self.settings.ollama_timeout_seconds,
        )

    def add_document(self, path: str | Path, trust_level: str = "unreviewed") -> str:
        document_id = self.builder.add_document(path, trust_level=trust_level)
        self.index = self.builder.index
        return document_id

    def ask(self, question: str, document_ids: set[str] | None = None) -> AskResult:
        if not question.strip():
            return self._empty_question(question)
        hits = hybrid_search(
            question,
            embedder=self.embedder,
            vector_index=self.index,
            store=self.store,
            top_k_vector=self.settings.top_k_vector,
            top_k_lexical=self.settings.top_k_lexical,
            top_k_final=self.settings.top_k_final,
            rrf_k=self.settings.rrf_k,
            exact_id_boost=self.settings.exact_id_boost,
            document_ids=document_ids,
        )
        return self._answer_from_hits(question, hits, score_threshold=self.settings.min_retrieval_score)

    def ask_vector_only(self, question: str, document_ids: set[str] | None = None) -> AskResult:
        """Vector-search-only evaluation condition; shares the same answer and quote checks."""
        if not question.strip():
            return self._empty_question(question)
        candidate_k = len(self.index.chunk_ids) if document_ids is not None else self.settings.top_k_vector
        raw_hits = self.index.search(self.embedder.embed([question]), candidate_k)
        hits: list[Hit] = []
        for rank, (chunk_id, score) in enumerate(raw_hits, start=1):
            chunk = self.store.get_chunk(chunk_id)
            if chunk is None or (document_ids is not None and chunk.document_id not in document_ids):
                continue
            hits.append(Hit(chunk=chunk, score=score, source="vector", rank=rank))
            if len(hits) >= self.settings.top_k_final:
                break
        return self._answer_from_hits(question, hits, score_threshold=self.settings.min_retrieval_score)

    @staticmethod
    def _empty_question(question: str) -> AskResult:
        return AskResult(question, "Please enter a question.", abstained=True, reason="empty question")

    def _answer_from_hits(self, question: str, hits: list[Hit], score_threshold: float) -> AskResult:
        if not hits or hits[0].score < score_threshold:
            return AskResult(
                question,
                "I couldn't find enough relevant evidence in the indexed documents to answer reliably.",
                hits=hits,
                abstained=True,
                reason="no sufficiently relevant evidence retrieved",
            )
        payload = self.llm.generate_json(answer_prompt(question, [hit.chunk for hit in hits]))
        claims: list[Claim] = []
        response_claims = payload.get("claims", [])
        for item in response_claims if isinstance(response_claims, list) else []:
            if not isinstance(item, dict):
                continue
            quote = str(item.get("quote", ""))
            text = str(item.get("text", "")).strip()
            source_id = str(item.get("document_id", ""))
            source_name = str(item.get("document_name", ""))
            page_number = item.get("page_number")
            source_hit = next(
                (
                    hit.chunk
                    for hit in hits
                    if (not source_id or hit.chunk.document_id == source_id)
                    and (page_number is None or hit.chunk.page_number == page_number)
                    and verified(quote, hit.chunk)
                ),
                None,
            )
            if text and source_hit:
                claims.append(
                    Claim(
                        text=text,
                        quote=quote,
                        document_id=source_hit.document_id,
                        document_name=source_hit.document_name or source_name,
                        page_number=source_hit.page_number,
                        verified=True,
                    )
                )
        asked_to_abstain = bool(payload.get("abstain", False))
        if asked_to_abstain or not claims:
            reason = str(payload.get("reason", "No claims had verifiable supporting quotes."))
            return AskResult(
                question,
                str(payload.get("answer", "The indexed evidence does not support a reliable answer.")),
                claims=claims,
                hits=hits,
                abstained=True,
                reason=reason,
            )
        answer = "\n\n".join(
            f"{claim.text}\n\nEvidence: “{claim.quote}” — {claim.document_name}, p. {claim.page_number}."
            for claim in claims
        )
        return AskResult(question, answer, claims=claims, hits=hits)

    def extract_document(self, document_id: str, fields: list[str]) -> dict[str, FieldResult]:
        return extract_document_fields(
            document_id,
            fields,
            chunks=self.store.list_chunks(document_id),
            llm=self.llm,
            store=self.store,
        )

    def compare(self, document_ids: list[str], fields: list[str]) -> dict[str, dict[str, object]]:
        gathered: dict[str, dict[str, FieldResult]] = {}
        for document_id in document_ids:
            document = self.store.get_document(document_id)
            if not document:
                continue
            gathered[document["document_name"]] = self.extract_document(document_id, fields)
        return compare_documents(gathered)
