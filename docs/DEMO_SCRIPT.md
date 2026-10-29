# PATCHPROOF — 3-TO-5 MINUTE DEMO SCRIPT

Follow this script to showcase the core capabilities, deterministic risk scoring, and safety guarantees of PATCHPROOF.

---

## Step 1: Open the Application (0:00 - 0:30)
1. Open your browser to `http://127.0.0.1:8000` (or `http://localhost:5173` if running Vite dev server).
2. Highlight the visual personality:
   - Deep violet/midnight command center palette (`#090812`, `#17142A`).
   - Electric cyan accents (`#22D3EE`).
   - Prominent **Auto-Merge: Disabled (Guaranteed)** safety guard badge in the header.
   - Tagline: *"Find the risk. Prove the fix."*

---

## Step 2: Launch Real Repository Analysis (0:30 - 1:00)
1. Click on the demo fixture card: **"Vulnerable Python Microservice"** (or paste any public GitHub repository URL e.g. `https://github.com/psf/requests`).
2. Watch the real-time pipeline indicators advance:
   - *Input Validation* → *Repo Retrieval* → *Dependency Parsing* → *SBOM Generation* → *OSV.dev Lookup* → *Secret Scanning* → *Health Check* → *Risk Scoring* → *Safe Remediation*.
3. Note the analysis completes in seconds with commit SHA pinning.

---

## Step 3: Explore the Security Dashboard & SBOM Explorer (1:00 - 1:45)
1. Point out the **Composite Risk Score (85.0 / 100 - Critical)**:
   - Explain the deterministic breakdown: Base CVSS + Active CISA KEV override (+25 points) + Reachability.
2. Click the **"SBOM Inventory"** tab:
   - View the searchable component table with Package URLs (`pkg:pypi/requests@2.19.1`), scope (`Direct`), and licenses.
   - Click **"CycloneDX 1.5 JSON"** to download the machine-readable SBOM document.
   - Click **"SPDX 2.3 JSON"** to download the standard SPDX document.

---

## Step 4: Inspect Vulnerability Intelligence & Redacted Secrets (1:45 - 2:30)
1. Switch to the **"Vulnerabilities"** tab:
   - Notice deduplication: `GHSA-79v4-hx79-jx7p` and `CVE-2018-18074` are unified into one finding rather than double-counted.
   - Click the finding card to reveal the expanded intelligence drawer: affected range (`< 2.20.0`), reachability, confidence, and authoritative references.
2. Switch to the **"Secrets"** tab (or test with the "Git History Secret Leaks" fixture):
   - Show detected simulated credentials.
   - **Point out the redaction:** The raw key is masked (`ghp_****************************3456`).
   - Show the concrete rotation playbook instructions.

---

## Step 5: Safe Remediation & Draft PR Review (2:30 - 3:30)
1. Switch to the **"Remediations"** tab:
   - Show the calculated proposal: Upgrading `requests` from `2.19.1` to `2.20.0`.
   - Point out that PATCHPROOF chose the **smallest safe version bump** rather than recklessly jumping to latest major version.
   - Inspect the **Unified Manifest Diff**:
     ```diff
     --- a/requirements.txt
     +++ b/requirements.txt
     - requests==2.19.1
     + requests==2.20.0
     ```
   - Review suggested test command: `pytest tests/`.
2. Click **"Review & Create Draft PR"**:
   - The review modal appears with proposed branch `patchproof/fix-requests-2.20.0`.
   - Note the un-checked authorization box. If you attempt to click submit, it will block you until confirmed.
   - Check the box: *"I have reviewed the proposed dependency modification and authorize PATCHPROOF to open a DRAFT pull request."*
   - Click **"Submit DRAFT Pull Request"**.
3. View the confirmation:
   - The PR is created strictly as a **DRAFT**.
   - Review the safety badge: *"PATCHPROOF creates draft pull requests for human review only and will never automatically merge changes."*

---

## Step 6: Review Tamper-Evident Audit Log (3:30 - 4:00)
1. Switch to the **"Audit Trail"** tab:
   - Review the chronological event log from `ANALYSIS_INITIALIZED` to `DRAFT_PULL_REQUEST_CREATED`.
   - Show that each entry has a cryptographic **SHA-256 integrity hash**.
   - Show that zero secrets or auth tokens exist in the audit logs.

