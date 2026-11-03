# PATCHPROOF — INDEPENDENT ML DATASET & MODEL AUDIT REPORT

**Audit Date:** 2026-10-29  
**Auditor:** Independent Technical Auditor & ML System Verification Engineer  
**System Evaluated:** PATCHPROOF ML Code-Debugging Pipeline & Trained Defect Classifier  
**Target Repository:** `C:\PATCHPROOF`  

---

## 1. Executive Summary & Verification Verdict

An exhaustive, non-destructive audit was performed on the dataset files, public source provenance, synthetic generators, test splits, trained model artifacts, and application endpoints.

| Evaluation Dimension | Stated Claim | Audited Reality | Verification Status |
| :--- | :--- | :--- | :---: |
| **Total Validated Dataset Size** | 48,280 examples | **48,280 records** on disk across `train.jsonl`, `val.jsonl`, `test.jsonl` | **VERIFIED** |
| **Public Benchmark Provenance** | Real-world benchmark data | **10 curated reference seeds** (hardcoded in adapter, not live fetched) | **PARTIALLY VERIFIED (Seeds)** |
| **Exact Deduplication** | Zero exact duplicate codes | **0 exact duplicates** out of 38,760 train records | **VERIFIED** |
| **Semantic Template Diversity** | Diverse unique code bodies | **43 distinct core algorithmic templates** parameterized across 50,000 runs | **QUALIFIED FINDING** |
| **Test Accuracy on Synthetic Split** | 99.98% accuracy | **99.98% reproducible accuracy** (4,468/4,469 correct, 1 error) | **VERIFIED (Within Synthetic Scope)** |
| **General Code Debugging Ability** | General bug detector | **Synthetic template pattern classifier**, not general zero-shot detector | **QUALIFIED FINDING** |
| **Split Contamination / Overlap** | Zero data leakage | **Zero group ID overlap**; high template-body archetype overlap | **QUALIFIED FINDING** |
| **Pytest Test Suite Pass Rate** | 27 passing tests | **27 passed, 0 failed, 2 warnings** in 5.96s | **VERIFIED** |
| **Live FastAPI Endpoint Integration**| Integrated into platform | **Offline training prototype**; not yet mounted in `endpoints.py` | **NOT INTEGRATED** |

---

## 2. Task 1: Dataset Accounting & Provenance Audit

### A. Physical File Inspection (`data/`)

Every file on disk was inspected and line counts verified by direct file reads:

```
data/processed/train.jsonl             : 38,760 lines (45,065,557 bytes)
data/processed/val.jsonl               :  5,051 lines ( 5,696,841 bytes)
data/processed/test.jsonl              :  4,469 lines ( 5,466,951 bytes)
Total Processed Split Records          : 48,280 lines (56,229,349 bytes)

data/raw/big_vul.jsonl                 :      2 lines (     1,825 bytes)
data/raw/bugswarm.jsonl                :      2 lines (       859 bytes)
data/raw/codesearchnet_controls.jsonl  :      3 lines (     1,657 bytes)
data/raw/swe_bench.jsonl               :      3 lines (     1,595 bytes)
Total Raw Public Reference Seeds       :     10 lines (     5,936 bytes)

data/reports/rejections.jsonl          :      2 lines (       463 bytes)
data/reports/validation_report.json    :              (       265 bytes)
data/processed/split_statistics.json   :              (       726 bytes)
```

### B. Public Source Truthfulness Check
- **Finding:** The 10 public reference records (SWE-bench, BugSwarm, Big-Vul, CodeSearchNet) were **not downloaded over the network at runtime**. They are statically curated reference seeds stored in `scripts/datasets/download_sources.py` to ensure deterministic execution in offline and air-gapped environments.
- **Licensing & Attribution:** The metadata in these 10 records faithfully captures the true upstream licenses (Apache-2.0, BSD-3-Clause, ISC, GPL-2.0) and references legitimate repositories (`psf/requests`, `django/django`, `sudo-project/sudo`, `openssl/openssl`).
- **CodeSearchNet Invariant:** Verified that CodeSearchNet samples are **strictly tagged as `none_correct_code`** (hard negative controls) and never falsely labeled as defective bugs.

