# PATCHPROOF — PHASE O: INDEPENDENT C SECURITY BENCHMARK DESIGN & AUDIT REPORT
**Phase:** Phase O — Independent Cross-Repository C Security Benchmark
**Date:** 2026-11-05 18:30:00 UTC
**Status:** Protocol & Architecture Complete — Ready for Acquisition Approval
**Safety Invariant:** `NEVER_MERGE_ACTIVE = True` (Preserved & Verified)
**Deliverables Generated:**
- Benchmark Design: [`models/experiments/experiment_o/phase_o_benchmark_design.json`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o_benchmark_design.json)
- Source & Licensing Audit: [`models/experiments/experiment_o/phase_o_source_audit.json`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o_source_audit.json)
- Frozen Evaluation Protocol: [`models/experiments/experiment_o/phase_o_evaluation_protocol.json`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o_evaluation_protocol.json)

---

## EXECUTIVE SUMMARY

Phase N established that Candidate L2’s memory-safety recall can be significantly recovered via inference-time decision-boundary adjustments ($\tau=0.30, \delta=-0.12$ achieving 66.79% recall vs 56.00% argmax on validation data). However, the Phase N.1 audit revealed that **100% of all clean C validation code** came exclusively from QEMU and FFmpeg.

To eliminate repository bias, evaluate real-world generalization, and rigorously compare all candidate models, **Phase O establishes an independent, cross-repository C security benchmark of 2,500 verified C functions**.

### Core Governance & Safety Guarantees
- **No data has been acquired yet; no models have been trained or retrained.**
- **Strict Isolation:** Zero access to `data/processed/test.jsonl` or `robust_heldout_test.jsonl` for parameter selection.
- **Repository Independence:** QEMU and FFmpeg are 100% excluded.
- **Production Baseline Preserved:** `NEVER_MERGE_ACTIVE = True` remains enforced in `backend/app/core/config.py`.

---

## 1. PHASE 1 — BENCHMARK ARCHITECTURE & TAXONOMY

### 1.1 Target Sample Size and Class Balance
The benchmark targets exactly **2,500 real-world C functions** with a 50/50 split between genuine vulnerabilities and verified clean functions:
- **Clean C Functions:** 1,250 samples (50.0%)
- **Vulnerable C Functions:** 1,250 samples (50.0%)

### 1.2 Vulnerability Taxonomy Mapping to PATCHPROOF's 13 Canonical Classes
Every sample maps directly into PATCHPROOF’s 13 canonical defect classes:

| Vulnerability Subtype | CWE Identifiers | Canonical Class | Target Samples | % of Vulnerable | % of Total Benchmark |
|---|---|:---:|:---:|:---:|:---:|
| **Buffer Overflow (Stack & Heap)** | CWE-119, CWE-120, CWE-121, CWE-122 | `memory_safety` | **300** | 24.0% | 12.0% |
| **Out-of-Bounds Read/Write** | CWE-125, CWE-787 | `memory_safety` | **250** | 20.0% | 10.0% |
| **Use-After-Free (UAF)** | CWE-416 | `memory_safety` | **200** | 16.0% | 8.0% |
| **Double-Free** | CWE-415 | `memory_safety` | **100** | 8.0% | 4.0% |
| **Null-Pointer Dereference** | CWE-476 | `null_pointer` | **150** | 12.0% | 6.0% |
| **Resource Leak (Memory & FD)** | CWE-401, CWE-775 | `resource_leak` | **100** | 8.0% | 4.0% |
| **Integer Overflow / Wraparound** | CWE-190, CWE-191 | `undefined_behavior` | **100** | 8.0% | 4.0% |
| **Off-by-One Loop/Index** | CWE-193 | `off_by_one` | **50** | 4.0% | 2.0% |
| **Clean Safe C Function** | N/A (Verified Non-Vulnerable) | `none_correct_code` | **1,250** | — | 50.0% |
| **Total Benchmark** | | | **2,500** | **100.0%** | **100.0%** |

### 1.3 Target Repository Quota
To ensure broad architectural diversity across network servers, OS kernels, protocol clients, and databases, 7 independent projects are partitioned:

| Target Repository | Domain | Vulnerable Target | Clean Target | Total Quota | Benchmark Share |
|---|---|:---:|:---:|:---:|:---:|
| **Linux Kernel (`torvalds/linux`)** | OS Kernel & Networking | 200 | 200 | **400** | 16.0% |
| **OpenSSL (`openssl/openssl`)** | Cryptography & TLS Engine | 200 | 200 | **400** | 16.0% |
| **Wireshark (`wireshark/wireshark`)** | Packet Parsing & Dissectors | 200 | 200 | **400** | 16.0% |
| **curl (`curl/curl`)** | Transfer Protocol Client & `libcurl` | 175 | 175 | **350** | 14.0% |
| **Redis (`redis/redis`)** | In-Memory Key-Value Store & RESP | 175 | 175 | **350** | 14.0% |
| **nginx (`nginx/nginx`)** | Reverse Proxy & HTTP Server | 150 | 150 | **300** | 12.0% |
| **SQLite (`sqlite/sqlite`)** | Embedded SQL Database & VM | 150 | 150 | **300** | 12.0% |
| **Total Benchmark** | | **1,250** | **1,250** | **2,500** | **100.0%** |

