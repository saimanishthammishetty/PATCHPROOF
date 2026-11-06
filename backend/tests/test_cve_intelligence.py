import pytest
import asyncio
from pathlib import Path
from app.services.vulnerability_service import VulnerabilityService, extract_cve_identifiers
from app.services.risk_engine import RiskEngine
from app.services.secret_scanner import SecretScanner
from app.services.remediation_service import RemediationService
from app.models.schemas import Component, VulnerabilityFinding, SecretFinding, DependencyHealthFinding

# 1. Vulnerability with a CVE alias
def test_cve_extraction_single_alias():
    adv_id = "GHSA-79v4-hx79-jx7p"
    aliases = ["CVE-2018-18074"]
    primary_cve, all_cves = extract_cve_identifiers(adv_id, aliases)
    assert primary_cve == "CVE-2018-18074"
    assert all_cves == ["CVE-2018-18074"]

# 2. Vulnerability with multiple CVE aliases
def test_cve_extraction_multiple_aliases():
    adv_id = "GHSA-multi-test-1234"
    aliases = ["CVE-2020-8203", "CVE-2020-8204", "GHSA-other"]
    primary_cve, all_cves = extract_cve_identifiers(adv_id, aliases)
    assert primary_cve == "CVE-2020-8203"
    assert "CVE-2020-8203" in all_cves
    assert "CVE-2020-8204" in all_cves
    assert len(all_cves) == 2

# 3. Vulnerability with OSV ID but no CVE
def test_cve_extraction_no_cve():
    adv_id = "GHSA-xxxx-yyyy-zzzz"
    aliases = ["PYSEC-2021-999"]
    primary_cve, all_cves = extract_cve_identifiers(adv_id, aliases)
    assert primary_cve is None
    assert all_cves == []

# 4. Vulnerability with direct CVE identifier
def test_cve_extraction_direct_cve():
    adv_id = "CVE-2021-44228"
    aliases = ["GHSA-jfh8-c2jp-5v3q"]
    primary_cve, all_cves = extract_cve_identifiers(adv_id, aliases)
    assert primary_cve == "CVE-2021-44228"
    assert all_cves == ["CVE-2021-44228"]

# 5. Vulnerability with no CVSS information
def test_risk_scoring_no_cvss():
    vuln = VulnerabilityFinding(
        id="GHSA-no-cvss-123",
        aliases=[],
        package="test-pkg",
        ecosystem="pypi",
        affected_version="1.0.0",
        fixed_version="1.0.1",
        severity="HIGH",
        cvss_score=None, # Missing numeric score
        reachability="reachable",
        recommended_action="Upgrade test-pkg",
        explanation="High severity issue without CVSS score in advisory",
        confidence="Medium"
    )
    score = RiskEngine.calculate_finding_risk(vuln)
    # Default high severity derivation (7.5 / 10 * 35) + reachability (10) + epss baseline
    assert score >= 35.0, f"Expected conservative non-zero score for missing CVSS, got {score}"

# 6. Vulnerability with no fixed version
def test_vulnerability_no_fixed_version():
    comp = Component(
        name="unfixed-lib",
        version="0.9.0",
        ecosystem="pypi",
        purl="pkg:pypi/unfixed-lib@0.9.0",
        direct=True,
        manifest_path="requirements.txt"
    )
    vuln = VulnerabilityFinding(
        id="GHSA-unfixed-001",
        aliases=["CVE-2023-99999"],
        package="unfixed-lib",
        ecosystem="pypi",
        affected_version="0.9.0",
        fixed_version=None,
        severity="MEDIUM",
        reachability="unknown",
        recommended_action="Investigate unfixed-lib advisory GHSA-unfixed-001",
        explanation="No upstream fix available",
        confidence="Medium"
    )
    # Remediation service must not propose an upgrade when fixed_version is None
    proposals = RemediationService.generate_remediations(
        repo_path=Path("."),
        vulnerabilities=[vuln],
        components=[comp]
    )
    assert len(proposals) == 0, "Should not generate remediation proposal without a verified fixed version"

# 7. Offline fallback vulnerability findings
def test_offline_fallback_cve_enrichment(monkeypatch):
    monkeypatch.setenv("PATCHPROOF_OFFLINE", "1")
    comps = [
        Component(
            name="requests",
            version="2.19.1",
            ecosystem="pypi",
            purl="pkg:pypi/requests@2.19.1",
            direct=True,
            manifest_path="fixtures/vulnerable-python-repo/requirements.txt",
            scope="fixture",
            line_number=1,
            manifest_snippet="requests==2.19.1"
        )
    ]
    findings = asyncio.run(VulnerabilityService.scan_components(comps))
    assert len(findings) >= 1
    req_finding = findings[0]
    assert req_finding.cve_id == "CVE-2018-18074"
    assert "CVE-2018-18074" in req_finding.cve_ids
    assert req_finding.cisa_kev is False
    assert req_finding.cisa_kev_status == "not_listed"
    assert "Local fallback result" in req_finding.confidence_reason
    assert req_finding.scope == "fixture"
    assert req_finding.manifest_line == 1
    assert req_finding.manifest_snippet == "requests==2.19.1"

