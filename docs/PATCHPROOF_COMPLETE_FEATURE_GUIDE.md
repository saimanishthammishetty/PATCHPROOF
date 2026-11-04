# PATCHPROOF — Complete Product Feature & Functionality Guide

**Version:** 1.0.0 Production Baseline  
**Project Path:** `C:\PATCHPROOF`  
**Safety Invariant:** `NEVER_MERGE_ACTIVE = True` (Permanent Architectural Protection)  
**Trained ML Model:** `models/bug_detector.joblib` (SHA-256: `5F93BBA9CE457FE991580AFCD3C482D2D8FB626C019AB1DCDA58B73731176A20`)

---

## Executive Overview: What is PATCHPROOF?

PATCHPROOF is an autonomous software supply chain security platform and machine-learning code debugger. It bridges the gap between vulnerability detection and practical developer remediation:

1. **Find the Risk:** Ingests repositories, extracts full dependency trees, generates compliant Software Bills of Materials (SBOMs), correlates vulnerabilities against OSV.dev and the US CISA Known Exploited Vulnerabilities (KEV) catalog, scans git history for leaked credentials, and computes transparent, mathematically grounded risk scores.
2. **Prove the Fix:** Computes verified minimum safe version upgrades, evaluates breaking change risks, and generates genuine unified diffs against the actual project manifests.
3. **Debug Code Defects:** Inspects source code snippets across multiple languages using a trained 13-archetype machine-learning classifier combined with Abstract Syntax Tree (AST) line localization to identify subtle syntax and logical defects.
4. **Ironclad Safety Guarantee:** Enforces a non-negotiable **`NEVER_MERGE`** architecture. Pull requests are opened strictly in **DRAFT** mode and require explicit, interactive human authorization. Automatic pull request merging is permanently prohibited in the platform's routing and service layers.

---

## Feature 1: Repository Ingestion & Supply Chain Scanner
**Status:** `IMPLEMENTED AND TESTED` (Java POM parsing: `IMPLEMENTED BUT NOT FULLY TESTED`)

### 1. What is the feature?
The Repository Ingestion & Supply Chain Scanner is the entry gateway of PATCHPROOF. It retrieves public GitHub repositories or pre-packaged offline demonstration fixtures, discovers all supported software manifests across the repository tree, and extracts component inventories.

### 2. What problem does it solve?
Modern software applications rely on hundreds of third-party libraries across multiple ecosystems. Developers often do not know their complete dependency tree, especially indirect (transitive) dependencies brought in by top-level packages.

### 3. Why is it needed?
Security auditing cannot begin without an accurate, comprehensive inventory of all software packages running in an application. Without this feature, nested dependencies and multi-ecosystem repositories (e.g., Python microservices with Node.js frontends) are missed.

### 4. What input does the user provide?
- **Target Repository URL:** A standard HTTPS GitHub repository URL (e.g., `https://github.com/owner/repository`) OR an offline demonstration fixture URI (`fixture://vulnerable-python-repo`, `fixture://vulnerable-node-repo`, `fixture://secret-leak-repo`, `fixture://secure-go-repo`).
- **Branch (Optional):** Target branch name (defaults to `main` if omitted).
- **Scan Toggles:** Boolean flags enabling/disabling secret scanning (`run_secret_scan: true`) and dependency health inspection (`run_health_check: true`).

### 5. What happens internally after the user submits the input?
1. **URL Validation (`security.py`):** The URL is checked against SSRF and private-network blacklists.
2. **Repository Retrieval (`repository_service.py`):**
   - For `fixture://*` URIs, the service bypasses the network and resolves directly to `C:\PATCHPROOF\fixtures\<name>`, generating an offline commit hash.
   - For GitHub URLs, it executes a shallow clone (`git clone --depth 1`) into a unique temporary directory under `%TEMP%\patchproof_repos` with an enforced 45-second timeout.
3. **Ecosystem & Manifest Walk (`dependency_parser.py`):**
   - Recursively walks the repository directory tree, automatically excluding vendor and virtual environment directories (`node_modules`, `.venv`, `venv`, `vendor`, `.git`).
   - Identifies and parses:
     - **Python (PyPI):** `requirements*.txt`, `pyproject.toml`, `poetry.lock`.
     - **Node.js (npm):** `package.json`, `package-lock.json` (v1, v2, v3).
     - **Golang (Go Modules):** `go.mod`.
     - **Java (Maven):** `pom.xml`.
4. **Direct vs. Transitive Disambiguation:**
   - Packages declared directly in top-level requirement files or `dependencies` blocks are flagged `direct: true`.
   - Packages extracted strictly from lockfiles or `// indirect` annotations are flagged `direct: false`.
5. **Component Deduplication:** Normalizes package names (lowercase) and maps them into canonical `Component` models with Package URLs (PURLs).

