import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["safety_guard"] == "NEVER_MERGE_ACTIVE"

def test_get_demo_repositories():
    response = client.get("/api/demos")
    assert response.status_code == 200
    demos = response.json()
    assert len(demos) >= 4
    ids = [d["id"] for d in demos]
    assert "vulnerable-python" in ids
    assert "vulnerable-node" in ids
    assert "secret-leak" in ids
    assert "secure-go" in ids

def test_end_to_end_analysis_vulnerable_python():
    payload = {
        "repo_url": "fixture://vulnerable-python-repo",
        "run_secret_scan": True,
        "run_health_check": True
    }
    response = client.post("/api/analyses", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert data["total_components"] >= 3
    assert data["risk_overview"]["score"] >= 80.0
    assert data["risk_overview"]["label"] == "Critical"
    assert len(data["vulnerabilities"]) >= 3
    assert len(data["remediations"]) >= 1

    analysis_id = data["id"]

    # Test CycloneDX SBOM export
    cyclonedx_resp = client.get(f"/api/analyses/{analysis_id}/sbom?format=cyclonedx")
    assert cyclonedx_resp.status_code == 200
    bom = cyclonedx_resp.json()
    assert bom["bomFormat"] == "CycloneDX"
    assert len(bom["components"]) >= 3

    # Test SPDX SBOM export
    spdx_resp = client.get(f"/api/analyses/{analysis_id}/sbom?format=spdx")
    assert spdx_resp.status_code == 200
    spdx = spdx_resp.json()
    assert spdx["spdxVersion"] == "SPDX-2.3"

    # Test Audit Trail
    audit_resp = client.get(f"/api/analyses/{analysis_id}/audit")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) >= 4
    for log in logs:
        assert "integrity_hash" in log
        assert len(log["integrity_hash"]) == 64  # SHA-256

def test_draft_pr_creation_api():
    # 1. Run analysis
    analysis_resp = client.post("/api/analyses", json={"repo_url": "fixture://vulnerable-python-repo"})
    analysis_data = analysis_resp.json()
    analysis_id = analysis_data["id"]
    remediation = analysis_data["remediations"][0]

    # 2. Attempt draft PR without user confirmation (must fail 400)
    fail_payload = {
        "analysis_id": analysis_id,
        "remediation_id": remediation["id"],
        "base_branch": "main",
        "pr_title": "Fix vulnerability",
        "pr_body": "Automated fix description",
        "user_confirmed": False
    }
    fail_resp = client.post(f"/api/analyses/{analysis_id}/draft-pr", json=fail_payload)
    assert fail_resp.status_code == 400

    # 3. Create draft PR with explicit confirmation
    success_payload = {
        "analysis_id": analysis_id,
        "remediation_id": remediation["id"],
        "base_branch": "main",
        "pr_title": f"Upgrade {remediation['package']} to {remediation['proposed_version']}",
        "pr_body": "Detailed security description",
        "user_confirmed": True
    }
    success_resp = client.post(f"/api/analyses/{analysis_id}/draft-pr", json=success_payload)
    assert success_resp.status_code == 200
    pr_data = success_resp.json()
    assert pr_data["success"] is True
    assert "DRAFT" in pr_data["draft_status"]
    assert "never automatically merge" in pr_data["safety_notice"]