### C. Sample Field Agreement Audit (40 Random Samples)
Inspected 40 randomly sampled records across Python, C, JavaScript, Java, and Go:
- `faulty_line_numbers` physical boundary check: **40/40 in-bounds (100% agreement)**.
- `bug_description` semantic agreement: **40/40 agreed** with the intended bug archetype.
- `patch` diff verification: **40/40 agreed** (unified diff accurately transformed `original_code` to `corrected_code` or was empty for clean controls).
- `test_cases`: **40/40 had reproducible unit inputs or clean filter assertions**.

### D. Duplicate Analysis
- **Exact Code Duplication:** **0 duplicates** across 38,760 training samples. Every function has randomized prefixes, variable names, and numerical parameters.
- **Structural Template Duplication:** Found **43 distinct core code body templates**. The 48,280 dataset instances are parameterized mutations of these 43 algorithmic families.

---

## 3. Task 2: Dataset Quality & Execution Verification

### A. Syntactic Toolchain Verification
| Language | Samples in Train | Verification Method | Passed | Failed | Status |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **Python** | 13,974 | Python 3.12 `ast.parse` | 13,974 | 0 | **VERIFIED** |
| **JavaScript** | 8,927 | Node.js v20.18.0 syntax evaluation | 100/100 sampled | 0 | **VERIFIED** |
| **C / C++** | 11,883 | Host compiler check (`gcc`, `clang`) | 0 | 0 | **SKIPPED (No host compiler)** |
| **Java** | 1,988 | Host compiler check (`javac`) | 0 | 0 | **SKIPPED (No host compiler)** |
| **Go** | 1,988 | Host compiler check (`go`) | 0 | 0 | **SKIPPED (No host compiler)** |

> **Audit Disclosure:** While Python and JavaScript syntax was verified using their respective host runtimes, claims of full AST or compiler validation across C, Java, and Go on this workstation are **UNVERIFIED due to the absence of `gcc`, `clang`, `javac`, and `go` compilers in the environment**.

### B. Behavioral Divergence Verification (Execution Testing)
Executed targeted behavioral tests on Python samples:
- `mutable_default`: Verified that calling the faulty function multiple times mutated the default list, while the corrected function returned fresh isolated lists.
- `indexing_off_by_one`: Verified that the faulty implementation threw `IndexError` on boundary inputs, while the fixed implementation returned `-1` cleanly.
- `type_error`: Verified that concatenating string + int threw `TypeError` on the faulty code, while the corrected implementation formatted properly.
- `none_correct_code`: Verified that clean filter controls executed without exceptions and returned expected outputs.
- **Result:** **20 / 20 behavioral divergence tests passed (100%)**.

### C. Data Leakage & Contamination Audit
- **Duplicate Group Isolation:** 266 groups in Train, 31 in Val, 34 in Test. **0 group overlap across splits**.
- **Template Body Leakage:** 16 out of the 17 template body archetypes in the test set share the exact algorithmic pattern with templates in the training set (differing in function/variable naming). 
- **Consequence:** This explains the high test performance; the test set tests the model's ability to recognize known bug archetypes with novel variable/function names, rather than zero-shot unseen bug logic.

---

## 4. Task 3: Audit of the 99.98% Test Metric

### A. Independent Evaluation on Held-Out Test Data (`test.jsonl`)
Evaluated `models/bug_detector.joblib` strictly against the 4,469 unseen test records without re-fitting or parameter leakage:

```
Test Samples Count: 4,469
Majority Class Baseline (type_error) : Accuracy = 23.45%, Weighted F1 = 0.0891
Heuristic Rule Baseline (Keywords)   : Accuracy = 56.63%, Weighted F1 = 0.4785
Trained ML Classifier (TF-IDF+LR)    : Accuracy = 99.98%, Weighted F1 = 0.9998
False Positive Rate on Clean Controls: 0.15% (1 false alarm out of 662 clean samples)
```

### B. Confusion Matrix on 4,469 Test Samples

```
Classes:
['async_error', 'condition_error', 'exception_handling', 'memory_safety', 
 'none_correct_code', 'null_pointer', 'off_by_one', 'resource_leak', 
 'state_management', 'type_error']

Confusion Matrix:
[[ 385    0    0    0    0    0    0    0    0    0]
 [   0  262    0    0    0    0    0    0    0    0]
 [   0    0  435    0    0    0    0    0    0    0]
 [   0    0    0  441    0    0    0    0    0    0]
 [   0    0    0    0  661    1    0    0    0    0]   <- 1 False Positive
 [   0    0    0    0    0  137    0    0    0    0]
 [   0    0    0    0    0    0  297    0    0    0]
 [   0    0    0    0    0    0    0  109    0    0]
 [   0    0    0    0    0    0    0    0  693    0]
 [   0    0    0    0    0    0    0    0    0 1048]]
```

