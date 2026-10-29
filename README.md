# PATCHPROOF 🛡️

> **"Find the risk. Prove the fix."**

**PATCHPROOF** is an agentic developer-security platform for identifying vulnerable dependencies, suspicious packages, and leaked secrets across public GitHub repositories, proposing evidence-backed safe version fixes through human-reviewed **DRAFT** pull requests.

---

## ⚡ Core Value & Safety Guarantees

- **Software Bill of Materials (SBOM):** Standard CycloneDX 1.5 JSON and SPDX 2.3 JSON generation with Package URLs (PURLs).
- **Vulnerability Intelligence:** Direct and transitive dependency inspection via OSV.dev, GitHub Security Advisories, NVD, CISA KEV, and EPSS scores with strict deduplication across CVE/GHSA aliases.
- **Zero-Exposure Secret Detection:** Scans source code and Git commit history with instant redaction (raw secrets never leak to logs, prompts, or UI).
- **Transparent Deterministic Risk Scoring:** Documented 0–100 mathematical risk evaluation.
- **Safe, Minimal Dependency Remediation:** Computes the smallest safe version upgrade that satisfies security constraints, generating interactive unified manifest diffs.
- **Non-Negotiable Safety Contract:** **PATCHPROOF NEVER MERGES A PULL REQUEST.** Draft PRs are created only with explicit human authorization and labeled as DRAFT for peer review.

---

## 🏗️ Architecture

```
PATCHPROOF/
├── backend/                   # Python FastAPI Backend
│   ├── app/
│   │   ├── api/endpoints.py   # REST API Endpoints
│   │   ├── core/              # Config, Security, SSRF & Injection Protections
│   │   ├── models/schemas.py  # Pydantic Schemas
│   │   └── services/          # Parser, SBOM, OSV, Secrets, Risk, Remediation, GitHub, Audit
│   └── tests/                 # 16 Pytest Automated Unit, Boundary & Safety Tests
├── frontend/                  # React + TypeScript + Vite + Tailwind CSS
│   ├── src/components/        # Dashboard, SBOM, Vulnerabilities, Secrets, Remediation, PR Modal, Audit
│   └── dist/                  # Production build served directly by FastAPI
├── fixtures/                  # Controlled test repositories (Python, Node, Secrets, Go)
└── docs/                      # Technical Spec, Architecture, Threat Model, Evaluation, Demo Script
```

---

## 📋 Prerequisites

- **Python:** 3.11 or newer (Python 3.12 recommended)
- **Node.js:** v20+ and npm (for frontend building/development)
- **Git:** Installed and available in PATH

---

## 🚀 Quick Start Guide

### 1. Clone & Setup Backend

```bash
# In the root repository directory
cd backend
pip install -r requirements.txt
```

### 2. Environment Setup

Copy `.env.example` to `.env` if custom credentials or tokens are desired:
```bash
cp .env.example .env
```
*(Note: A GitHub token is entirely optional; when omitted, the platform uses deterministic dry-run draft PR generation for demonstration and testing.)*

### 3. Run Backend & Frontend (Unified Single Command)

Because the production frontend is pre-built into `frontend/dist`, simply starting the FastAPI backend serves both the complete UI and the REST API:

```bash
# From workspace root
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to: **http://127.0.0.1:8000**

---

## 💻 Optional: Running Frontend in Vite Dev Mode

If you are modifying the frontend React code:

```bash
cd frontend
npm install
npm run dev
```

Vite dev server will start at `http://localhost:5173` with automatic API proxying to `http://127.0.0.1:8000`.

---

## 🧪 Running Automated Tests

Run the full automated test suite (16 tests covering package parsing, OSV deduplication, risk scoring, secret redaction, SSRF defenses, and PR merge prohibition):

```bash
python -m pytest backend/tests -v
```

Expected output:
```
backend/tests/test_api.py ................. PASSED
backend/tests/test_dependency_parser.py ... PASSED
backend/tests/test_risk_engine.py ......... PASSED
backend/tests/test_safety_guarantees.py ... PASSED
backend/tests/test_secret_scanner.py ...... PASSED
backend/tests/test_vulnerability_service.py PASSED

======================= 16 passed in 3.75s =======================
```

---

## 🔍 Interactive Demo Scenarios

On the landing page, click any of the 4 pre-configured demo fixtures:
1. **Vulnerable Python Microservice:** Demonstrates detection of `requests==2.19.1` (CVE-2018-18074, CISA KEV weaponized) and generates a safe manifest diff upgrading to `2.20.0`.
2. **Compromised Node.js / React App:** Demonstrates npm lockfile inspection and prototype pollution detection in `lodash==4.17.15`.
3. **Git History Secret Leaks:** Demonstrates detection of simulated AWS, GitHub, and OpenAI tokens in historical commits with **100% masked redaction**.
4. **Hardened Go Microservice:** Demonstrates a clean zero-CVE baseline with 10/10 health score and Low risk.

---

## 🛡️ Security Limitations & Policy

- **No Arbitrary Code Execution:** The analyzer never runs `npm install`, `setup.py`, or untrusted build scripts.
- **SSRF Protection:** IP range validation rejects loopbacks (`127.0.0.1`), metadata endpoints (`169.254.169.254`), and private networks.
- **Permanent Merge Restriction:** `GitHubService.merge_pull_request` is permanently disabled in code and will unconditionally raise `NotImplementedError`.

---

## 📖 Technical Documentation

- [Detailed Technical Specification](docs/TECHNICAL_SPEC.md)
- [Architecture & Sequence Diagrams](docs/ARCHITECTURE.md)
- [Threat Model & Defense-in-Depth](docs/THREAT_MODEL.md)
- [Evaluation & Benchmark Report](docs/EVALUATION.md)
- [3-to-5 Minute Demo Script](docs/DEMO_SCRIPT.md)