### 6. What technologies, algorithms, APIs, and ML models are used?
- **Subprocess / Git CLI:** Shallow cloning with enforced timeouts.
- **Python Regex Engine:** Manifest grammar tokenizers for `requirements.txt` and `go.mod`.
- **Python `xml.etree.ElementTree`:** XML parser for Maven `pom.xml`.
- **Standard Library `json`:** JSON parser for `package.json` and lockfiles.
- **Specification:** Package URL (PURL) specification (`pkg:<type>/<namespace>/<name>@<version>`).
- **Source Implementation:** `backend/app/services/repository_service.py:12-76`, `backend/app/services/dependency_parser.py:10-314`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 1-3`, `backend/tests/test_dependency_parser.py`, `backend/tests/test_api.py:test_start_analysis_and_results`.

### 7. What exact output does the user receive?
- An array of `Component` objects stored under `analysisResult.components`:
  - `name`: Package name (e.g., `"requests"`).
  - `version`: Installed version string (e.g., `"2.19.1"`).
  - `ecosystem`: Target ecosystem (`"pypi"`, `"npm"`, `"golang"`, `"maven"`).
  - `purl`: Canonical Package URL (`"pkg:pypi/requests@2.19.1"`).
  - `direct`: Boolean indicating direct dependency status (`true`/`false`).
  - `manifest_path`: Relative file path to the source manifest (`"requirements.txt"`).
  - `license`: Declared license identifier or `"Unknown"`.

### 8. How should the user interpret that output?
The user can view the total dependency count and identify which libraries they directly manage versus which ones are transitively pulled into their dependency graph.

### 9. What practical action can the user take based on the output?
- Filter components by ecosystem or search by package name in the **SBOM Inventory** tab.
- Identify unpinned or outdated direct dependencies that should be explicitly bounded in manifest files.

### 10. What are the current limitations?
- External GitHub cloning requires public access or active internet connectivity.
- Private repositories requiring SSH keys or custom credentials are not supported without setting environment variables.
- Monorepos with millions of lines may exceed the 45-second shallow clone timeout.

---

## Feature 2: Software Bill of Materials (SBOM) Generation
**Status:** `IMPLEMENTED AND TESTED`

### 1. What is the feature?
The SBOM Generation engine exports the repository's component inventory into standardized, machine-readable Software Bill of Materials in both **CycloneDX 1.5 JSON** and **SPDX 2.3 JSON** formats.

### 2. What problem does it solve?
Enterprises and government agencies require formal supply-chain transparency (e.g., US Executive Order 14028). Security teams cannot manually inspect raw dependency files scattered across dozens of repositories.

### 3. Why is it needed?
Standardized SBOMs allow downstream vulnerability scanners, compliance checkers, and enterprise asset managers to ingest software inventories without proprietary vendor lock-in.

### 4. What input does the user provide?
The user clicks the **`CycloneDX 1.5 JSON`** or **`SPDX 2.3 JSON`** export button on the **SBOM Inventory** tab.

### 5. What happens internally after the user submits the input?
1. The frontend invokes `GET /api/analyses/{id}/sbom?format={cyclonedx|spdx}`.
2. The backend `SBOMService`:
   - Retrieves the cached `AnalysisResult` and its `Component` list.
   - For **CycloneDX 1.5**:
     - Generates UUID v4 serial number and RFC 3339 UTC timestamp.
     - Adds tool metadata identifying `patchproof-sbom-engine v1.0.0`.
     - Maps each component to a library entry with `bom-ref`, `purl`, `scope` (`required` for direct, `optional` for transitive), and custom PATCHPROOF properties (reachability, ecosystem, source manifest).
     - Builds a dependency tree linking the root application component to its direct dependencies.
   - For **SPDX 2.3**:
     - Formats document namespace (`https://patchproof.dev/spdx/...`).
     - Declares `dataLicense: "CC0-1.0"`.
     - Generates `SPDXRef-Package-*` nodes for all libraries with `NOASSERTION` download locations and relationship links (`DESCRIBES`, `DEPENDS_ON`).
3. Returns JSON with `Content-Type: application/json` and `Content-Disposition: attachment; filename=sbom-{id}-{format}.json`.

### 6. What technologies, algorithms, APIs, and ML models are used?
- **CycloneDX v1.5 JSON Schema.**
- **SPDX v2.3 JSON Specification.**
- **Python `uuid` and `datetime` (UTC).**
- **Source Implementation:** `backend/app/services/sbom_service.py:9-125`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 4` (SBOM Export CycloneDX 1.5 & SPDX 2.3), `validate_sbom.py`.

### 7. What exact output does the user receive?
An instant browser file download of `sbom-<analysis_id>-cyclonedx.json` or `sbom-<analysis_id>-spdx.json`.

### 8. How should the user interpret that output?
The downloaded file is a cryptographically serializable, industry-standard audit artifact. It can be fed into enterprise scanners (e.g., Dependency-Track, Grype, Snyk) or delivered to compliance auditors.

### 9. What practical action can the user take based on the output?
- Archive the SBOM in CI/CD release pipelines.
- Verify supplier compliance against enterprise dependency policies.

### 10. What are the current limitations?
- Cryptographic package file hashes (SHA-256 of the downloaded tarball/wheel) are not computed because source packages are not downloaded from registries during scanning.
- License detection relies on manifest metadata; deep license source-code header scanning is not performed.

---

## Feature 3: Vulnerability Detection & Threat Intelligence
**Status:** `IMPLEMENTED AND TESTED`

### 1. What is the feature?
The Vulnerability Detection engine cross-references all parsed dependencies against the **OSV.dev** vulnerability database, the **US CISA Known Exploited Vulnerabilities (KEV)** catalog, and the **FIRST.org Exploit Prediction Scoring System (EPSS)**.

### 2. What problem does it solve?
Knowing what dependencies you have is useless if you don't know which ones have documented security flaws, whether those flaws are being actively exploited in the wild, or what version fixes them.

### 3. Why is it needed?
Security teams suffer from alert fatigue. By prioritizing vulnerabilities that are actively weaponized (CISA KEV) or have high exploit probabilities (EPSS), developers can focus on immediate existential threats rather than theoretical low-severity alerts.

### 4. What input does the user provide?
Automated: triggered when an analysis is launched. The user filters findings on the **Vulnerabilities** tab by severity (All, Critical, High, Medium, Low) or searches by package/CVE keyword.

### 5. What happens internally after the user submits the input?
1. `VulnerabilityService.query_vulnerabilities(components)` aggregates components into batch queries.
2. Queries the OSV.dev batch API (`https://api.osv.dev/v1/querybatch`) over HTTP with a 5-second timeout.
3. If the network times out or fails (e.g. offline hackathon demo), it seamlessly falls back to the local high-fidelity advisory cache (`FALLBACK_ADVISORIES`) without crashing.
4. For each advisory returned:
   - Evaluates semver ranges using `packaging.version.parse` via `is_version_affected()`. If the installed version is already greater than or equal to the fixed version, the finding is discarded as a false positive.
   - Enriches the advisory with CVSS v3 score and severity label.
   - Checks the CVE identifier against the CISA KEV catalog (`KNOWN_CISA_KEV`).
   - Retrieves EPSS probability (0.0 to 1.0) indicating exploit probability in the next 30 days.
   - Extracts the minimum fixed version string.

