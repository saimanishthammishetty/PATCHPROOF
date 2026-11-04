# PATCHPROOF — EXPERIMENT M2: INDEPENDENT VALIDATION OF EXPERIMENT M FINDINGS
## Authoritative Verification, Discrepancy Reconciliation, and Empirical Audit

> **Document Version:** 1.0.0 — Authoritative Verification Report  
> **Audit Date:** 2026-11-04  
> **Audited System:** PATCHPROOF AI Code Debugger (`C:\PATCHPROOF`)  
> **Audited Artifact:** `docs/EXPERIMENT_M_DATASET_EXPANSION_PLAN.md`  
> **Production Model Integrity:** SHA-256 `5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20` (VERIFIED INTACT)  
> **Test Dataset Integrity:** SHA-256 `9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d` (VERIFIED INTACT)  
> **Safety Guard Enforced:** `NEVER_MERGE_ACTIVE`  

---

## 1. Executive Verdict

This independent read-only audit conducted an exhaustive verification of every quantitative claim, metric table, split assertion, and architectural recommendation in the Experiment M report (`docs/EXPERIMENT_M_DATASET_EXPANSION_PLAN.md`).

### Summary of Independent Audit Findings

1. **Dataset Accounting Discrepancy Fully Reconciled:**
   - The reported **96,763 records** corresponds strictly to the **Phase 3 (v2)** dataset state archived in `data/processed_v2_backup/` and documented in `data/processed/split_statistics.json` (78,734 train + 9,676 val + 8,353 test = 96,763).
   - The reported **105,537 records** corresponds to the **current active files** on disk in `data/processed/` (86,324 train + 10,860 val + 8,353 test = 105,537). The delta of **8,774 records** consists of `robust_synthetic` samples generated during Experiments J/K that were appended to `train.jsonl` (+7,590) and `val.jsonl` (+1,184).
   - The reported **106,763 records** is the exact grand total including the isolated `robust_heldout_test.jsonl` file (1,226 records).
   - **Critical Accounting Finding:** `split_statistics.json` in `data/processed/` was never re-emitted when robust samples were added; it represents the pre-robust Phase 3 state.
2. **Zero Cross-Split Leakage Confirmed:**
   - Pairwise intersection tests confirmed **0 duplicate record IDs**, **0 identical normalized code snippets**, and **0 overlapping group/template keys** between `train.jsonl`, `val.jsonl`, `test.jsonl`, and `robust_heldout_test.jsonl`. Group isolation was 100% maintained.
3. **Split Deficiency & Language Erasure Verified:**
   - The root-cause diagnosis of `scripts/datasets/split.py` was verified: greedy group allocation filled `train.jsonl` to 80% first, absorbing 100% of all groups for 6 minority defect classes (`api_misuse`, `exception_handling`, `loop_error`, `off_by_one`, `state_management`, and `undefined_behavior`).
   - **New Audit Discovery:** In addition to the 6 missing defect classes, **two entire programming languages are completely missing from `test.jsonl`**: JavaScript (0 samples) and Go (0 samples). `test.jsonl` is 79.3% C, 15.3% Python, and 5.4% Java.
4. **Apples-to-Oranges Metric Invalidation:**
   - In Section 2.6 and Section 5.1 of the Experiment M report, **validation-set metrics for Strategy 5 (10,860 samples)** were contrasted against **test-set metrics for Candidate H1 and Baseline (8,353 samples)**.
   - On the *exact same* validation set, Candidate H1 achieved only **37.08%** bug recall, whereas Strategy 5 achieved **52.60%** bug recall. Strategy 5 did *not* have lower bug recall; comparing Strategy 5 on validation against Candidate H1 on test was an invalid cross-split comparison.
5. **Out-of-Ground-Truth Predictions are Genuine Model Errors:**
   - The Baseline model's 1,059 predictions of `off_by_one` on `test.jsonl` were audited against actual sample contents: 552 were clean code (`none_correct_code`) and 450 were memory safety vulnerabilities (`memory_safety`). They are genuine false alarm and class confusion errors, not missing evaluation labels or loader bugs.

---

## 2. Phase 1: Reconciled Dataset Inventory & Accounting

### 2.1 Complete File-by-File Ledger

Every dataset file in `data/` was audited for exact byte size, line count, and SHA-256 cryptographic hash:

```
+------------------------------------+------------+------------+------------------------------------------------------------------+
| Relative File Path                 | File Bytes | Line Count | SHA-256 Cryptographic Hash                                       |
+------------------------------------+------------+------------+------------------------------------------------------------------+
| data/processed/train.jsonl         | 200,790,230|     86,324 | 6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad |
| data/processed/val.jsonl           |  25,844,509|     10,860 | 935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f |
| data/processed/test.jsonl          |  26,555,716|      8,353 | 9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d |
| data/processed/robust_heldout_...  |   1,400,620|      1,226 | e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1 |
| data/processed/split_statistics.json|        946|        N/A | 97680840f4f4daa5c04df4ec970170a4a8ce885bb3c67530e37bc63d0859560f |
+------------------------------------+------------+------------+------------------------------------------------------------------+
| Active Processed Corpus (Total)    | 254,591,075|    106,763 | —                                                                |
+------------------------------------+------------+------------+------------------------------------------------------------------+
| data/processed_v2_backup/train...  | 191,561,737|     78,734 | d80410b8c682689b099432f865f3a0937a3461ec9c79243da8722253ce35d644 |
| data/processed_v2_backup/val...    |  24,277,471|      9,676 | 0874ef9d4d9be2b5f79a95a8f4c7d0d19688463ae37d1624c965e94b293c66f5 |
| data/processed_v2_backup/test...   |  26,555,716|      8,353 | 9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d |
| data/processed_v2_backup/split_... |        946|        N/A | 97680840f4f4daa5c04df4ec970170a4a8ce885bb3c67530e37bc63d0859560f |
+------------------------------------+------------+------------+------------------------------------------------------------------+
| Phase 3 / v2 Backup Corpus (Total) | 242,394,924|     96,763 | —                                                                |
+------------------------------------+------------+------------+------------------------------------------------------------------+
| data/processed_v1_backup/train...  |  45,065,557|     38,760 | 723ae7d7cb250ed48f95c898c60dc8a4e320f77e69950d87a7ae89d6eef83313 |
| data/processed_v1_backup/val...    |   5,696,841|      5,051 | 3f937a30508bb5da24b42385c3f9153a4794e7722770ae991854c6020556f8f5 |
| data/processed_v1_backup/test...   |   5,466,951|      4,469 | 574117f9bfbc6aa647e62bf0dbf88c3a19da4c64b54e7d17e63b65a58d601b07 |
+------------------------------------+------------+------------+------------------------------------------------------------------+
| Phase 2 / v1 Backup Corpus (Total) |  56,229,349|     48,280 | —                                                                |
+------------------------------------+------------+------------+------------------------------------------------------------------+
| data/raw/big_vul_real_15000.jsonl  |  57,887,045|     15,000 | 44e7eb602b22872ff721a329d479361a9c3ffca2a5370d9a69ee95f368bb3efc |
| data/raw/devign_all.jsonl          |  63,580,053|     27,318 | 5cbfd2c505dfdb7fe1e555ea2ae1cb18cae7d704d9b4b0292ff2fc5e26343354 |
| data/raw/csn_python_10000.jsonl    |  12,617,993|     10,000 | 3d37f8c9fb1d4da1c7bce1f8fce14b8db8f158d6a894a4c6a218f0a055106e57 |
| data/raw/muennighoff_python_bugs...|   2,215,384|      1,000 | 1d9a02204ae34ede8467406ae93bc0c213cb5562d987d605c31758c0c46b6814 |
+------------------------------------+------------+------------+------------------------------------------------------------------+
```

### 2.2 Numerical Reconciliation

```mermaid
flowchart TD
    V1[Phase 2 / v1: 48,280 Samples\n48,274 Synthetic + 6 Seeds] -->|+48,483 Public Benchmark Samples| V2[Phase 3 / v2: 96,763 Samples\nTrain: 78,734 | Val: 9,676 | Test: 8,353]
    V2 -->|+8,774 Robust Synthetic Samples| ACTIVE[Current Active Processed: 105,537 Samples\nTrain: 86,324 | Val: 10,860 | Test: 8,353]
    ACTIVE -->|+1,226 Robust Held-Out| GRAND[Grand Evaluated Total: 106,763 Samples]
```