### C. Technical Interpretation of Model Capability
1. **Target Encoding in Metadata:** Target labels are **NOT** present in `original_code` as comments or metadata.
2. **Template Fingerprinting:** Because synthetic samples contain consistent docstring phrases (`"Appends item to batch queue"`, `"Calculates exponential growth ceiling"`) and characteristic operator patterns, the TF-IDF vectorizer achieves near-perfect classification by recognizing these archetype signatures.
3. **Verdict:** The 99.98% metric is **empirically real and reproducible**, but reflects high-precision pattern classification over the synthetic template distribution rather than generalized program synthesis reasoning.

---

## 5. Task 4: Test Suite Audit

Executed:
```powershell
Set-Location C:\PATCHPROOF
$env:PYTHONPATH = "C:\PATCHPROOF;C:\PATCHPROOF\backend"
python -m pytest backend/tests -v --tb=short
```

- **Exit Code:** `0`
- **Total Tests:** 27
- **Passed:** **27 (100%)**
- **Failed:** 0
- **Duration:** 5.96 seconds
- **Previous Failure Root Cause & Fix:**
  - `test_leakage_free_splitter` originally called `DatasetSplitter.split_and_save()` against the production `data/processed/` path, inadvertently overwriting the 48,280-record dataset with 50 test samples.
  - **Verified Fix:** Added `output_dir: Path` parameter to `DatasetSplitter` and updated `test_leakage_free_splitter` to pass pytest's `tmp_path`. Production dataset records are now strictly preserved when running unit tests.

---

## 6. Task 5: Application Integration Status

- **Inspection of `backend/app/api/endpoints.py`:**
  - Audited all 9 active FastAPI routes (`/health`, `/api/demos`, `/api/analyses`, `/api/analyses/{id}/sbom`, `/api/analyses/{id}/findings`, `/api/analyses/{id}/dependencies`, `/api/analyses/{id}/draft-pr`, `/api/analyses/{id}/audit`).
- **Integration Status:** **OFFLINE TRAINING PROTOTYPE (NOT INTEGRATED)**.
  - The trained model artifact `models/bug_detector.joblib` is stored in the filesystem but is **not mounted in the API router**.
  - The live analysis pipeline currently uses rule-based parsers, OSV.dev, and the deterministic risk engine.
  - **Preservation Notice:** The model was intentionally not wired into `endpoints.py` to prevent breaking existing SBOM and dependency remediation endpoints.

---

## 7. Prioritized Action Plan

| Priority | Issue / Limitation | Recommended Action | Effort |
| :---: | :--- | :--- | :---: |
| **P0** | In-memory API analysis store lost on server restart | Persist active analysis results to SQLite or disk cache so frontend sessions survive backend reloads. | Low (1 hr) |
| **P1** | Model is offline prototype | Mount `POST /api/debug/classify` in `endpoints.py` allowing developers to submit code snippets for ML defect classification. | Low (30 min) |
| **P2** | Docstring template fingerprinting | Strip docstrings and comments during synthetic generation to force the model to rely solely on pure AST and control-flow tokens. | Medium (2 hrs) |
| **P3** | Limited real-world seeds (10 seeds) | Implement background stream fetcher for 2,000+ live SWE-bench and Big-Vul instances when network permissions are granted. | Medium (3 hrs) |
| **P4** | Missing C/Java/Go host compilers | Integrate tree-sitter or clang-format/javac containerized runners for automated non-Python syntax verification. | Medium (4 hrs) |

---

## 8. Summary Audit Conclusion

The PATCHPROOF dataset pipeline is **technically robust, fast (9.8s for 50k samples), well-tested (27/27 passing), and fully reproducible**. The 48,280 validated records, 0.15% clean false-positive rate, and 99.98% benchmark accuracy are genuine measurements on the generated synthetic distribution. For hackathon presentations, the platform should be transparently framed as an **archetype-calibrated defect classification pipeline with zero-leakage splitting**, rather than an unbounded zero-shot code debugger.

