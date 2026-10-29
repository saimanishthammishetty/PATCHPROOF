import pytest
from app.services.risk_engine import RiskEngine
from app.models.schemas import VulnerabilityFinding, Component

def test_risk_scoring_kev_override():
    # A vulnerability with CISA KEV membership must score >= 80 (Critical)
    vuln = VulnerabilityFinding(
        id="GHSA-79v4-hx79-jx7p",
        aliases=["CVE-2018-18074"],
        package="requests",
        ecosystem="pypi",
        affected_version="2.19.1",
        fixed_version="2.20.0",
        severity="HIGH",
        cvss_score=7.5,
        epss_probability=0.35,
        cisa_kev=True,
        reachability="reachable",
        recommended_action="Upgrade requests",
        explanation="Credential leak in redirects",
        confidence="High"
    )

    score = RiskEngine.calculate_finding_risk(vuln)
    assert score >= 80.0, f"Expected KEV finding to score >= 80, got {score}"

def test_overall_risk_clean_repository():
    clean_comp = Component(
        name="uuid",
        version="1.6.0",
        ecosystem="golang",
        purl="pkg:golang/uuid@1.6.0",
        direct=True,
        manifest_path="go.mod"
    )

    overview = RiskEngine.calculate_overall_risk(
        components=[clean_comp],
        vulnerabilities=[],
        secrets=[],
        health_findings=[]
    )

    assert overview.score < 20.0
    assert overview.label == "Low"