1. **The 96,763 figure** is the record count of the **v2 frozen dataset** recorded in `data/processed_v2_backup/` and documented in `data/processed/split_statistics.json`:
   $$\text{Train (78,734)} + \text{Val (9,676)} + \text{Test (8,353)} = 96,763$$
2. **The 105,537 figure** is the line count of the **current active splits** in `data/processed/`:
   $$\text{Train (86,324)} + \text{Val (10,860)} + \text{Test (8,353)} = 105,537$$
3. **The 106,763 figure** is the **combined corpus** including the isolated held-out set:
   $$\text{Active Primary (105,537)} + \text{Robust Held-Out (1,226)} = 106,763$$
4. **Origin of the 10,000-sample delta:**
   During Experiments J/K, `scripts/datasets/generate_robust_samples.py` generated exactly 10,000 `robust_synthetic` samples:
   - **7,590 records** were appended to `train.jsonl` ($78,734 + 7,590 = 86,324$).
   - **1,184 records** were appended to `val.jsonl` ($9,676 + 1,184 = 10,860$).
   - **1,226 records** were written to `robust_heldout_test.jsonl`.
   - **0 records** were added to `test.jsonl` (preserving its SHA-256 hash `9aad8de8...` 100% intact).
   - Total: $7,590 + 1,184 + 1,226 = 10,000$.
5. **Denominator Accuracy Audit:**
   - In Section 2.4 of the Experiment M report, the language percentages (57.1% C, 26.3% Python, 11.8% JS, 2.4% Go, 2.4% Java) correctly used the **96,763 denominator** from `split_statistics.json`.
   - On the updated **106,763 corpus**, the true language shares are:
     - C / C++: 57,956 (54.29%)
     - Python: 29,099 (27.26%)
     - JavaScript: 15,070 (14.12%)
     - Go: 2,323 (2.18%)
     - Java: 2,315 (2.17%)

---

## 3. Phase 2: Split Integrity & Cross-Split Leakage Audit

### 3.1 Pairwise Cross-Split Overlap Assertion

To independently verify that no samples, mutant variations, or template clones leaked across splits, a four-way intersection matrix was executed across all active splits:

```
+------------------------------------+------------------+------------------+------------------+
| Split Comparison Pair              | ID Overlap       | Code Overlap     | Group Overlap    |
+------------------------------------+------------------+------------------+------------------+
| `train.jsonl` vs `val.jsonl`       | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) |
| `train.jsonl` vs `test.jsonl`      | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) |
| `train.jsonl` vs `robust_heldout`  | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) |
| `val.jsonl` vs `test.jsonl`        | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) |
| `val.jsonl` vs `robust_heldout`    | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) |
| `test.jsonl` vs `robust_heldout`   | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) | 0 (ZERO LEAKAGE) |
+------------------------------------+------------------+------------------+------------------+
```
*Methodology: `example_id` matching, normalized whitespace-free string hashing, and atomic group key matching (`template_family` or `repository` or `duplicate_group_id`).*

**Finding:** Group-level isolation is **strictly maintained across all 6 split pairs**. No training data, template families, or repositories contaminated validation or test splits.

### 3.2 Intra-File Deduplication Audit
While cross-split leakage is zero, the audit discovered minor **internal code collisions within individual split files**:
- `train.jsonl`: 165 internal code collisions (e.g. `pp-rob-c-3f712ac2f1` and `pp-rob-c-7404feb86f`).
- `val.jsonl`: 68 internal code collisions.
- `test.jsonl`: **0 internal collisions** (8,353 distinct codes).
- `robust_heldout_test.jsonl`: 60 internal code collisions.

*Root Cause:* When the 10,000 robust synthetic samples were generated, internal deduplication was performed within the generation batch, but was not executed across the pre-existing files prior to concatenation. This has zero impact on split isolation, but introduces slight redundancy inside `train.jsonl`.

### 3.3 Complete Class Coverage Matrix Across All 13 Archetypes

