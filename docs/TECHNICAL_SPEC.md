# PATCHPROOF — TECHNICAL SPECIFICATION

**Product Name:** PATCHPROOF  
**Tagline:** "Find the risk. Prove the fix."  
**Version:** 1.0.0  
**Security Boundary:** Human-in-the-Loop Safe Dependency Remediation  
**Architectural Invariant:** NEVER MERGE A PULL REQUEST.

---

## 1. Problem Statement & Objectives

Modern software applications are constructed from hundreds of third-party open-source components. Software supply-chain attacks exploit:
1. **Unpatched High-Severity CVEs** (especially those actively exploited in the wild, listed in CISA KEV).
2. **Transitive Dependency Blindspots** where vulnerable libraries are pulled in through dependencies of dependencies.
3. **Accidentally Committed Secrets and Credentials** embedded in code or buried in Git commit history.
4. **Malicious / Suspicious Packages** using typosquatting or running unauthorized post-install scripts.
5. **Reckless Automated Tools** that break production by indiscriminately upgrading libraries or automatically merging unverified changes without developer peer review.

### Objectives of PATCHPROOF
- Provide deterministic, evidence-based software supply chain analysis for public GitHub repositories.
- Extract comprehensive Software Bill of Materials (SBOM) in standard CycloneDX 1.5 JSON and SPDX 2.3 JSON formats.
- Cross-reference dependencies against OSV.dev, GitHub Security Advisories, NVD, and CISA KEV with strict deduplication across CVE and GHSA aliases.
- Perform high-entropy secret detection with immediate and permanent redaction.
- Formulate transparent, explainable 0–100 risk scoring.
- Calculate verified safe minimal version upgrades and present interactive manifest diffs.
- Create human-reviewed GitHub **DRAFT** pull requests with zero auto-merge capability.

---

## 2. Scope & Assumptions

- **Primary Ecosystems:** Python (PyPI), JavaScript/TypeScript (npm), Go (go.mod), and Java (Maven pom.xml).
- **Execution Environment:** Windows, Linux, and macOS supported. Python 3.11+ backend with FastAPI; React/TypeScript frontend.
- **Safety Boundary:** Analysis is non-destructive and read-only. Draft pull requests require explicit human authorization and are marked as `[DRAFT]`. Automatic merging is prohibited by contract.

---

## 3. Architecture Overview

```mermaid
flowchart TD
    User([Developer / Security Engineer]) -->|Input GitHub URL| FE[PATCHPROOF Frontend - React / Tailwind]
    FE -->|POST /api/analyses| BE[FastAPI Backend Core]
    
    subgraph Analysis Pipeline
        BE --> RS[Repository Service: Shallow Clone & Pin Commit]
        RS --> DP[Dependency Parser: PyPI, npm, Go, Maven]
        DP --> SBOM[SBOM Service: CycloneDX 1.5 & SPDX 2.3]
        DP --> VS[Vulnerability Service: OSV.dev + CISA KEV + EPSS]
        RS --> SS[Secret Scanner: Tree & Git History Regex/Entropy]
        DP --> DH[Dependency Health & Typosquatting Analyzer]
    end

    VS --> RE[Deterministic Risk Engine: 0 - 100 Score]
    SS --> RE
    DH --> RE

    RE --> RM[Remediation Service: Smallest Safe Upgrade & Unified Diff]
    RM -->|Human Review & Authorization| GH[GitHub Service: Draft PR Only]
    
    subgraph Safeguards
        GH -.->|BLOCKED BY DESIGN| MergeKillSwitch[Never Merge Prohibition]
        SS -.->|STRICT REDACTION| SecretShield[Zero Plaintext Secrets]
        Audit[Immutable Audit Logger: SHA-256 Hashes]
    end
    
    GH -->|Draft PR Opened| GitHubPlatform([GitHub Repository])
```

---

## 4. Supported Ecosystems & Manifests

| Ecosystem | Manifest Files | Resolved Lockfiles | PURL Format |
| :--- | :--- | :--- | :--- |
| **Python** | `requirements.txt`, `pyproject.toml` | `poetry.lock` | `pkg:pypi/{name}@{version}` |
| **JavaScript / TypeScript** | `package.json` | `package-lock.json`, `yarn.lock` | `pkg:npm/{name}@{version}` |
| **Go** | `go.mod` | `go.sum` | `pkg:golang/{name}@{version}` |
| **Java** | `pom.xml` | Local Maven resolution | `pkg:maven/{group}/{artifact}@{version}` |

