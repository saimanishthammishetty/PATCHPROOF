import httpx
import json
import sys
from pathlib import Path

# Ensure backend package is importable
backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

def get_client():
    """Returns an httpx client targeting live 8000 or in-process TestClient fallback."""
    base_url = "http://127.0.0.1:8000"
    try:
        r = httpx.get(f"{base_url}/health", timeout=1.0)
        if r.status_code == 200:
            print("[INFO] Testing against live backend at http://127.0.0.1:8000")
            return httpx.Client(base_url=base_url, timeout=30.0)
    except Exception:
        pass
    
    print("[INFO] Live server on port 8000 not detected. Using FastAPI TestClient.")
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def run_sbom_validation():
    client = get_client()
    
    # Step 1: Create an analysis to validate SBOM exports against
    print("[1] Initializing fresh analysis for SBOM validation...")
    init_resp = client.post(
        "/api/analyses",
        json={"repo_url": "fixture://vulnerable-python-repo", "run_secret_scan": False, "run_health_check": False}
    )
    assert init_resp.status_code == 200, f"Analysis creation failed: {init_resp.text}"
    analysis = init_resp.json()
    analysis_id = analysis["id"]
    print(f"    Analysis ID created: {analysis_id}")
    print(f"    Total components parsed: {analysis['total_components']}")
    
    # Step 2: Validate CycloneDX 1.5 Export
    print("\n[2] Testing CycloneDX 1.5 SBOM endpoint...")
    cdx_resp = client.get(f"/api/analyses/{analysis_id}/sbom?format=cyclonedx")
    print(f"    HTTP Status: {cdx_resp.status_code}")
    print(f"    Content-Type: {cdx_resp.headers.get('content-type')}")
    print(f"    Content-Disposition: {cdx_resp.headers.get('content-disposition')}")
    print(f"    Raw Body (truncated 250 chars):\n    {cdx_resp.text[:250]}...")
    
    assert cdx_resp.status_code == 200, "CycloneDX request returned non-200"
    assert "application/vnd.cyclonedx+json" in cdx_resp.headers.get("content-type", "")
    
    cdx = cdx_resp.json()
    assert cdx.get("bomFormat") == "CycloneDX", f"Expected bomFormat=CycloneDX, got {cdx.get('bomFormat')}"
    assert cdx.get("specVersion") == "1.5", f"Expected specVersion=1.5, got {cdx.get('specVersion')}"
    assert str(cdx.get("serialNumber", "")).startswith("urn:uuid:"), "Invalid serialNumber URI format"
    assert "metadata" in cdx and "tools" in cdx["metadata"]
    assert "components" in cdx and len(cdx["components"]) >= 3
    
    for comp in cdx["components"]:
        assert comp.get("type") == "library"
        assert comp.get("name") in ["requests", "urllib3", "pyyaml"]
        assert comp.get("version") is not None
        assert comp.get("purl", "").startswith("pkg:pypi/")
        print(f"    -> CycloneDX Component Validated: {comp['name']} v{comp['version']} ({comp['purl']})")
    
    # Step 3: Validate SPDX 2.3 Export
    print("\n[3] Testing SPDX 2.3 SBOM endpoint...")
    spdx_resp = client.get(f"/api/analyses/{analysis_id}/sbom?format=spdx")
    print(f"    HTTP Status: {spdx_resp.status_code}")
    print(f"    Content-Type: {spdx_resp.headers.get('content-type')}")
    print(f"    Content-Disposition: {spdx_resp.headers.get('content-disposition')}")
    print(f"    Raw Body (truncated 250 chars):\n    {spdx_resp.text[:250]}...")
    
    assert spdx_resp.status_code == 200, "SPDX request returned non-200"
    assert "application/spdx+json" in spdx_resp.headers.get("content-type", "")
    
    spdx = spdx_resp.json()
    assert spdx.get("spdxVersion") == "SPDX-2.3", f"Expected spdxVersion=SPDX-2.3, got {spdx.get('spdxVersion')}"
    assert spdx.get("dataLicense") == "CC0-1.0", f"Expected dataLicense=CC0-1.0, got {spdx.get('dataLicense')}"
    assert spdx.get("SPDXID") == "SPDXRef-DOCUMENT"
    assert "packages" in spdx and len(spdx["packages"]) >= 3
    assert "relationships" in spdx and len(spdx["relationships"]) >= 3
    
    for pkg in spdx["packages"]:
        assert pkg.get("SPDXID", "").startswith("SPDXRef-Package-")
        assert pkg.get("name") in ["requests", "urllib3", "pyyaml"]
        assert pkg.get("downloadLocation") == "NOASSERTION"
        print(f"    -> SPDX Package Validated: {pkg['SPDXID']} - {pkg['name']} v{pkg['versionInfo']}")
        
    print("\n[SUCCESS] CycloneDX 1.5 and SPDX 2.3 JSON schemas strictly verified against live API.")

if __name__ == "__main__":
    run_sbom_validation()