```
+----------------------+------------+------------+------------+------------+------------+
| Defect Archetype     | Train      | Val        | Test       | Robust     | Grand Total|
+----------------------+------------+------------+------------+------------+------------+
| none_correct_code    | 32,735     | 4,263      | 3,596      | 0          | 40,594     |
| memory_safety        | 18,135     | 1,825      | 2,431      | 0          | 22,391     |
| type_error           |  2,085     | 1,991      | 1,999      | 594        |  6,669     |
| condition_error      |  5,731     |    99      |   140      | 0          |  5,970     |
| null_pointer         |  4,854     |    15      |    27      | 0          |  4,896     |
| resource_leak        |  2,759     |   563      |   134      | 0          |  3,456     |
| async_error          |  3,805     | 1,062      |    26      | 632        |  5,525     |
| exception_handling   |  1,962     | 1,042      |     0 ⚠️   | 0          |  3,004     |
| off_by_one           |  5,433     |     0 ⚠️   |     0 ⚠️   | 0          |  5,433     |
| loop_error           |  2,008     |     0 ⚠️   |     0 ⚠️   | 0          |  2,008     |
| api_misuse           |  2,567     |     0 ⚠️   |     0 ⚠️   | 0          |  2,567     |
| undefined_behavior   |  2,368     |     0 ⚠️   |     0 ⚠️   | 0          |  2,368     |
| state_management     |  1,882     |     0 ⚠️   |     0 ⚠️   | 0          |  1,882     |
+----------------------+------------+------------+------------+------------+------------+
| Total Samples        | 86,324     | 10,860     | 8,353      | 1,226      | 106,763    |
| Active Classes       | 13 of 13   | 8 of 13    | 7 of 13    | 2 of 13    | 13 of 13   |
+----------------------+------------+------------+------------+------------+------------+
```

### 3.4 Language Erasure in the Test Split
An unexpected discovery of this audit is that **`test.jsonl` completely lacks JavaScript and Go**:

```
+----------------------+------------+------------+------------+------------+------------+
| Language             | Train      | Val        | Test       | Robust     | Grand Total|
+----------------------+------------+------------+------------+------------+------------+
| C / C++              | 47,819     | 3,515      | 6,622      | 0          | 57,956     |
| Python               | 21,858     | 5,365      | 1,282      | 594        | 29,099     |
| JavaScript           | 13,844     |   594      |     0 ⚠️   | 632        | 15,070     |
| Go                   |  1,410     |   913      |     0 ⚠️   | 0          |  2,323     |
| Java                 |  1,393     |   473      |   449      | 0          |  2,315     |
+----------------------+------------+------------+------------+------------+------------+
| Total Samples        | 86,324     | 10,860     | 8,353      | 1,226      | 106,763    |
+----------------------+------------+------------+------------+------------+------------+
```
`test.jsonl` contains 79.28% C, 15.35% Python, and 5.37% Java. A model evaluated on `test.jsonl` is completely unbenchmarked on JavaScript and Go.

---

## 4. Phase 3: Metric Verification & Apples-to-Oranges Resolution

### 4.1 Metric Reproduction on `test.jsonl` (8,353 Samples)

Both the Production Baseline and Candidate H1 were evaluated against `data/processed/test.jsonl` (SHA-256: `9aad8de8...`). The reported metrics in `docs/EXPERIMENT_K_EVALUATION.md` and `docs/EXPERIMENT_M_DATASET_EXPANSION_PLAN.md` were independently verified against `models/experiments/experiment_k/phase_k2_cross_dataset.json`:

```
+------------------------------------+---------------------+---------------------+--------------------+
| Evaluation Metric                  | Production Baseline | Candidate H1        | Verified in File   |
+------------------------------------+---------------------+---------------------+--------------------+
| Overall Test Accuracy              | 42.97% (3,589/8,353)| 42.69% (3,566/8,353)| VERIFIED EXACT     |
| Macro F1-Score                     | 0.1174              | 0.2023              | VERIFIED EXACT     |
| Weighted F1-Score                  | 0.4200              | 0.3752              | VERIFIED EXACT     |
| Bug Detection Recall               | 72.59%              | 98.97%              | VERIFIED EXACT     |
| Clean Code False Positive Rate     | 58.26%              | 63.26%              | VERIFIED EXACT     |
| Big-Vul CVE Recall (1,091 samples) | 53.35% (Acc: 4.12%) | 96.98% (Acc: 50.41%)| VERIFIED EXACT     |
| CodeSearchNet Python Clean Acc     | 49.22% (FPR: 50.78%)| 100.00% (FPR: 0.00%)| VERIFIED EXACT     |
| Expected Calibration Error (ECE)   | 0.1104              | 0.2415              | VERIFIED EXACT     |
+------------------------------------+---------------------+---------------------+--------------------+
```

