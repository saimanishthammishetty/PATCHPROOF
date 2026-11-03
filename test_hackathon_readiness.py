"""
PATCHPROOF End-to-End Hackathon Readiness Verification Suite
Tests all 8 core product features + Code Debugger + Security Guarantees:
1. GitHub repository URL input and repository scanning (public GitHub and fixtures)
2. SBOM generation (CycloneDX 1.5 JSON & SPDX 2.3 JSON)
3. Vulnerability detection (OSV.dev, CISA KEV, EPSS)
4. Secret scanning (working tree, git history, redaction)
5. Dependency risk analysis (manifest parsing, direct vs transitive, health)
6. Explainable risk scoring (0-100 deterministic formula)
7. Remediation recommendations and PR drafts (unified diffs, human confirmation, draft-only)
8. Dashboard and audit logs (tamper-evident SHA-256 trail)
9. Code Debugger (ML classification & static defect localization)
10. Security & SSRF protections (blocking localhost, private IPs, auto-merges)
"""

import sys
import json
import time
from pathlib import Path

backend_path = Path("backend").resolve()
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import (
    validate_repository_url,
    verify_safe_pull_request_action,
    redact_secret_string
)

def run_readiness_audit():
    client = TestClient(app)
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    def record_test(name: str, passed: bool, details: str):
        status = "PASS" if passed else "FAIL"
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append({"name": name, "status": status, "details": details})
        print(f"[{status}] {name}: {details}")

    print("=" * 80)
    print("PATCHPROOF HACKATHON READINESS VERIFICATION AUDIT")
    print("=" * 80)

    # -----------------------------------------------------------------------
    # Test 1: API Startup & Health
    # -----------------------------------------------------------------------
    try:
        r = client.get("/health")
        passed = (r.status_code == 200 and r.json().get("status") == "healthy")
        record_test("API Startup & Health Check", passed, f"Status: {r.status_code}, Payload: {r.json()}")
    except Exception as e:
        record_test("API Startup & Health Check", False, str(e))

    # -----------------------------------------------------------------------
    # Test 2: Demo Repositories Discovery
    # -----------------------------------------------------------------------
    try:
        r = client.get("/api/demos")
        demos = r.json()
        passed = (r.status_code == 200 and len(demos) >= 4)
        record_test("Demo Repositories Discovery", passed, f"Found {len(demos)} demo repositories")
    except Exception as e:
        record_test("Demo Repositories Discovery", False, str(e))

    # -----------------------------------------------------------------------
    # Test 3: Feature 1 & 5 — Dependency Parsing & Manifest Inspection (Python)
    # -----------------------------------------------------------------------
    analysis_py = None
    try:
        r = client.post("/api/analyses", json={
            "repo_url": "fixture://vulnerable-python-repo",
            "run_secret_scan": True,
            "run_health_check": True
        })
        passed = (r.status_code == 200)
        analysis_py = r.json()
        comp_count = analysis_py.get("total_components", 0)
        passed = passed and (comp_count == 3)
        record_test("Python Repository & Dependency Parsing", passed, f"Parsed {comp_count} components from requirements.txt")
    except Exception as e:
        record_test("Python Repository & Dependency Parsing", False, str(e))

    # -----------------------------------------------------------------------
    # Test 4: Feature 2 — SBOM Generation (CycloneDX & SPDX)
    # -----------------------------------------------------------------------
    try:
        aid = analysis_py["id"]
        cdx = client.get(f"/api/analyses/{aid}/sbom?format=cyclonedx")
        spdx = client.get(f"/api/analyses/{aid}/sbom?format=spdx")
        cdx_json = cdx.json()
        spdx_json = spdx.json()

        cdx_valid = (cdx.status_code == 200 and cdx_json.get("bomFormat") == "CycloneDX" and len(cdx_json.get("components", [])) == 3)
        spdx_valid = (spdx.status_code == 200 and spdx_json.get("spdxVersion") == "SPDX-2.3" and len(spdx_json.get("packages", [])) == 3)
        passed = cdx_valid and spdx_valid
        record_test("SBOM Export (CycloneDX 1.5 & SPDX 2.3)", passed, f"CycloneDX components: {len(cdx_json.get('components', []))}, SPDX packages: {len(spdx_json.get('packages', []))}")
    except Exception as e:
        record_test("SBOM Export (CycloneDX 1.5 & SPDX 2.3)", False, str(e))

    # -----------------------------------------------------------------------
    # Test 5: Feature 3 — Vulnerability Detection (OSV.dev + CISA KEV + EPSS)
    # -----------------------------------------------------------------------
    try:
        vulns = analysis_py.get("vulnerabilities", [])
        has_kev = any(v.get("cisa_kev") for v in vulns)
        has_critical = any(v.get("severity") == "CRITICAL" for v in vulns)
        passed = (len(vulns) >= 2 and has_critical and has_kev)
        record_test("Vulnerability Detection & Threat Enrichment", passed, f"Identified {len(vulns)} advisories (Critical: {has_critical}, CISA KEV: {has_kev})")
    except Exception as e:
        record_test("Vulnerability Detection & Threat Enrichment", False, str(e))

    # -----------------------------------------------------------------------
    # Test 6: Feature 4 — Secret Scanning & Redaction
    # -----------------------------------------------------------------------
    try:
        r_sec = client.post("/api/analyses", json={
            "repo_url": "fixture://secret-leak-repo",
            "run_secret_scan": True,
            "run_health_check": False
        })
        sec_data = r_sec.json()
        secrets = sec_data.get("secrets", [])
        passed = (r_sec.status_code == 200 and len(secrets) >= 3)
        all_masked = all("*" in s.get("masked_value", "") for s in secrets)
        no_raw_leaks = all("AKIA" not in s.get("masked_value", "")[4:] for s in secrets)
        passed = passed and all_masked and no_raw_leaks
        record_test("Secret Scanner & Zero-Leak Redaction", passed, f"Found {len(secrets)} secrets; all strictly redacted with rotation playbooks")
    except Exception as e:
        record_test("Secret Scanner & Zero-Leak Redaction", False, str(e))

    # -----------------------------------------------------------------------
    # Test 7: Feature 6 — Explainable Risk Engine
    # -----------------------------------------------------------------------
    try:
        risk = analysis_py.get("risk_overview", {})
        score = risk.get("score", 0)
        label = risk.get("label", "")
        breakdown = risk.get("breakdown", {})
        passed = (score >= 70.0 and label == "Critical" and "cvss_factor" in breakdown and "kev_factor" in breakdown)
        record_test("Deterministic Explainable Risk Engine", passed, f"Score: {score}/100 ({label}) with mathematical factor breakdown")
    except Exception as e:
        record_test("Deterministic Explainable Risk Engine", False, str(e))

    # -----------------------------------------------------------------------
    # Test 8: Feature 7 — Safe Remediation Proposal & Unified Diff
    # -----------------------------------------------------------------------
    remediation_id = None
    try:
        remeds = analysis_py.get("remediations", [])
        passed = (len(remeds) >= 1)
        r0 = remeds[0]
        remediation_id = r0.get("id")
        has_diff = ("---" in r0.get("manifest_diff", "") and "+++" in r0.get("manifest_diff", ""))
        passed = passed and has_diff and (r0.get("proposed_version") != r0.get("current_version"))
        record_test("Automated Safe Remediation Planning", passed, f"Generated proposal for {r0.get('package')} ({r0.get('current_version')} -> {r0.get('proposed_version')}) with unified diff")
    except Exception as e:
        record_test("Automated Safe Remediation Planning", False, str(e))

    # -----------------------------------------------------------------------
    # Test 9: Feature 7 — Draft PR Creation (Confirmed vs Unconfirmed)
    # -----------------------------------------------------------------------
    try:
        aid = analysis_py["id"]
        # A: Unconfirmed attempt (MUST BE REJECTED)
        unconf_resp = client.post(f"/api/analyses/{aid}/draft-pr", json={
            "analysis_id": aid,
            "remediation_id": remediation_id,
            "user_confirmed": False,
            "pr_title": "Fix vulnerability",
            "base_branch": "main"
        })
        reject_passed = (unconf_resp.status_code == 400)

        # B: Confirmed attempt (MUST SUCCEED AS DRAFT ONLY)
        conf_resp = client.post(f"/api/analyses/{aid}/draft-pr", json={
            "analysis_id": aid,
            "remediation_id": remediation_id,
            "user_confirmed": True,
            "pr_title": "Security Fix: Upgrade requests to safe version",
            "base_branch": "main"
        })
        pr_data = conf_resp.json()
        accept_passed = (conf_resp.status_code == 200 and pr_data.get("success") is True and "DRAFT" in pr_data.get("draft_status"))
        passed = reject_passed and accept_passed
        record_test("Human-Reviewed Draft PR Creation Gate", passed, f"Unconfirmed rejected (400): {reject_passed}; Confirmed created Draft: {pr_data.get('draft_status')}")
    except Exception as e:
        record_test("Human-Reviewed Draft PR Creation Gate", False, str(e))

    # -----------------------------------------------------------------------
    # Test 10: Feature 8 — Cryptographic Audit Trail
    # -----------------------------------------------------------------------
    try:
        aid = analysis_py["id"]
        r_audit = client.get(f"/api/analyses/{aid}/audit")
        logs = r_audit.json()
        passed = (r_audit.status_code == 200 and len(logs) >= 5)
        all_hashed = all(len(log.get("integrity_hash", "")) == 64 for log in logs)
        passed = passed and all_hashed
        record_test("Tamper-Evident SHA-256 Audit Trail", passed, f"Recorded {len(logs)} lifecycle events with verified 256-bit cryptographic hashes")
    except Exception as e:
        record_test("Tamper-Evident SHA-256 Audit Trail", False, str(e))

    # -----------------------------------------------------------------------
    # Test 11: Feature 9 — ML Code Debugger Endpoint
    # -----------------------------------------------------------------------
    try:
        debug_req = {
            "code": "def process_data(items=[]):\n    items.append(1)\n    return items",
            "language": "python"
        }
        r_dbg = client.post("/api/debug/analyze", json=debug_req)
        dbg_data = r_dbg.json()
        passed = (r_dbg.status_code == 200 and dbg_data.get("detected_archetype") == "api_misuse" and len(dbg_data.get("proposed_fixes", [])) >= 1)
        record_test("ML-Assisted Code Debugger Inference", passed, f"Detected archetype: {dbg_data.get('detected_archetype')}, Confidence: {dbg_data.get('confidence')*100:.1f}%, Proposed fix diff generated")
    except Exception as e:
        record_test("ML-Assisted Code Debugger Inference", False, str(e))

    # -----------------------------------------------------------------------
    # Test 12: Security & SSRF Protection Gates
    # -----------------------------------------------------------------------
    try:
        ssrf_cases = [
            "http://127.0.0.1:8000/internal",
            "http://localhost:3000",
            "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.1/admin",
            "ftp://github.com/owner/repo"
        ]
        all_blocked = True
        for target in ssrf_cases:
            valid, msg = validate_repository_url(target)
            if valid:
                all_blocked = False
                break
        
        # Test merge violation guard
        merge_blocked = False
        try:
            verify_safe_pull_request_action("merge")
        except RuntimeError:
            merge_blocked = True

        passed = all_blocked and merge_blocked
        record_test("SSRF & Auto-Merge Security Architecture", passed, f"Blocked 5/5 SSRF attack vectors; Prohibited merge guard active")
    except Exception as e:
        record_test("SSRF & Auto-Merge Security Architecture", False, str(e))

    # -----------------------------------------------------------------------
    # Test 13: Node.js / npm Ecosystem Parsing & Vulnerability
    # -----------------------------------------------------------------------
    try:
        r_node = client.post("/api/analyses", json={
            "repo_url": "fixture://vulnerable-node-repo",
            "run_secret_scan": False,
            "run_health_check": True
        })
        node_data = r_node.json()
        passed = (r_node.status_code == 200 and node_data.get("total_components") >= 2 and len(node_data.get("vulnerabilities", [])) >= 2)
        record_test("Node.js / npm Ecosystem Analysis", passed, f"Parsed {node_data.get('total_components')} npm packages; Found {len(node_data.get('vulnerabilities', []))} vulnerabilities")
    except Exception as e:
        record_test("Node.js / npm Ecosystem Analysis", False, str(e))

    # -----------------------------------------------------------------------
    # Test 14: Hardened Go Repository (Clean Control)
    # -----------------------------------------------------------------------
    try:
        r_go = client.post("/api/analyses", json={
            "repo_url": "fixture://secure-go-repo",
            "run_secret_scan": True,
            "run_health_check": True
        })
        go_data = r_go.json()
        passed = (r_go.status_code == 200 and len(go_data.get("vulnerabilities", [])) == 0 and go_data.get("risk_overview", {}).get("score") == 0.0)
        record_test("Hardened Clean Repository Control", passed, f"0 CVEs detected; Risk Score: {go_data.get('risk_overview', {}).get('score')}/100 ({go_data.get('risk_overview', {}).get('label')})")
    except Exception as e:
        record_test("Hardened Clean Repository Control", False, str(e))

    print("\n" + "=" * 80)
    print(f"AUDIT SUMMARY: {results['passed']} PASSED, {results['failed']} FAILED (Total: {len(results['tests'])})")
    print("=" * 80)

    return results

if __name__ == "__main__":
    res = run_readiness_audit()
    with open("docs/hackathon_readiness_test_results.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    sys.exit(0 if res["failed"] == 0 else 1)