### 6. What technologies, algorithms, APIs, and ML models are used?
- **Google OSV.dev REST API** (`/v1/querybatch`).
- **CISA Known Exploited Vulnerabilities (KEV) Catalog.**
- **FIRST.org EPSS Scoring Model.**
- **Python `packaging.version`:** Semver and PEP 440 version range evaluation.
- **`httpx` asynchronous client.**
- **Source Implementation:** `backend/app/services/vulnerability_service.py:1-372`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 5`, `backend/tests/test_vulnerability_service.py:test_osv_batch_query_and_deduplication`.

### 7. What exact output does the user receive?
An array of `VulnerabilityFinding` records displayed on the **Vulnerabilities** tab:
- `id`: Advisory ID (e.g., `GHSA-79v4-hx79-jx7p`).
- `aliases`: CVE identifiers (e.g., `["CVE-2018-18074"]`).
- `package`: Affected library (e.g., `"requests"`).
- `installed_version`: Current version (e.g., `"2.19.1"`).
- `fixed_version`: Target remediation version (e.g., `"2.20.0"`).
- `severity`: `"CRITICAL"`, `"HIGH"`, `"MEDIUM"`, `"LOW"`.
- `cvss_score`: Float between 0.0 and 10.0.
- `cisa_kev`: Boolean flag indicating active weaponization.
- `epss_probability`: Percentage probability of exploitation.
- `summary`: Human-readable summary of the vulnerability mechanism.
- `references`: Direct external links to advisory documentation.

### 8. How should the user interpret that output?
- Any vulnerability with **`CISA KEV: ACTIVE`** represents an urgent zero-day or weaponized threat currently used by adversaries in the wild.
- High EPSS scores (> 0.30) indicate high statistical likelihood of automated exploit scanning.

### 9. What practical action can the user take based on the output?
Navigate to the **Remediations** tab to review PATCHPROOF's proposed automated dependency upgrade diff for that specific package.

### 10. What are the current limitations?
- Live OSV queries require internet connectivity; offline environments rely on the curated fallback knowledge base.
- Reachability analysis is currently heuristic and does not perform whole-program call-graph trace analysis from main entry points to vulnerable functions.

---

## Feature 4: Secret Detection & Zero-Leak Redaction
**Status:** `IMPLEMENTED AND TESTED`

### 1. What is the feature?
The Secret Detection module scans the latest working tree files AND deep Git commit history (up to the last 10 commits) for exposed credentials, API keys, private tokens, and cryptographic certificates. It enforces strict **Zero-Leak Redaction** across all UI views and API payloads.

### 2. What problem does it solve?
Developers frequently commit sensitive API keys, cloud tokens, or database credentials accidentally. Even if deleted in a subsequent commit, secrets remain exposed in the repository's Git history forever.

### 3. Why is it needed?
Leaked secrets provide attackers with immediate access to cloud infrastructure, databases, and third-party SaaS platforms, bypassing software defenses entirely. Furthermore, security tools that report secrets must never re-expose raw credentials in logs or dashboards.

### 4. What input does the user provide?
Automated: triggered when `run_secret_scan: true` is set during analysis.

### 5. What happens internally after the user submits the input?
1. `SecretScanner.scan_repository()` walks working-tree files under 1MB, skipping binary formats.
2. Evaluates every line against 12 high-precision regular expressions (`SECRET_PATTERNS`) combined with Shannon entropy thresholds.
3. Invokes `git log -p -n 10 --unified=0` to inspect added diff lines (`+`) in historical commits.
4. When a secret match is found:
   - The raw credential value is **immediately redacted** via `redact_secret_string()`.
   - The token is masked: preserving 4 leading and 4 trailing characters while masking the middle with asterisks (e.g., `AKIA****************`).
   - If the token is short (<= 6 chars), it is completely masked (`******`).
   - The raw credential is deleted from memory and never returned in API responses or audit logs.
5. The finding is annotated with a specific remediation playbook from `ROTATION_GUIDES`.

### 6. What technologies, algorithms, APIs, and ML models are used?
- **12 High-Precision Regex Patterns:** AWS Access Keys (`AKIA*`), AWS Secret Keys, GitHub PATs (`ghp_*`, `github_pat_*`), GitHub OAuth (`gho_*`), Slack Bot/User tokens (`xoxb-*`, `xoxp-*`), OpenAI API keys (`sk-*`), Stripe Secret Keys (`sk_live_*`), Google Cloud API keys (`AIza*`), PEM Private Key blocks, Generic High-Entropy tokens, and JWT Bearer tokens.
- **Shannon Entropy Heuristics.**
- **Git CLI:** `git log -p` commit history differential parsing.
- **Source Implementation:** `backend/app/services/secret_scanner.py:1-122`, `backend/app/core/security.py:7-76`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 6`, `backend/tests/test_secret_scanner.py:test_secret_detection_and_rotation_playbooks`.

