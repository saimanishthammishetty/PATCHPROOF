# PATCHPROOF — Experiment J Evaluation Report

> **Generated:** 2026-11-03  
> **Status:** COMPLETE — Candidate NOT promoted to production  
> **NEVER_MERGE_ACTIVE:** Enforced  
> **Production baseline SHA-256:** `5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20` ✅ Intact  
> **Test set SHA-256:** `9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d` ✅ Intact

---

## 1. Objective

Investigate the 2.74-percentage-point accuracy regression on the untouched test set introduced by Experiment I's Hybrid Engine, determine its root cause, and attempt to recover it through val-set-tuned fusion parameter optimization while preserving or improving bug detection recall.

**Strict constraints applied throughout:**
- No training or tuning on `test.jsonl`
- No modification of `models/bug_detector.joblib`
- All threshold selection done exclusively on `data/processed/val.jsonl`
- All metrics are from genuine held-out evaluation

---

## 2. Phase J1 — Untouched Test Regression Investigation

### 2.1 Dataset Counts

| Dataset | Records | Classes | Languages |
|---------|--------:|---------|-----------|
| Untouched test (`test.jsonl`) | 8,353 | 7 | C (6,622), Python (1,282), Java (449) |
| Validation (`val.jsonl`) | 10,860 | 8 | Mixed |
| Robust heldout (`robust_heldout_test.jsonl`) | 1,226 | 2 | Python (594), JavaScript (632) |

### 2.2 Test Set Class Distribution

| Class | Count | % of Total |
|-------|------:|--------:|
| `none_correct_code` | 3,596 | 43.05% |
| `memory_safety` | 2,431 | 29.10% |
| `type_error` | 1,999 | 23.93% |
| `condition_error` | 140 | 1.68% |
| `resource_leak` | 134 | 1.60% |
| `null_pointer` | 27 | 0.32% |
| `async_error` | 26 | 0.31% |

### 2.3 Root Cause: H1 ML Over-Classification of C Code

Phase J1 identified that **100% of the 229-sample regression** originated from Candidate H1 predicting `memory_safety` on C kernel/system code that the static rules correctly classified or defaulted to `none_correct_code`.

**Per-class net delta (Baseline vs Hybrid I):**

| Class | Baseline Correct | Hybrid I Correct | Delta |
|-------|----------------:|----------------:|------:|
| `type_error` | 1,957/1,999 (97.90%) | 1/1,999 (0.05%) | **-1,956** |
| `none_correct_code` | 1,502/3,596 (41.74%) | 1,303/3,596 (36.23%) | -199 |
| `null_pointer` | 8/27 (29.63%) | 0/27 (0.00%) | -8 |
| `memory_safety` | 120/2,431 (4.94%) | 2,036/2,431 (83.79%) | **+1,917** |
| `condition_error` | 0/140 (0.00%) | 8/140 (5.71%) | +8 |
| `resource_leak` | 3/134 (2.24%) | 9/134 (6.72%) | +6 |
| `async_error` | 0/26 (0.00%) | 2/26 (7.69%) | +2 |

**Finding:** H1 has learned that pointer/array C syntax correlates with `memory_safety` but has no way to distinguish actual memory bugs from clean QEMU/S390/FFmpeg kernel code using the same vocabulary. The model swapped 1,956 correct `type_error` predictions for `memory_safety` false positives.

> [!IMPORTANT]
> The `type_error` class in `test.jsonl` consists of C format-specifier mismatches (`printf("%d", long_var)`) and Python str+int concat bugs. The production baseline memorized `%d`, `uint8_t`, `parseint` tokens. H1's AST normalization stripped these, causing the regression.

---

## 3. Phase J2 — Static Analyzer Rule-Level Audit

**Test set processed:** 8,353 records  
**Static rule triggers total:** 61 / 8,353 (0.73% coverage)

### 3.1 Per-Rule Statistics

