import pytest
from app.services.secret_scanner import SecretScanner
from app.core.config import FIXTURES_DIR
from app.core.security import redact_secret_string

def test_secret_scanner_detection_and_redaction():
    fixture_path = FIXTURES_DIR / "secret-leak-repo"
    findings = SecretScanner.scan_repository(fixture_path)

    assert len(findings) >= 3, "Expected at least 3 detected secrets"

    # CRITICAL SECURITY TEST: Ensure raw secret values are NEVER present
    raw_forbidden_values = [
        "AKIAIOSFODNN7EXAMPLE",
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "ghp_TestDummyToken1234567890abcdef123456",
        "sk-TestSampleOpenAISecretKey1234567890abcdef1234"
    ]

    for finding in findings:
        for raw_val in raw_forbidden_values:
            assert raw_val != finding.masked_value, f"Raw secret leaked in masked_value: {raw_val}"
            assert raw_val not in finding.masked_value, f"Raw secret fragment leaked: {raw_val}"

        # Verify mask format contains asterisks
        assert "*" in finding.masked_value

def test_redact_secret_string_utility():
    sample = "ghp_1234567890abcdef1234567890abcdef"
    masked = redact_secret_string(sample)
    assert sample not in masked
    assert masked.startswith("ghp_")
    assert masked.endswith("cdef")
    assert "*" in masked