### 7. What exact output does the user receive?
Displayed in the **Secrets** tab:
- `secret_type`: Classification (e.g., `"AWS Access Key ID"`).
- `file_path`: Source file (or `"git_history"`).
- `line_number`: Line location in code.
- `commit_sha`: Git commit where the secret was introduced.
- `masked_value`: Safe redacted token string (e.g., `AKIA****************`).
- `remediation_instructions`: Exact step-by-step credential revocation and rotation procedure.

### 8. How should the user interpret that output?
Any detected secret must be treated as fully compromised. Deleting the file is insufficient; the credential must be revoked at the cloud provider immediately.

### 9. What practical action can the user take based on the output?
Follow the printed rotation playbook: log into the respective vendor dashboard (AWS IAM, GitHub Settings, OpenAI Console), revoke the compromised key, issue a new key, and update secrets managers.

### 10. What are the current limitations?
- Scans up to the last 10 historical Git commits by default to maintain sub-second performance on large repositories.
- Does not check if the secret has already been revoked upstream by pinging vendor APIs (to avoid alerting attackers or triggering rate limits).

---

## Feature 5: Deterministic Risk Engine & Factor Breakdown
**Status:** `IMPLEMENTED AND TESTED`

### 1. What is the feature?
The Risk Engine computes a transparent, explainable 0 to 100 risk score for individual findings and the repository as a whole, breaking down the exact mathematical factors that influenced the score.

### 2. What problem does it solve?
Most security tools act as "black boxes"—they assign arbitrary high or critical scores without showing developers how the number was calculated, leading to skepticism and confusion.

### 3. Why is it needed?
Developers and security managers need an objective, repeatable metric to compare repository security postures, track remediation progress over time, and understand why a repository was rated Critical versus Medium.

### 4. What input does the user provide?
Automated: aggregates all vulnerabilities, secrets, and dependency health findings from the scan.

### 5. What happens internally after the user submits the input?
1. **Individual Finding Formula (`RiskEngine.calculate_finding_risk`):**
   $$\text{Score} = (\text{CVSS} \times 35) + (\text{KEV} \times 25) + (\text{EPSS} \times 20) + (\text{Reachability} \times 10) + (\text{Health} \times 10)$$
   - *CVSS Factor:* Up to 35 points based on base score (0.0–10.0).
   - *CISA KEV Factor:* 25 points if active in KEV, 0 otherwise.
   - *EPSS Factor:* Up to 20 points based on exploit probability (0.0–1.0).
   - *Reachability Factor:* 10 points if directly imported, 5 if unknown.
2. **Critical Overrides:**
   - Any CISA KEV finding is guaranteed an individual score of at least **82.0** (Critical).
   - Any CVSS >= 9.0 direct finding is guaranteed a score of at least **78.0** (Critical).
3. **Composite Repository Score (`RiskEngine.calculate_overall_risk`):**
   - Base = Worst individual finding score.
   - Secret Penalty = Added based on count (up to 30 points).
   - Suspicious Package Penalty = Added based on typosquatting/scripts (up to 20 points).
   - KEV Presence Floor = If any KEV finding exists, overall score is guaranteed at least **85.0**.
   - Secret Presence Floor = If any high-confidence secret exists, score is guaranteed at least **75.0**.
4. **Severity Labeling:**
   - `0.0 – 19.9`: **Low**
   - `20.0 – 39.9`: **Medium**
   - `40.0 – 69.9`: **High**
   - `70.0 – 100.0`: **Critical**