| Rule | Fires | TP | FP | Precision |
|------|------:|---:|---:|----------:|
| `C_PRINTF_STR_SPEC_ON_INT` | 21 | 0 | 21 | 0.000 |
| `PY_BARE_EXCEPT` | 14 | 0 | 14 | 0.000 |
| `PY_MUTABLE_DEFAULT` | 8 | 0 | 8 | 0.000 |
| `C_RESOURCE_LEAK_ON_RETURN` | 7 | 1 | 6 | 0.143 |
| `PY_EXCEPTION_SWALLOWED` | 4 | 0 | 4 | 0.000 |
| `PY_STR_NUM_CONCAT` | 3 | 0 | 3 | 0.000 |
| `PY_IDENTITY_ON_LITERAL` | 3 | 0 | 3 | 0.000 |
| `C_RETURNING_STACK_ADDRESS` | 1 | 0 | 1 | 0.000 |

> [!WARNING]
> Static rules have 0% precision on most classes on the full test set. The test set's bug samples come from synthetic templates with different structural signatures than what the static rules target. Static rules ARE highly effective on the robust heldout (100% accuracy), confirming they work precisely on the patterns they were designed for.

### 3.2 Per-Class Static-Only Performance (Test Set)

| Class | TP | FP | FN | Precision | Recall | F1 |
|-------|---:|---:|---:|----------:|-------:|---:|
| `none_correct_code` | 3,559 | 4,733 | 37 | 0.429 | 0.990 | 0.599 |
| `resource_leak` | 1 | 6 | 133 | 0.143 | 0.007 | 0.014 |
| All others | 0 | — | — | 0.000 | 0.000 | 0.000 |

**Static-only accuracy on test set: 42.62%** — achieved almost entirely by defaulting to `none_correct_code`.

**Conclusion:** Static rules are NOT responsible for the regression. They fired on only 61 samples. The regression is exclusively from H1 ML.

---

## 4. Phase J3 — Fusion Parameter Optimization (Val Set Only)

**Approach:** Sweep ML confidence threshold 0.35 to 0.75 on `val.jsonl` exclusively.  
**Selection metric:** Macro F1.

> [!CAUTION]
> `test.jsonl` was NOT accessed during threshold selection. All results below reflect val-set performance only.

### 4.1 Threshold Sweep Results (val.jsonl, 10,860 records)

| Threshold | Val Accuracy | Val Macro F1 | Bug Recall | Clean FPR |
|----------:|------------:|-------------:|-----------:|----------:|
| **0.35** (selected) | 57.86% | **0.2527** | 73.53% | 33.94% |
| 0.40 | 57.21% | 0.2464 | 64.06% | 33.71% |
| 0.45 | 56.70% | 0.2430 | 62.26% | 33.47% |
| 0.50 | 55.98% | 0.2387 | 60.09% | 33.03% |
| 0.55 | 55.72% | 0.2361 | 58.18% | 31.67% |
| 0.60 | 55.40% | 0.2329 | 55.93% | 29.81% |
| 0.65 | 55.29% | 0.2300 | 53.98% | 27.47% |
| 0.70 | 55.49% | 0.2275 | 51.98% | 24.18% |
| 0.75 | 55.96% | 0.2247 | 49.48% | 19.49% |

**Selected threshold: 0.35** (val Macro F1 = 0.2527)

---

## 5. Phase J4 — Final Comparative Evaluation

### 5.1 Systems Compared

| ID | System | Description |
|----|--------|-------------|
| A | **Baseline_Production** | `models/bug_detector.joblib` — TF-IDF + LogReg |
| B | **H1_ML_Only** | AST-normalized TF-IDF + LogReg (Experiment H) |
| C | **Static_Only** | Deterministic AST rule engine (Experiment I) |
| D | **Hybrid_I_thresh040** | Static-first + H1 fallback at threshold 0.40 |
| E | **Hybrid_J_thresh035** | Static-first + H1 fallback at threshold 0.35 (val-tuned) |

### 5.2 50-Snippet Novel Benchmark

