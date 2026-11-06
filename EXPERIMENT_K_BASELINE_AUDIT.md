# PATCHPROOF — Experiment K Baseline Audit Report

> **Document:** `EXPERIMENT_K_BASELINE_AUDIT.md`
> **Date:** 2026-11-05
> **Status:** AUDIT COMPLETE — PHASE 0 VERIFIED
> **Safety Invariants:** `NEVER_MERGE_ACTIVE` strictly enforced; zero production artifacts overwritten.

---

## 1. Executive Summary

This document establishes the empirical ground-truth baseline for **Experiment K** in accordance with PATCHPROOF's strict experimentation and safety guidelines. Every metric, file path, checksum, and class distribution documented below has been verified directly against the live repository artifacts and active runtime environment.

### Core Audit Outcomes:
1. **Taxonomy Verification:** The 13 canonical defect classes are firmly established and verified in `models/bug_detector.joblib` and `backend/app/services/debug_service.py`.
2. **Dataset Audit:** The four official dataset splits (`train.jsonl`, `val.jsonl`, `test.jsonl`, and `robust_heldout_test.jsonl`) contain 106,763 total samples across five programming languages (C, Python, JavaScript, Go, Java).
3. **Severe Split Asymmetry Discovered:** While `train.jsonl` covers all 13 classes, `val.jsonl` contains only 8 classes (missing 5), `test.jsonl` contains only 7 classes (missing 6), and `robust_heldout_test.jsonl` contains only 2 classes (missing 11).
4. **Live API Integration:** The baseline model (`models/bug_detector.joblib`, SHA-256: `5f93bba9ce...`) is actively loaded by `DebugService` and exposed via `/api/debug/code`. It must remain strictly read-only and preserved throughout all experimental phases.
5. **Git & Workspace State:** All 17 modified working-tree files (including the newly polished enterprise frontend) and the untracked `presentations/` directory have been verified and preserved.
6. **Dedicated Working Directory:** Created isolated `data/experiments/experiment_k/` without altering or overwriting existing experiments.

---

## 2. Canonical 13-Class Defect Taxonomy

The PATCHPROOF defect detection pipeline classifies source code into exactly 13 mutually exclusive defect categories:

| # | Class Identifier | Super-Category | Severity | Scope & Definition |
|---|---|---|---|---|
| 1 | `none_correct_code` | Benign | INFO | Clean, valid code containing no known software defects or security vulnerabilities. |
| 2 | `memory_safety` | Memory | CRITICAL | Spatial or temporal memory corruption (buffer overflows, use-after-free, double-free, dangling pointers, heap out-of-bounds). |
| 3 | `type_error` | Types & Format | MEDIUM | Type mismatch, incompatible operands, format string/specifier mismatches (e.g. `%d` on a `long`, string concatenated to integer). |
| 4 | `null_pointer` | Pointer Dereference | HIGH | Dereferencing null/nil/None pointers, invoking methods or accessing attributes on unverified null objects. |
| 5 | `resource_leak` | Lifecycle | HIGH | Failure to release acquired system resources (file descriptors, sockets, database handles, heap allocations) across all return paths. |
| 6 | `condition_error` | Logic & Control | MEDIUM | Flawed conditional branching, inverted boundary conditions, missing validation logic, incorrect boolean operators. |
| 7 | `async_error` | Concurrency | MEDIUM | Unhandled Promise rejections, missing `await` on asynchronous operations, async race conditions, unsafe channel operations. |
| 8 | `exception_handling` | Error Handling | LOW | Bare `except:` clauses, silently swallowed critical exceptions, improper catch blocks masking system interrupts. |
| 9 | `loop_error` | Logic & Control | HIGH | Infinite loops, broken termination criteria, improper iterator increment/decrement, off-schedule break conditions. |
| 10 | `off_by_one` | Logic & Control | MEDIUM | Fencepost errors, indexing with `index <= len` instead of `< len`, incorrect slice bounds, `range(len + 1)` indexing. |
| 11 | `api_misuse` | API Contract | LOW | Mutable default arguments in Python, invalid API call order, contract violations, improper object initialization. |
| 12 | `state_management` | Concurrency | MEDIUM | Direct state mutations in concurrent/reactive state machines, unsynchronized shared global variables, re-entrancy bugs. |
| 13 | `undefined_behavior` | Runtime Safety | HIGH | Reading uninitialized stack/heap memory, integer overflow resulting in C-standard undefined behavior, shifting beyond bit-width. |

---

## 3. Dataset Audit & Provenance

### 3.1 Dataset Split Files & Checksums

| Split File | Path | Sample Count | File Size (Bytes) | SHA-256 Checksum |
|---|---|---:|---:|---|
| **Train** | `data/processed/train.jsonl` | 86,324 | 148,879,531 | `6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad` |
| **Validation** | `data/processed/val.jsonl` | 10,860 | 18,745,861 | `935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f` |
| **Held-Out Test** | `data/processed/test.jsonl` | 8,353 | 14,481,421 | `9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d` |
| **Robust Test** | `data/processed/robust_heldout_test.jsonl` | 1,226 | 2,130,557 | `e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1` |
| **Total** | | **106,763** | **184,237,370** | |