### 6. What technologies, algorithms, APIs, and ML models are used?
- **Deterministic Multi-Factor Scoring Formula.**
- **Safe Boundary Clamp:** Min 0.0, Max 100.0.
- **Rule-Based Override Guards.**
- **Source Implementation:** `backend/app/services/risk_engine.py:1-140`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 7`, `backend/tests/test_risk_engine.py:test_cisa_kev_scoring_override`.

### 7. What exact output does the user receive?
On the **Security Dashboard** and **Risk & Health** tabs:
- Numerical score (e.g., `85.0 / 100`).
- Color-coded severity badge (Red: Critical, Orange: High, Yellow: Medium, Green: Low).
- Breakdown factors dictionary: `cvss_factor`, `kev_factor`, `epss_factor`, `secrets_factor`.
- Plain English mathematical explanation string.

### 8. How should the user interpret that output?
- A score >= 70 indicates critical threats requiring same-day remediation.
- The factor breakdown clearly reveals whether the score is driven by known exploits (KEV), high CVSS vulnerabilities, or leaked credentials.

### 9. What practical action can the user take based on the output?
Target remediations that provide the highest score reduction—resolving CISA KEV vulnerabilities and rotating secrets will immediately drop the score out of the Critical tier.

### 10. What are the current limitations?
- Weights (35/25/20/10/10) are statically calibrated in the configuration and cannot be customized per enterprise policy via the UI.

---

## Feature 6: Automated Safe Remediation Planning & Diffing
**Status:** `IMPLEMENTED AND TESTED`

### 1. What is the feature?
The Safe Remediation engine computes minimum safe dependency upgrades that resolve all detected advisories for a package, evaluates breaking change risks, and generates genuine unified diffs against the repository's manifests.

### 2. What problem does it solve?
Developers often know a package is vulnerable, but they don't know what version to upgrade to without breaking their application. Blindly upgrading to the latest major release frequently causes breaking API incompatibilities.

### 3. Why is it needed?
Security tools that only report problems without offering verifiable, minimally invasive solutions create friction and stall remediation. PATCHPROOF proposes the *minimum safe bump* required to exit the vulnerable window.

### 4. What input does the user provide?
The user views candidate upgrades on the **Remediations** tab and selects a package card.

### 5. What happens internally after the user submits the input?
1. `RemediationService.generate_remediations()` groups all vulnerabilities by package.
2. Evaluates fixed versions across all advisories affecting that package.
3. Selects the minimum version that is strictly greater than the currently installed version (`fixed_version > current_version`) and resolves all advisories. Downgrades are prohibited.
4. Checks for **breaking change risks**: compares major version numbers (`target_major > current_major`). If a major bump is required, flags `breaking_change_warning: true` and warns the user.
5. Performs a precise, in-memory string replacement on the target manifest file (`requirements.txt`, `package.json`, or `go.mod`).
6. Computes a real unified diff using Python's `difflib.unified_diff()`.
7. Applies `redact_secrets_in_content()` to ensure no credentials embedded in manifest files are leaked in the diff while strictly preserving diff control headers (`---`, `+++`, `@@`, `-`, `+`).
8. Generates recommended test commands (e.g., `pytest tests/`, `npm test`).

### 6. What technologies, algorithms, APIs, and ML models are used?
- **Python `difflib.unified_diff`.**
- **PEP 440 & Semver Parsers (`packaging.version`).**
- **Pattern-Preserving Secret Sanitization (`security.py`).**
- **Source Implementation:** `backend/app/services/remediation_service.py:1-286`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 8`, `backend/tests/test_remediation_diff.py:test_successful_update_produces_unified_diff`.

### 7. What exact output does the user receive?
On the **Remediations** tab:
- Package name, current version, and proposed version (e.g., `requests 2.19.1 → 2.31.0`).
- Breaking change pill: `Safe Patch` (green) or `Major Bump` (yellow).
- Compatibility assessment notes.
- Suggested verification test command.
- Syntax-highlighted unified diff preview:
  ```diff
  --- requirements.txt
  +++ requirements.txt
  @@ -1,3 +1,3 @@
  -requests==2.19.1
  +requests==2.31.0
  ```

### 8. How should the user interpret that output?
The diff represents the exact lines of code that will be changed in their dependency manifest. A "Safe Patch" indicates a minor/patch version bump with high backward compatibility.

### 9. What practical action can the user take based on the output?
Click **`Review & Create Draft PR`** to initiate the human-supervised pull request creation flow.

### 10. What are the current limitations?
- Resolves manifest files directly; it does not automatically re-lock compiled lockfiles (e.g., running `poetry lock --no-update` or `npm install --package-lock-only`) inside the sandbox.

---

## Feature 7: Human-Reviewed Draft PR System & NEVER_MERGE Gate
**Status:** `IMPLEMENTED AND TESTED` (Dry-run mode: `SIMULATED`; Live GitHub API: `IMPLEMENTED BUT NOT FULLY TESTED`)

### 1. What is the feature?
The Draft Pull Request System allows developers to push remediation proposals into GitHub as **DRAFT** pull requests, strictly guarded by an interactive human confirmation checkbox and a permanent architectural ban on automatic merging (`NEVER_MERGE_ACTIVE`).

### 2. What problem does it solve?
Automated security bots that automatically push commits and auto-merge dependency updates can break production builds, introduce undetected regressions, or become vectors for supply-chain poisoning.

### 3. Why is it needed?
Enterprise engineering standards require human oversight before modifying codebase dependencies. Developers need convenience without sacrificing authority.

### 4. What input does the user provide?
In the **Draft PR Review Modal**:
- Target Base Branch (default: `"main"`).
- Proposed Branch Name (e.g., `"patchproof/fix-requests-2.31.0"`).
- Pull Request Title.
- **Mandatory Human Confirmation:** The user must explicitly click the checkbox:
  > *"Explicit Authorization: I have reviewed the proposed dependency modification and authorize PATCHPROOF to open a DRAFT pull request."*

### 5. What happens internally after the user submits the input?
1. The frontend validates that the checkbox is checked; if unchecked, the submit button remains disabled.
2. When submitted, `POST /api/analyses/{id}/draft-pr` is called with `user_confirmed: true`.
3. The backend endpoint enforces:
   - If `user_confirmed` is false or omitted, the API rejects the request immediately with **HTTP 400 Bad Request**.
   - If the title contains merge directives, it is blocked.