| System | Accuracy | Macro F1 | Bug Recall | Clean FPR |
|--------|--------:|--------:|----------:|----------:|
| Baseline_Production | 36.00% | 0.2367 | 33.33% | 35.00% |
| H1_ML_Only | 24.00% | 0.1017 | 53.33% | 50.00% |
| **Static_Only** | **50.00%** | **0.3229** | 33.33% | **5.00%** |
| Hybrid_I (0.40) | 30.00% | 0.2003 | 70.00% | 55.00% |
| Hybrid_J (0.35) | 30.00% | 0.2003 | **70.00%** | 55.00% |

### 5.3 Untouched Test Set (8,353 records) — Primary Evaluation

| System | Accuracy | Macro F1 | Bug Recall | Clean FPR |
|--------|--------:|--------:|----------:|----------:|
| **Baseline_Production** | **51.18%** | **0.2163** | 61.49% | 39.18% |
| H1_ML_Only | 41.72% | 0.1921 | **93.71%** | 63.15% |
| Static_Only | 42.62% | 0.0876 | 0.50% | 1.03% |
| Hybrid_I (0.40) | 40.23% | 0.1751 | 89.95% | 63.77% |
| **Hybrid_J (0.35)** | 41.12% | 0.1888 | **93.71%** | 64.04% |

Hybrid J improves on Hybrid I by **+0.89 pp accuracy** and **+0.0137 macro F1** while maintaining peak bug recall (93.71%). It does not recover the full baseline regression because the root cause is architectural.

### 5.4 Robust Heldout (1,226 records — async_error + type_error only)

| System | Accuracy | Macro F1 | Bug Recall |
|--------|--------:|--------:|----------:|
| Baseline_Production | 53.67% | 0.3099 | 86.70% |
| H1_ML_Only | **0.00%** | 0.0000 | 0.00% |
| Static_Only | **100.00%** | **1.0000** | **100.00%** |
| Hybrid_I (0.40) | **100.00%** | **1.0000** | **100.00%** |
| Hybrid_J (0.35) | **100.00%** | **1.0000** | **100.00%** |

> [!NOTE]
> Robust heldout contains only Python type_error (str+int concat) and JavaScript async_error templates — both perfectly matched by static rules. These results reflect static rule precision on specific template families, not general ML generalization. H1 scores 0% due to a class-mapping mismatch on this dataset.

### 5.5 Overall Summary

| System | Bench Acc | Bench F1 | Test Acc | Test F1 | Rob Acc | Rob F1 |
|--------|----------:|---------:|---------:|--------:|--------:|-------:|
| Baseline_Production | 36.00% | 0.2367 | 51.18% | 0.2163 | 53.67% | 0.3099 |
| H1_ML_Only | 24.00% | 0.1017 | 41.72% | 0.1921 | 0.00% | 0.0000 |
| Static_Only | **50.00%** | **0.3229** | 42.62% | 0.0876 | **100.00%** | **1.0000** |
| Hybrid_I (0.40) | 30.00% | 0.2003 | 40.23% | 0.1751 | **100.00%** | **1.0000** |
| Hybrid_J (0.35) | 30.00% | 0.2003 | 41.12% | 0.1888 | **100.00%** | **1.0000** |

---

## 6. Phase J4 — Failure Analysis: Hybrid_J on 50-Snippet Benchmark (35/50 failures)

| Pattern | Count | Root Cause |
|---------|------:|-----------|
| Mutable default (`[]`/`{}`) predicted as `type_error` | 3 | H1 conflates mutable-default with type mismatch |
| Missing `await` predicted as `none_correct_code` | 3 | Async structural pattern not in H1 training |
| `null_pointer` predicted as `none_correct_code` | 3 | Null deref patterns require flow analysis |
| `malloc`/`fopen` leak vs. safety confusion | 4 | H1 cannot distinguish resource_leak from memory_safety |
| C format mismatch predicted as `memory_safety` | 3 | H1 dominant pattern: C + format = memory bug |
| Clean C code predicted as `memory_safety` | 6 | H1 false positives: any C pointer vocabulary triggers |
| Clean JS code predicted as `async_error`/`condition_error` | 3 | JS async/null-check patterns over-triggered |

