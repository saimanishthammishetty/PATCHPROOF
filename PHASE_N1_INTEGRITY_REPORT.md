# PATCHPROOF — PHASE N.1: DECISION BOUNDARY INTEGRITY AUDIT REPORT
**Audit Stage:** Independent Verification & Discrepancy Resolution
**Date:** 2026-11-05 18:04:32 UTC
**Environment:** Offline Experimental Evaluation
**Dataset Audited:** `data/processed/val.jsonl` (10,860 samples)
**Evaluator:** Independent Audit Harness (`scripts/experiments/experiment_n/audit_phase_n1.py`)
**Safety Invariant:** `NEVER_MERGE_ACTIVE = True` (Preserved & Verified)

---

## EXECUTIVE SUMMARY

Phase N investigated inference-time decision-boundary adjustments on Candidate L2 without retraining. Before proceeding to further experimentation, this Phase N.1 integrity audit was conducted under strict offline read-only protocols to independently verify all calculations, resolve identified numerical discrepancies, examine the exact mechanics of the decision rule, and audit sample denominators across repositories.

### Key Audit Findings

1. **Resolution of Configuration C Discrepancy:**
   - In `run_phase_n.py`, the recommendation dictionary defined `Config_C_HighRecall` as $\tau=0.34, \delta=-0.12$ (Recall: 65.81%, Precision: 68.01%, C Clean FPR: 38.18%), whereas the Pareto table recorded $\tau=0.30, \delta=-0.12$ (Recall: 66.79%, Precision: 68.29%, C Clean FPR: 38.18%).
   - The audit confirmed that both configurations produce the **exact same clean C false positive rate** (38.18%, 557 false alarms out of 1,459 clean C samples) because **zero clean C validation samples** fall in the probability interval $P(\text{mem}) \in [0.30, 0.34)$ with margin $\ge -0.12$.
   - However, exactly **18 genuine memory-safety vulnerabilities** fall into that window. Consequently, $\tau=0.30, \delta=-0.12$ **strictly Pareto-dominates** $\tau=0.34, \delta=-0.12$, securing +0.98% higher recall at identical clean C FPR.

2. **Decision-Rule Mechanics Verified:**
   - The implemented rule:
     $$\text{pred} = \begin{cases} \text{"memory\_safety"}, & \text{if } P(\text{mem}) \ge \tau \text{ and } (P(\text{mem}) - P(\text{clean})) \ge \delta \\ \text{orig\_argmax}, & \text{otherwise} \end{cases}$$
   - Functions as an **asymmetric promotion / override rule**: it overrides non-memory-safety predictions to `memory_safety` when thresholds pass, but **preserves existing memory-safety argmax predictions** when thresholds fail. It does **not** enforce a strict bidirectional threshold (it never demotes a low-confidence memory-safety argmax to clean code).

3. **Repository Support Denominator Clarification (Zero-Denominator Fallacy Fixed):**
   - In `val.jsonl`, exactly 100% of the 1,459 clean C samples originate from only two repositories: **QEMU** (964 samples) and **FFmpeg** (495 samples).
   - Android, Chrome, and Linux validation subsets contain **0 clean C samples**.
   - Describing Android, Chrome, and Linux as having "0.00% Clean C FPR" was a mathematical artifact ($0/0$). The technically correct reporting is **N/A (zero clean C support)**.

---

## 1. CONFIGURATION C DISCREPANCY AUDIT

### 1.1 Discrepancy Context
In the initial Phase N summary:
- The **Pareto Frontier Table** listed: $\tau=0.30, \delta=-0.12 \implies \text{Recall} = 66.79\%, \text{C Clean FPR} = 38.18\%$.
- The **Recommended Configurations Section** listed: $\text{Config C} \implies \tau=0.34, \delta=-0.12 \implies \text{Recall} = 65.81\%, \text{C Clean FPR} = 38.18\%$.

### 1.2 Quantitative Audit & Resolution
The audit evaluated both $(\tau=0.30, \delta=-0.12)$ and $(\tau=0.34, \delta=-0.12)$ across all 10,860 validation records.

