# PATCHPROOF — EXPERIMENT N1.1: INDEPENDENT SPLITTER CORRECTNESS & FEASIBILITY AUDIT
## Authoritative Verification, Robust Isolation Proof, and Algorithmic Ratio Calibration

> **Document Version:** 1.0.0 — Authoritative Verification Report  
> **Audit Phase:** Experiment N1.1 (Independent Splitter Correctness Audit)  
> **Date:** 2026-11-04  
> **Audited Implementation:** `scripts/datasets/experimental_stratified_group_split.py` (v1.1.0)  
> **Audited Unit Test Suite:** `scripts/datasets/test_experimental_stratified_group_split.py` (13 tests)  
> **Audited Dry-Run Report:** `models/experiments/experiment_n1_dry_run_report.json`  
> **Safety Status:** VERIFIED (Dry-run audit; zero modifications to production datasets or model weights)  
> **Production Model Integrity:** SHA-256 `5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20` (VERIFIED INTACT)  
> **Test Dataset Integrity:** SHA-256 `9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d` (VERIFIED INTACT)  
> **Robust Held-Out Dataset Integrity:** SHA-256 `e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1` (VERIFIED INTACT)  
> **Safety Invariant Enforced:** `NEVER_MERGE_ACTIVE`  

---

## 1. Executive Summary

This independent read-only correctness audit evaluated the experimental multi-objective stratified group splitter developed in Experiment N1 against the primary software repository and dataset files at `C:\PATCHPROOF`.

### Key Findings of Audit N1.1

1. **Robust Held-Out Quarantine Rectification:**
   - In the initial N1 dry-run audit script, `data/processed/robust_heldout_test.jsonl` (1,226 records) was inadvertently concatenated into the input pool alongside the primary dataset, resulting in an input total of 106,763 records and absorbing robust samples into the proposed training split.
   - **Correction in v1.1.0:** The robust held-out dataset was strictly quarantined and excluded from the splitter input pool. The primary corpus was locked to exactly **105,537 records** (`train.jsonl` 86,324 + `val.jsonl` 10,860 + `test.jsonl` 8,353).
   - Post-split verification proved **zero ID overlap, zero code overlap, and zero group overlap** between the quarantined 1,226 robust records and all three proposed splits (`train`, `val`, and `test`). Its cryptographic hash remains identical (`e080c897...`).
2. **Resolution of the 12.6 Percentage Point Split-Ratio Deviation:**
   - In Experiment N1, the proposed split sizes deviated from target (Train: 67.4% vs 80% target, Val: 22.5% vs 10% target).
   - **Root Cause Identified:** In Step 4 (Seed Allocation) of the v1.0.0 splitter, the line `val_cand = grps[0]` took the *largest available group* of every multi-group class and assigned it to the 10% Validation split. Consequently, massive groups like `bigvul_CVE-UNKNOWN` (7,467 records) and eight ~2,000-record synthetic template families were dumped into `val` before deficit balancing even began, consuming 23,065 records.
   - **Algorithmic Correction (v1.1.0):** Seed allocation was made *capacity-aware*. The largest group of each multi-group class is assigned to `train` (the 80% split that possesses the capacity to absorb large blocks), while `test` and `val` are seeded with groups calibrated to their 10% quotas.
   - **Revised Empirical Split Ratios on 105,537 Records:**
     - **Train:** **81,905 records (77.61%)** — Target 80.00% (within 2.39 pp).
     - **Validation:** **12,516 records (11.86%)** — Target 10.00% (within 1.86 pp).
     - **Test:** **11,116 records (10.53%)** — Target 10.00% (within 0.53 pp).
