# PATCHPROOF — Hackathon Live Demo Runbook

**Date:** November 3, 2026  
**Audience:** Presenter / Live Demo Driver / Hackathon Team  
**System Path:** `C:\PATCHPROOF`  
**Safety Status:** `NEVER_MERGE_ACTIVE = True` (Permanent Architectural Invariant)  
**ML Model Hash:** `5F93BBA9CE457FE991580AFCD3C482D2D8FB626C019AB1DCDA58B73731176A20`

---

## 1. Quick Startup Commands (Windows CMD)

To start PATCHPROOF from a fresh Windows Command Prompt (`cmd.exe`):

### Production Mode (Recommended — Unified Single Port: 8000)
Runs FastAPI backend and serves the compiled React production application simultaneously:

```cmd
cd /d C:\PATCHPROOF
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

> **Note:** If `frontend/dist` was cleaned or needs rebuilding prior to demo, run this one-time build command first:
> ```cmd
> npm --prefix frontend run build
> ```

---

### Alternative: Dual-Terminal Developer Mode (Ports 8000 + 5173)
Use this only if you require active frontend hot-reloading:

**Terminal 1 (Backend API):**
```cmd
cd /d C:\PATCHPROOF
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend Dev Server):**
```cmd
cd /d C:\PATCHPROOF\frontend
npm run dev
```

---

## 2. Pre-Startup Environment & Dependency Verification

Run these verification commands in CMD before starting the server:

```cmd
:: 1. Check Python version (requires Python 3.10+)
python --version

:: 2. Check Node & npm versions
node -v
npm -v

:: 3. Verify ML model file exists and is intact
dir C:\PATCHPROOF\models\bug_detector.joblib

:: 4. Verify model SHA-256 integrity (must match 5F93BBA9...)
python -c "import hashlib; print(hashlib.sha256(open(r'C:\PATCHPROOF\models\bug_detector.joblib', 'rb').read()).hexdigest().upper())"

:: 5. Verify local demo fixtures directory exists
dir C:\PATCHPROOF\fixtures

:: 6. Check for port 8000 availability
netstat -ano | findstr :8000
```

If port 8000 is occupied by an orphaned process, terminate it:
```cmd
:: Replace <PID> with the process ID returned from findstr
taskkill /F /PID <PID>
```

---

## 3. Backend Health Verification

Once the server is launched, verify backend responsiveness from a second terminal or browser:

```cmd
curl http://127.0.0.1:8000/health
```

### Expected Output:
```json
{"status":"healthy","safety_guard":"NEVER_MERGE_ACTIVE"}
```

Confirm that `safety_guard` is `"NEVER_MERGE_ACTIVE"`. This verifies that the non-negotiable PR merge prevention guard is active.

---

## 4. Browser URL & Expected Landing Page

1. Open your browser (Google Chrome, Microsoft Edge, or Firefox).
2. Navigate to: **`http://127.0.0.1:8000`** *(or `http://localhost:5173` if running Dual-Terminal Developer Mode)*.

### Expected Landing Screen:
- **Top Navigation Bar:**
  - Dark obsidian header with the PATCHPROOF logo.
  - Mode toggle pills: **`[ Supply Chain Scanner ]`** (active by default) and **`[ AI Code Debugger ]`**.
  - Status indicator: **`Auto-Merge: Disabled (Guaranteed)`** badge (backed by the backend `NEVER_MERGE_ACTIVE` guard).
- **Hero Section:**
  - Headline: *"Find the risk. Prove the fix."*
  - Subtitle: *"PATCHPROOF inspects your GitHub repositories for vulnerable dependencies, suspicious packages, and committed secrets, generating verifiable CycloneDX SBOMs and safe, human-reviewed GitHub draft pull requests."*
- **Repository Search Console:**
  - Input field placeholder: `https://github.com/owner/repository`.
  - Notice badge: `Read-only analysis • Never merges PRs`.