### 4.2 The Cross-Split Comparison Invalidity

In Section 2.6 and Section 5.1 of the Experiment M report, **Strategy 5 (Dynamic Reliability Fusion)** was reported with:
- Accuracy: 46.00%
- Macro F1: 0.2534
- Clean FPR: 33.78%
- Bug Recall: 52.60%

When these figures were listed adjacent to Candidate H1's test metrics (where H1 had 98.97% bug recall), it created the misleading impression that Strategy 5 suffered from a severe regression in bug recall.

#### Independent Empirical Resolution:
Strategy 5 was evaluated **strictly on `data/processed/val.jsonl` (10,860 samples)**, NOT `test.jsonl`.
Evaluating Candidate H1, Strategy 5, and Baseline on the **exact same validation set** reveals the true picture:

```
+---------------------------+------------+------------+------------+------------+------------+
| Model on VALIDATION SET   | Accuracy   | Macro F1   | Wgt F1     | Bug Recall | Clean FPR  |
| (10,860 Samples)          |            |            |            |            |            |
+---------------------------+------------+------------+------------+------------+------------+
| Production Baseline       | 52.96%     | 0.2125     | 0.5371     | 78.96%     | 29.13%     |
| Candidate H1 (AST-Only)   | 40.61%     | 0.1361     | 0.3058     | 37.08% ⚠️  | 33.71%     |
| Strategy 1 (Structural)   | 40.61%     | 0.1361     | 0.3058     | 37.08%     | 33.71%     |
| Strategy 2 (Lexical)      | 46.20%     | 0.2282     | 0.3874     | 53.15%     | 33.78%     |
| Strategy 3 (Early Fusion) | 40.79%     | 0.1647     | 0.3061     | 43.84%     | 33.29%     |
| Strategy 4 (Late Fusion)  | 45.76%     | 0.2514     | 0.3821     | 52.48%     | 33.87%     |
| Strategy 5 (Dynamic) ⭐   | 46.00%     | 0.2534     | 0.3836     | 52.60% ⭐  | 33.78%     |
+---------------------------+------------+------------+------------+------------+------------+
```
*Source: `models/experiments/experiment_l/phase_l2_results.json`*

#### Key Analytical Conclusions:
1. **Strategy 5 DID NOT regress bug recall:** When compared on the *same validation population*, Strategy 5 increased bug recall from **37.08% (H1) to 52.60% (+15.52 pp)** and Macro F1 from **0.1361 to 0.2534 (+0.1173)**.
2. **Why Candidate H1 had 98.97% recall on test:** On `test.jsonl`, Candidate H1 predicted `memory_safety` on **6,695 out of 8,353 samples (80.15%)**. Predicting the dominant class on 80% of all samples mathematically captures nearly all defects, but produces a disastrous 63.26% false positive rate on clean code and 0.001 recall on format-specifier type errors.
3. **Validation Rule:** Never present validation metrics in the same comparative column as test metrics without explicit subheadings and split labeling.

---

## 5. Phase 4: Label and Prediction Audit

### 5.1 Investigation of the 1,214 Out-of-Ground-Truth Predictions

On `test.jsonl`, the Production Baseline generated 1,214 predictions for classes with zero test support:
- `off_by_one`: 1,059 predictions
- `api_misuse`: 105 predictions
- `undefined_behavior`: 26 predictions
- `exception_handling`: 21 predictions
- `loop_error`: 3 predictions

We audited the exact ground-truth labels and code snippets for all 1,059 `off_by_one` predictions:

```
+------------------------------------+------------------+------------------+
| True Ground-Truth Label            | Sample Count     | Percentage (%)   |
+------------------------------------+------------------+------------------+
| `none_correct_code` (Clean Code)   | 552              | 52.12%           |
| `memory_safety` (Real C Vuln)      | 450              | 42.49%           |
| `resource_leak`                    |  28              |  2.64%           |
| `condition_error`                  |  16              |  1.51%           |
| `async_error`                      |   6              |  0.57%           |
| `type_error`                       |   6              |  0.57%           |
| `null_pointer`                     |   1              |  0.09%           |
+------------------------------------+------------------+------------------+
| Total Out-of-Ground-Truth Preds    | 1,059            | 100.00%          |
+------------------------------------+------------------+------------------+
```