| Metric | Pareto Entry ($\tau=0.30, \delta=-0.12$) | Script Entry ($\tau=0.34, \delta=-0.12$) | Delta ($\tau=0.30$ vs $\tau=0.34$) |
|---|:---:|:---:|:---:|
| **Memory-Safety Recall** | **66.79%** (1,219 / 1,825) | 65.81% (1,201 / 1,825) | **+0.98% (+18 TP)** |
| **Memory-Safety Precision** | **68.29%** (1,219 / 1,785) | 68.01% (1,201 / 1,766) | **+0.28%** |
| **Memory-Safety F1** | **0.6753** | 0.6689 | **+0.0064** |
| **Clean-Code FPR (Overall)** | 14.00% (597 / 4,263) | 14.00% (597 / 4,263) | **0.00% (0)** |
| **C Clean-Code FPR** | **38.18%** (557 / 1,459) | **38.18%** (557 / 1,459) | **0.00% (0)** |
| **C Clean Mem FP Count** | 556 | 556 | 0 |
| **Overall Accuracy** | **88.05%** | 87.88% | +0.17% |
| **Macro F1** | **0.5035** | 0.5024 | +0.0011 |
| **Weighted F1** | **0.8846** | 0.8829 | +0.0017 |
| **Bug Detection FNR** | **8.08%** (533 / 6,597) | 8.28% (546 / 6,597) | **-0.20% (-13 FN)** |

### 1.3 Differing Samples Breakdown
Exactly **19 samples** out of 10,860 change predictions between $\tau=0.30$ and $\tau=0.34$:
- **Ground Truth of Differing Samples:**
  - `memory_safety`: **18 samples** (all correctly recovered at $\tau=0.30$; missed at $\tau=0.34$).
  - `condition_error`: **1 sample** (misclassified as memory_safety at $\tau=0.30$).
  - `none_correct_code` (Clean C): **0 samples**.
- **Languages:** All 19 samples are in C.
- **Why C Clean FPR Is Identical:** Exactly zero clean C files have $0.30 \le P(\text{mem}) < 0.34$ and margin $\ge -0.12$.
- **Conclusion:** $\tau=0.30, \delta=-0.12$ strictly Pareto-dominates $\tau=0.34, \delta=-0.12$. The Pareto analysis correctly identified $\tau=0.30$ as non-dominated.

---

## 2. DECISION-RULE MECHANISM VERIFICATION

### 2.1 Code Implementation Analysis
Inspection of `run_phase_n.py` reveals the following prediction logic:

```python
if (p_mem >= tau) and ((p_mem - p_clean) >= delta):
    preds_sweep.append("memory_safety")
else:
    preds_sweep.append(preds_l2_orig[i])
```

### 2.2 Mechanism Classification: Asymmetric Promotion
This rule is **not** a symmetric bidirectional threshold classifier. Instead, it operates as an **asymmetric promotion / override rule**:
1. **Promotion:** When the sample was originally predicted as *non-memory-safety* (e.g. `none_correct_code`, `condition_error`), but meets both $P(\text{mem}) \ge \tau$ and $P(\text{mem}) - P(\text{clean}) \ge \delta$, the model promotes the prediction to `memory_safety`.
2. **Preservation:** When the sample was originally predicted as `memory_safety` by the base argmax model, but fails the threshold conditions ($P(\text{mem}) < \tau$ or margin $< \delta$), the rule executes the `else` block: `preds_l2_orig[i]`, which **preserves the prediction as `memory_safety`**.
3. **Absence of Demotion:** A strict threshold rule would demote low-confidence memory-safety predictions ($P(\text{mem}) < \tau$) to clean code or a secondary class. The implemented rule never demotes any base memory-safety prediction.

### 2.3 Concrete Validation Traces (Config B: $\tau=0.38, \delta=-0.10$)

#### Trace Type A: Preserved Memory-Safety (Failing Threshold Condition)
Under Config B ($\tau=0.38, \delta=-0.10$), exactly **44 samples** had base argmax = `memory_safety` but failed the threshold condition ($P(\text{mem}) < 0.38$). All 44 were preserved as `memory_safety`.
- **Sample Index 327 (`pp-bvl-dc4965fd11`):**
  - Ground Truth: `memory_safety`
  - Probabilities: $P(\text{mem}) = 0.3312$, $P(\text{clean}) = 0.2877$
  - Argmax: `memory_safety` (highest class probability)
  - Condition: $0.3312 \ge 0.38$ is **FALSE**.
  - Rule Execution: Falls into `else: preds_l2_orig[i]` $\implies$ **Preserved as `memory_safety`** (True Positive).
- **Sample Index 411 (`pp-bvl-18bcd63a84`):**
  - Ground Truth: `memory_safety`
  - Probabilities: $P(\text{mem}) = 0.3043$, $P(\text{clean}) = 0.2610$
  - Argmax: `memory_safety`
  - Condition: $0.3043 \ge 0.38$ is **FALSE**.
  - Rule Execution: Falls into `else` $\implies$ **Preserved as `memory_safety`** (True Positive).