### 1.4 Data Schema Compliance
Every benchmark record follows the strict `CodeDebuggingExample` schema:
```json
{
  "example_id": "pp-bench-o-a1b2c3d4e5f6",
  "language": "c",
  "bug_category": "memory_safety",
  "vulnerability_subtype": "buffer_overflow",
  "cwe_id": "CWE-120",
  "cve_id": "CVE-2023-38545",
  "original_code": "int parse_header(...) { ... }",
  "corrected_code": "int parse_header(...) { ... }",
  "patch": "--- a/src/parse.c\n+++ b/src/parse.c\n@@ ...",
  "faulty_line_numbers": [42, 43],
  "repository": "curl/curl",
  "commit_hash": "a1b2c3d4e5f67890...",
  "fix_commit_hash": "f6e5d4c3b2a10987...",
  "file_path": "lib/socks.c",
  "function_name": "parse_socks5",
  "license": "curl",
  "verification_status": "cve_verified_paired",
  "difficulty": "medium",
  "split": "benchmark_o"
}
```

---

## 2. PHASE 2 — SOURCE SELECTION & LICENSING AUDIT

All 7 proposed repositories have been audited for intellectual property licensing, upstream stability, CVE tracking maturity, and historical overlap with PATCHPROOF.

### 2.1 Repository Audit Matrix

| Repository | Upstream License | License Category | Commercial/Research Suitability | CVE Tracking Source | Audit Verdict |
|---|---|---|:---:|---|:---:|
| **`torvalds/linux`** | GPL-2.0-only WITH Linux-syscall-note | Reciprocal Open Source | Approved | Kernel CVE Project, NVD, Syzkaller | **Approved with Quarantine** (BigVul commits excluded) |
| **`openssl/openssl`** | Apache-2.0 (v3.0+) / OpenSSL & SSLeay | Permissive | Approved | Official OpenSSL Security Advisories | **Approved (High Priority)** |
| **`wireshark/wireshark`** | GPL-2.0-or-later | Reciprocal Open Source | Approved | Wireshark wnpa-sec Advisories & GitLab | **Approved (High Priority)** |
| **`curl/curl`** | curl (MIT-derivate) | Permissive | Approved | Official curl Security Database (`curl.se`) | **Approved (Gold Standard)** |
| **`redis/redis`** | BSD-3-Clause (pre-v7.4 / pre-March 2024) | Permissive | Approved | GitHub Security Advisories (`GHSA-redis`) | **Approved (Restricted to BSD Commits)** |
| **`nginx/nginx`** | BSD-2-Clause | Permissive | Approved | Official nginx Security Advisories | **Approved (High Priority)** |
| **`sqlite/sqlite`** | blessing (Public Domain) | Public Domain | Approved | Fossil Check-ins, OSS-Fuzz Reports | **Approved (Zero Encumbrance)** |

### 2.2 Explicit Repository Exclusions
- **`qemu/qemu`:** Strictly excluded. QEMU accounts for 66.07% of clean C validation code and 13,477 training functions. Retaining QEMU would perpetuate identifier bias.
- **`ffmpeg/ffmpeg`:** Strictly excluded. FFmpeg accounts for 33.93% of clean C validation code and 7,271 training functions (`av_` prefix leakage).
- **`libpng`, `libtiff`, `tcpdump`, `krb5`:** Excluded due to historical inclusion in BigVul training splits.

---

## 3. PHASE 3 — LEAKAGE PREVENTION & DEDUPLICATION ARCHITECTURE

To guarantee that the benchmark measures true generalization rather than data memorization, a 5-stage leakage prevention pipeline is defined:

```
[Candidate Ingestion]
         │
         ▼
[Stage 1: Repository & Commit Quarantine] ──> Exclude QEMU, FFmpeg & known BigVul commit hashes
         │
         ▼
[Stage 2: Exact SHA-256 Deduplication]    ──> Collision check against 57,000+ train/val/test hashes
         │
         ▼
[Stage 3: Normalized AST Deduplication]   ──> Strip comments, collapse whitespace, debias identifiers
         │
         ▼
[Stage 4: Signature & Template Check]     ──> Match function names, file paths, synthetic templates
         │
         ▼
[Stage 5: Dual Provenance Verification]   ──> Verify official CVE / advisory URL / 12-month clean stability
         │
         ▼
[Benchmark_O Dataset Locked]
```

### 3.1 Deduplication Specifications
1. **Exact-Code SHA-256:**
   $$\text{Hash}_{\text{exact}} = \text{SHA-256}(\text{utf-8}(\text{code}))$$
   Checked against all hashes from `train.jsonl` (34,860), `val.jsonl` (10,860), and pre-compiled exclusion sets from test splits without reading test labels.
2. **Normalized-Code AST Hash:**
   $$\text{Hash}_{\text{norm}} = \text{SHA-256}\left(\text{"c:"} + \text{StripWhitespace}(\text{StripComments}(\text{Debias}(\text{code})))\right)$$
   Guarantees that variable renames, formatting changes, or re-indented functions cannot bypass deduplication.