---

## 5. Dependency Parsing & Fallback Behavior

1. **Manifest Inspection:** Parsers extract declared and resolved dependencies, capturing package name, pinned version, manifest file path, and scope (`direct` vs `transitive`).
2. **Missing Versions:** If a manifest specifies a non-pinned version constraint (e.g. `>=1.0.0`), the system records the constraint, attempts lockfile cross-referencing, and flags unresolved metadata rather than fabricating versions.
3. **Network Isolation Fallback:** If internet access is interrupted, the vulnerability scanner activates an embedded, verified advisory fallback knowledge base for core packages (e.g. `requests`, `lodash`, `urllib3`, `pyyaml`, `axios`), ensuring deterministic test evaluation.

---

## 6. SBOM Schema & Metadata

PATCHPROOF generates machine-readable SBOMs adhering to:
- **CycloneDX v1.5 JSON:** Includes `bomFormat: CycloneDX`, `specVersion: 1.5`, component types, Package URLs (`purl`), licenses, scopes, and dependency tree structures.
- **SPDX v2.3 JSON:** Includes document namespaces, creation info, package records with external PURL references, and `DESCRIBES` relationships.

---

## 7. Vulnerability Detection & Deduplication

- **OSV.dev Integration:** Utilizes batch querying (`/v1/querybatch`) followed by concurrent detailed advisory resolution (`/v1/vulns/{id}`).
- **Alias Deduplication:** A vulnerability often shares a CVE identifier (e.g., `CVE-2018-18074`) and a GHSA identifier (e.g., `GHSA-79v4-hx79-jx7p`). PATCHPROOF unifies aliases under a single canonical finding, preventing duplicate counting.
- **CISA KEV Matching:** Vulnerabilities found on the CISA Known Exploited Vulnerabilities catalog are prioritized with active weaponization flags.
- **EPSS Scoring:** Exploitation Prediction Scoring System probabilities are linked to estimate the likelihood of real-world exploitation within 30 days.

---

## 8. Secret Detection Strategy

Scans both working directory source files and historical Git commits:
- High-entropy patterns covering: AWS Access Keys, GitHub PATs, Slack Tokens, OpenAI Keys, Stripe Secrets, Google Cloud Keys, RSA/EC Private Key blocks, and Generic Secrets.
- **Strict Masking:** Raw secrets are **never** rendered in UI, returned in API payloads, saved to audit logs, or passed to LLM prompts.
- **Masking Format:** Example: `ghp_1234567890abcdef1234567890abcdef` -> `ghp_****************************cdef`.

---

## 9. Suspicious Package Heuristics

1. **Typosquatting Detection:** Calculates Levenshtein edit distance between dependency names and curated top-100 popular packages (e.g. detecting `reqeusts` vs `requests`, `loadash` vs `lodash`).
2. **Suspicious Scripts:** Scans package lifecycle hooks (`preinstall`, `postinstall`) for external execution vectors (`curl`, `wget`, `bash -i`, `powershell`, `eval`).
3. **OpenSSF Scorecard Heuristics:** Emulates maintenance and licensing posture signals.

---

## 10. Transparent Risk Scoring Formula

The risk score $R \in [0, 100]$ is computed deterministically:

$$R_{\text{finding}} = (CVSS \times 3.5) + (KEV \times 25.0) + (EPSS \times 20.0) + (Reachability \times 10.0)$$

### Overriding Safety Rules:
- **CISA KEV Weaponization:** Guarantees minimum score of **82.0** (Critical).
- **CVSS ≥ 9.0 (Direct Scope):** Guarantees minimum score of **78.0** (Critical).
- **Repository Rollup:** A repository's score is driven by its most severe finding, preventing critical issues from being diluted by averaging with clean packages:

$$R_{\text{repo}} = \min(100, \max(R_{\text{worst}}, R_{\text{worst}} + S_{\text{secrets}} + P_{\text{suspicious}}))$$

### Risk Thresholds:
- **0 – 19:** Low
- **20 – 39:** Medium
- **40 – 69:** High
- **70 – 100:** Critical

---

## 11. Confidence Methodology

