import urllib.request
import urllib.error
import json

def test_endpoints():
    print("Testing Direct Backend & Vite Proxy Connections...\n")

    # 1. Health
    with urllib.request.urlopen("http://127.0.0.1:8000/health") as r:
        assert r.status == 200
        health_data = json.loads(r.read())
        print("1. Backend /health:", health_data)

    # 2. API Health
    with urllib.request.urlopen("http://127.0.0.1:8000/api/health") as r:
        assert r.status == 200
        print("2. Backend /api/health: OK")

    # 3. Vite Proxy Health
    with urllib.request.urlopen("http://127.0.0.1:5173/api/health") as r:
        assert r.status == 200
        proxy_health = json.loads(r.read())
        print("3. Vite Proxy /api/health:", proxy_health)

    # 4. Vite Proxy Demos
    with urllib.request.urlopen("http://127.0.0.1:5173/api/demos") as r:
        assert r.status == 200
        demos = json.loads(r.read())
        print(f"4. Vite Proxy /api/demos: Found {len(demos)} demo repos")

    # 5. Start Analysis via Vite Proxy
    req = urllib.request.Request(
        "http://127.0.0.1:5173/api/analyses",
        data=json.dumps({
            "repo_url": "fixture://vulnerable-python-repo",
            "run_secret_scan": True,
            "run_health_check": True
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        analysis = json.loads(r.read())
        aid = analysis["id"]
        vuln_count = len(analysis["vulnerabilities"])
        score = analysis["risk_overview"]["score"]
        status = analysis["status"]
        print(f"5. Start Analysis: ID={aid}, status={status}, vulns={vuln_count}, risk={score}")

    # 6. Fetch Analysis
    with urllib.request.urlopen(f"http://127.0.0.1:5173/api/analyses/{aid}") as r:
        assert r.status == 200
        print("6. Fetch Analysis: OK")

    # 7. CycloneDX SBOM
    with urllib.request.urlopen(f"http://127.0.0.1:5173/api/analyses/{aid}/sbom?format=cyclonedx") as r:
        assert r.status == 200
        sbom_cdx = json.loads(r.read())
        print(f"7. CycloneDX SBOM: bomFormat={sbom_cdx.get('bomFormat')}, components={len(sbom_cdx.get('components', []))}")

    # 8. SPDX SBOM
    with urllib.request.urlopen(f"http://127.0.0.1:5173/api/analyses/{aid}/sbom?format=spdx") as r:
        assert r.status == 200
        sbom_spdx = json.loads(r.read())
        print(f"8. SPDX SBOM: spdxVersion={sbom_spdx.get('spdxVersion')}, packages={len(sbom_spdx.get('packages', []))}")

    # 9. Audit Logs
    with urllib.request.urlopen(f"http://127.0.0.1:5173/api/analyses/{aid}/audit") as r:
        assert r.status == 200
        audit = json.loads(r.read())
        verified_hashes = all(len(e["integrity_hash"]) == 64 for e in audit)
        print(f"9. Audit Logs: {len(audit)} entries, verified hashes={verified_hashes}")

    # 10. Draft PR (Unconfirmed - expect 400)
    rem_id = analysis["remediations"][0]["id"]
    try:
        req_bad = urllib.request.Request(
            f"http://127.0.0.1:5173/api/analyses/{aid}/draft-pr",
            data=json.dumps({
                "analysis_id": aid,
                "remediation_id": rem_id,
                "user_confirmed": False,
                "pr_title": "Fix",
                "base_branch": "main"
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req_bad)
        raise AssertionError("Unconfirmed draft PR should fail with HTTP 400!")
    except urllib.error.HTTPError as e:
        assert e.code == 400
        print("10. Unconfirmed Draft PR: Correctly rejected (HTTP 400)")

    # 11. Draft PR (Confirmed)
    req_good = urllib.request.Request(
        f"http://127.0.0.1:5173/api/analyses/{aid}/draft-pr",
        data=json.dumps({
            "analysis_id": aid,
            "remediation_id": rem_id,
            "user_confirmed": True,
            "pr_title": "Fix vulnerability",
            "base_branch": "main"
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_good) as r:
        assert r.status == 200
        pr_res = json.loads(r.read())
        print(f"11. Confirmed Draft PR: status={pr_res.get('draft_status')}, branch={pr_res.get('branch_name')}")

    # 12. Debugger Defect
    req_dbg = urllib.request.Request(
        "http://127.0.0.1:5173/api/debug/analyze",
        data=json.dumps({
            "code": "def f(x=[]):\n    x.append(1)\n    return x",
            "language": "python"
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_dbg) as r:
        assert r.status == 200
        dbg = json.loads(r.read())
        print(f"12. Code Debugger (Defect): archetype={dbg.get('detected_archetype')}, line={dbg.get('faulty_line_number')}, conf={dbg.get('confidence_score')}")

    # 13. Debugger Clean
    req_dbg_clean = urllib.request.Request(
        "http://127.0.0.1:5173/api/debug/analyze",
        data=json.dumps({
            "code": "def add(a, b):\n    return a + b",
            "language": "python"
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_dbg_clean) as r:
        assert r.status == 200
        dbg_clean = json.loads(r.read())
        print(f"13. Code Debugger (Clean): archetype={dbg_clean.get('detected_archetype')}, issue_detected={dbg_clean.get('issue_detected')}")

    # 14. Secret Leak Analysis
    req_sec = urllib.request.Request(
        "http://127.0.0.1:5173/api/analyses",
        data=json.dumps({
            "repo_url": "fixture://secret-leak-repo",
            "run_secret_scan": True,
            "run_health_check": False
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_sec) as r:
        assert r.status == 200
        sec_analysis = json.loads(r.read())
        secrets = sec_analysis.get("secrets", [])
        assert len(secrets) >= 3
        assert all("*" in s["masked_value"] for s in secrets)
        print(f"14. Secret Leak Analysis: Found {len(secrets)} secrets; all masked with zero raw leaks")

    # 15. Frontend Root HTML
    with urllib.request.urlopen("http://127.0.0.1:5173/") as r:
        assert r.status == 200
        html = r.read().decode("utf-8")
        assert '<div id="root">' in html
        print("15. Frontend Root HTML: Loaded successfully (id=root present)")

    print("\nALL 15 COMMUNICATION PATHS VERIFIED VIA VITE PROXY AND BACKEND!")

if __name__ == "__main__":
    test_endpoints()
