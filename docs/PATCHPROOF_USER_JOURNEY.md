# PATCHPROOF — Complete End-to-End User Journey Walkthrough

**Document:** Complete User Experience & Persona Walkthrough  
**Audience:** Developers, Security Analysts, Hackathon Judges, Enterprise Reviewers  
**Reference Target:** `fixture://vulnerable-python-repo` (Vulnerable Python Microservice)  
**Safety Invariant:** `NEVER_MERGE_ACTIVE = True`

---

## 1. Journey Overview & User Persona

This walkthrough follows **Alex**, a Lead Backend Software Engineer at a fast-growing cloud company. Alex’s team is preparing for a SOC 2 audit and wants to:
1. Audit their microservices for supply chain vulnerabilities and weaponized CVEs.
2. Produce executive-grade Software Bills of Materials (SBOMs) for enterprise compliance.
3. Verify that credentials have not been leaked in Git commit history.
4. Safely upgrade outdated dependencies without causing production outages.
5. Debug subtle Python code defects using machine learning.
6. Ensure that automated tools **never automatically merge changes** into their production branches.

Below is Alex's complete step-by-step experience using PATCHPROOF.

---

## Step 1: Launching the Application & Landing Screen

Alex opens their browser and navigates to the local PATCHPROOF instance:
**`http://127.0.0.1:8000`**

### What Alex Sees on Screen:
1. **Header Navigation Bar:**
   - Brand logo and title: `PATCHPROOF v1.0 Security Agent`.
   - Tagline: *"Find the risk. Prove the fix."*
   - Mode Toggle Pills: **`[ Supply Chain Scanner ]`** (active) and **`[ AI Code Debugger ]`**.
   - Platform Safety Badge: `Auto-Merge: Disabled (Guaranteed)` with a cyan pulsing indicator and lock icon.
2. **Hero Section:**
   - Headline: *"Find the risk. Prove the fix."*
   - Overview: *"PATCHPROOF inspects your GitHub repositories for vulnerable dependencies, suspicious packages, and committed secrets, generating verifiable CycloneDX SBOMs and safe, human-reviewed GitHub draft pull requests."*
3. **Repository Input Console:**
   - Search bar with placeholder: `https://github.com/owner/repository`.
   - Security assurance pill: `Read-only analysis • Never merges PRs`.
   - Primary Call-to-Action button: `Analyze Repository`.
4. **Interactive Demo Loaders:**
   - Four instant scenario cards representing distinct software ecosystems:
     1. **Vulnerable Python Microservice** (`Python / PyPI`)
     2. **Compromised Node.js / React App** (`Node.js / npm`)
     3. **Git History Secret Leaks Fixture** (`Multi-language`)
     4. **Hardened Go Cloud Microservice** (`Golang`)

---

## Step 2: Triggering the Vulnerable Python Microservice Analysis

Alex wants to evaluate a Python microservice containing outdated dependencies.

### Alex's Actions:
- Alex clicks the first scenario card: **"Vulnerable Python Microservice"**.
- The repository input bar automatically populates with `fixture://vulnerable-python-repo`.
- The analysis pipeline triggers automatically (or Alex clicks **`Analyze Repository`**).

### What Happens Behind the Scenes (in ~1.5 seconds):
1. **SSRF Validation:** The backend confirms `fixture://` is an authorized demonstration scheme.
2. **Repository Ingestion:** Resolves `C:\PATCHPROOF\fixtures\vulnerable-python-repo` directly from local disk.
3. **Dependency Parsing:** Extracts 3 dependencies from `requirements.txt`:
   - `requests==2.19.1` (Direct)
   - `urllib3==1.24.1` (Direct)
   - `pyyaml==5.2` (Direct)
4. **SBOM Generation:** Builds CycloneDX 1.5 and SPDX 2.3 dependency graphs in memory.
5. **Vulnerability Correlation:** Enriches dependencies against OSV.dev and CISA KEV, discovering 9 total security advisories.
6. **Secret Scanning:** Inspects working tree files and git commit history for credentials.
7. **Risk Engine:** Computes a composite risk score of **`85.0 / 100 (Critical Risk)`**.
8. **Remediation Planning:** Synthesizes a safe unified diff upgrading `requests` to `2.31.0`.
9. **Audit Trail:** Generating tamper-evident SHA-256 integrity hashes for each lifecycle event.