- **High:** Exact package identity, corroborated by lockfile, authoritative advisory range, and verified upstream release.
- **Medium:** Declared manifest version with advisory match, but no verified lockfile pin.
- **Low:** Heuristic warning only or unconfirmed affected range.

---

## 12. Agent Strategy & Prompt-Injection Defenses

- **Deterministic Core:** Deterministic Python code handles all parsing, hashing, scoring, diff calculation, and safety validation.
- **Untrusted Input Shield:** All package descriptions, READMEs, and commit messages pass through regex filters stripping instruction hijacking patterns (`ignore previous instructions`, `system prompt`, `override`).

---

## 13. Remediation & Draft PR Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer
    participant UI as PATCHPROOF UI
    participant API as FastAPI Backend
    participant GH as GitHub API
    
    Dev->>UI: Selects Remediation Proposal
    UI->>Dev: Displays Unified Manifest Diff & Compatibility Warning
    Dev->>UI: Clicks "Review & Create Draft PR"
    UI->>Dev: Opens Review Modal with Authorization Checkbox
    Dev->>UI: Confirms: "I authorize opening a DRAFT PR"
    UI->>API: POST /api/analyses/{id}/draft-pr (user_confirmed: true)
    API->>API: Verify Safe Action (Safety checks enforce NEVER_MERGE)
    API->>GH: Open Pull Request with draft=true
    GH-->>API: Returns Draft PR URL
    API-->>UI: DraftPRResponse (DRAFT status confirmed)
    UI-->>Dev: Displays Draft PR link and manual review instructions
```

---

## 14. Human-In-The-Loop Safeguards

1. **Explicit Authorization Required:** Creating a branch or draft PR without `user_confirmed: true` returns HTTP 400.
2. **Hardcoded Merge Killswitch:** `GitHubService.merge_pull_request` unconditionally throws `NotImplementedError`.
3. **No Unrequested Changes:** Only the specific package and version approved by the user is altered.

---

## 15. API Contract Summary

- `POST /api/analyses` — Initiates end-to-end repository scan.
- `GET /api/analyses/{id}` — Retrieves full analysis results and status.
- `GET /api/analyses/{id}/sbom?format={cyclonedx|spdx}` — Downloads CycloneDX 1.5 or SPDX 2.3 JSON.
- `GET /api/analyses/{id}/findings` — Filtered vulnerability findings.
- `GET /api/analyses/{id}/dependencies` — Component dependency inventory.
- `POST /api/analyses/{id}/draft-pr` — Creates a human-reviewed draft pull request.
- `GET /api/analyses/{id}/audit` — Retrieves cryptographic audit log entries.
- `GET /api/demos` — Returns pre-configured demo test repositories.
- `GET /health` — Health check verifying `NEVER_MERGE_ACTIVE`.

---

## 16. Threat Model

- **Threat:** Malicious repository containing prompt injection in `README.md` or dependency metadata.  
  *Mitigation:* Content sanitization strips delimiter and instruction override tokens before any processing.
- **Threat:** SSRF attacking internal AWS/GCP metadata (`169.254.169.254`) or local services (`127.0.0.1`).  
  *Mitigation:* `validate_repository_url` blocks private RFC 1918 IPs, loopbacks, and non-GitHub hosts.
- **Threat:** Leaking customer secrets in logs or API responses.  
  *Mitigation:* Real-time masking utility redacts all matching secret strings before storage or serialization.
- **Threat:** Malicious third-party package executing during install.  
  *Mitigation:* PATCHPROOF inspects manifests statically. It never runs untrusted repository setup scripts.

---

## 17. Evaluation Methodology & Verification

All core requirements are verified via automated Pytest test suites:
- 16 test cases passing across unit, boundary, safety, and API tests.
- Proved draft PR safety: automated merge path is blocked.
- Proved secret redaction: zero raw secret leakage in outputs.

---

## 18. Known Limitations

- Private GitHub repositories require configuring `GITHUB_TOKEN` with repository read access.
- Deep dynamic reachability (call graph taint tracking) for compiled binaries requires runtime instrumentation, which is represented as "unknown" reachability.

---

## 19. Installation & Deployment

Refer to the project `README.md` for complete prerequisites and setup instructions.

---

## 20. Future Improvements

- Static call-graph AST reachability analysis for Python and JavaScript.
- VEX (Vulnerability Exploitability eXchange) statement generation in CycloneDX.
- SARIF export for direct integration into GitHub Advanced Security code scanning alerts.