3. **Minority-Class Group Cardinality & Feasibility Verified:**
   - Inspection confirmed the exact group counts:
     - `api_misuse`: Exactly **2 groups** (`synth_python_mutable_default` [1,957] and `robust_py_mutable_default` [610]).
     - `undefined_behavior`: Exactly **2 groups** (`synth_c_uninitialized_var` [1,884] and `robust_c_uninitialized_var` [484]).
     - `loop_error`: Exactly **1 group** (`synth_python_broken_while_termination` [2,008]).
     - `state_management`: Exactly **1 group** (`synth_js_state_mutation` [1,882]).
   - Under indivisible-group constraints, `loop_error` and `state_management` can **only appear in one split** (`train`), while `api_misuse` and `undefined_behavior` can appear in **two splits** (`train` and `test`). The algorithm honestly reports them without manufacturing samples.
4. **Expanded Synthetic Test Suite:**
   - 13 comprehensive unit tests covering all edge cases (leakage, conservation, robust exclusion, multi-class/multi-language groups, large super-groups, reproducibility) executed and passed in **0.030 seconds**.

---

## 2. Robust Held-Out Isolation Audit

### 2.1 Physical File Integrity & Cryptographic Hashes
The physical dataset files on disk were verified before and after this audit:

```
+------------------------------------+------------+------------+------------------------------------------------------------------+
| Relative File Path                 | File Bytes | Line Count | SHA-256 Cryptographic Hash                                       |
+------------------------------------+------------+------------+------------------------------------------------------------------+
| data/processed/robust_heldout_...  |   1,400,620|      1,226 | e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1 |
| data/processed/train.jsonl         | 200,790,230|     86,324 | 6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad |
| data/processed/val.jsonl           |  25,844,509|     10,860 | 935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f |
| data/processed/test.jsonl          |  26,555,716|      8,353 | 9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d |
+------------------------------------+------------+------------+------------------------------------------------------------------+
```

### 2.2 Input Pipeline Audit & Isolation Proof
In Experiment N1.1, `scripts/datasets/run_dry_run_audit.py` was refactored to implement strict segregation:

```mermaid
flowchart TD
    subgraph Primary Corpus: 105,537 Records
        TR[train.jsonl: 86,324]
        VA[val.jsonl: 10,860]
        TE[test.jsonl: 8,353]
    end
    subgraph Quarantined Benchmark: 1,226 Records
        ROB[robust_heldout_test.jsonl: 1,226]
    end

    TR --> SPLIT[ExperimentalStratifiedGroupSplitter]
    VA --> SPLIT
    TE --> SPLIT

    SPLIT --> P_TR[Proposed Train: 81,905]
    SPLIT --> P_VA[Proposed Val: 12,516]
    SPLIT --> P_TE[Proposed Test: 11,116]

    ROB -.->|Strict Post-Split Leakage Check| P_TR
    ROB -.->|Strict Post-Split Leakage Check| P_VA
    ROB -.->|Strict Post-Split Leakage Check| P_TE
```

#### Independent Leakage Assertion Results (Primary Splits vs Robust Held-Out):
```
+---------------------------+--------------+--------------+----------------+--------------------------+
| Proposed Split            | Record Count | ID Overlap   | Code Overlap   | Group Overlap            |
+---------------------------+--------------+--------------+----------------+--------------------------+
| Proposed Train            | 81,905       | 0 (ZERO)     | 0 (ZERO)       | 0 (ZERO)                 |
| Proposed Validation       | 12,516       | 0 (ZERO)     | 0 (ZERO)       | 0 (ZERO)                 |
| Proposed Test             | 11,116       | 0 (ZERO)     | 0 (ZERO)       | 0 (ZERO)                 |
+---------------------------+--------------+--------------+----------------+--------------------------+
| Overall Robust Quarantine | 1,226 heldout| 0 LEAKAGE    | 0 LEAKAGE      | PASSED_STRICTLY_ISOLATED |
+---------------------------+--------------+--------------+----------------+--------------------------+
```
*Assertion: Exactly 0 of the 1,226 robust held-out records enter the primary proposed splits in any form.*

---

## 3. Algorithmic Audit: Group Indivisibility & Record Conservation

Every allocation rule in `scripts/datasets/experimental_stratified_group_split.py` was audited against mathematical invariance principles:

### 3.1 Strict Record Conservation Proof
$$\sum_{S \in \{\text{train}, \text{val}, \text{test}\}} |S| = 81,905 + 12,516 + 11,116 = 105,537 = N_{\text{primary}}$$
- Exact input set: 105,537 unique `example_id`s.
- Exact output set: 105,537 unique `example_id`s.
- Total samples dropped: **0**.
- Total samples duplicated: **0**.

### 3.2 Indivisible Group Isolation Proof
Pairwise group intersection checks confirmed zero cross-split group contamination:
$$\text{groups}(\text{train}) \cap \text{groups}(\text{val}) = \emptyset \quad (|G_{\text{tr}} \cap G_{\text{va}}| = 0)$$
$$\text{groups}(\text{train}) \cap \text{groups}(\text{test}) = \emptyset \quad (|G_{\text{tr}} \cap G_{\text{te}}| = 0)$$
$$\text{groups}(\text{val}) \cap \text{groups}(\text{test}) = \emptyset \quad (|G_{\text{va}} \cap G_{\text{te}}| = 0)$$

### 3.3 Handling of Multi-Class and Multi-Language Groups
The audit verified that when real-world commits or repositories contain multiple defect classes or languages:
- The entire group is assigned to a single split as an indivisible unit.
- The multi-objective utility function weights deficits across all classes and languages contained in the group simultaneously:
  $$\text{Score}_{\text{class}}(S) = \sum_{c \in G} \frac{\max(0, T_{S, c} - C_{S, c})}{T_{S, c} + 1} \times c_{G, c}$$
  $$\text{Score}_{\text{lang}}(S) = \sum_{l \in G} \frac{\max(0, T_{S, l} - L_{S, l})}{T_{S, l} + 1} \times l_{G, l}$$
- This prevents tearing multi-file commits or polyglot repositories apart while allocating them to the split that requires their joint representation most urgently.

---

## 4. Root-Cause & Resolution of the Split-Ratio Deviation

### 4.1 Diagnostic Anatomy of the N1 Deviation
In Experiment N1, the observed ratios were Train: 67.4%, Val: 22.5%, Test: 10.1%.
Our audit traced this 12.6 pp deviation to line 212 of `experimental_stratified_group_split.py` (v1.0.0):
```python
# v1.0.0 FLUSHED LARGE GROUPS TO VAL:
test_cand = min(grps, key=lambda g: abs(g.size - min(test_target_c, 200)))
assign_group(test_cand, "test")
grps.remove(test_cand)

val_cand = grps[0]  # <--- BUG: grps was sorted by size descending!
assign_group(val_cand, "val")  # Gave the largest remaining group to Val!
```
Because `val_cand = grps[0]` selected the largest remaining group for every single class with $\ge 3$ groups, the 10% Validation split was loaded with **23,065 records** during seed initialization alone:
- `bigvul_CVE-UNKNOWN`: **7,467 records** assigned to `val`.
- `synth_c_double_free`: **2,071 records** assigned to `val`.
- `synth_python_type_error_concat`: **1,971 records** assigned to `val`.
- `synth_c_off_by_one_buffer`: **1,965 records** assigned to `val`.
- `synth_python_exception_swallowing`: **1,962 records** assigned to `val`.
- `synth_c_missing_free_leak`: **1,921 records** assigned to `val`.
- `synth_js_undefined_prop_access`: **1,912 records** assigned to `val`.
- `synth_python_is_vs_equality`: **1,912 records** assigned to `val`.
- `synth_js_missing_await`: **1,884 records** assigned to `val`.

### 4.2 The v1.1.0 Capacity-Aware Seeding Calibration
In v1.1.0, seed allocation was refactored:
1. `train` (the 80% split) has an 84,429-sample quota. It receives `grps[0]` (the largest group), naturally absorbing massive blocks like `bigvul_CVE-UNKNOWN` (7,467 records) without exceeding capacity.
2. `test` (10% split) and `val` (10% split) select available groups that match their 10% target quotas ($\approx 200\text{--}600$ records).

