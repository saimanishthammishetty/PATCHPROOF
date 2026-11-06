# PATCHPROOF — PHASE O.2.1: INDEPENDENT RESULTS CONSISTENCY AUDIT REPORT
**Phase:** Phase O.2.1 — Strictly Read-Only Independent Results Consistency Audit
**Date:** 2026-11-06 01:00:00 UTC
**Audit Protocol:** Read-Only Mathematical Recalculation & Epistemological Audit
**Safety Invariant:** `NEVER_MERGE_ACTIVE = True` (Preserved & Cryptographically Verified)
**Dataset Under Audit:** [`models/experiments/experiment_o/phase_o_benchmark_dataset.jsonl`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o_benchmark_dataset.jsonl)
**Audited Benchmark SHA-256:** `caa7abe4f0dc22eefebf39a042934f3a3eaf8994290c4c6a057abd25f6e3d0dc`

---

## EXECUTIVE SUMMARY

Phase O.2.1 executes an independent, strictly read-only mathematical consistency and epistemological audit of the Phase O.2 frozen evaluation results.

### Audit Verdict: **MATHEMATICALLY CONSISTENT — 15 / 15 CLAIMS PASSED — INTERPRETATIONS CORRECTED**
1. **Mathematical Consistency:** Every metric, false-positive count, true-positive count, subgroup reconciliation, and confidence interval reported in [`PHASE_O2_FINAL_REPORT.md`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o2/PHASE_O2_FINAL_REPORT.md) was recalculated directly from the saved 13x13 confusion matrices and verified with 100% precision.
2. **Saved Predictions Limitation:** Row-by-row prediction arrays were not serialized as a separate flat CSV/JSON column file during Phase O.2, but were retained in full via the saved 13x13 contingency matrices, per-class metrics, repository breakdowns, and subgroup files. In accordance with strict instructions, model inference was **not re-run**; all metrics were verified directly from the serialized contingency data.
3. **Subgroup Reconciliation:** Subgroup counts (`core_unseen_vuln` N=41 + `curated_same_commit_vuln` N=159) sum exactly to the 200 vulnerable benchmark samples across all models for both overall bug detection and memory-safety true positives.
4. **Epistemological Corrections Enforced:**
   - **Phase N is an operational trade-off point, NOT a strict Pareto improvement** over Candidate K (which has higher recall: 49.09% vs 29.09%) or Candidate L2 (which has lower FPR: 22.00% vs 27.36%).
   - **Production Baseline:** Near-zero detection of memory safety on this C benchmark (1.82%), but must not be characterized as "universally non-functional" across other domains.
   - **Repository Concentration:** The benchmark is 86.28% Linux and 13.31% OpenSSL; it cannot be interpreted as broad multi-repository validation.
   - **Clean Code Verification:** Represents empirical negative defect filtering, not formal mathematical proof of total bug absence.
   - **Zero Automatic Promotion:** No candidate is promoted to production.

---

## 1. CLAIM-BY-CLAIM VERIFICATION TABLE

Every specific numerical claim in `PHASE_O2_FINAL_REPORT.md` was cross-checked against independent recalculations:

| Claim ID | Verified Target / Claim | Reported Value | Recalculated Value | Audit Status |
|:---:|---|:---:|:---:|:---:|
| **C-01** | Candidate K vulnerable detection recall | 60.50% (121 / 200) | **60.50% (121 / 200)** | **PASS** |
| **C-02** | Candidate L2 vulnerable detection recall | 39.00% (78 / 200) | **39.00% (78 / 200)** | **PASS** |
| **C-03** | Phase N Policy vulnerable detection recall | 44.00% (88 / 200) | **44.00% (88 / 200)** | **PASS** |
| **C-04** | Benchmark memory-safety ground truth support | exactly 55 | **55** | **PASS** |
| **C-05** | Candidate K memory-safety true positives | 27 / 55 (49.09%) | **27 / 55 (49.09%)** | **PASS** |
| **C-06** | Candidate L2 memory-safety true positives | 12 / 55 (21.82%) | **12 / 55 (21.82%)** | **PASS** |
| **C-07** | Phase N Policy memory-safety true positives | 16 / 55 (29.09%) | **16 / 55 (29.09%)** | **PASS** |
| **C-08** | Clean Code False Positive Counts (Base, K, L2, N) | 769, 500, 275, 342 | **769, 500, 275, 342** | **PASS** |
| **C-09** | Clean Code False Positive Rates (Base, K, L2, N) | 61.52%, 40.00%, 22.00%, 27.36% | **61.52%, 40.00%, 22.00%, 27.36%** | **PASS** |
| **C-10** | Subgroup reconciliation: Candidate K vulnerable TP | 29 (Core) + 92 (Curated) = 121 | **29 + 92 = 121** | **PASS** |
| **C-11** | Subgroup reconciliation: Candidate L2 vulnerable TP | 19 (Core) + 59 (Curated) = 78 | **19 + 59 = 78** | **PASS** |
| **C-12** | Subgroup reconciliation: Phase N vulnerable TP | 21 (Core) + 67 (Curated) = 88 | **21 + 67 = 88** | **PASS** |
| **C-13** | Subgroup reconciliation: Candidate K memory-safety TP | 6 (Core) + 21 (Curated) = 27 | **6 + 21 = 27** | **PASS** |
| **C-14** | Subgroup reconciliation: Candidate L2 memory-safety TP | 5 (Core) + 7 (Curated) = 12 | **5 + 7 = 12** | **PASS** |
| **C-15** | Subgroup reconciliation: Phase N memory-safety TP | 6 (Core) + 10 (Curated) = 16 | **6 + 10 = 16** | **PASS** |

---

## 2. INDEPENDENT RECALCULATION & DENOMINATOR AUDIT

All metrics recalculated directly from [`models/experiments/experiment_o/phase_o2/phase_o2_confusion_matrices.json`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o2/phase_o2_confusion_matrices.json):

### 2.1 Overall Performance Metrics

| Metric | Production Baseline | Candidate K | Candidate L2 | Phase N Policy (`tau=0.30`, `delta=-0.12`) |
|---|:---:|:---:|:---:|:---:|
| **Accuracy** | 33.38% (484 / 1,450) | 55.03% (798 / 1,450) | **69.17% (1,003 / 1,450)** | 64.83% (940 / 1,450) |
| **Weighted F1** | 45.03% | 63.70% | **72.99%** | 70.33% |
| **Clean Code FPR** | 61.52% (769 / 1,250) | 40.00% (500 / 1,250) | **22.00% (275 / 1,250)** | 27.36% (342 / 1,250) |
| **Overall Bug FNR** | 57.00% (114 / 200) | **39.50% (79 / 200)** | 61.00% (122 / 200) | 56.00% (112 / 200) |
| **Vulnerable Recall** | 43.00% (86 / 200) | **60.50% (121 / 200)** | 39.00% (78 / 200) | 44.00% (88 / 200) |
| **Vulnerable Precision** | 10.06% (86 / 855) | 19.48% (121 / 621) | **22.10% (78 / 353)** | 20.47% (88 / 430) |
| **Vulnerable F1** | 16.30% | **29.48%** | 28.21% | 27.94% |
| **Memory-Safety Recall** | 1.82% (1 / 55) | **49.09% (27 / 55)** | 21.82% (12 / 55) | 29.09% (16 / 55) |
| **Memory-Safety Precision** | 1.89% (1 / 53) | **7.05% (27 / 383)** | 6.74% (12 / 178) | 6.23% (16 / 257) |
| **Memory-Safety F1** | 1.85% | **12.33%** | 10.30% | 10.26% |

