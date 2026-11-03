from __future__ import annotations
import re
from secquery.models import VulnRecord

PATTERNS: dict[str, re.Pattern[str]] = {
    "cve_ids": re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE),
    "cwe_ids": re.compile(r"\bCWE-\d{1,5}\b", re.IGNORECASE),
    "cvss_scores": re.compile(r"\bCVSS(?:\s+v?\d(?:\.\d)?)?\s*[:=]?\s*(?:\d{1,2}(?:\.\d{1,2})?)\b", re.IGNORECASE),
    "attack_ids": re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE),
}

VERSION_RE = re.compile(
    r"(?<![\w.])(?:v(?:ersion)?\s*)?(\d{1,4}\.\d{1,4}(?:\.\d{1,4}){0,2}(?:[-+][0-9A-Za-z.-]+)?)(?![\w.])",
    re.IGNORECASE,
)


def extract_entities(text: str) -> dict[str, list[str]]:
    """Return deduplicated identifiers; IP addresses and plain dates are not IDs."""
    result: dict[str, list[str]] = {}
    for field, pattern in PATTERNS.items():
        values = [m.group(0).upper().replace("  ", " ") for m in pattern.finditer(text)]
        result[field] = list(dict.fromkeys(values))
    versions = []
    for match in VERSION_RE.finditer(text):
        value = match.group(1)
        prefix = text[max(0, match.start() - 16) : match.start()].lower()
        if re.search(r"\b(?:ip|ipv4|date|dated|on)\s*$", prefix):
            continue
        if re.fullmatch(r"(?:19|20)\d{2}\.\d{1,2}(?:\.\d{1,2})?", value):
            continue
        if re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", value):
            continue
        versions.append(value)
    result["versions"] = list(dict.fromkeys(versions))
    return result


def record_for_document(document_id: str, document_name: str, text: str) -> VulnRecord:
    """Build an identifier-only vulnerability record from concatenated document text."""
    entities = extract_entities(text)
    return VulnRecord(
        document_id=document_id,
        document_name=document_name,
        cve_ids=entities["cve_ids"],
        cwe_ids=entities["cwe_ids"],
        cvss_scores=entities["cvss_scores"],
        attack_ids=entities["attack_ids"],
        versions=entities["versions"],
    )