### Visual Feedback:
The UI displays the animated `PipelineProgress` component, visually moving through:
`Discovery` → `Parsing` → `SBOM` → `Advisories` → `Secrets` → `Risk Engine` → `Complete`.

---

## Step 3: Executive Security Overview (Security Dashboard Tab)

Once complete, the platform transitions to the active analysis view, defaulting to the **Security Dashboard** tab.

### What Alex Inspects:
- **Risk Score Card:**
  - Displays **`85.0 / 100`** in bold red with the label **`CRITICAL RISK`**.
  - Risk summary explanation: *"High risk driven by active CISA KEV exploitation on requests (CVE-2018-18074) and CVSS 9.8 vulnerability on pyyaml."*
- **Key Metrics Grid:**
  - Total Components: **3**
  - Total Advisories: **9**
  - Critical Severity Findings: **3**
  - High Severity Findings: **4**
  - Active CISA KEV Exploits: **1** (Warning badge highlighted)
- **Top Vulnerability Banner:**
  - Highlights `CVE-2018-18074` (`requests==2.19.1`):
    *"Unintended leak of Authorization headers across HTTP redirects. Active in CISA KEV."*

### Alex's Takeaway:
Alex immediately knows their microservice has an actively exploited vulnerability in production.

---

## Step 4: Software Bill of Materials (SBOM Inventory Tab)

Alex's compliance officer needs an official SBOM for the upcoming audit.

### Alex's Actions:
1. Alex clicks the **`SBOM Inventory (3)`** tab.
2. Alex reviews the structured component table:
   - `requests` | `2.19.1` | `pypi` | `pkg:pypi/requests@2.19.1` | `Direct` | `requirements.txt`
   - `urllib3` | `1.24.1` | `pypi` | `pkg:pypi/urllib3@1.24.1` | `Direct` | `requirements.txt`
   - `pyyaml` | `5.2` | `pypi` | `pkg:pypi/pyyaml@5.2` | `Direct` | `requirements.txt`
3. Alex clicks the **`CycloneDX 1.5 JSON`** button in the top right.
   - The browser immediately downloads `sbom-scan-xxxx-cyclonedx.json`.
4. Alex clicks the **`SPDX 2.3 JSON`** button.
   - The browser downloads `sbom-scan-xxxx-spdx.json`.

### Alex's Takeaway:
In two clicks, Alex has generated specification-compliant, machine-readable SBOMs that satisfy executive cybersecurity mandates.

---

## Step 5: Triage & Threat Enrichment (Vulnerabilities Tab)

Alex wants to understand the technical details of the advisories.

### Alex's Actions:
1. Alex clicks the **`Vulnerabilities (9)`** tab.
2. Alex clicks the **`CRITICAL`** filter pill to isolate critical findings.
3. Alex inspects `CVE-2018-18074` on package `requests`:
   - **Severity Badge:** `CRITICAL` (CVSS Score: `7.5` base with KEV override).
   - **Exploit Status:** **`CISA KEV: ACTIVE`** (Red shield badge).
   - **EPSS Score:** `35.0%` probability of active automated scanning.
   - **Affected Range:** `< 2.20.0`.
   - **Fixed Version:** `2.20.0` (or `2.31.0` stable).
   - **Reference Links:** Direct link to NIST NVD advisory and GitHub issue.

### Alex's Takeaway:
Alex sees that `requests` must be upgraded to at least `2.20.0` (or the modern secure release `2.31.0`) to neutralize the active CISA KEV threat.

---

## Step 6: Git History Secret Inspection (Secrets Tab)

Alex wants to ensure no credentials were accidentally leaked in the repository.