### 3.2 Exact Class Distributions Across Splits

```
+--------------------+---------------+---------------+---------------+---------------+
| Defect Category    | Train (86.3k) | Val (10.9k)   | Test (8.4k)   | Robust (1.2k) |
+--------------------+---------------+---------------+---------------+---------------+
| none_correct_code  | 32,735 (37.9%)|  4,263 (39.3%)|  3,596 (43.1%)|     0 ( 0.0%) |
| memory_safety      | 18,135 (21.0%)|  1,825 (16.8%)|  2,431 (29.1%)|     0 ( 0.0%) |
| condition_error    |  5,731 ( 6.6%)|     99 ( 0.9%)|    140 ( 1.7%)|     0 ( 0.0%) |
| off_by_one         |  5,433 ( 6.3%)|      0 ( 0.0%)|      0 ( 0.0%)|     0 ( 0.0%) |
| null_pointer       |  4,854 ( 5.6%)|     15 ( 0.1%)|     27 ( 0.3%)|     0 ( 0.0%) |
| async_error        |  3,805 ( 4.4%)|  1,062 ( 9.8%)|     26 ( 0.3%)|   632 (51.5%) |
| resource_leak      |  2,759 ( 3.2%)|    563 ( 5.2%)|    134 ( 1.6%)|     0 ( 0.0%) |
| api_misuse         |  2,567 ( 3.0%)|      0 ( 0.0%)|      0 ( 0.0%)|     0 ( 0.0%) |
| undefined_behavior |  2,368 ( 2.7%)|      0 ( 0.0%)|      0 ( 0.0%)|     0 ( 0.0%) |
| type_error         |  2,085 ( 2.4%)|  1,991 (18.3%)|  1,999 (23.9%)|   594 (48.5%) |
| loop_error         |  2,008 ( 2.3%)|      0 ( 0.0%)|      0 ( 0.0%)|     0 ( 0.0%) |
| exception_handling |  1,962 ( 2.3%)|  1,042 ( 9.6%)|      0 ( 0.0%)|     0 ( 0.0%) |
| state_management   |  1,882 ( 2.2%)|      0 ( 0.0%)|      0 ( 0.0%)|     0 ( 0.0%) |
+--------------------+---------------+---------------+---------------+---------------+
| Total Count        | 86,324        | 10,860        | 8,353         | 1,226         |
| Represented Classes| 13 Classes    | 8 Classes     | 7 Classes     | 2 Classes     |
| Missing Classes    | 0 Classes     | 5 Classes     | 6 Classes     | 11 Classes    |
+--------------------+---------------+---------------+---------------+---------------+
```

### 3.3 Key Findings on Dataset Quality & Leakage
1. **Zero Sample-Level Overlap:** Exact content-hash deduplication confirms 0 duplicate snippets between `train.jsonl` and `test.jsonl`.
2. **Template Cluster Partitioning:** The original data generation pipeline partitioned records grouped by `template_family`. Small template families for `api_misuse`, `loop_error`, `off_by_one`, and `state_management` were clustered entirely into `train.jsonl`, resulting in 0 test-set examples for these classes.
3. **Language Imbalance:** C represents 55.4% of `train.jsonl` and 79.3% of `test.jsonl`. Go and Java are underrepresented (<2% each in training).

```
+--------------------+---------------+---------------+---------------+---------------+
| Language           | Train (86.3k) | Val (10.9k)   | Test (8.4k)   | Robust (1.2k) |
+--------------------+---------------+---------------+---------------+---------------+
| c                  | 47,819 (55.4%)|  3,515 (32.4%)|  6,622 (79.3%)|     0 ( 0.0%) |
| python             | 21,858 (25.3%)|  5,365 (49.4%)|  1,282 (15.3%)|   594 (48.5%) |
| javascript         | 13,844 (16.0%)|    594 ( 5.5%)|      0 ( 0.0%)|   632 (51.5%) |
| go                 |  1,410 ( 1.6%)|    913 ( 8.4%)|      0 ( 0.0%)|     0 ( 0.0%) |
| java               |  1,393 ( 1.6%)|    473 ( 4.4%)|    449 ( 5.4%)|     0 ( 0.0%) |
+--------------------+---------------+---------------+---------------+---------------+
```

---

## 4. Current Baseline Model & Pipeline Architecture

### 4.1 Production Model Identity
- **Primary Model File:** `models/bug_detector.joblib`
- **Backup Baseline File:** `models/bug_detector_v1_baseline.joblib`
- **File Size:** 622,564 bytes
- **SHA-256 Checksum:** `5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20` (identical in both files)

### 4.2 Pipeline Implementation Details
Inspected directly via `joblib.load('models/bug_detector.joblib')`:

```python
Pipeline(steps=[
    ('tfidf', TfidfVectorizer(
        analyzer='word',
        ngram_range=(1, 2),
        max_features=4000,
        sublinear_tf=True,
        token_pattern=r'(?u)\b\w+\b|[<>=!+\-*/&|~^%]+'
    )),
    ('clf', LogisticRegression(
        C=1.0,
        class_weight='balanced',
        max_iter=500,
        random_state=42
    ))
])
```