### 2.2 Macro F1 Denominator Investigation
The audit revealed an important mathematical nuance regarding Macro F1 calculation:
- In `phase_o_benchmark_dataset.jsonl`, exactly **8 classes** have ground-truth support > 0 (`none_correct_code`, `condition_error`, `memory_safety`, `resource_leak`, `state_management`, `undefined_behavior`, `null_pointer`, `exception_handling`).
- Across predictions, models predicted samples for 9–10 classes, yielding a union set of **11 classes**.
- Scikit-learn's default `precision_recall_fscore_support(y_true, y_pred, average="macro")` divides by the 11 union classes:
  - Baseline: **4.99%** | Candidate K: **9.79%** | Candidate L2: **10.39%** | Phase N: **10.12%**
- If averaged strictly over all 13 canonical taxonomy classes (including 5 unrepresented classes with F1 = 0):
  - Baseline: **4.22%** | Candidate K: **8.29%** | Candidate L2: **8.79%** | Phase N: **8.56%**
- If averaged strictly over the 8 ground-truth classes with support > 0:
  - Baseline: **6.86%** | Candidate K: **13.47%** | Candidate L2: **14.28%** | Phase N: **13.91%**
- **Conclusion:** Under all three denominator definitions, the relative ordering and conclusions are identical: Candidate L2 achieves the highest Macro F1, followed closely by Phase N, Candidate K, and Production Baseline.

---

## 3. DECISION POLICY IMPLEMENTATION AUDIT