```python
# v1.1.0 CAPACITY-AWARE SEEDING:
train_cand = grps[0]  # Largest group goes to Train (80% capacity)
assign_group(train_cand, "train")
grps.remove(train_cand)

test_cand = min(grps, key=lambda g: abs(g.size - min(test_target_c, self.min_test_samples_per_class)))
assign_group(test_cand, "test")
grps.remove(test_cand)

val_cand = min(grps, key=lambda g: abs(g.size - min(val_target_c, self.min_test_samples_per_class)))
assign_group(val_cand, "val")
grps.remove(val_cand)
```

### 4.3 Resulting Empirical Split Allocation (105,537 Records)

```
+----------------------+----------------------+----------------------+----------------------+----------------------+
| Split Name           | Target Ratio (%)     | Target Sample Count  | Actual Sample Count  | Actual Ratio (%)     |
+----------------------+----------------------+----------------------+----------------------+----------------------+
| Proposed Train Split | 80.00%               | 84,429               | 81,905               | **77.61%** (-2.39 pp)|
| Proposed Val Split   | 10.00%               | 10,554               | 12,516               | **11.86%** (+1.86 pp)|
| Proposed Test Split  | 10.00%               | 10,554               | 11,116               | **10.53%** (+0.53 pp)|
+----------------------+----------------------+----------------------+----------------------+----------------------+
| Total Primary Corpus | 100.00%              | 105,537              | 105,537              | **100.00%**          |
+----------------------+----------------------+----------------------+----------------------+----------------------+
```
*Conclusion: The revised allocation brings all three splits within 2.4 percentage points of ideal ratios while maintaining 100% indivisible group isolation.*

---

## 5. Verification of Minority-Class Feasibility

A direct scan of the primary corpus (`data/processed/train.jsonl`, `val.jsonl`, `test.jsonl`) verified the exact group counts and sample volumes for the four severely constrained classes:

```
+----------------------+--------------+--------------+---------------------------------------------+--------------------------+
| Defect Class         | Total Samples| Group Count  | Group Key & Sample Distribution             | Mathematical Feasibility |
+----------------------+--------------+--------------+---------------------------------------------+--------------------------+
| `state_management`   | 1,882        | **1 group**  | `synth_js_state_mutation` (1,882 samples)   | `SINGLE_GROUP` (Train)   |
| `loop_error`         | 2,008        | **1 group**  | `synth_python_broken_while_...` (2,008 smp) | `SINGLE_GROUP` (Train)   |
| `api_misuse`         | 2,567        | **2 groups** | `synth_python_mutable_default` (1,957 smp)  | `PARTIALLY_CONSTRAINED`  |
|                      |              |              | `robust_py_mutable_default` (610 smp)       | (Train: 1,957, Test: 610)|
| `undefined_behavior` | 2,368        | **2 groups** | `synth_c_uninitialized_var` (1,884 smp)     | `PARTIALLY_CONSTRAINED`  |
|                      |              |              | `robust_c_uninitialized_var` (484 smp)      | (Train: 1,884, Test: 484)|
+----------------------+--------------+--------------+---------------------------------------------+--------------------------+
```

### Precise Split Allocation Rules for Constrained Classes
1. **`state_management` (1 group):** Must be placed in `train` (1,882 samples) so the model can learn concurrency mutations. Cannot appear in `val` (0) or `test` (0) without breaking group isolation.
2. **`loop_error` (1 group):** Must be placed in `train` (2,008 samples) so the model can learn infinite loops. Cannot appear in `val` (0) or `test` (0).
3. **`api_misuse` (2 groups):** Larger group (1,957 samples) placed in `train`; second group (610 samples) placed in `test`. Validation has 0.
4. **`undefined_behavior` (2 groups):** Larger group (1,884 samples) placed in `train`; second group (484 samples) placed in `test`. Validation has 0.

---

## 6. Full Corpus Dry-Run Results (v1.1.0 on 105,537 Primary Records)