### Alex's Actions:
1. In the current Python microservice, Alex checks the **`Secrets (0)`** tab. It shows:
   *"Zero credentials leaked. Deterministic entropy & regex scanning confirmed clean."*
2. To verify how PATCHPROOF behaves when a leak does exist, Alex clicks **`New Analysis`** in the top navbar and selects the **"Git History Secret Leaks Fixture"** (`fixture://secret-leak-repo`).
3. Alex clicks **`Analyze Repository`** and opens the **`Secrets`** tab:
   - Finding 1: `AWS Access Key ID` in `deploy/aws.tf` (Commit `a1b2c3d4`).
     - Masked Token: `AKIA****************` (Raw secret is 100% redacted).
   - Finding 2: `GitHub Personal Access Token` in `.github/workflows/ci.yml`.
     - Masked Token: `ghp_****************************cdef`.
   - Finding 3: `OpenAI API Key` in `src/config.py`.
     - Masked Token: `sk-********************************`.
   - **Actionable Rotation Playbooks:** Each finding displays a dedicated remediation playbook (e.g. *"Revoke IAM User access key in AWS IAM console, generate new credentials, and store in AWS Secrets Manager"*).

### Alex's Takeaway:
Raw credentials are never exposed on screen or in API logs. Alex is given actionable rotation steps for incident response.

---

## Step 7: Automated Safe Remediation (Remediations Tab)

Alex returns to the Python scan to fix the vulnerable packages.

### Alex's Actions:
1. Alex navigates to the **`Remediations (1)`** tab.
2. In the candidate sidebar, Alex selects the upgrade for **`requests`**:
   - Current Version: `2.19.1`
   - Proposed Fixed Version: `2.31.0`
   - Status Tag: `Safe Patch` (green pill)
3. Alex reviews the **Compatibility & Breaking Change Assessment**:
   - `Breaking Change Warning:` None detected (Minor/Patch Upgrade within 2.x stream).
   - `Suggested Verification Command:` `pytest tests/`
4. Alex reviews the **Manifest Unified Diff Preview**:
   ```diff
   --- requirements.txt
   +++ requirements.txt
   @@ -1,3 +1,3 @@
   -requests==2.19.1
   +requests==2.31.0
   ```
   The UI syntax-highlights `-requests==2.19.1` in red and `+requests==2.31.0` in green.

### Alex's Takeaway:
PATCHPROOF didn't just tell Alex that `requests` was vulnerable; it generated the exact, syntax-checked unified diff needed to fix it without introducing major breaking API changes.

---

## Step 8: Safe Draft Pull Request Creation & The Authorization Gate

Alex is ready to propose this fix to their engineering team.

### Alex's Actions:
1. Alex clicks the primary button: **`Review & Create Draft PR`**.
2. The **Draft Pull Request Review Modal** opens:
   - Target Repository: `fixture://vulnerable-python-repo`
   - Base Branch: `main`
   - Proposed Branch: `patchproof/fix-requests-2.31.0`
   - Draft PR Title: `Upgrade requests to 2.31.0 (Remediates CVE-2018-18074)`
   - Diff preview is rendered inside the modal.
3. **The Non-Negotiable Safety Guarantee Box:**
   The modal clearly displays:
   > *"PATCHPROOF strictly opens PRs in DRAFT mode. Auto-merging is permanently disabled in the architecture. Human review and manual merge are strictly required."*
4. Alex notices the **`Submit DRAFT Pull Request`** button is **disabled**.
5. Alex reads and checks the mandatory authorization checkbox:
   > ☑️ *"Explicit Authorization: I have reviewed the proposed dependency modification (requests 2.19.1 → 2.31.0) and authorize PATCHPROOF to open a DRAFT pull request."*
6. The submit button illuminates in cyan/violet gradient. Alex clicks **`Submit DRAFT Pull Request`**.
7. The modal transitions to the success screen:
   - Green checkmark: `Draft Pull Request Successfully Created`.
   - Status: `DRAFT (DRY RUN / SIMULATION)`
   - Branch: `patchproof/fix-requests-2.31.0`
   - Notice: *"Draft pull request preview prepared for human peer review. Auto-merging is permanently prohibited."*