### 5.2 Mechanistic Diagnosis
- **552 Clean Code False Alarms:** In clean C functions, common loop idioms such as `for (i = 0; i < len; i++)` or `p = buf + len - 1` triggered high TF-IDF feature weights for `off_by_one` tokens. The Baseline model falsely flagged benign code as an off-by-one bug.
- **450 Memory Safety Confusion Errors:** Real buffer overflows from Devign/Big-Vul frequently involve boundary checks. The Baseline model misclassified real memory safety defects as `off_by_one`.
- **Verdict:** These predictions are **genuine model misclassifications and false alarms**. They are NOT missing labels, test loader defects, or dataset annotation bugs. Discarding them or relabeling test samples would be fraudulent.

---

## 6. Phase 5: Architecture and Promotion Criteria Review

Every major recommendation in the Experiment M report was scrutinized and classified into one of three rigorous epistemic tiers:

```
+------------------------------------+--------------------------------+-------------------------------------------------------------+
| Recommendation / Claim             | Epistemic Classification       | Evidence Base & Audit Justification                         |
+------------------------------------+--------------------------------+-------------------------------------------------------------+
| 1. Dual-Channel Feature Union      | ✅ Empirically Demonstrated    | Proven in Experiment L2 on 10,860 validation samples.      |
|    (AST Structural + Lexical N-Gram|                                | Macro F1 increased from 0.1361 to 0.2534; JS async F1       |
|    with preserved format tokens)   |                                | restored from 0.00 to 0.6663; parser fallback doubled.       |
| 2. Operational Abstention Gate     | ✅ Empirically Demonstrated    | Proven in Experiment K4 on 8,353 test samples. Selective   |
|    at Confidence tau = 0.70        |    (on current test set)       | accuracy reached 66.31% at tau=0.70 (46.4% coverage) and    |
|                                    |                                | 91.95% at tau=0.90 (13.2% coverage).                        |
| 3. Abstention Accuracy on Novel    | ⚠️ Supported but Not Yet       | While demonstrated on the 7-class test set, behavior on a   |
|    Balanced 13-Class Test Set      |    Demonstrated                | re-stratified 13-class test set requires Experiment N data. |
| 4. Platt / Temperature Scaling     | 🔬 Hypothesis Requiring        | Temperature scaling mathematically minimizes NLL, but      |
|    reducing ECE below 0.06         |    an Experiment               | achieving ECE < 0.06 on unseen 13 classes is a projection. |
| 5. Multi-Objective Stratified      | ⚠️ Supported by Root-Cause     | Mathematical algorithm prevents class starvation, but full  |
|    Group Splitter Implementation   |    Audit                       | execution on the 75k corpus must be validated in Exp N.     |
| 6. BugsInPy & Defects4J Extraction | ⚠️ Supported by Gap Audit       | Audit proves Python & Java defect deficits; format parsing |
|    for Minority Class Balancing    |                                | and multi-class mapping scripts must be tested in Exp N.    |
| 7. Proposed Promotion Gates        | ✅ Governance Specification    | Strict criteria prevent promoting overfitted candidates.   |
+------------------------------------+--------------------------------+-------------------------------------------------------------+
```

---

## 7. Corrected Recommendations for Experiment N

Based on the verified findings of this independent validation, the following corrections must be incorporated into Experiment N:

1. **Re-Stratify the Primary Test Set (High Priority):**
   - The primary test benchmark must not remain starved of 6 defect classes and 2 programming languages.
   - The Multi-Objective Stratified Group Splitter must be executed first to create a balanced, leak-free test split where all 13 defect classes have $\ge 200$ samples and JavaScript, Go, Python, Java, and C are all represented.
2. **Eliminate Apples-to-Oranges Metric Reporting:**
   - Any future ablation report must maintain strict columnar separation between validation-tuned metrics and held-out test metrics.
3. **Separate Linear Model from Selective Prediction in Promotion Gates:**
   - The promotion gate for unthresholded primary test accuracy should be set realistically at $\ge 50.0\%$ (given the 13-class balanced challenge), while the selective prediction gate ($\tau \ge 0.70$) should target $\ge 65.0\%$ precision.
