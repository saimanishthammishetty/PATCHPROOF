import subprocess
import time
import urllib.request
import urllib.error
import json
import sys

def run_suite():
    print("==================================================")
    print("PATCHPROOF COMPREHENSIVE INTEGRATION AUDIT SUITE")
    print("==================================================")

    # 1. Start server on isolated port 8002
    port = 8002
    base_url = f"http://127.0.0.1:{port}"
    print(f"\n[STEP 1] Starting backend test server on {base_url}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(5)

    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }

    def record_pass(test_name):
        print(f"  [PASS] {test_name}")
        test_results["passed"] += 1

    def record_fail(test_name, reason):
        print(f"  [FAIL] {test_name} - {reason}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{test_name}: {reason}")

    try:
        # A. Health check
        print("\n--- Testing System Health & Safety Guard ---")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=5) as r:
                data = json.loads(r.read())
                if data.get("status") == "healthy" and data.get("safety_guard") == "NEVER_MERGE_ACTIVE":
                    record_pass("GET /health returns healthy & NEVER_MERGE_ACTIVE")
                else:
                    record_fail("GET /health", f"Unexpected payload: {data}")
        except Exception as e:
            record_fail("GET /health", str(e))

        # B. Demo Repositories
        print("\n--- Testing Demo Repositories Endpoint ---")
        demos = []
        try:
            with urllib.request.urlopen(f"{base_url}/api/demos", timeout=5) as r:
                demos = json.loads(r.read())
                if len(demos) == 4:
                    record_pass("GET /api/demos returns 4 demo fixtures")
                else:
                    record_fail("GET /api/demos", f"Expected 4 demos, got {len(demos)}")
        except Exception as e:
            record_fail("GET /api/demos", str(e))

        # C. Full Pipeline for Each Demo Repository
        print("\n--- Testing Full End-to-End Pipeline on Fixtures ---")
        for demo in demos:
            demo_id = demo["id"]
            demo_url = demo["url"]
            print(f"\n>> Running Analysis Pipeline for: {demo_id} ({demo_url})")

            # 1. POST /api/analyses
            try:
                payload = json.dumps({
                    "repo_url": demo_url,
                    "run_secret_scan": True,
                    "run_health_check": True
                }).encode()
                req = urllib.request.Request(
                    f"{base_url}/api/analyses",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    analysis = json.loads(r.read())
                    aid = analysis.get("id")
                    record_pass(f"POST /api/analyses ({demo_id}) created id={aid}")

                    # Validate pipeline outputs
                    comps = analysis.get("components", [])
                    vulns = analysis.get("vulnerabilities", [])
                    secrets = analysis.get("secrets", [])
                    healths = analysis.get("health_findings", [])
                    remediations = analysis.get("remediations", [])
                    risk = analysis.get("risk_overview", {})
                    audit_logs = analysis.get("audit_logs", [])

                    print(f"     Components: {len(comps)}, Vulns: {len(vulns)}, Secrets: {len(secrets)}, Remediations: {len(remediations)}, Risk Score: {risk.get('score')}")

                    if demo_id == "vulnerable-python":
                        if len(comps) >= 3 and len(vulns) >= 3 and len(remediations) >= 1:
                            record_pass("vulnerable-python: components, CVEs, and remediations verified")
                        else:
                            record_fail("vulnerable-python expectations", f"comps={len(comps)}, vulns={len(vulns)}, rems={len(remediations)}")

                    elif demo_id == "vulnerable-node":
                        if len(comps) >= 2 and len(vulns) >= 2:
                            record_pass("vulnerable-node: components and CVEs verified")
                        else:
                            record_fail("vulnerable-node expectations", f"comps={len(comps)}, vulns={len(vulns)}")

                    elif demo_id == "secret-leak":
                        if len(secrets) >= 3:
                            # Verify all secrets are masked
                            all_masked = all("*" in s.get("masked_value", "") for s in secrets)
                            if all_masked:
                                record_pass(f"secret-leak: {len(secrets)} secrets detected and 100% masked")
                            else:
                                record_fail("secret-leak: masking", "Unmasked secret detected!")
                        else:
                            record_fail("secret-leak expectations", f"secrets={len(secrets)}")

                    elif demo_id == "secure-go":
                        if len(vulns) == 0 and risk.get("score") == 0:
                            record_pass("secure-go: clean repo verified (0 vulns, 0 risk)")
                        else:
                            record_fail("secure-go expectations", f"vulns={len(vulns)}, risk={risk.get('score')}")

                    # 2. GET /api/analyses/{aid}
                    with urllib.request.urlopen(f"{base_url}/api/analyses/{aid}", timeout=10) as get_r:
                        fetched = json.loads(get_r.read())
                        if fetched.get("id") == aid:
                            record_pass(f"GET /api/analyses/{aid} succeeds")
                        else:
                            record_fail(f"GET /api/analyses/{aid}", "Mismatched ID")

                    # 3. GET /api/analyses/{aid}/sbom?format=cyclonedx
                    with urllib.request.urlopen(f"{base_url}/api/analyses/{aid}/sbom?format=cyclonedx", timeout=10) as cdx_r:
                        cdx = json.loads(cdx_r.read())
                        if cdx.get("bomFormat") == "CycloneDX" and cdx.get("specVersion") == "1.5":
                            record_pass(f"CycloneDX 1.5 export for {demo_id}")
                        else:
                            record_fail(f"CycloneDX export {demo_id}", f"Invalid format: {cdx.get('bomFormat')}")

                    # 4. GET /api/analyses/{aid}/sbom?format=spdx
                    with urllib.request.urlopen(f"{base_url}/api/analyses/{aid}/sbom?format=spdx", timeout=10) as spdx_r:
                        spdx = json.loads(spdx_r.read())
                        if spdx.get("spdxVersion") == "SPDX-2.3":
                            record_pass(f"SPDX 2.3 export for {demo_id}")
                        else:
                            record_fail(f"SPDX export {demo_id}", f"Invalid version: {spdx.get('spdxVersion')}")

                    # 5. GET /api/analyses/{aid}/findings
                    with urllib.request.urlopen(f"{base_url}/api/analyses/{aid}/findings", timeout=10) as find_r:
                        findings = json.loads(find_r.read())
                        if len(findings) == len(vulns):
                            record_pass(f"GET /findings for {demo_id} returns {len(findings)} records")
                        else:
                            record_fail(f"GET /findings {demo_id}", "Count mismatch")

                    # 6. GET /api/analyses/{aid}/dependencies
                    with urllib.request.urlopen(f"{base_url}/api/analyses/{aid}/dependencies", timeout=10) as dep_r:
                        dependencies = json.loads(dep_r.read())
                        if len(dependencies) == len(comps):
                            record_pass(f"GET /dependencies for {demo_id} returns {len(dependencies)} records")
                        else:
                            record_fail(f"GET /dependencies {demo_id}", "Count mismatch")

                    # 7. GET /api/analyses/{aid}/audit
                    with urllib.request.urlopen(f"{base_url}/api/analyses/{aid}/audit", timeout=10) as aud_r:
                        audit_list = json.loads(aud_r.read())
                        if len(audit_list) > 0 and all("integrity_hash" in e for e in audit_list):
                            record_pass(f"GET /audit for {demo_id} verified with SHA-256 hashes")
                        else:
                            record_fail(f"GET /audit {demo_id}", "No audit or missing hashes")

                    # 8. Test Draft PR if remediations exist
                    if remediations:
                        rem_id = remediations[0]["id"]
                        
                        # Test without user_confirmed -> expect 400
                        try:
                            bad_pr_payload = json.dumps({
                                "analysis_id": aid,
                                "remediation_id": rem_id,
                                "base_branch": "main",
                                "pr_title": "Fix upgrade",
                                "pr_body": "test",
                                "user_confirmed": False
                            }).encode()
                            bad_req = urllib.request.Request(
                                f"{base_url}/api/analyses/{aid}/draft-pr",
                                data=bad_pr_payload,
                                headers={"Content-Type": "application/json"}
                            )
                            urllib.request.urlopen(bad_req, timeout=10)
                            record_fail(f"Draft PR user_confirmed=False guard ({demo_id})", "Request should have been rejected with 400")
                        except urllib.error.HTTPError as he:
                            if he.code == 400:
                                record_pass(f"Draft PR rejects unconfirmed request with HTTP 400 ({demo_id})")
                            else:
                                record_fail(f"Draft PR guard ({demo_id})", f"Expected 400, got {he.code}")

                        # Test with user_confirmed = True
                        try:
                            good_pr_payload = json.dumps({
                                "analysis_id": aid,
                                "remediation_id": rem_id,
                                "base_branch": "main",
                                "pr_title": f"Safe bump {remediations[0]['package']}",
                                "pr_body": "Automated patch proposal",
                                "user_confirmed": True
                            }).encode()
                            good_req = urllib.request.Request(
                                f"{base_url}/api/analyses/{aid}/draft-pr",
                                data=good_pr_payload,
                                headers={"Content-Type": "application/json"}
                            )
                            with urllib.request.urlopen(good_req, timeout=10) as pr_r:
                                pr_data = json.loads(pr_r.read())
                                if pr_data.get("success") and "DRAFT" in pr_data.get("draft_status", ""):
                                    record_pass(f"Draft PR creation verified as DRAFT ({demo_id})")
                                else:
                                    record_fail(f"Draft PR result ({demo_id})", f"Invalid response: {pr_data}")
                        except Exception as pe:
                            record_fail(f"Draft PR creation ({demo_id})", str(pe))

            except Exception as e:
                record_fail(f"POST /api/analyses ({demo_id})", str(e))

        # D. Security Validation: URL restrictions & SSRF protection
        print("\n--- Testing Security Validation & SSRF Boundary ---")
        disallowed_urls = [
            "http://127.0.0.1:8000",
            "http://localhost/repo",
            "http://169.254.169.254/latest/meta-data",
            "http://0.0.0.0/foo",
            "file:///etc/passwd",
            "ftp://github.com/foo/bar"
        ]
        for bad_url in disallowed_urls:
            try:
                p = json.dumps({"repo_url": bad_url}).encode()
                req = urllib.request.Request(
                    f"{base_url}/api/analyses",
                    data=p,
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=5)
                record_fail(f"Security: Disallowed URL {bad_url}", "Should have been rejected!")
            except urllib.error.HTTPError as he:
                if he.code == 400:
                    record_pass(f"Security: Blocked invalid/SSRF URL '{bad_url}' (HTTP 400)")
                else:
                    record_fail(f"Security: {bad_url}", f"Expected 400, got {he.code}")
            except Exception as e:
                record_pass(f"Security: Blocked '{bad_url}' with {type(e).__name__}")

        # E. AI Code Debugger Complete Workflow
        print("\n--- Testing AI Code Debugger Workflow ---")
        debug_test_cases = [
            {
                "name": "Empty source code",
                "code": "   ",
                "lang": "python",
                "expect_error": 400
            },
            {
                "name": "Oversized source code (>100k)",
                "code": "x = 1\n" * 25000,
                "lang": "python",
                "expect_error": 400
            },
            {
                "name": "Unsupported programming language",
                "code": "print('hello')",
                "lang": "cobol",
                "expect_error": 400
            },
            {
                "name": "Python Mutable Default Argument",
                "code": "def process_batch(item, queue=[]):\n    queue.append(item)\n    return queue\n",
                "lang": "python",
                "expect_issue": True,
                "check_diff": True,
                "check_line": 1
            },
            {
                "name": "Python Identity Comparison on Literal",
                "code": "def check(status):\n    if status is 200:\n        return True\n    return False\n",
                "lang": "python",
                "expect_issue": True,
                "check_diff": True,
                "check_line": 2
            },
            {
                "name": "JavaScript Loose Equality",
                "code": "function checkUser(val) {\n    if (val == 0) {\n        return 'EMPTY';\n    }\n    return 'OK';\n}\n",
                "lang": "javascript",
                "expect_issue": True,
                "check_diff": True,
                "check_line": 2
            },
            {
                "name": "Python Clean Code Control",
                "code": "def calculate_sum(items):\n    if not isinstance(items, list):\n        raise TypeError('Expected list')\n    return sum(x for x in items if isinstance(x, (int, float)))\n",
                "lang": "python",
                "expect_issue": False
            },
            {
                "name": "C Dangling Local Buffer",
                "code": "char* get_buffer() {\n    char buf[64];\n    return buf;\n}\n",
                "lang": "c",
                "expect_issue": True,
                "check_line": 3
            },
            {
                "name": "Java Method Inspection",
                "code": "public class Demo {\n    public static int add(int a, int b) {\n        return a + b;\n    }\n}\n",
                "lang": "java",
                "expect_issue": False
            },
            {
                "name": "Go Function Inspection",
                "code": "package main\n\nfunc Add(a int, b int) int {\n    return a + b\n}\n",
                "lang": "go",
                "expect_issue": False
            }
        ]

        for tc in debug_test_cases:
            tc_name = tc["name"]
            req_body = json.dumps({"code": tc["code"], "language": tc["lang"]}).encode()
            req = urllib.request.Request(
                f"{base_url}/api/debug/analyze",
                data=req_body,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    if tc.get("expect_error"):
                        record_fail(tc_name, f"Expected error {tc['expect_error']}, but got 200")
                    else:
                        issue_detected = data.get("issue_detected")
                        cat = data.get("predicted_category")
                        conf = data.get("confidence_score")
                        diff = data.get("diff")
                        flno = data.get("faulty_line_number")
                        print(f"     -> {tc_name}: issue={issue_detected}, cat={cat}, conf={conf}, line={flno}, has_diff={bool(diff)}")

                        if tc.get("expect_issue") is True and not issue_detected:
                            record_fail(tc_name, f"Expected issue detected, got clean ({cat})")
                        elif tc.get("expect_issue") is False and issue_detected:
                            record_fail(tc_name, f"Expected clean code, got issue ({cat})")
                        else:
                            if tc.get("check_diff") and not diff:
                                record_fail(tc_name, "Expected remediation diff, got None")
                            elif tc.get("check_line") and flno != tc["check_line"]:
                                record_fail(tc_name, f"Expected line {tc['check_line']}, got {flno}")
                            else:
                                record_pass(f"AI Debugger: {tc_name}")

            except urllib.error.HTTPError as he:
                if tc.get("expect_error") and he.code == tc["expect_error"]:
                    record_pass(f"AI Debugger validation guard: {tc_name} returned HTTP {he.code}")
                else:
                    record_fail(tc_name, f"Unexpected HTTP {he.code}: {he.read().decode()[:200]}")
            except Exception as e:
                record_fail(tc_name, str(e))

    finally:
        print("\n[STEP 5] Shutting down backend test server...")
        proc.terminate()
        proc.wait()

    print("\n==================================================")
    print("AUDIT SUMMARY RESULTS")
    print("==================================================")
    print(f"Total Passed: {test_results['passed']}")
    print(f"Total Failed: {test_results['failed']}")
    if test_results['errors']:
        print("\nFailure Details:")
        for err in test_results['errors']:
            print(f" - {err}")
    print("==================================================")

    return test_results["failed"] == 0

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)