The code in [`evaluate_phase_o2.py`](file:///C:/PATCHPROOF/scripts/experiments/experiment_o/evaluate_phase_o2.py#L226-L238) was audited against Phase N specifications:

```python
tau = 0.30
delta = -0.12
preds_n = []
for i in range(len(records)):
    p_mem = probs_l2[i][mem_idx]      # col 5: memory_safety
    p_clean = probs_l2[i][clean_idx]  # col 6: none_correct_code
    if (p_mem >= tau) and ((p_mem - p_clean) >= delta):
        preds_n.append("memory_safety")
    else:
        preds_n.append(preds_l2[i])
```

### Verification Findings:
1. **Exact Parameters:** `tau = 0.30`, `delta = -0.12` match the frozen Phase N / N.1 Pareto configuration.
2. **Probability Sourcing:** Probabilities originate directly from Candidate L2 (`model_l2.predict_proba(X_deb)`), utilizing frozen debiasing regex (`lib_` replacement).
3. **Monotonic Promotion Property:** The rule can **only promote** non-memory-safety argmax predictions to `memory_safety`.
4. **Demotion Impossibility:** If Candidate L2's argmax was already `memory_safety`, then `p_mem >= p_clean` and `p_mem >= 1/13 ≈ 0.0769`. The condition `(p_mem - p_clean >= -0.12)` is automatically satisfied. If it were to enter the else branch, it falls back to `preds_l2[i]`, which is already `memory_safety`. Therefore, an existing `memory_safety` prediction is **never demoted**.
5. **No Label Mismatches:** Class indexing was verified identical across all models.

---

## 4. STATISTICAL & UNCERTAINTY AUDIT

1. **Wilson Score Confidence Intervals:** All proportions were validated against the standard Wilson continuity equation with $z = 1.95996$. No zero-division or out-of-bounds intervals occurred.
2. **Bootstrap Resampling:** Bootstrap intervals for Macro and Weighted F1 utilized $B = 1,000$ resamples with fixed seed (`seed = 42`) and sample-with-replacement over rows.
3. **Subgroup Sample Size Warning:** Subgroups with small sample sizes (`curl` N=2, `redis` N=2, `wireshark` N=2, `openssl` vulnerable N=15) have wide uncertainty bands and must not be used to assert general multi-repository claims.

---

## 5. INTERPRETATION AUDIT & CORRECTIONS

The following conceptual and interpretive corrections are permanently recorded:

1. **Phase N is an Operational Compromise, Not a Strict Pareto Improvement:**
   - In earlier draft text, Phase N was informally described as a "Pareto improvement".
   - *Correction:* While `tau=0.30, delta=-0.12` Pareto-dominated `tau=0.34, delta=-0.12` during the Phase N threshold sweep on validation data, it is **not** a Pareto improvement over Candidate K (which has higher recall: 49.09% vs 29.09%) or Candidate L2 (which has lower FPR: 22.00% vs 27.36%). Phase N represents an **intermediate operational trade-off point** that recovers +7.27 pp of recall over L2 while avoiding 158 of K's false alarms.
2. **Baseline Characterization:**
   - The Production Baseline exhibited near-zero memory safety detection on this benchmark (1.82% recall, 61.52% FPR). However, it should be characterized specifically as "ineffective for modern C security analysis" rather than "universally non-functional" across unrelated languages and tasks.
3. **Repository Scope & Generalization:**
   - The benchmark is 86.28% Linux and 13.31% OpenSSL. The results provide valuable repository-independent validation within these projects, but cannot be claimed as representative of all C codebases across the software ecosystem.
4. **Clean Code Epistemology:**
   - Clean status reflects negative defect filtering (`StaticAnalyzer.analyze_c`) and clean git history, not mathematical verification of bug absence.
5. **Production Deployment Stance:**
   - In strict compliance with safety rules, no model promotion or production deployment is recommended or approved.

---

## 6. FINAL CRYPTOGRAPHIC AUDIT

All 7 core model and dataset files were verified identical:

| Artifact / File | Target SHA-256 | Current SHA-256 | Verification Status |
|---|---|---|:---:|
| [`models/bug_detector.joblib`](file:///C:/PATCHPROOF/models/bug_detector.joblib) | `5f93bba9ce457fe9...` | `5f93bba9ce457fe9...` | **MATCH (VERIFIED)** |
| [`models/experiments/experiment_k/bug_detector_candidate_k.joblib`](file:///C:/PATCHPROOF/models/experiments/experiment_k/bug_detector_candidate_k.joblib) | `c6ed9f42e8547137...` | `c6ed9f42e8547137...` | **MATCH (VERIFIED)** |
| [`models/experiments/experiment_l/candidate_l2_debiased.joblib`](file:///C:/PATCHPROOF/models/experiments/experiment_l/candidate_l2_debiased.joblib) | `399d155684ff6ac6...` | `399d155684ff6ac6...` | **MATCH (VERIFIED)** |
| [`data/processed/train.jsonl`](file:///C:/PATCHPROOF/data/processed/train.jsonl) | `6868ccac75c0048b...` | `6868ccac75c0048b...` | **MATCH (VERIFIED)** |
| [`data/processed/val.jsonl`](file:///C:/PATCHPROOF/data/processed/val.jsonl) | `935c6011b67ec85b...` | `935c6011b67ec85b...` | **MATCH (VERIFIED)** |
| [`data/processed/test.jsonl`](file:///C:/PATCHPROOF/data/processed/test.jsonl) | `9aad8de8b09b0e2f...` | `9aad8de8b09b0e2f...` | **UNTOUCHED (ISOLATED)** |
| [`data/processed/robust_heldout_test.jsonl`](file:///C:/PATCHPROOF/data/processed/robust_heldout_test.jsonl) | `e080c89720ba3efa...` | `e080c89720ba3efa...` | **UNTOUCHED (ISOLATED)** |
| [`models/experiments/experiment_o/phase_o_benchmark_dataset.jsonl`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o_benchmark_dataset.jsonl) | `caa7abe4f0dc22ee...` | `caa7abe4f0dc22ee...` | **MATCH (VERIFIED)** |

**Safety Invariant:** `backend.app.core.config.NEVER_MERGE = True` is active.

---

## 7. DELIVERABLES SUMMARY

All deliverables for Phase O.2.1 are complete and saved:
- Recalculated Metrics: [`models/experiments/experiment_o/phase_o2/phase_o2_1_recalculated_metrics.json`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o2/phase_o2_1_recalculated_metrics.json)
- Consistency Audit Spec: [`models/experiments/experiment_o/phase_o2/phase_o2_1_consistency_audit.json`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o2/phase_o2_1_consistency_audit.json)
- Final Audit Report: [`models/experiments/experiment_o/phase_o2/PHASE_O2_1_FINAL_REPORT.md`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o2/PHASE_O2_1_FINAL_REPORT.md)