- **Demo Quick Loaders:**
  - Four cards titled:
    1. **Vulnerable Python Microservice** (`Python / PyPI`)
    2. **Compromised Node.js / React App** (`Node.js / npm`)
    3. **Git History Secret Leaks Fixture** (`Multi-language`)
    4. **Hardened Go Cloud Microservice** (`Golang`)

---

## 5. Audit: Documented Fixtures vs. Actual Implementation

We audited `backend/app/api/endpoints.py` (`DEMO_REPOSITORIES`), `C:\PATCHPROOF\fixtures`, and the frontend components to confirm alignment:

| Card Title in UI | Fixture URL | Disk Path in `fixtures/` | Manifests Present | Expected Findings vs Actual API Findings |
| :--- | :--- | :--- | :--- | :--- |
| **Vulnerable Python Microservice** | `fixture://vulnerable-python-repo` | `fixtures/vulnerable-python-repo` | `requirements.txt` | • Card states: *3 Critical/High CVEs (1 in CISA KEV), 1 Safe Remediation proposal*<br>• Actual API: 3 direct components (`requests`, `urllib3`, `pyyaml`), 9 total advisories (including CVE-2018-18074 in CISA KEV), Risk Score: **85/100 (Critical)**, 1 remediation diff for `requests`. |
| **Git History Secret Leaks Fixture** | `fixture://secret-leak-repo` | `fixtures/secret-leak-repo` | Multi-language git repository | • Card states: *3 High-confidence credential leaks with strict automated redaction*<br>• Actual API: 5 detected credentials across historical commits (AWS, GitHub PAT, OpenAI, Slack), 100% masked, zero plain secrets leaked. |
| **Compromised Node.js / React App** | `fixture://vulnerable-node-repo` | `fixtures/vulnerable-node-repo` | `package.json`, `package-lock.json` | • Card states: *2 High severity CVEs, npm-lockfile dependencies, safe version bump to 4.17.19*<br>• Actual API: 3 npm dependencies (`lodash`, `axios`, `express`), 7 vulnerabilities (prototype pollution & SSRF), safe version bump proposed. |
| **Hardened Go Cloud Microservice** | `fixture://secure-go-repo` | `fixtures/secure-go-repo` | `go.mod` | • Card states: *0 Vulnerabilities, 10/10 Health Score, Low Risk (0/100)*<br>• Actual API: 2 Go modules, 0 CVEs, Health Score **10/10**, Risk Score **0.0/100 (Low)**. |

> **Alignment Confirmation:** All 4 demo card fixtures map 1:1 to local disk directories. No missing directories, no broken paths.

---

## 6. Exact 5-Minute Demonstration Sequence

Follow this minute-by-minute script during the presentation:

```
+----------------------------------------------------------------------------------------------------+
| 0:00 - 1:00  |  Architecture & Landing Screen Overview                                             |
| 1:00 - 2:00  |  Vulnerable Python Scan -> SBOM Export (CycloneDX/SPDX) -> CISA KEV Intelligence    |
| 2:00 - 3:00  |  Secret Scanning & Git Commit Leaks -> Zero-Leak Redaction & Rotation Playbooks    |
| 3:00 - 4:00  |  Safe Remediation Engine -> Unified Diff -> Draft PR Human-in-the-Loop Gate       |
| 4:00 - 5:00  |  AI Code Debugger -> 13 Defect Archetypes -> Mutable Default Bug -> Clean Control   |
+----------------------------------------------------------------------------------------------------+
```

---

### Minute 1: The Platform & Safety Architecture (0:00 – 1:00)

**Presenter Talking Points:**
> *"Software supply chain attacks and accidental vulnerabilities are at an all-time high. But traditional security tools create two major problems: either they drown developers in noisy alerts with no verified fix, or they blindly open automated pull requests that break production.*
> 
> *PATCHPROOF is built on an architectural guarantee: **Find the risk. Prove the fix. Never auto-merge.** We provide end-to-end supply chain transparency, standard-compliant SBOMs, and evidence-backed unified diffs with non-negotiable human-in-the-loop review."*

