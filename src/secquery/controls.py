from __future__ import annotations

CONTROL_MAP: dict[str, list[dict[str, str]]] = {
    "sql injection": [
        {"control": "Parameterized queries", "family": "Secure coding", "reference": "OWASP ASVS"},
        {"control": "Input validation", "family": "Application security", "reference": "OWASP Top 10"},
    ],
    "credential theft": [
        {"control": "Phishing-resistant MFA", "family": "Identity", "reference": "NIST CSF 2.0"},
        {"control": "Credential rotation and session revocation", "family": "Incident response", "reference": "Organization policy"},
    ],
    "privilege escalation": [
        {"control": "Least privilege", "family": "Access control", "reference": "NIST CSF 2.0"},
        {"control": "Review privileged access", "family": "Identity", "reference": "Organization policy"},
    ],
}


def map_threat_to_controls(threat: str) -> list[dict[str, str]]:
    """Return candidate controls, clearly treated as suggestions rather than compliance claims."""
    lowered = threat.casefold()
    matches = [control for key, values in CONTROL_MAP.items() if key in lowered for control in values]
    return matches or [{"control": "Review applicable security policy", "family": "General", "reference": "Not mapped"}]
