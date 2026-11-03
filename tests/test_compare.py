from secquery.compare import compare_documents, compare_values
from secquery.models import FieldResult


def test_compare_reports_gaps_and_conflicts():
    result = compare_values({"A": FieldResult("fixed", "4.2.8"), "B": "not stated", "C": "4.3.1"})
    assert result["gaps"] == ["B"]
    assert result["conflicts"]


def test_compare_documents_builds_fieldwise_results():
    result = compare_documents({"A": {"CVSS": "8.8"}, "B": {"CVE": "not stated", "CVSS": "7.2"}})
    assert result["CVSS"]["conflicts"]
    assert result["CVE"]["gaps"] == ["A", "B"]
