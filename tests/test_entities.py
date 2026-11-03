from secquery.entities import extract_entities

def test_security_identifiers_are_extracted_and_deduplicated():
    result = extract_entities("CVE-2024-12345 and cve-2024-12345; CWE-79; CVSS v3.1: 8.8; ATT&CK T1059.001; version 4.2.8")
    assert result["cve_ids"] == ["CVE-2024-12345"]
    assert result["cwe_ids"] == ["CWE-79"]
    assert any("8.8" in score for score in result["cvss_scores"])
    assert result["attack_ids"] == ["T1059.001"]
    assert "4.2.8" in result["versions"]


def test_dates_and_ip_addresses_are_not_treated_as_versions_or_ids():
    result = extract_entities("Published 2024-10-26; IPv4 192.168.1.10; internal id 12345")
    assert not result["cve_ids"]
    assert not result["cwe_ids"]
    assert "192.168.1.10" not in result["versions"]
    assert "2024.10.26" not in result["versions"]