4. **Intra-File Deduplication Pass:**
   - Before model fitting, run a deduplication pass across `train.jsonl` to eliminate the 165 internal code collisions identified in this audit.

---

## 8. Exact Reproduction Commands (Windows CMD / PowerShell)

All empirical numbers in this report can be reproduced using standard Python commands without modifying repository files:

```bash
# 1. Dataset Line Counts and SHA-256 Hashes
python -c "import hashlib; [print(p, hashlib.sha256(open(p, 'rb').read()).hexdigest()) for p in ['models/bug_detector.joblib', 'data/processed/test.jsonl', 'data/processed/train.jsonl', 'data/processed/val.jsonl', 'data/processed/robust_heldout_test.jsonl']]"

# 2. Pairwise Leakage and Overlap Assertion
python -c "import json; splits = {'train': 'data/processed/train.jsonl', 'val': 'data/processed/val.jsonl', 'test': 'data/processed/test.jsonl', 'robust': 'data/processed/robust_heldout_test.jsonl'}; ids = {s: set(json.loads(l)['example_id'] for l in open(p, encoding='utf-8')) for s, p in splits.items()}; print('Cross-split ID overlaps:', [(n1, n2, len(ids[n1] & ids[n2])) for n1 in splits for n2 in splits if n1 < n2])"

# 3. Class by Split Distribution Table
python -c "import json; splits = {'train': 'data/processed/train.jsonl', 'val': 'data/processed/val.jsonl', 'test': 'data/processed/test.jsonl', 'robust': 'data/processed/robust_heldout_test.jsonl'}; counts = {s: {} for s in splits}; [counts[s].__setitem__(json.loads(l)['bug_category'], counts[s].get(json.loads(l)['bug_category'], 0) + 1) for s, p in splits.items() for l in open(p, encoding='utf-8')]; print(json.dumps(counts, indent=2))"

# 4. Validation Set Apples-to-Apples Ablation Comparison (Experiment L2)
python -c "import json; d = json.load(open('models/experiments/experiment_l/phase_l2_results.json')); [print(k, {m: round(v[m], 4) for m in ['accuracy', 'macro_f1', 'weighted_f1', 'bug_detection_recall', 'clean_code_fpr']}) for k, v in d['results'].items()]"

# 5. Abstention Curve and Calibration Reproduction (Experiment K4)
python -c "import json; d = json.load(open('models/experiments/experiment_k/phase_k4_calibration.json')); print('ECE:', d['test_calibration']['expected_calibration_error']); [print(f'tau={i[\"threshold\"]:.2f} Cov={i[\"coverage\"]*100:.2f}% Acc={i[\"selective_accuracy\"]*100:.2f}%') for i in d['test_selective_curve'] if i['threshold'] in [0.35, 0.50, 0.70, 0.90]]"
```

---

## 9. Protected Artifact Integrity Confirmation

In strict compliance with the safety directives, all protected files were re-verified at the completion of this audit:

```
+------------------------------------+------------------------------------------------------------------+-------------------+
| Protected File Path                | Verified SHA-256 Cryptographic Hash                              | State Post-Audit  |
+------------------------------------+------------------------------------------------------------------+-------------------+
| models/bug_detector.joblib         | 5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20 | VERIFIED INTACT   |
| data/processed/test.jsonl          | 9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d | VERIFIED INTACT   |
| backend/app/main.py                | NEVER_MERGE_ACTIVE Enforcement Verified                          | VERIFIED INTACT   |
+------------------------------------+------------------------------------------------------------------+-------------------+
```

- **Zero Training Operations Conducted:** Confirmed.
- **Zero Dataset Downloads Executed:** Confirmed.
- **Zero Existing Experiments (A through M) Overwritten:** Confirmed.
- **Files Created:** Only `docs/EXPERIMENT_M2_INDEPENDENT_VALIDATION.md`.
- **Active Production Server:** Uninterrupted on port 8000.

---
*Report Author: Antigravity Autonomous Research Harness*  
*Delivery Document: `docs/EXPERIMENT_M2_INDEPENDENT_VALIDATION.md`*  
*Repository: `C:\PATCHPROOF`*