#### Trace Type B: Promoted Non-Memory-Safety (Passing Threshold Condition)
Under Config B, exactly **266 samples** originally predicted as non-memory-safety were promoted to `memory_safety`.
- **Sample Index 10 (`pp-dvn-8e8e29b349`):**
  - Ground Truth: `none_correct_code` (Clean C)
  - Probabilities: $P(\text{mem}) = 0.4227$, $P(\text{clean}) = 0.4693$
  - Argmax: `none_correct_code` ($0.4693 > 0.4227$)
  - Condition Check:
    - $\tau$: $0.4227 \ge 0.38$ $\implies$ **TRUE**.
    - $\delta$: $0.4227 - 0.4693 = -0.0466 \ge -0.10$ $\implies$ **TRUE**.
  - Rule Execution: Condition passes $\implies$ **Promoted to `memory_safety`** (False Alarm).
- **Sample Index 12 (`pp-dvn-9244d238a9`):**
  - Ground Truth: `none_correct_code` (Clean C)
  - Probabilities: $P(\text{mem}) = 0.4520$, $P(\text{clean}) = 0.5177$
  - Argmax: `none_correct_code`
  - Condition Check: $0.4520 \ge 0.38$ (TRUE) and $0.4520 - 0.5177 = -0.0657 \ge -0.10$ (TRUE).
  - Rule Execution: **Promoted to `memory_safety`** (False Alarm).

---

## 3. INDEPENDENT REPRODUCTION OF SELECTED CONFIGURATIONS

All metrics were independently re-computed from scratch over `val.jsonl` (10,860 samples).

### 3.1 Primary Comparative Performance Table

| Configuration | Thresholds | Accuracy | Macro F1 | Weighted F1 | Mem Prec | Mem Recall | Mem F1 | Overall Clean FPR | C Clean FPR | Bug FNR |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Candidate L2 (Argmax Baseline)** | Base Argmax | 87.79% | 0.4986 | 0.8782 | **72.07%** | 56.00% (1,022/1,825) | 0.6303 | **10.04%** (428/4,263) | **26.59%** (388/1,459) | 10.82% (714/6,597) |
| **Config A (Conservative)** | $\tau=0.42, \delta=-0.05$ | 87.85% | 0.4997 | 0.8804 | 70.57% | 59.51% (1,086/1,825) | 0.6457 | 11.38% (485/4,263) | 30.50% (445/1,459) | 9.85% (650/6,597) |
| **Config B (Balanced)** | $\tau=0.38, \delta=-0.10$ | 87.73% | 0.5010 | 0.8806 | 68.41% | 63.12% (1,152/1,825) | 0.6566 | 13.23% (564/4,263) | 35.92% (524/1,459) | 8.94% (590/6,597) |
| **Config C (Script Entry)** | $\tau=0.34, \delta=-0.12$ | 87.88% | 0.5024 | 0.8829 | 68.01% | 65.81% (1,201/1,825) | 0.6689 | 14.00% (597/4,263) | 38.18% (557/1,459) | 8.28% (546/6,597) |
| **Config C (Pareto Entry)** | $\tau=0.30, \delta=-0.12$ | **88.05%** | **0.5035** | **0.8846** | 68.29% | **66.79%** (1,219/1,825) | **0.6753** | 14.00% (597/4,263) | **38.18%** (557/1,459) | **8.08%** (533/6,597) |

### 3.2 Verified Denominators & Support Counts
- **Total Validation Samples:** 10,860
- **Memory-Safety Ground Truth Support:** 1,825 samples
- **Total Clean-Code Ground Truth Support:** 4,263 samples
- **C Clean-Code Ground Truth Support:** 1,459 samples
- **Total Bug Ground Truth Support:** 6,597 samples

### 3.3 Full 13-Class Breakdown Across Audited Configurations

#### Original L2 Argmax Baseline
| Class Name | Precision | Recall | F1-Score | Support |
|---|:---:|:---:|:---:|:---:|
| `api_misuse` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `async_error` | 0.9981 | 0.9934 | 0.9958 | 1,062 |
| `condition_error` | 0.3125 | 0.4545 | 0.3704 | 99 |
| `exception_handling` | 0.9981 | 1.0000 | 0.9990 | 1,042 |
| `loop_error` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `memory_safety` | **0.7207** | **0.5600** | **0.6303** | 1,825 |
| `none_correct_code` | 0.8430 | 0.8996 | 0.8704 | 4,263 |
| `null_pointer` | 0.8000 | 0.5333 | 0.6400 | 15 |
| `off_by_one` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `resource_leak` | 0.9772 | 0.9876 | 0.9823 | 563 |
| `state_management` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `type_error` | 0.9980 | 0.9900 | 0.9939 | 1,991 |
| `undefined_behavior` | 0.0000 | 0.0000 | 0.0000 | 0 |