3. **Clean Code Verification:**
   Clean functions must originate from tagged stable releases maintained for $\ge 12$ months with zero security advisories or CVE patches affecting that specific function.

---

## 4. PHASE 4 — FROZEN EVALUATION PROTOCOL

### 4.1 Evaluation Candidates
The benchmark evaluates exactly 5 model configurations under identical batch conditions:

1. **Production Baseline:**
   - Artifact: `models/bug_detector.joblib` (`5f93bba9ce457fe9...`)
   - Model: Word/Char TF-IDF + Logistic Regression
   - Decision Rule: Base Argmax
2. **Candidate BugModel K:**
   - Artifact: `models/experiments/experiment_k/bug_detector_candidate_k.joblib` (`c6ed9f42e8547137...`)
   - Model: Candidate K with 10,000 additional samples
   - Decision Rule: Base Argmax
3. **Candidate L2 (Debiased Baseline):**
   - Artifact: `models/experiments/experiment_l/candidate_l2_debiased.joblib` (`399d155684ff6ac6...`)
   - Model: Candidate L2 with identifier debiasing and balanced class weights ($C=1.5$)
   - Decision Rule: Base Argmax
4. **Candidate L2 with Configuration B:**
   - Artifact: `models/experiments/experiment_l/candidate_l2_debiased.joblib`
   - Decision Rule: Asymmetric Promotion Override:
     $$\text{pred} = \begin{cases} \text{"memory\_safety"}, & \text{if } P(\text{mem}) \ge 0.38 \text{ and } (P(\text{mem}) - P(\text{clean})) \ge -0.10 \\ \text{orig\_argmax}, & \text{otherwise} \end{cases}$$
5. **Candidate L2 with Configuration C (Pareto):**
   - Artifact: `models/experiments/experiment_l/candidate_l2_debiased.joblib`
   - Decision Rule: Asymmetric Promotion Override:
     $$\text{pred} = \begin{cases} \text{"memory\_safety"}, & \text{if } P(\text{mem}) \ge 0.30 \text{ and } (P(\text{mem}) - P(\text{clean})) \ge -0.12 \\ \text{orig\_argmax}, & \text{otherwise} \end{cases}$$

### 4.2 Standard Metrics & Reporting Breakdown
All 5 candidates will be evaluated on the identical 2,500 samples reporting:
- **Global Metrics:** Accuracy, Macro F1, Weighted F1.
- **Memory-Safety Detection:** Precision, Recall, F1, True Positives, False Positives, False Negatives (Support = 850).
- **Clean C Reliability:** Clean C False Positive Rate (FPR), False Alarms specifically misclassified as `memory_safety` (Support = 1,250).
- **Bug Detection Reliability:** Bug False Negative Rate (FNR), Bug Recall (Support = 1,250).
- **Per-Repository Breakdown:** Performance matrix across all 7 repositories (Linux, OpenSSL, Wireshark, curl, Redis, nginx, SQLite).
- **Per-Vulnerability Breakdown:** Performance across Buffer Overflow, Out-of-Bounds, Use-After-Free, Double-Free, Null Pointer, Resource Leak, Integer Overflow, and Off-by-One.
- **Inference Latency:** Mean, median (p50), 90th percentile (p90), 95th percentile (p95), 99th percentile (p99), and throughput (samples/sec).

---

## 5. CRYPTOGRAPHIC VERIFICATION & SAFETY INVARIANTS

### 5.1 Artifact Integrity State
All SHA-256 checksums remain verified and locked:

| Target File | Expected SHA-256 Hash | Integrity Status |
|---|---|:---:|
| `models/bug_detector.joblib` | `5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20` | **MATCH (LOCKED)** |
| `models/experiments/experiment_k/bug_detector_candidate_k.joblib` | `c6ed9f42e8547137577a311f603a9f752084cb2d0be5ff7ce4b75af7bae2377a` | **MATCH (LOCKED)** |
| `models/experiments/experiment_l/candidate_l2_debiased.joblib` | `399d155684ff6ac689624175696b4dd6db7bff149fa7421a63b30c76f25c4942` | **MATCH (LOCKED)** |
| `data/processed/train.jsonl` | `6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad` | **MATCH (LOCKED)** |
| `data/processed/val.jsonl` | `935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f` | **MATCH (LOCKED)** |
| `data/processed/test.jsonl` | `9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d` | **UNTOUCHED (ISOLATED)** |
| `data/processed/robust_heldout_test.jsonl` | `e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1` | **UNTOUCHED (ISOLATED)** |

### 5.2 System Invariants
- `backend/app/core/config.py`: `NEVER_MERGE = True` is permanently enabled.
- Production server running on `http://127.0.0.1:8000` remains intact and unaffected.
- **No data acquisition, model training, or candidate evaluation has been initiated.**

---

## 6. STATUS & AWAITING APPROVAL

Phase O benchmark design, repository sourcing audit, leakage prevention pipeline, and evaluation protocols are fully established.

**Execution is halted.** We await user approval before proceeding to sample acquisition or model evaluation.