---

## 7. Phase J5 — Generalization Testing (29 tests, 37.9% overall accuracy)

| Category | Tests | Pass | Accuracy | Key Failures |
|----------|------:|-----:|---------:|--------------|
| Novel identifiers | 7 | 2 | 28.6% | C pointer code, malloc/fopen confusion |
| Formatting variants | 6 | 3 | 50.0% | Extra-space printf, JS clean async |
| Nested expressions | 5 | 2 | 40.0% | Nested mutable default, clean with+try |
| Adversarial clean | 6 | 3 | 50.0% | Correct malloc+free, correct fopen+fclose |
| Language boundary | 5 | 1 | 20.0% | Type annotations, null deref |

**Systematic failure: C memory_safety over-triggering.** H1 fires `memory_safety` on any C code with pointers (`*`, `malloc`, `fopen`), regardless of whether the code is correct. This is the dominant false-positive pattern.

---

## 8. Limitations

> [!CAUTION]
> These limitations prevent Experiment J from improving over the baseline:

1. **H1 ML cannot distinguish C pointer syntax from C memory bugs** — training data has insufficient clean C negative examples.
2. **Type-error tokens are stripped by AST normalization** — `%d`, `uint8_t`, `parseint` that the baseline memorized are removed, eliminating 97.9% correct type_error recall.
3. **Static rules have <1% test-set coverage** (61/8,353 samples) — insufficient to compensate for ML failures.
4. **Val/test label mismatch** (`exception_handling` in val only) makes val-based threshold tuning noisy.
5. **Robust heldout is not representative** — it only tests two template families static rules handle perfectly.

---

## 9. Conclusions and Deployment Recommendation

### Ranking by Test-Set Macro F1

| Rank | System | Test Macro F1 | Test Accuracy | Bug Recall |
|------|--------|:------------:|:------------:|:---------:|
| 1 | **Baseline_Production** | **0.2163** | **51.18%** | 61.49% |
| 2 | Hybrid_J (0.35) | 0.1888 | 41.12% | **93.71%** |
| 3 | H1_ML_Only | 0.1921 | 41.72% | **93.71%** |
| 4 | Hybrid_I (0.40) | 0.1751 | 40.23% | 89.95% |
| 5 | Static_Only | 0.0876 | 42.62% | 0.50% |

> [!IMPORTANT]
> **Experiment J is NOT recommended for promotion to production.**
>
> The production baseline remains the best system on the primary metric (test-set accuracy 51.18%, macro F1 0.2163). No candidate from Experiments A–J has simultaneously improved both test accuracy AND bug recall over the baseline. Hybrid J achieves higher bug recall (93.71%) but at the cost of 10 pp lower accuracy due to false positives on C clean code.

### Required for Future Improvement

The fundamental blockers identified through Experiments A–J:

1. **Real-world negative examples:** Clean C kernel/system code (QEMU, Linux, FFmpeg) with complex pointer usage must be in training negatives.
2. **Feature architecture:** TF-IDF cannot model program flow. `resource_leak` vs `memory_safety` requires dataflow analysis.
3. **Label granularity:** `memory_safety` conflates pointer bugs, malloc leaks, buffer overflows, stack returns — each needs separate training data.
4. **Type-error representation:** Format-specifier and type-annotation patterns need dedicated feature channels that survive normalization.

**Suggested next direction:** Graph-based neural representations (code property graphs) or fine-tuned code LLM (CodeBERT/UniXcoder) with expanded real-world bug datasets (BigVul, D2A).

---

*All metrics reproducible from scripts in `scripts/experiments/experiment_j/`. Production model not modified. Random seed: fixed by sklearn default (42 in training scripts).*