4. `GitHubService.create_draft_pull_request()` formats a structured Markdown pull request body detailing affected packages, resolved CVEs, compatibility notes, and safety notices.
5. **Execution Mode Branching:**
   - If `GITHUB_TOKEN` is configured and targeting a real repository, it calls the GitHub REST API (`POST /repos/{owner}/{repo}/pulls`) with `"draft": true`.
   - If `GITHUB_TOKEN` is unset or analyzing a fixture (e.g. hackathon demo), it enters transparent **Dry-Run Simulation Mode**, returning `draft_status: "DRAFT (DRY RUN / SIMULATION)"` and a preview URL.
6. **The NEVER_MERGE Invariant:**
   - No route or handler exists to merge pull requests.
   - Any internal code calling `GitHubService.merge_pull_request()` immediately raises `NotImplementedError("CRITICAL SECURITY RESTRICTION: PATCHPROOF is strictly prohibited from merging pull requests.")`.

### 6. What technologies, algorithms, APIs, and ML models are used?
- **GitHub REST API v3** (`POST /repos/{owner}/{repo}/pulls`).
- **Pydantic v2 Schema Validation.**
- **FastAPI HTTP Status Enforcement (400 on unauthorized).**
- **Source Implementation:** `backend/app/services/github_service.py:1-132`, `backend/app/core/config.py:19`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 9`, `backend/tests/test_safety_guarantees.py:test_github_service_never_merges`, `backend/tests/test_api.py:test_create_draft_pull_request_unconfirmed`.

### 7. What exact output does the user receive?
In the modal success view:
- Success confirmation banner.
- Draft PR Status: `"DRAFT"` (Live) or `"DRAFT (DRY RUN / SIMULATION)"` (Demo).
- Proposed branch name.
- Pull request URL link.
- Non-negotiable safety notice.

### 8. How should the user interpret that output?
The proposal has been safely staged in draft mode. The pull request will **never** be merged automatically; maintainers must review the diff, run CI tests, and merge manually on GitHub.

### 9. What practical action can the user take based on the output?
Maintainers navigate to the pull request URL on GitHub, verify CI test suite results, and perform peer review before merging.

### 10. What are the current limitations?
- In demo/offline mode without a live `GITHUB_TOKEN`, pull request creation operates in dry-run simulation mode to ensure safety and avoid requiring credentials.

---

## Feature 8: AI Code Debugger & ML Defect Classifier
**Status:** `IMPLEMENTED AND TESTED`

### 1. What is the feature?
The AI Code Debugger is a machine-learning-assisted static analysis module that detects bug archetypes across 13 calibrated defect categories, pinpoints the exact faulty line of code using AST analysis, and proposes concrete code diff fixes.

### 2. What problem does it solve?
Supply-chain vulnerabilities often stem from subtle source-code defects—such as mutable default arguments in Python, loose equality coercion in JavaScript, or missing error handling. Standard linters produce noisy false alarms, while generative AI can hallucinate incorrect fixes.

### 3. Why is it needed?
Developers need fast, calibrated, offline-capable code inspection that accurately distinguishes buggy patterns from clean control code without executing untrusted code or sending proprietary code to third-party LLM clouds.

### 4. What input does the user provide?
In the **AI Code Debugger** view:
- **Language Selector:** Python, JavaScript, TypeScript, C, C++, Java, Go.
- **Source Code Textarea:** Custom code snippet (up to 100,000 characters) OR one-click presets:
  1. *Python: Mutable Default Argument* (`def process_batch(item, queue=[]):`)
  2. *Python: Identity Comparison on Literal* (`if status_code is 200:`)
  3. *JavaScript: Loose Equality Coercion* (`if (val == 0)`)
  4. *Python: Clean Bug-Free Control* (`def filter_positives(items):`)
- Click **`Analyze Code`**.

### 5. What happens internally after the user submits the input?
1. `DebugService.analyze_code()` validates language and character limits.
2. Loads the cached, pre-trained scikit-learn model artifact from `models/bug_detector.joblib`.
3. Runs TF-IDF feature extraction and `predict_proba()` across 13 defect classes.
4. **Deterministic AST Worker Verification:**
   - For Python: Invokes `_localize_python_defect()` using Python's native `ast` module.
   - For JavaScript/C: Invokes `_localize_js_c_defect()`.
   - Checks for mutable defaults (`ast.List`, `ast.Dict` in `args.defaults`), identity comparisons (`ast.Is` on `ast.Constant`), bare excepts (`ast.ExceptHandler`), and off-by-one loops.
5. **Confidence Calibration Guard:**
   - If statistical confidence is < 45% and AST confirms no syntax defect, the snippet is reclassified as `none_correct_code` (Clean Code) to prevent false positive alarms.
   - If AST confirms a known defect, confidence is calibrated to `>= 85.0%`.
6. **Unified Diff Synthesis:**
   - Synthesizes a safe replacement (e.g. replacing `= []` with `= None` and inserting `if queue is None: queue = []`).
   - Generates unified diff via `difflib.unified_diff(original, remediated)`.

### 6. What technologies, algorithms, APIs, and ML models are used?
- **Trained Model:** scikit-learn TF-IDF Vectorizer + Multinomial/Logistic Regression trained on defect corpus (SHA-256: `5F93BBA9...`).
- **Python Native `ast` Module:** Abstract Syntax Tree parsing and traversal (`ast.walk`).
- **13 Defect Archetype Classes:** `api_misuse`, `async_error`, `condition_error`, `exception_handling`, `loop_error`, `memory_safety`, `none_correct_code`, `null_pointer`, `off_by_one`, `resource_leak`, `state_management`, `type_error`, `undefined_behavior`.
- **Python `difflib.unified_diff`.**
- **Source Implementation:** `backend/app/services/debug_service.py:1-294`, `backend/app/api/endpoints.py:323-338`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 11`, `backend/tests/test_debug_api.py:test_debug_analyze_mutable_default`.