**Exact Actions:**
1. Point to the top navigation bar status badge: **`Auto-Merge: Disabled (Guaranteed)`** (reflecting the `NEVER_MERGE_ACTIVE` safety guard).
2. Point out the dual mode selector: **Supply Chain Scanner** and **AI Code Debugger**.
3. Under *One-Click Interactive Demo Scenarios*, click the first card: **"Vulnerable Python Microservice"**.
4. The URL input auto-fills with `fixture://vulnerable-python-repo` and launches the scan (or click **"Analyze Repository"**).

---

### Minute 2: SBOM Generation & Vulnerability Intelligence (1:00 – 2:00)

**Presenter Talking Points:**
> *"In under two seconds, PATCHPROOF has retrieved the repository, parsed the manifest, correlated every dependency against OSV.dev and the US CISA Known Exploited Vulnerabilities catalog, and generated specification-grade SBOMs."*

**Exact Actions & What to Show:**
1. **Pipeline Progress Animation:** Watch the real-time progress phases complete: `Discovery` → `Parsing` → `SBOM` → `Advisories` → `Secrets` → `Risk Engine`.
2. **Security Dashboard Tab:**
   - Risk Score reads **`85/100 (Critical Risk)`**.
   - Show the **CISA KEV Alert Badge** on `CVE-2018-18074` (`requests`): explain that this vulnerability is actively exploited by threat actors in the wild.
3. **SBOM Tab:**
   - Click the **`SBOM Inventory`** tab.
   - Show the component inventory table containing `requests`, `urllib3`, and `pyyaml` with exact Package URLs (PURLs).
   - Click **`CycloneDX 1.5 JSON`**: browser downloads `sbom-scan-xxxx-cyclonedx.json`. Mention this is compliant with executive cybersecurity orders.
   - Click **`SPDX 2.3 JSON`**: browser downloads the SPDX standard format.
4. **Vulnerabilities Tab:**
   - Click **`Vulnerabilities`** tab.
   - Filter by severity: select `CRITICAL` or search for `CVE-2018-18074` to show CVSS metrics and remediation paths.

---

### Minute 3: Git History Secret Scanning & Zero-Leak Redaction (2:00 – 3:00)

**Presenter Talking Points:**
> *"Supply chain defense isn't just about third-party packages; it's about leaked credentials that give attackers entry into your infrastructure. PATCHPROOF scans not only the latest tree but deep historical commit logs with Shannon entropy analysis."*

**Exact Actions & What to Show:**
1. In the top navbar, click **`New Analysis`** to return to the landing screen.
2. Click the card: **"Git History Secret Leaks Fixture"** (`fixture://secret-leak-repo`).
4. Click the **`Secrets`** tab:
   - Point out the detected credentials across git commits (AWS Access Keys, GitHub PATs, OpenAI Keys).
   - **Crucial Security Feature:** Point to the masked tokens (`AKIA****************`). Explain that raw credentials are **never logged, never stored, and never exposed in the UI or API**.
   - Show the **Required Revocation & Rotation Procedure** box for the finding, demonstrating actionable incident response playbooks.

---

### Minute 4: Safe Remediation & The Human Approval Gate (3:00 – 4:00)

**Presenter Talking Points:**
> *"Now the most critical stage: how do we fix it safely? PATCHPROOF generates genuine unified diffs against the actual dependency manifests. And to prevent supply chain poisoning or accidental outages, PATCHPROOF will NEVER auto-merge. Human review is strictly mandatory."*

**Exact Actions & What to Show:**
1. Switch back to the Python analysis (or click **"Vulnerable Python Microservice"** and scan).
2. Click the **`Remediations`** tab:
   - Select candidate upgrade: `requests 2.19.1 → 2.31.0` (or `2.33.0`).
   - Show the **Manifest Unified Diff Preview**:
     ```diff
     --- requirements.txt
     +++ requirements.txt
     @@ -1,3 +1,3 @@
     -requests==2.19.1
     +requests==2.31.0
     ```
   - Highlight the green and red diff syntax highlighting.
   - Point out the suggested verification command: `pytest tests/`.