# 8. Correct association between vulnerability and dependency
def test_vulnerability_dependency_association():
    comp = Component(
        name="requests",
        version="2.19.1",
        ecosystem="pypi",
        purl="pkg:pypi/requests@2.19.1",
        direct=True,
        manifest_path="requirements.txt",
        scope="production",
        scope_reason="Declared in production requirements.txt",
        line_number=4,
        manifest_snippet="requests==2.19.1"
    )
    findings = asyncio.run(VulnerabilityService.scan_components([comp]))
    for f in findings:
        assert f.package == "requests"
        assert f.affected_version == "2.19.1"
        assert f.scope == "production"
        assert f.manifest_line == 4
        assert f.manifest_snippet == "requests==2.19.1"

# 9. Correct risk-score explanation
def test_risk_score_explainability_and_cve_counts():
    comp = Component(
        name="requests",
        version="2.19.1",
        ecosystem="pypi",
        purl="pkg:pypi/requests@2.19.1",
        direct=True,
        manifest_path="requirements.txt",
        scope="production"
    )
    vuln_with_cve = VulnerabilityFinding(
        id="GHSA-79v4-hx79-jx7p",
        aliases=["CVE-2018-18074"],
        cve_id="CVE-2018-18074",
        cve_ids=["CVE-2018-18074"],
        package="requests",
        ecosystem="pypi",
        affected_version="2.19.1",
        fixed_version="2.20.0",
        severity="HIGH",
        cvss_score=7.5,
        cisa_kev=True,
        scope="production",
        reachability="reachable",
        recommended_action="Upgrade requests",
        explanation="Credential leak",
        confidence="High"
    )
    vuln_no_cve = VulnerabilityFinding(
        id="GHSA-no-cve-test",
        aliases=[],
        cve_id=None,
        cve_ids=[],
        package="requests",
        ecosystem="pypi",
        affected_version="2.19.1",
        fixed_version="2.20.0",
        severity="LOW",
        cvss_score=3.0,
        cisa_kev=False,
        scope="production",
        reachability="reachable",
        recommended_action="Upgrade requests",
        explanation="Minor issue",
        confidence="Low"
    )

    overview = RiskEngine.calculate_overall_risk(
        components=[comp],
        vulnerabilities=[vuln_with_cve, vuln_no_cve],
        secrets=[],
        health_findings=[]
    )

    breakdown = overview.breakdown
    assert breakdown["with_cve_count"] == 1
    assert breakdown["without_cve_count"] == 1
    assert breakdown["total_findings_count"] == 2
    assert breakdown["kev_count"] == 1
    assert overview.score >= 80.0
    assert overview.production_score >= 80.0

# 10. Secret classification: Real credential vs Synthetic credential in test directory
def test_secret_classification_never_dismisses_real_secret_in_test_dir():
    # A genuine random token in a test file must NOT be classified as synthetic!
    real_token = "ghp_RealSecretRandomToken9876543210ABC"
    real_info = SecretScanner.classify_secret(real_token, "tests/test_auth.py", "GitHub Personal Access Token")
    assert real_info["is_synthetic"] is False, "Must not classify real secret as synthetic solely because of test dir"
    assert real_info["secret_category"] == "Potential real credential"
    assert real_info["scope"] == "test"

    # A mock placeholder token in a test file MUST be classified as synthetic test credential
    dummy_token = "ghp_TestDummyToken1234567890abcdef1234"
    dummy_info = SecretScanner.classify_secret(dummy_token, "tests/test_auth.py", "GitHub Personal Access Token")
    assert dummy_info["is_synthetic"] is True
    assert dummy_info["secret_category"] == "Test credential"
    assert dummy_info["scope"] == "test"

# 11. Remediation diff generation and verification
def test_remediation_diff_and_safety_gate(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("requests==2.19.1\n", encoding="utf-8")

    comp = Component(
        name="requests",
        version="2.19.1",
        ecosystem="pypi",
        purl="pkg:pypi/requests@2.19.1",
        direct=True,
        manifest_path="requirements.txt"
    )
    vuln = VulnerabilityFinding(
        id="GHSA-79v4-hx79-jx7p",
        aliases=["CVE-2018-18074"],
        cve_id="CVE-2018-18074",
        package="requests",
        ecosystem="pypi",
        affected_version="2.19.1",
        fixed_version="2.20.0",
        severity="HIGH",
        reachability="reachable",
        recommended_action="Upgrade requests",
        explanation="Credential leak",
        confidence="High"
    )

    proposals = RemediationService.generate_remediations(
        repo_path=tmp_path,
        vulnerabilities=[vuln],
        components=[comp]
    )

    assert len(proposals) == 1
    prop = proposals[0]
    assert prop.proposed_version == "2.20.0"
    assert "-requests==2.19.1" in prop.diff
    assert "+requests==2.20.0" in prop.diff
    assert prop.verification_status == "Verified compatible"

# 12. No duplicate vulnerability counting across aliases
def test_no_duplicate_vulnerability_counting():
    comp = Component(
        name="requests",
        version="2.19.1",
        ecosystem="pypi",
        purl="pkg:pypi/requests@2.19.1",
        direct=True,
        manifest_path="requirements.txt"
    )
    # Scanning requests==2.19.1 should return deduplicated findings, not duplicates for CVE-2018-18074 and GHSA-79v4-hx79-jx7p
    findings = asyncio.run(VulnerabilityService.scan_components([comp]))
    ids_and_aliases = []
    for f in findings:
        ids_and_aliases.append(f.id)
        ids_and_aliases.extend(f.aliases)

    # GHSA-79v4-hx79-jx7p should only have one primary finding
    ghsa_findings = [f for f in findings if f.id == "GHSA-79v4-hx79-jx7p"]
    assert len(ghsa_findings) == 1