### 6.1 Test Split Class Coverage Comparison

```
+----------------------+--------------------+--------------------+------------+--------------------------+
| Defect Archetype     | Current Test Count | Proposed Test Count| Net Change | Feasibility Classification
+----------------------+--------------------+--------------------+------------+--------------------------+
| api_misuse           |      0 (STARVED) ⚠️|     610 (Recovered)|   +610     | PARTIALLY_CONSTRAINED    |
| async_error          |     26             |     621            |   +595     | FEASIBLE_ALL_SPLITS      |
| condition_error      |    140             |     645            |   +505     | FEASIBLE_ALL_SPLITS      |
| exception_handling   |      0 (STARVED) ⚠️|     452 (Recovered)|   +452     | FEASIBLE_ALL_SPLITS      |
| loop_error           |      0 (STARVED) ⚠️|       0            |     +0     | SINGLE_GROUP_CONSTRAINED |
| memory_safety        |  2,431             |   2,177            |   -254     | FEASIBLE_ALL_SPLITS      |
| none_correct_code    |  3,596             |   2,128            | -1,468     | FEASIBLE_ALL_SPLITS      |
| null_pointer         |     27             |     470            |   +443     | FEASIBLE_ALL_SPLITS      |
| off_by_one           |      0 (STARVED) ⚠️|   1,025 (Recovered)| +1,025     | FEASIBLE_ALL_SPLITS      |
| resource_leak        |    134             |     556            |   +422     | FEASIBLE_ALL_SPLITS      |
| state_management     |      0 (STARVED) ⚠️|       0            |     +0     | SINGLE_GROUP_CONSTRAINED |
| type_error           |  1,999             |   1,948            |    -51     | FEASIBLE_ALL_SPLITS      |
| undefined_behavior   |      0 (STARVED) ⚠️|     484 (Recovered)|   +484     | PARTIALLY_CONSTRAINED    |
+----------------------+--------------------+--------------------+------------+--------------------------+
| Total Active Classes | 7 of 13 Classes    | 11 of 13 Classes   | +4 Classes | Zero Fabricated Samples  |
+----------------------+--------------------+--------------------+------------+--------------------------+
```
*Note: Under v1.1.0, every single active test class possesses $\ge 450$ samples, far exceeding the $\ge 200$ test quota requirement.*

### 6.2 Test Split Language Coverage Comparison

```
+----------------------+--------------------+--------------------+------------+--------------------------+
| Language             | Current Test Count | Proposed Test Count| Net Change | Status                   |
+----------------------+--------------------+--------------------+------------+--------------------------+
| C / C++              |  6,622 (79.3%)     |  3,544 (31.9%)     | -3,078     | De-skewed                |
| JavaScript           |      0 (STARVED) ⚠️|  4,415 (39.7%)     | +4,415     | **Fully Recovered**      |
| Python               |  1,282 (15.3%)     |  1,816 (16.3%)     |   +534     | Balanced                 |
| Go                   |      0 (STARVED) ⚠️|    914 ( 8.2%)     |   +914     | **Fully Recovered**      |
| Java                 |    449 ( 5.4%)     |    427 ( 3.8%)     |    -22     | Preserved                |
+----------------------+--------------------+--------------------+------------+--------------------------+
| Total Active Langs   | 3 of 5 Languages   | 5 of 5 Languages   | +2 Langs   | All 5 Languages Active   |
+----------------------+--------------------+--------------------+------------+--------------------------+
```

---

## 7. Expanded Synthetic Unit Test Results

The test harness in `scripts/datasets/test_experimental_stratified_group_split.py` was executed with 13 automated tests:

```
Ran 13 tests in 0.030s
OK
```