### 7. What exact output does the user receive?
On the debugger results panel:
- Defect status pill: `Defect Identified` (red) or `Clean Code Control` (green).
- Category label (e.g., `"API Misuse / Mutable Default State"`).
- Model confidence percentage (e.g., `"85.0%"`).
- Source Code Input Editor: Faulty line highlighted in bold red in the gutter (e.g., Line 1).
- Unified remediation diff preview showing proposed fix.
- Plain-English explanation of the syntactic/logical bug.
- Model limitations and benchmark disclaimer.

### 8. How should the user interpret that output?
The tool flags high-probability defect patterns based on syntactic structure. It is static analysis; user code is never executed. Clean code classification indicates absence of recognized defect patterns.

### 9. What practical action can the user take based on the output?
Review the proposed diff in the right pane and copy the remediated function signature and guard statements into their source code.

### 10. What are the current limitations?
- Analyzes function/snippet-level scope (up to 100k characters); does not perform whole-program interprocedural taint analysis across multiple modules.
- Requires `models/bug_detector.joblib` to be present on disk.

---

## Feature 9: Immutable SHA-256 Audit Trail
**Status:** `IMPLEMENTED AND TESTED` (Process-isolated RAM storage; Persistent DB ledger: `PLANNED`)

### 1. What is the feature?
The Audit Trail records every critical security and remediation event in an immutable, tamper-evident log stream secured by per-event cryptographic SHA-256 integrity hashing.

### 2. What problem does it solve?
Security and compliance regulations (SOC 2, ISO 27001, HIPAA) require verifiable proof of who initiated security analyses, what vulnerabilities were found, when proposals were generated, and whether any unauthorized actions were attempted.

### 3. Why is it needed?
Provides forensic accountability. If an audit log can be secretly altered, security posture claims cannot be trusted by external auditors.

### 4. What input does the user provide?
Automated: events are registered as the pipeline executes. The user reviews the stream in the **Audit Trail** tab.

### 5. What happens internally after the user submits the input?
1. Whenever a pipeline event occurs (e.g. `ANALYSIS_INITIALIZED`, `DEPENDENCIES_PARSED`, `VULNERABILITY_SCAN_COMPLETED`, `SECRETS_IDENTIFIED`, `REMEDIATION_PLANNED`, `DRAFT_PULL_REQUEST_CREATED`), `audit_logger.record_event()` is called.
2. Sanitizes details via `redact_secret_string()` so no credentials ever enter the audit log.
3. Generates an RFC 3339 UTC timestamp.
4. Computes a 256-bit cryptographic hash:
   $$\text{Hash} = \text{SHA256}(\text{timestamp} : \text{eventType} : \text{repository} : \text{commitSha} : \text{cleanDetails} : \text{actor})$$
5. Appends the tamper-evident `AuditEntry` to the chronological log stream.

### 6. What technologies, algorithms, APIs, and ML models are used?
- **Python `hashlib.sha256`.**
- **ISO 8601 / RFC 3339 UTC Timestamps.**
- **Source Implementation:** `backend/app/services/audit_service.py:7-41`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 10` (Tamper-Evident SHA-256 Audit Trail).

### 7. What exact output does the user receive?
On the **Audit Trail** tab:
- Chronological list of events with event type badges (`ANALYSIS_INITIALIZED`, `DRAFT_PULL_REQUEST_CREATED`).
- Target repository and commit SHA.
- Actor attribution (`"System"` or `"Human Reviewer"`).
- Event details string.
- Verified 64-character hexadecimal SHA-256 integrity hash with green `Verified` status pill.

### 8. How should the user interpret that output?
The event stream demonstrates a complete, unbroken record of security actions. Any modification to timestamp, actor, or details would invalidate the integrity hash.

### 9. What practical action can the user take based on the output?
Export or present the audit log to compliance officers to demonstrate that human review was enforced prior to draft PR creation.

### 10. What are the current limitations?
- Stored in-memory for the duration of the server process; enterprise persistence to an external write-once ledger (e.g., AWS QLDB or append-only SQL database) is an enterprise roadmap feature.

---

## Feature 10: Security Invariants, SSRF Defense & Safety Boundaries
**Status:** `IMPLEMENTED AND TESTED`

### 1. What is the feature?
The Security Invariants module enforces platform-wide defensive boundaries: Server-Side Request Forgery (SSRF) defense, loopback/private IP blocking, URL validation, and the permanent enforcement of the `NEVER_MERGE` invariant.

### 2. What problem does it solve?
Automated security tools that clone remote repositories can be weaponized by attackers using SSRF payloads (e.g., `http://169.254.169.254/latest/meta-data/`) to steal cloud credentials, probe internal network services, or execute arbitrary shell commands.

### 3. Why is it needed?
A security platform must not introduce new vulnerabilities into the organization running it. Strict input validation and architectural constraints ensure PATCHPROOF remains resilient against malicious input.

### 4. What input does the user provide?
The user inputs repository URLs in the main input console.