#### Config B ($\tau=0.38, \delta=-0.10$)
| Class Name | Precision | Recall | F1-Score | Support |
|---|:---:|:---:|:---:|:---:|
| `api_misuse` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `async_error` | 0.9981 | 0.9934 | 0.9958 | 1,062 |
| `condition_error` | 0.3261 | 0.4545 | 0.3797 | 99 |
| `exception_handling` | 0.9981 | 1.0000 | 0.9990 | 1,042 |
| `loop_error` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `memory_safety` | **0.6841** | **0.6312** | **0.6566** | 1,825 |
| `none_correct_code` | 0.8617 | 0.8677 | 0.8647 | 4,263 |
| `null_pointer` | 0.8000 | 0.5333 | 0.6400 | 15 |
| `off_by_one` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `resource_leak` | 0.9789 | 0.9876 | 0.9832 | 563 |
| `state_management` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `type_error` | 0.9980 | 0.9900 | 0.9939 | 1,991 |
| `undefined_behavior` | 0.0000 | 0.0000 | 0.0000 | 0 |

#### Config C Pareto Entry ($\tau=0.30, \delta=-0.12$)
| Class Name | Precision | Recall | F1-Score | Support |
|---|:---:|:---:|:---:|:---:|
| `api_misuse` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `async_error` | 0.9981 | 0.9934 | 0.9958 | 1,062 |
| `condition_error` | 0.3409 | 0.4545 | 0.3896 | 99 |
| `exception_handling` | 0.9981 | 1.0000 | 0.9990 | 1,042 |
| `loop_error` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `memory_safety` | **0.6829** | **0.6679** | **0.6753** | 1,825 |
| `none_correct_code` | 0.8731 | 0.8600 | 0.8665 | 4,263 |
| `null_pointer` | 0.8000 | 0.5333 | 0.6400 | 15 |
| `off_by_one` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `resource_leak` | 0.9806 | 0.9876 | 0.9841 | 563 |
| `state_management` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `type_error` | 0.9980 | 0.9900 | 0.9939 | 1,991 |
| `undefined_behavior` | 0.0000 | 0.0000 | 0.0000 | 0 |

### 3.4 Language-Specific Performance Breakdown

| Language | Total Samples | Clean Samples | Bug Samples | Argmax Acc / WF1 | Config B Acc / WF1 | Config C Pareto Acc / WF1 | Clean FPR (Config B) | Bug FNR (Config B) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **C** | 3,515 | 1,459 | 2,056 | 63.41% / 0.6386 | 63.24% / 0.6387 | 64.21% / 0.6478 | 35.92% (524/1,459) | 28.70% (590/2,056) |
| **Python** | 5,365 | 2,804 | 2,561 | 99.25% / 0.9960 | 99.25% / 0.9960 | 99.25% / 0.9960 | 1.43% (40/2,804) | 0.00% (0/2,561) |
| **Go** | 913 | 0 | 913 | 100.0% / 1.0000 | 100.0% / 1.0000 | 100.0% / 1.0000 | N/A (0 clean) | 0.00% (0/913) |
| **Java** | 473 | 0 | 473 | 100.0% / 1.0000 | 100.0% / 1.0000 | 100.0% / 1.0000 | N/A (0 clean) | 0.00% (0/473) |
| **JavaScript** | 594 | 0 | 594 | 100.0% / 1.0000 | 100.0% / 1.0000 | 100.0% / 1.0000 | N/A (0 clean) | 0.00% (0/594) |

*Observation:* Decision boundary adjustments applied to `memory_safety` strictly affect C code; Python, Go, Java, and JavaScript performance is 100% invariant across all threshold configurations.

---

## 4. REPOSITORY AUDIT & ZERO-DENOMINATOR RESOLUTION

An exhaustive audit of repository distributions in `val.jsonl` was conducted to investigate the cross-repository false-positive rates reported in Phase N.

### 4.1 Audited Group Support Matrix in `val.jsonl`