3. Click **`Review & Create Draft PR`**:
   - The Draft PR review modal opens.
   - Point out that the **Submit** button is **disabled**.
   - Point to the red warning: *"Non-Negotiable Safety Guarantee: PATCHPROOF strictly opens PRs in DRAFT mode. Auto-merging is permanently disabled in the architecture."*
   - Check the **"Explicit Authorization"** checkbox:
     > *"I have reviewed the proposed dependency modification and authorize PATCHPROOF to open a DRAFT pull request."*
   - Click **`Submit DRAFT Pull Request`**.
   - Success screen confirms: `Draft PR Status: DRAFT (DRY RUN / SIMULATION)`.

---

### Minute 5: ML-Assisted Code Debugger & Defect Localization (4:00 – 5:00)

**Presenter Talking Points:**
> *"Finally, supply chain vulnerabilities frequently originate in application code logic. We built a machine learning defect classifier trained on 13 defect archetypes across Python, JavaScript, and C, with real AST line localization and diff generation."*

**Exact Actions & What to Show:**
1. In the top navbar, click **`AI Code Debugger`**.
2. Under **Quick Presets**, click: **`Python: Mutable Default Argument`**.
   - The code editor populates with:
     ```python
     def process_batch(item, queue=[]):
         """Appends item to batch queue."""
         queue.append(item)
         return queue
     ```
3. Click **`Analyze Code`**:
   - Status badge shows: **`Defect Identified`** in red.
   - Archetype category: **`API Misuse / Mutable Default State`**.
   - Model confidence: **`85.0%`**.
   - Editor gutter: **Line 1** is highlighted in red.
   - Suggested Remediation Diff:
     ```diff
     -def process_batch(item, queue=[]):
     +def process_batch(item, queue=None):
     +    if queue is None:
     +        queue = []
     ```
4. Now click preset: **`Python: Clean Bug-Free Control`** (`def filter_positives(items): ...`).
5. Click **`Analyze Code`**:
   - Status badge shows: **`Clean Code Control`** in green.
   - Category: **`No Defect Pattern Detected (Clean Code)`**.
   - Explanation: Demonstrates calibrated confidence thresholds that avoid false alarm fatigue on clean code.
6. **Closing Statement:**
   > *"PATCHPROOF delivers transparent, explainable supply chain intelligence from manifest to pull request, protecting developers while keeping humans firmly in control."*

---

## 7. Expected Outputs & Visual Verification Table

Use this table during rehearsal to ensure the screen reflects the expected numbers:

| Stage / Tab | Metric / Field | Expected Output on Screen |
| :--- | :--- | :--- |
| **Python Dashboard** | Risk Score | **`85/100`** or **`72/100`** (Critical / High Risk) |
| **Python Dashboard** | Direct Components | **3** (`requests`, `urllib3`, `pyyaml`) |
| **Python Dashboard** | Total Advisories | **9** total (including active CISA KEV alert) |
| **SBOM Tab** | PURLs | `pkg:pypi/requests@2.19.1`, `pkg:pypi/urllib3@1.24.1` |
| **SBOM Tab** | Export Downloads | `sbom-scan-xxxx-cyclonedx.json`, `sbom-scan-xxxx-spdx.json` |
| **Secrets Tab** | Leaks Found | **5** credential findings (AWS, GitHub, OpenAI, Slack) |
| **Secrets Tab** | Token Redaction | Masks like `AKIA****************` (0 unmasked tokens) |
| **Remediation Tab** | Package Upgrade | `requests` `2.19.1` → `2.31.0` (or `2.33.0`) |
| **Remediation Tab** | Diff Header | `--- requirements.txt` and `+++ requirements.txt` |
| **Draft PR Modal** | Authorization Gate | Submit button disabled until checkbox is checked |
| **Draft PR Modal** | Result Status | `DRAFT (DRY RUN / SIMULATION)` |
| **Audit Tab** | Integrity Column | 64-character SHA-256 hex string with green `Verified` pill |
| **Debugger Tab** | Mutable Default | `Defect Identified`, `API Misuse`, Line 1 highlighted |
| **Debugger Tab** | Clean Control | `Clean Code Control`, `No Defect Pattern Detected` |