- **Classes Fitted in Classifier:** 13 classes (`api_misuse`, `async_error`, `condition_error`, `exception_handling`, `loop_error`, `memory_safety`, `none_correct_code`, `null_pointer`, `off_by_one`, `resource_leak`, `state_management`, `type_error`, `undefined_behavior`).
- **Feature Space:** 4,000 sublinear TF-IDF features capturing lexical tokens and multi-character operators (`==`, `!=`, `<=`, `>=`, `&&`, `||`, `->`, etc.).

### 4.3 Training & Evaluation Scripts
- **Training Script:** `scripts/training/train.py`
  - Defines `MLCodeBugModel` (Phase 2 baseline) and `CandidateBugModel` (Phase 3 multi-scale feature union word+char).
  - Enforces loading only from `data/processed/train.jsonl` and `val.jsonl`.
- **Evaluation Script:** `scripts/training/evaluate.py`
  - Evaluates models on `data/processed/test.jsonl`.
  - Computes accuracy, weighted F1, clean code false positive rate (`none_correct_code` FPR), and breakdowns by language and source dataset.

---

## 5. Live API Integration Status

The baseline model is **DIRECTLY INTEGRATED INTO THE LIVE PRODUCTION API**:

- **Service Module:** `backend/app/services/debug_service.py`
  - Line 13: `MODEL_PATH = Path("C:/PATCHPROOF/models/bug_detector.joblib")`
  - Defines `_MODEL_CACHE` for thread-safe singleton model inference.
  - Performs keyword and AST heuristics before falling back to the ML pipeline.
- **API Endpoint:** `backend/app/api/endpoints.py`
  - Route: `POST /api/debug/code` (Line 331) invokes `DebugService.analyze_code(request)`.
  - Consumed live by the frontend's **AI Code Debugger** tab (`frontend/src/components/DebuggerTab.tsx`).

> [!IMPORTANT]
> **Safety Boundary:** Because `models/bug_detector.joblib` powers live user interactions in the application, it must NEVER be modified or overwritten during experiments. All Experiment K candidate models must be trained and evaluated strictly within isolated experimental directories (`data/experiments/experiment_k/` and `models/experiments/experiment_k/`).

---

## 6. Git Status & Preservation of Uncommitted Work

At the time of this audit, `git status` reveals 17 modified files and 1 untracked directory:

```
Changes not staged for commit:
  modified:   backend/app/services/remediation_service.py
  modified:   docs/hackathon_readiness_test_results.json
  modified:   frontend/index.html
  modified:   frontend/src/App.tsx
  modified:   frontend/src/components/AuditTab.tsx
  modified:   frontend/src/components/DashboardTab.tsx
  modified:   frontend/src/components/DebuggerTab.tsx
  modified:   frontend/src/components/DraftPRModal.tsx
  modified:   frontend/src/components/Navbar.tsx
  modified:   frontend/src/components/PipelineProgress.tsx
  modified:   frontend/src/components/RemediationTab.tsx
  modified:   frontend/src/components/RiskEngineTab.tsx
  modified:   frontend/src/components/SBOMTab.tsx
  modified:   frontend/src/components/SecretsTab.tsx
  modified:   frontend/src/components/VulnerabilitiesTab.tsx
  modified:   frontend/src/index.css
  modified:   frontend/tailwind.config.js

Untracked files:
  presentations/
```

- **Frontend Integrity:** Verified with `npm run build` (1,602 modules, 0 errors, built in 3.15s).
- **Whitespace / Git Check:** Verified with `git diff --check` (0 errors).
- **Preservation Commitment:** None of these uncommitted modifications will be reverted, reset, or modified during Experiment K.

---

## 7. Experiment K Isolation & Directory Setup

To ensure strict preservation of all existing experiments (including `models/experiments/experiment_f` through `experiment_l` and `data/experiments/experiment_n2*`):

- **New Working Data Directory:** `data/experiments/experiment_k/` (CREATED)
- **Designated Model Storage:** `models/experiments/experiment_k/` (EXISTING ARTIFACTS PRESERVED)
- **Designated Scripts:** `scripts/experiments/experiment_k/` (EXISTING SCRIPTS PRESERVED)

All generated artifacts, candidate datasets, source manifests, and validation logs for the 10,000-sample acquisition will be written exclusively into `data/experiments/experiment_k/`.

---

## 8. Phase 0 Audit Sign-Off

Phase 0 is complete and verified:
- [x] 13 defect classes confirmed from source of truth.
- [x] All 4 dataset splits inspected, hashed, and counted.
- [x] Baseline model architecture and hyperparameters verified.
- [x] Live API integration verified (`backend/app/services/debug_service.py`).
- [x] Working tree clean of git-check errors and preserved.
- [x] Working directory `data/experiments/experiment_k/` initialized.

Ready to proceed to **PHASE 1 — DATASET ACQUISITION**.