| Repository Group | Total Samples | Memory-Safety Bugs | Clean C Samples | Clean Non-C Samples | Other Defect Bugs | Clean C Support Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **QEMU** | 1,610 | 645 | **964** | 0 | 1 | **Valid (66.07% of clean C)** |
| **FFmpeg** | 930 | 435 | **495** | 0 | 0 | **Valid (33.93% of clean C)** |
| **Android** | 401 | 392 | **0** | 0 | 9 | **ZERO SUPPORT (0/0)** |
| **Chrome** | 268 | 131 | **0** | 0 | 137 | **ZERO SUPPORT (0/0)** |
| **Linux** | 107 | 69 | **0** | 0 | 38 | **ZERO SUPPORT (0/0)** |
| **Other** | 7,544 | 153 | **0** | 2,804 (Python) | 4,587 | **ZERO Clean C SUPPORT** |
| **Total** | **10,860** | **1,825** | **1,459** | **2,804** | **4,772** | **1,459 Clean C Total** |

### 4.2 Resolution of Zero-Denominator Artifact
- **Root Cause:** In the acquisition pipeline (Stream 1 & 2 / Devign), clean C functions were acquired exclusively from QEMU and FFmpeg commits. BigVul (Stream 4: Android, Chrome, Linux, OpenSSL) contributed only known CVE vulnerable commits and patch diffs, with **zero clean C samples** partitioned into the validation split.
- **Audit Correction:** In the Phase N report, tables displaying "0.00% Clean C FPR" for Android, Chrome, and Linux resulted from a default fallback when dividing by zero (`clean_fp / len(clean_indices) if len(clean_indices) > 0 else 0.0`).
- **Required Standard:** Clean C FPR for Android, Chrome, and Linux must be reported as **`N/A (zero clean C support)`**. True cross-repository C clean false positive rate can only be measured on QEMU and FFmpeg in this split:
  - **QEMU Clean C FPR:**
    - L2 Argmax: 27.59% (266 / 964)
    - Config B: 37.14% (358 / 964)
    - Config C Pareto: 39.42% (380 / 964)
  - **FFmpeg Clean C FPR:**
    - L2 Argmax: 24.65% (122 / 495)
    - Config B: 33.54% (166 / 495)
    - Config C Pareto: 35.76% (177 / 495)

---

## 5. CRYPTOGRAPHIC VERIFICATION & SAFETY INVARIANTS

### 5.1 Artifact Integrity Checks (Pre- and Post-Audit)
All SHA-256 checksums were verified at both startup and completion of the audit harness:

| Target File | Expected SHA-256 Hash | Audit Status |
|---|---|:---:|
| `models/bug_detector.joblib` | `5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20` | **MATCH (PASS)** |
| `models/experiments/experiment_k/bug_detector_candidate_k.joblib` | `c6ed9f42e8547137577a311f603a9f752084cb2d0be5ff7ce4b75af7bae2377a` | **MATCH (PASS)** |
| `models/experiments/experiment_l/candidate_l2_debiased.joblib` | `399d155684ff6ac689624175696b4dd6db7bff149fa7421a63b30c76f25c4942` | **MATCH (PASS)** |
| `data/processed/train.jsonl` | `6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad` | **MATCH (PASS)** |
| `data/processed/val.jsonl` | `935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f` | **MATCH (PASS)** |
| `data/processed/test.jsonl` | `9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d` | **UNTOUCHED (PASS)** |
| `data/processed/robust_heldout_test.jsonl` | `e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1` | **UNTOUCHED (PASS)** |

### 5.2 Safety Invariant Verification
- In `backend/app/core/config.py`:
  - `NEVER_MERGE = True` remains permanently set.
  - No candidate model has been promoted or deployed to production.
  - Zero modifications were made to training, validation, or test datasets.

---

## 6. AUDIT SUMMARY & RECOMMENDATIONS

1. **Adopt Pareto Config C Definition:** In all future documentation and benchmarking, "Configuration C" must refer to the non-dominated Pareto entry **$\tau=0.30, \delta=-0.12$** (Recall: 66.79%, Precision: 68.29%, C Clean FPR: 38.18%), which strictly Pareto-dominates the script entry $\tau=0.34, \delta=-0.12$.
2. **Acknowledge Asymmetric Decision Rule:** Document clearly that threshold tuning is currently implemented as an *asymmetric promotion override rule* that preserves existing base model true positives while lowering the activation barrier for borderline samples.
3. **Denominator Transparency:** State clearly in all reports that validation clean C false positive rates reflect QEMU (964 samples) and FFmpeg (495 samples) distributions exclusively.
4. **Readiness for Next Phase:** With this independent audit complete and verified, the quantitative integrity of the Phase N threshold sweep is fully established. All artifacts have been saved to `models/experiments/experiment_n/phase_n1_integrity_audit.json`.