---

## 8. Backup & Recovery Plan (If Anything Goes Wrong)

Hackathon demonstrations can encounter unexpected hiccups. Follow these immediate fallbacks:

### Scenario A: Browser Tab Freezes or UI Unresponsive
- **Action:** Press `Ctrl + F5` to force-refresh the page.
- State will reload cleanly. The demo fixtures are instant.

### Scenario B: API Call Times Out or Server Crashed
1. Switch to your CMD terminal running `uvicorn`.
2. Press `Ctrl + C` to stop.
3. Re-run:
   ```cmd
   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
4. Verify health: `curl http://127.0.0.1:8000/health`.

### Scenario C: Port 8000 Conflict
If port 8000 refuses to bind:
```cmd
netstat -ano | findstr :8000
taskkill /F /PID <PID_NUMBER>
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### Scenario D: Total Browser Failure / Screen Share Glitch
If the browser completely fails, demonstrate the platform directly via the automated CLI readiness suite:
```cmd
cd /d C:\PATCHPROOF
python test_hackathon_readiness.py
```
- This runs all 14 end-to-end checks in 4 seconds in the terminal.
- Output shows all 14 green `[PASS]` marks, proving SBOM generation, OSV correlation, secret scanning, risk scoring, unified diff generation, and ML code debugging.

---

## 9. Safe Shutdown Instructions

When the demonstration and judging questions are complete:

1. **Stop the Unified Server:**
   - In the CMD window running `uvicorn`, press:
     ```cmd
     Ctrl + C
     ```
   - Terminal will output: `Shutting down` and return to the command prompt.

2. **Clean Temporary Repositories (Optional):**
   ```cmd
   python -c "import shutil, os; shutil.rmtree(os.path.join(os.environ.get('TEMP', ''), 'patchproof_repos'), ignore_errors=True); print('Cleaned temp repos.')"
   ```

3. **Verify Git Working Tree:**
   ```cmd
   git status
   ```
   Confirm no unintended modifications were made to core models or source code.

---

## 10. Final Pre-Demo Checklist (15 Minutes Before Presentation)

Print or check off this list 15 minutes before taking the stage:

- [ ] **Laptop Power:** Plugged into AC power; display sleep and screen saver disabled.
- [ ] **CMD Terminal:** Open CMD at `C:\PATCHPROOF`.
- [ ] **Model Verified:** Run `python -c "import hashlib; print(hashlib.sha256(open(r'C:\PATCHPROOF\models\bug_detector.joblib', 'rb').read()).hexdigest().upper())"` and confirm starts with `5F93BBA9...`.
- [ ] **Server Started:** `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000` running with no error traces.
- [ ] **Health Check Verified:** `curl http://127.0.0.1:8000/health` returns `{"status":"healthy","safety_guard":"NEVER_MERGE_ACTIVE"}`.
- [ ] **Browser Ready:** Google Chrome open to `http://127.0.0.1:8000` in full-screen or 100% zoom.
- [ ] **Quick Smoke Test:**
  - Click `Vulnerable Python Microservice` -> Click `Analyze Repository`. Loads in <2s.
  - Click `AI Code Debugger` -> Click `Analyze Code` on Mutable Default preset. Line 1 highlighted in <50ms.
- [ ] **Reset View:** Click `New Analysis` to leave the landing page in a fresh, pristine state.
- [ ] **Backup Tab Open:** Keep a second terminal open at `C:\PATCHPROOF` ready to execute `python test_hackathon_readiness.py` if screen share issues arise.
- [ ] **Safety Reminder:** Remember the core message: *"Find the risk. Prove the fix. Never auto-merge."*