### 5. What happens internally after the user submits the input?
1. `validate_repository_url()` parses the URL using `urllib.parse.urlparse`.
2. Rejects non-HTTP/HTTPS schemes (blocking `file://`, `ftp://`, `gopher://`, `ssh://`).
3. Checks hostname against `DISALLOWED_HOSTS`:
   - `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`.
   - Cloud metadata services: `169.254.169.254`, `metadata.google.internal`.
4. Evaluates IP addresses using Python's `ipaddress` module:
   - Blocks private networks (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
   - Blocks loopback, link-local, and reserved IP ranges.
5. Enforces domain whitelist: allows only `github.com` (or explicit `fixture://` demonstration URIs).
6. Enforces repository path structure: requires at least two path segments (`/owner/repo`).

### 6. What technologies, algorithms, APIs, and ML models are used?
- **Python `ipaddress` module.**
- **Python `urllib.parse`.**
- **Disallowed host sets and CIDR range validators.**
- **Source Implementation:** `backend/app/core/security.py:78-140`.
- **Test Evidence:** `test_hackathon_readiness.py:Test 12`, `backend/tests/test_safety_guarantees.py:test_ssrf_blocking_localhost_and_private_ips`.

### 7. What exact output does the user receive?
If an SSRF or invalid URL is submitted, the API rejects the request immediately with **HTTP 400 Bad Request** and an explicit error message (e.g., `"Access to private/local IP '169.254.169.254' is strictly prohibited."`).

### 8. How should the user interpret that output?
The platform prevented an illegal internal network traversal attempt.

### 9. What practical action can the user take based on the output?
Provide a legitimate, public GitHub repository URL (`https://github.com/owner/repo`).

### 10. What are the current limitations?
- Scanning Git servers on internal enterprise networks (e.g. on-premise GitLab or GitHub Enterprise behind corporate VPNs) is disallowed by default by the SSRF defense rules.

---

## Feature 11: Frontend Dashboard & User Interface
**Status:** `IMPLEMENTED AND TESTED`

### 1. What is the feature?
The Frontend Dashboard is a modern, single-page application built with React 19, TypeScript, and Tailwind CSS. It provides dual operational modes, interactive visualizations, and responsive controls.

### 2. What problem does it solve?
Security data is complex. Dense JSON payloads and CLI logs are difficult for developers and executive stakeholders to navigate quickly.

### 3. Why is it needed?
An intuitive UI allows engineers to quickly grasp their threat landscape, inspect diffs, test code snippets, and review compliance logs within seconds.

### 4. What input does the user provide?
Mouse clicks, text inputs, dropdown selections, and tab switches.

### 5. What happens internally after the user submits the input?
React state hooks manage view switching, modal states, search filtering, and asynchronous API calls to `/api/*` endpoints with loading spinners and error boundaries.

### 6. What technologies, algorithms, APIs, and ML models are used?
- **React 19 & TypeScript.**
- **Tailwind CSS & Tailwind Typography.**
- **Lucide React Icons.**
- **Vite Build System.**
- **Source Implementation:** `frontend/src/App.tsx`, `frontend/src/components/*`.
- **Test Evidence:** Production build (`tsc && vite build`), live HTTP E2E tests (`scratch/e2e_validator.py`).

### 7. What exact output does the user receive?
- **Header Navbar:** Mode toggles (`Supply Chain Scanner` vs `AI Code Debugger`), `Auto-Merge: Disabled (Guaranteed)` lock badge, `New Analysis` button.
- **Landing Screen:** Hero headline, repository input bar with Enter key submission, 4 one-click interactive demo cards.
- **Scanning State:** `PipelineProgress` animated multi-phase bar (`Discovery` → `Parsing` → `SBOM` → `Advisories` → `Secrets` → `Risk Engine`).
- **Dashboard View (7 Tabs):**
  1. *Security Dashboard:* Risk score gauge, metric cards, top advisories, ecosystem breakdown.
  2. *SBOM Inventory:* Search bar, ecosystem filter, CycloneDX & SPDX download buttons, component table.
  3. *Vulnerabilities:* Severity filter buttons (Critical, High, Medium, Low), search bar, CISA KEV badges, EPSS meters.
  4. *Secrets:* Git commit badges, masked credential boxes, rotation playbook panels.
  5. *Risk & Health:* Mathematical breakdown meters, typosquatting alerts, OpenSSF scorecard signals.
  6. *Remediations:* Upgrade candidate sidebar, breaking change alert tags, syntax-highlighted diff viewer, `Review & Create Draft PR` CTA.
  7. *Audit Trail:* Chronological event stream, actor badges, verified SHA-256 integrity hash pills.
- **Draft PR Modal:** Form fields (base/proposed branch, title, diff preview), non-negotiable safety box, mandatory authorization checkbox, submit CTA.
- **AI Code Debugger View:** Language selector dropdown, 4 quick preset buttons, code input textarea with line numbers, defect analysis card, line-level highlighter, diff preview.

### 8. How should the user interpret that output?
The interface provides immediate visual feedback. Loading spinners indicate asynchronous backend computation, red badges indicate critical security issues, and green badges indicate clean or remediated states.

### 9. What practical action can the user take based on the output?
Navigate between supply chain inventory analysis and line-level code debugging to inspect, understand, and fix vulnerabilities across the entire software stack.

### 10. What are the current limitations?
- Built as a client-side Single Page Application (SPA); deep bookmarking of sub-tabs via browser URL hash/history is handled in React state.

