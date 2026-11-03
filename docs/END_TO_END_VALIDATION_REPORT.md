# PATCHPROOF — End-to-End Application Validation Report

**Date & Time:** November 3, 2026 — 19:32 IST  
**Environment:** Windows (PowerShell) / Python 3.12.10 / Node.js & Vite / Live In-Process Uvicorn Server  
**Backend Port:** `http://127.0.0.1:8008` (Serving both FastAPI REST API and compiled React SPA)  
**Production Model SHA-256:** `5F93BBA9CE457FE991580AFCD3C482D2D8FB626C019AB1DCDA58B73731176A20`  
**Safety Invariant:** `NEVER_MERGE_ACTIVE` (Enforced & Verified)

---

## 1. Executive Summary

A comprehensive, read-only end-to-end validation of the complete PATCHPROOF platform was conducted. Rather than testing isolated unit functions, this audit launched a live HTTP server mounting both the backend API and the production-built React Single Page Application (SPA), exercising the exact user journeys across all supported demo repositories and safety controls.

### Summary Metrics:
- **Total Workflows Tested:** 20
- **Passed:** 20 (100%)
- **Failed:** 0 (0%)
- **Blocked:** 0 (0%)
- **Zero-Leak Secret Redaction:** Verified 100% across all API payloads, manifest diffs, and audit logs.
- **`NEVER_MERGE` Safety Protection:** Verified 100% across runtime assertions, API routing tables, and authorization gates.
- **Frontend SPA & Asset Delivery:** Validated HTML, CSS bundle (28.25 kB), and JS bundle (322.28 kB).

---

## 2. Phase 1 — Application Startup & SPA Delivery

| Check | Target / Endpoint | HTTP Status | Result | Details |
| :--- | :--- | :---: | :---: | :--- |
| **Backend Health** | `GET /health` | 200 OK | **PASS** | `{"status": "healthy", "safety_guard": "NEVER_MERGE_ACTIVE"}` |
| **Frontend SPA HTML** | `GET /` | 200 OK | **PASS** | HTML delivered with `<div id="root"></div>`, module scripts, and viewport metadata |
| **Frontend CSS Bundle** | `GET /assets/index-wCvZrhO2.css` | 200 OK | **PASS** | 28,254 bytes delivered with full Tailwind styling and dark-theme tokens |
| **Frontend JS Bundle** | `GET /assets/index-BedhS8Cr.js` | 200 OK | **PASS** | 322,283 bytes delivered containing full React 19 SPA, Lucide icons, and dual-mode switcher |

---

## 3. Phase 2 — Complete User Journey Workflows

### Journey 1: Demo Repositories Discovery
- **Action:** `GET /api/demos`
- **Result:** **PASS**
- **Findings:** Discovered 4 demo repositories representing distinct ecosystems:
  1. `vulnerable-python` (`fixture://vulnerable-python-repo`, Python / PyPI)
  2. `vulnerable-node` (`fixture://vulnerable-node-repo`, Node.js / npm)
  3. `secret-leak` (`fixture://secret-leak-repo`, Multi-language)
  4. `secure-go` (`fixture://secure-go-repo`, Golang)

### Journey 2: Python Repository Scanning & Analysis
- **Action:** `POST /api/analyses` (`fixture://vulnerable-python-repo`)
- **Result:** **PASS**
- **Findings:**
  - Components parsed: 3 (`requests==2.19.1`, `urllib3==1.24.1`, `pyyaml==5.2`)
  - Advisories enriched: 9 vulnerabilities (including critical CVE-2018-18074, CVE-2019-11324, CVE-2020-14343)
  - Risk score: 85.0/100 (`Critical`)
  - Remediation proposals generated: 3 safe upgrade plans

### Journey 3: Dual-Format SBOM Generation
- **Action:** `GET /api/analyses/{id}/sbom?format=cyclonedx` & `GET /api/analyses/{id}/sbom?format=spdx`
- **Result:** **PASS**
- **Findings:**
  - **CycloneDX 1.5:** Generated valid JSON containing `bomFormat: "CycloneDX"`, `specVersion: "1.5"`, and 3 parsed components with package URLs (`pkg:pypi/requests@2.19.1`).
  - **SPDX 2.3:** Generated valid JSON containing `spdxVersion: "SPDX-2.3"`, document namespace, and 3 package elements.

### Journey 4: Vulnerability Filtering & Search
- **Action:** `GET /api/analyses/{id}/findings?severity=CRITICAL` & `GET /api/analyses/{id}/findings?search=requests`
- **Result:** **PASS**
- **Findings:**
  - Severity filter returned exactly 3 CRITICAL vulnerabilities.
  - Keyword search returned 4 findings matching `requests` and its aliases.

### Journey 5: Secret Scanning & Zero-Leak Redaction
- **Action:** `POST /api/analyses` (`fixture://secret-leak-repo`)
- **Result:** **PASS**
- **Findings:**
  - Detected 5 historical and working-tree credential leaks (AWS Access Keys, GitHub Personal Access Tokens, OpenAI Secret Keys).
  - All values masked (e.g. `AKIA****************EXAMPLE`, `ghp_****************************cdef`).
  - Zero raw credential values leaked into analysis payloads or audit trails.
  - Remediation instructions and rotation playbooks attached to each finding.