```
+-------------------------------------------------+-------------------------------------------------------------+---------------+
| Test Method                                     | Targeted Verification Invariant                             | Status        |
+-------------------------------------------------+-------------------------------------------------------------+---------------+
| `test_zero_group_leakage_invariable`            | Asserts zero group overlap across 50 groups.                | ✅ PASS (0.00s|
| `test_record_conservation_strict`               | Asserts total output count == total input count.            | ✅ PASS (0.00s|
| `test_robust_heldout_exclusion_safety`          | Asserts robust held-out records never enter any split.      | ✅ PASS (0.00s|
| `test_balanced_class_allocation`                | Asserts all 4 classes present in train/val/test.            | ✅ PASS (0.00s|
| `test_severe_class_imbalance`                   | Asserts minority classes (10 samples) reach test split.     | ✅ PASS (0.00s|
| `test_single_group_constrained_class`           | Asserts 1-group class is allocated indivisibly to train.    | ✅ PASS (0.00s|
| `test_two_group_constrained_class`              | Asserts 2-group class covers train and test.                | ✅ PASS (0.00s|
| `test_multi_label_groups`                       | Asserts multi-label group is not fragmented.                | ✅ PASS (0.00s|
| `test_multi_language_groups`                    | Asserts polyglot group is not fragmented.                   | ✅ PASS (0.00s|
| `test_conflicting_class_and_lang_requirements`  | Asserts solver resolves opposing class vs lang demands.     | ✅ PASS (0.00s|
| `test_large_super_group_ratio_impact`           | Asserts 400-sample super-group is assigned to train.        | ✅ PASS (0.00s|
| `test_deterministic_reproducibility`            | Asserts byte-identical splits across repeated runs (seed).  | ✅ PASS (0.00s|
| `test_language_coverage_in_test`                | Asserts all 5 languages reach test split.                   | ✅ PASS (0.00s|
+-------------------------------------------------+-------------------------------------------------------------+---------------+
```

---

## 8. Exact Reproduction Commands

```bash
# 1. Execute expanded 13-test synthetic suite
cmd /c "set PYTHONPATH=C:\PATCHPROOF && python -m unittest scripts/datasets/test_experimental_stratified_group_split.py"

# 2. Execute dry-run audit on primary 105,537 records with robust quarantine
cmd /c "set PYTHONPATH=C:\PATCHPROOF && python scripts/datasets/run_dry_run_audit.py"

# 3. Verify SHA-256 hashes of protected artifacts
python -c "import hashlib; [print(p, hashlib.sha256(open(p, 'rb').read()).hexdigest()) for p in ['models/bug_detector.joblib', 'data/processed/test.jsonl', 'data/processed/robust_heldout_test.jsonl']]"
```

---

## 9. Protected Artifact Integrity Confirmation

```
+------------------------------------+------------------------------------------------------------------+-------------------+
| Protected File Path                | Verified SHA-256 Cryptographic Hash                              | Verification State|
+------------------------------------+------------------------------------------------------------------+-------------------+
| `models/bug_detector.joblib`       | 5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20 | VERIFIED INTACT   |
| `data/processed/test.jsonl`        | 9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d | VERIFIED INTACT   |
| `data/processed/robust_heldout...` | e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1 | VERIFIED INTACT   |
| `data/processed/train.jsonl`       | 6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad | VERIFIED INTACT   |
| `data/processed/val.jsonl`         | 935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f | VERIFIED INTACT   |
| `scripts/datasets/split.py`        | Legacy production splitter 100% untouched                        | VERIFIED INTACT   |
| `backend/app/main.py`              | NEVER_MERGE_ACTIVE Enforcement Verified                          | VERIFIED INTACT   |
+------------------------------------+------------------------------------------------------------------+-------------------+
```

- **Zero Training Conducted:** Confirmed.
- **Zero External Network Downloads:** Confirmed.
- **Zero Modifications to Existing Datasets:** Confirmed.
- **Active Production Server:** Uninterrupted on port 8000.

---
*Report Author: Antigravity Autonomous Research Harness*  
*Delivery Document: `docs/EXPERIMENT_N1_1_CORRECTNESS_AUDIT.md`*  
*Repository: `C:\PATCHPROOF`*