### Alex's Takeaway:
Alex’s organization is protected against rogue automated commits. Nothing is pushed without human eyes, and automatic merging is architecturally impossible.

---

## Step 9: Tamper-Evident Audit Trail (Audit Trail Tab)

Alex needs to document this remediation for the SOC 2 compliance auditor.

### Alex's Actions:
1. Alex closes the modal and clicks the **`Audit Trail`** tab.
2. Alex views the chronological event stream:
   - `ANALYSIS_INITIALIZED` | Actor: `System`
   - `DEPENDENCIES_PARSED` | 3 components extracted from `requirements.txt`
   - `VULNERABILITY_SCAN_COMPLETED` | 9 advisories identified
   - `SECRETS_SCAN_COMPLETED` | 0 secrets found
   - `RISK_SCORING_FINALIZED` | Composite score 85.0
   - `REMEDIATION_PLANNED` | Proposal created for `requests`
   - `DRAFT_PULL_REQUEST_CREATED` | Actor: `Human Reviewer` | Opened DRAFT pull request
3. Alex inspects the right column of each event:
   - Every event has a unique **SHA-256 Integrity Hash** (e.g., `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855...`) with a green `Verified` badge.

### Alex's Takeaway:
Alex has cryptographic proof that a human reviewer authorized the remediation proposal.

---

## Step 10: AI Code Debugging & Defect Localization

Finally, Alex wants to inspect a Python function in their microservice that has been behaving erratically in production.

### Alex's Actions:
1. In the top navbar, Alex clicks **`AI Code Debugger`**.
2. Alex selects the quick preset: **`Python: Mutable Default Argument`**.
3. The editor loads:
   ```python
   def process_batch(item, queue=[]):
       """Appends item to batch queue."""
       queue.append(item)
       return queue
   ```
4. Alex clicks **`Analyze Code`**.
5. In under 20 milliseconds, the results pane populates:
   - **Classification:** `Defect Identified` (Red badge).
   - **Category:** `API Misuse / Mutable Default State`.
   - **Model Confidence:** `85.0%`.
   - **Code Editor:** **Line 1** is highlighted in bold red in the gutter.
   - **Synthesized Unified Diff:**
     ```diff
     --- original
     +++ remediated
     @@ -1,3 +1,5 @@
     -def process_batch(item, queue=[]):
     +def process_batch(item, queue=None):
     +    if queue is None:
     +        queue = []
          """Appends item to batch queue."""
     ```
   - **Plain English Explanation:** Explains that default list arguments are shared across all invocations in Python, creating unexpected state retention bugs across requests.
6. Alex tests the clean control preset: **`Python: Clean Bug-Free Control`** (`def filter_positives(items):`).
   - Status: `Clean Code Control` (Green badge).
   - Confidence: No defect patterns detected. Verified clean classification on tested benchmark control snippet.

### Alex's Takeaway:
Alex discovered a state leak bug in their Python handler, received a line-level localization, and obtained a drop-in patch—all computed statically in milliseconds without cloud LLM latency or cost.

---

## 3. Summary of Alex's Experience

| Milestone | Time Elapsed | Outcome |
| :--- | :---: | :--- |
| **Launch to Scan** | 10 seconds | Repository ingested, dependencies parsed across manifests. |
| **SBOM Export** | 30 seconds | CycloneDX 1.5 & SPDX 2.3 JSON compliance files downloaded. |
| **Threat Triage** | 60 seconds | Isolated weaponized CISA KEV exploit (`CVE-2018-18074`). |
| **Secret Verification** | 90 seconds | Verified zero working credentials exposed. |
| **Remediation & PR** | 3 minutes | Generated unified diff; authorized DRAFT PR under `NEVER_MERGE`. |
| **Code Debugging** | 4 minutes | Static ML defect classification and line localization on Python code. |

**Final Verdict:** Alex completed an end-to-end supply chain security review and source code audit in under five minutes, with full mathematical transparency, cryptographic auditability, and verifiable safety guarantees.