### Journey 6: Explainable Risk Scoring Engine
- **Action:** Evaluated `risk_overview` breakdown for `vulnerable-python-repo`
- **Result:** **PASS**
- **Findings:**
  - Overall score: `85.0/100` (`Critical`).
  - Factor breakdown:
    - `max_vulnerability_score`: 84.9 (CVSS-derived)
    - `cisa_kev_active`: 1.0 (Active exploitation confirmed)
    - `cvss_factor`: 84.9
    - `kev_factor`: 1.0
    - `epss_factor`: 0.0
    - `secrets_factor`: 0.0
  - Transparent mathematical explanation generated.

### Journey 7: Safe Remediation & Unified Diff Generation
- **Action:** Inspected `remediations` proposal for `requests`
- **Result:** **PASS**
- **Findings:**
  - Proposed upgrade: `requests` `2.19.1` -> `2.33.0`.
  - Generated unified diff:
    ```diff
    --- a/requirements.txt
    +++ b/requirements.txt
    @@ -1,4 +1,4 @@
    -requests==2.19.1
    +requests==2.33.0
     urllib3==1.24.1
     pyyaml==5.2
    ```
  - Preserved indentation, comments, and unrelated package lines.
  - Recommended verification command: `pytest tests/`.

### Journey 8: Draft PR Gate & Human Authorization
- **Action:** Tested unconfirmed vs. confirmed draft PR creation
- **Result:** **PASS**
- **Findings:**
  - **Unconfirmed request (`user_confirmed: false`):** Rejected with HTTP 400 (`"Explicit user confirmation is mandatory before creating a draft PR."`).
  - **Confirmed request (`user_confirmed: true`):** Created draft PR preview with HTTP 200 (`draft_status: "DRAFT (DRY RUN / SIMULATION)"`).
  - Non-negotiable safety notice verified: `"PATCHPROOF creates draft pull requests for human review only and will never automatically merge changes."`

### Journey 9: Tamper-Evident Cryptographic Audit Trail
- **Action:** `GET /api/analyses/{id}/audit`
- **Result:** **PASS**
- **Findings:**
  - Recorded 11 immutable lifecycle events (`ANALYSIS_INITIALIZED`, `DEPENDENCIES_PARSED`, `VULNERABILITY_SCAN_COMPLETED`, `SECRETS_IDENTIFIED`, `RISK_SCORING_FINALIZED`, `REMEDIATION_PLANNED`, `DRAFT_PULL_REQUEST_CREATED`).
  - Every entry contains a verified 64-character SHA-256 `integrity_hash`.

### Journey 10: AI Code Debugger & Defect Localization
- **Action:** `POST /api/debug/analyze` with defective and clean code
- **Result:** **PASS**
- **Findings:**
  - **Defective Snippet (`def process_batch(item, queue=[]):`):** Correctly classified as `api_misuse`, localized to line 1, confidence `96.1%`, generated unified remediation diff replacing mutable list default with `None` guard.
  - **Clean Control Snippet (`def filter_positives(items):`):** Correctly classified as `none_correct_code`, `issue_detected: false`, severity `INFO`.

### Journey 11: Node.js / npm Ecosystem Analysis
- **Action:** `POST /api/analyses` (`fixture://vulnerable-node-repo`)
- **Result:** **PASS**
- **Findings:**
  - Parsed 3 npm dependencies from `package.json` (`lodash 4.17.15`, `axios 0.21.1`).
  - Detected 7 vulnerabilities (Prototype Pollution in lodash, SSRF in axios).
  - Recommended safe bump to lodash `4.17.21`.

### Journey 12: Clean Control Hardened Go Repository Scan
- **Action:** `POST /api/analyses` (`fixture://secure-go-repo`)
- **Result:** **PASS**
- **Findings:**
  - Parsed `go.mod`.
  - 0 vulnerabilities detected.
  - Risk score: `0.0/100` (`Low`).
  - Clean SBOM and 10.0/10 health score confirmed.

---

## 4. Phase 3 — Safety & Security Validation

| Protection | Validation Check | Result | Details |
| :--- | :--- | :---: | :--- |
| **Zero Merge Routes** | FastAPI route table audit | **PASS** | Audited all routes; 0 merge routes exist. |
| **SSRF Defense** | Probed private IPs, metadata & loopbacks | **PASS** | 6/6 attack vectors blocked (`127.0.0.1`, `localhost`, `169.254.169.254`, `192.168.1.1`, `ftp://`, `file://`). |
| **Compile/Runtime Merge Denial** | Direct call to `GitHubService.merge_pull_request` | **PASS** | Unconditionally raises `NotImplementedError` ("strictly prohibited from merging"). |
| **Zero Secret Exposure** | Checked all API payloads and audit trails | **PASS** | No raw API tokens, private keys, or passwords ever exposed. |
| **External Write Prevention** | Dry-run simulation enforcement | **PASS** | When `GITHUB_TOKEN` is unset or fixtures are analyzed, PR actions remain simulated dry-runs. No external GitHub repositories are modified. |

---

## 5. Deployment & Demo Readiness Assessment

- **Demo Blockers:** **NONE**. All 4 fixture repositories (`vulnerable-python`, `vulnerable-node`, `secret-leak`, `secure-go`) are functional offline without external internet dependency.
- **Packaging:** Both backend and frontend can be started via standard single-process hosting (FastAPI serving static frontend on port 8000) or dual-process dev setup (Vite proxying port 5173 to port 8000).
- **ML Engine:** The TF-IDF + Archetype Logistic Regression classifier is loaded from cached disk artifact `models/bug_detector.joblib` and evaluates in <15ms per snippet.

