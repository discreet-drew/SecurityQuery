from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Page:
    document_id: str
    document_name: str
    page_number: int
    text: str
    char_count: int = 0
    has_text: bool = True

    def __post_init__(self) -> None:
        self.char_count = len(self.text)
        self.has_text = bool(self.text.strip())


@dataclass(slots=True)
class Chunk:
    document_id: str
    document_name: str
    page_number: int
    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Hit:
    chunk: Chunk
    score: float
    source: str = "hybrid"
    rank: int = 0


@dataclass(slots=True)
class Claim:
    text: str
    quote: str = ""
    document_id: str = ""
    document_name: str = ""
    page_number: int | None = None
    verified: bool = False
    note: str = ""


@dataclass(slots=True)
class FieldResult:
    field: str
    value: str = "not stated"
    quote: str = ""
    document_id: str = ""
    document_name: str = ""
    page_number: int | None = None
    verified: bool = False
    cached: bool = False


@dataclass(slots=True)
class VulnRecord:
    document_id: str
    document_name: str
    cve_ids: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    cvss_scores: list[str] = field(default_factory=list)
    attack_ids: list[str] = field(default_factory=list)
    versions: list[str] = field(default_factory=list)
    fields: dict[str, FieldResult] = field(default_factory=dict)


@dataclass(slots=True)
class AskResult:
    question: str
    answer: str
    claims: list[Claim] = field(default_factory=list)
    hits: list[Hit] = field(default_factory=list)
    abstained: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "claims": [asdict(c) for c in self.claims],
            "hits": [
                {"score": h.score, "source": h.source, "chunk": asdict(h.chunk)} for h in self.hits
            ],
            "abstained": self.abstained,
            "reason": self.reason,
        }