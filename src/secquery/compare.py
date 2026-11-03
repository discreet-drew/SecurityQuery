from __future__ import annotations
from collections.abc import Mapping
from secquery.models import FieldResult

def compare_values(values: Mapping[str, FieldResult | str]) -> dict[str, object]:
    """Compare supplied values deterministically; differing values are possible conflicts."""
    normalized: dict[str, str] = {}
    gaps: list[str] = []
    groups: dict[str, list[str]] = {}
    for document_name, item in values.items():
        value = item.value if isinstance(item, FieldResult) else str(item)
        normalized[document_name] = value
        if not value.strip() or value.strip().casefold() == "not stated":
            gaps.append(document_name)
        else:
            groups.setdefault(value.strip().casefold(), []).append(document_name)
    conflicts = [
        {"value": normalized[names[0]], "documents": names}
        for names in groups.values()
        if len(names) > 1
    ]
    distinct = {value.strip().casefold() for value in normalized.values() if value.strip() and value.casefold() != "not stated"}
    has_conflict = len(distinct) > 1
    return {
        "values": normalized,
        "gaps": gaps,
        "conflicts": (
            [{"type": "different_stated_values", "values": {k: v for k, v in normalized.items() if v.casefold() != "not stated"}}]
            if has_conflict
            else []
        ),
        "matching_groups": conflicts,
        "summary": "Potential differences need scope/version review." if has_conflict else "No conflicting stated values detected.",
    }

def compare_documents(
    document_fields: Mapping[str, Mapping[str, FieldResult | str]],
) -> dict[str, dict[str, object]]:
    field_names = sorted({field for fields in document_fields.values() for field in fields})
    result: dict[str, dict[str, object]] = {}
    for field in field_names:
        values = {
            doc_name: fields.get(field, "not stated")
            for doc_name, fields in document_fields.items()
        }
        result[field] = compare_values(values)
    return result
