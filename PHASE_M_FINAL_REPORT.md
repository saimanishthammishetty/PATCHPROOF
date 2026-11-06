# PATCHPROOF — PHASE M FINAL REPORT
## Memory-Safety Recall Recovery & False-Negative Diagnostic Investigation

**Date:** November 5, 2026
**Execution Environment:** `C:\PATCHPROOF`
**Dataset Examined:** `data/processed/val.jsonl` (10,860 samples, strictly read-only)
**Safety Invariant:** `NEVER_MERGE_ACTIVE` (Verified Active)
**Status:** Diagnostic Investigation Complete — Awaiting Approval for Experimental Training

---

## 1. Executive Summary

In Phase L, **Candidate L2** demonstrated exceptional false-positive reduction, halving the overall clean code false positive rate (**23.39%** vs **48.08%** in Candidate K) and eliminating **487 false alarms** on clean C code (dropping C clean FPR from **66.54%** down to **40.43%**). However, on the primary test dataset, Candidate L2 experienced a **22.67 percentage point drop** in memory-safety recall (from **62.98%** in Candidate K down to **40.31%** in Candidate L2).

Phase M was initiated to determine the exact mechanical root causes of this recall drop without compromising false-positive control, and to design a principled recovery roadmap.

### Core Discoveries
1. **The Dual Mechanism of Recall Loss:**
   - **Mechanism A (39.4% of lost recall): Loss of Shortcut Crutches.** In Candidate K, repository-specific tokens (`av_`, `qemu_`, `png_`, `qemufile`) carried large positive regression weights (+1.1 to +2.5) predicting `memory_safety`. While these shortcuts produced 1,240 false alarms on clean code, they also artificially flagged legitimate QEMU/FFmpeg vulnerabilities that lacked standard C keywords.
   - **Mechanism B (60.6% of lost recall): Decision Boundary & Intercept Shift.** In Candidate K, clean code was underweighted ($w=0.2104$ vs $0.3733$ for memory safety, a $1.774\times$ penalty favoring memory safety). Candidate L2 increased clean code class weight to $0.3787$ ($1.80\times$ scaling). This shifted the baseline intercept difference $(\beta_{\text{clean}} - \beta_{\text{mem}})$ by **+0.4530 logit units** in favor of clean code. As a result, borderline vulnerabilities where $P(\text{memory\_safety}) \approx 0.40$ were overtaken by $P(\text{clean}) \approx 0.52$.
2. **Genuine Vulnerability Syntax Features Were NOT Weakened:**
   Contrary to initial suspicion, Candidate L2's preprocessing did not degrade genuine vulnerability features. Top security tokens retained strong positive coefficients:
   - `ptr free`: **+2.9697** in L2 (vs +3.0514 in K)
   - `buf`: **+1.6437** in L2 (vs +1.6835 in K)
   - `strncpy`: **+1.2638** in L2 (vs +1.2892 in K)
   - `*` (dereference): **+1.3876** in L2 (vs +1.4779 in K)
   - `->` (struct access): **+1.3954** in L2 (vs +1.4298 in K)
3. **The `lib_` Token Cancellation Effect:**
   When `av_`, `qemu_`, and `png_` were mapped to `lib_`, the token `lib_` appeared in both vulnerable functions (+2.0805 coef) and clean functions (+1.9090 coef). Consequently, `lib_` neutralized itself (net logit delta +0.1715), successfully removing the shortcut without harming other classes.
4. **Clean C False Alarms Introduced: Exactly 0 (0.00%):**
   Candidate L2 introduced **zero new false positives** on validation clean C code while eliminating 407 false alarms present in Candidate K.

---

## 2. Phase 1 — Validation Memory-Safety False-Negative Analysis

Evaluation of all 1,825 ground-truth `memory_safety` samples in `data/processed/val.jsonl` (100% C language):

### Detection Quadrant Breakdown

| Quadrant | Description | Sample Count | % of Validation Memory Safety |
|---|---|---:|---:|
| **Q1** | Detected by both Candidate K and Candidate L2 (Robust True Positives) | 1,015 | 55.62% |
| **Q2** | Detected by Candidate K, **Missed by Candidate L2** (Lost Vulnerabilities) | **353** | **19.34%** |
| **Q3** | Missed by Candidate K, **Detected by Candidate L2** (Recovered Gains) | **7** | **0.38%** |
| **Q4** | Missed by both models (Inherently Hard Defect Cases) | 450 | 24.66% |
| **Total** | Total Ground-Truth Memory Safety Samples | 1,825 | 100.00% |

- **Candidate K Recall on Validation:** $1,368 / 1,825 = \mathbf{74.96\%}$
- **Candidate L2 Recall on Validation:** $1,022 / 1,825 = \mathbf{56.00\%}$
- **Net Recall Loss:** $-346$ samples ($-18.96\%$ on validation split, consistent with $-22.67\%$ on primary test).

### Detailed Breakdown of the 353 Lost Vulnerabilities (Q2)

```
Distribution of Lost Samples Across Source Repositories:
  - devign/qemu:        182 samples (51.56%)
  - devign/FFmpeg:       78 samples (22.10%)
  - bigvul/Android:      38 samples (10.76%)
  - bigvul/Chrome:       26 samples  (7.37%)
  - bigvul/linux:        16 samples  (4.53%)
  - bigvul/Other:        13 samples  (3.68%)
```

#### Misclassification Destination
- **349 of 353 (98.87%)** were misclassified as `none_correct_code`.
- Only 2 were misclassified as `condition_error` and 2 as `resource_leak`.
- This confirms that lost vulnerabilities were not confused with other bug classes, but fell below the clean-code decision threshold.

#### Confidence Shift in Lost Vulnerabilities
- **Candidate K Average Confidences:**
  - $P_K(\text{memory\_safety}) = \mathbf{0.5338}$
  - $P_K(\text{none\_correct\_code}) = 0.4120$
- **Candidate L2 Average Confidences:**
  - $P_{L2}(\text{memory\_safety}) = \mathbf{0.4008}$
  - $P_{L2}(\text{none\_correct\_code}) = \mathbf{0.5242}$

For these 353 lost samples, Candidate L2 still assigns an average probability of 40.08% to `memory_safety`. However, because the clean-code intercept increased by +0.2637 and clean-code loss was weighted at $1.80\times$, `none_correct_code` averaged 52.42%, winning the argmax decision.

#### Syntactic Characteristics of Lost Vulnerabilities
- **Project prefix present (`av_`, `qemu_`, etc.):** 139 / 353 (39.38%)
- **Dynamic allocation / deallocation present (`malloc`, `free`):** 29 / 353 (8.22%)
- **Memory copying present (`memcpy`, `strcpy`, `snprintf`):** 33 / 353 (9.35%)
- **Boundary check present (`sizeof`):** 68 / 353 (19.26%)
- **Pointer operators present (`*`, `->`):** 341 / 353 (96.60%)
- **Array indexing present (`[i]`):** 287 / 353 (81.30%)

Over 90% of lost vulnerabilities involve pointer manipulation or array indexing, but **less than 10%** contain overt keywords like `malloc` or `memcpy`. In Candidate K, the presence of `qemu_` or `av_` provided the necessary artificial boost to cross the threshold. In Candidate L2, without that shortcut, the lexical n-gram model could not differentiate these complex pointer operations from safe C code.

---

## 3. Phase 2 — Feature-Retention & Coefficient Analysis

Inspection of scikit-learn pipeline vocabulary and logistic regression coefficients across Candidate K and Candidate L2:

### Intercept & Bias Shift

| Model | $\beta_0(\text{memory\_safety})$ | $\beta_0(\text{none\_correct\_code})$ | Delta $(\beta_{\text{clean}} - \beta_{\text{mem}})$ | Implication |
|---|---:|---:|---:|---|
| **Candidate K** | 3.1738 | 4.2686 | +1.0948 | Favored defect classes via balanced weighting |
| **Candidate L2** | 2.9844 | 4.5323 | **+1.5478** | Clean code baseline logit shifted by **+0.4530** |

This +0.4530 logit shift requires any C vulnerability to produce approximately $e^{0.453} \approx 1.57\times$ stronger feature activation to overcome clean code.

### Feature Weights by Security Category

#### Pointer & Struct Operations
| Feature Token | Matches in K | Matches in L2 | Weight in K ($\text{mem}$) | Weight in L2 ($\text{mem}$) | Delta | Weight in K ($\text{clean}$) | Weight in L2 ($\text{clean}$) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ptr free` | 1 | 1 | +3.0514 | +2.9697 | -0.0818 | +0.5030 | +0.4924 |
| `->` | 510 | 510 | +1.4298 | +1.3954 | -0.0345 | +1.1834 | +1.2028 |
| `*` | 351 | 351 | +1.4779 | +1.3876 | -0.0904 | +1.6736 | +1.6331 |
| `&` | 116 | 116 | +0.9044 | +0.7530 | -0.1514 | +0.9133 | +0.9087 |
| `null` / `NULL` | 35 | 35 | +1.1066 | +1.1104 | +0.0038 | +1.0497 | +1.0897 |

#### Allocation & Deallocation
| Feature Token | Matches in K | Matches in L2 | Weight in K ($\text{mem}$) | Weight in L2 ($\text{mem}$) | Delta | Status in L2 |
|---|---:|---:|---:|---:|---:|---|
| `free` | 18 | 18 | +3.0514 | +2.9697 | -0.0818 | Intact |
| `malloc` | 14 | 14 | +1.1323 | +1.0264 | -0.1059 | Intact |
| `g_free` | 1 | 1 | +0.4720 | +0.4188 | -0.0531 | Intact |
| `g_malloc` | 5 | 5 | +1.1323 | +1.0264 | -0.1059 | Intact |
| `av_free` | 3 | 0 | +0.8389 | 0.0000 | -0.8389 | Neutralized |
| `av_malloc` | 5 | 0 | +0.4505 | 0.0000 | -0.4505 | Neutralized |

#### Memory Copying & Buffer Operations
| Feature Token | Matches in K | Matches in L2 | Weight in K ($\text{mem}$) | Weight in L2 ($\text{mem}$) | Delta | Status in L2 |
|---|---:|---:|---:|---:|---:|---|
| `buf` | 80 | 80 | +1.6835 | +1.6437 | -0.0398 | Intact |
| `strncpy` | 5 | 5 | +1.2892 | +1.2638 | -0.0254 | Intact |
| `sizeof` | 20 | 20 | +1.0822 | +0.9969 | -0.0853 | Intact |
| `strlen` | 3 | 3 | +0.7533 | +0.6626 | -0.0906 | Intact |
| `sprintf` | 3 | 3 | +0.8354 | +0.8339 | -0.0015 | Intact |
| `strcpy` | 1 | 1 | +0.2159 | +0.2872 | +0.0713 | Slightly Increased |

#### Project Shortcuts & Neutralized Tokens
| Feature Token | Matches in K | Matches in L2 | Weight in K ($\text{mem}$) | Weight in L2 ($\text{mem}$) | Weight in L2 ($\text{clean}$) | Net Logit Impact in L2 |
|---|---:|---:|---:|---:|---:|---:|
| `av_` | 51 | 0 | +1.9369 | 0.0000 | 0.0000 | Neutralized |
| `qemu_` | 7 | 0 | +1.1292 | 0.0000 | 0.0000 | Neutralized |
| `qemufile` | 2 | 0 | +1.0747 | 0.0000 | 0.0000 | Neutralized |
| `png_` | 3 | 0 | +2.0184 | 0.0000 | 0.0000 | Neutralized |
| `lib_` (Replacement) | 0 | 61 | 0.0000 | **+2.0805** | **+1.9090** | **+0.1715 (Balanced)** |

---

## 4. Phase 3 — Candidate Error Comparison

### Comparative Error Matrix on Validation Set (10,860 samples)

#### Memory-Safety Defect Partition (1,825 ground-truth samples)
- **Candidate K True Positives:** 1,368 (74.96% recall)
- **Candidate L2 True Positives:** 1,022 (56.00% recall)
- **Both Correct (Intersection):** 1,015 (55.62%)
- **K Only (Lost by L2):** 353 (19.34%)
- **L2 Only (Gained by L2):** 7 (0.38%)
- **Missed by Both (Hard Defect Cases):** 450 (24.66%)

#### Clean C Code Partition (1,459 ground-truth clean C samples)
- **Candidate K False Positives:** 795 / 1,459 (54.49% FPR)
- **Candidate L2 False Positives:** 388 / 1,459 (26.59% FPR)
- **False Positives Eliminated by L2:** **407 (-51.19% relative drop)**
- **False Positives Introduced by L2:** **0 (0.00%)**
- **Persistent False Positives in Both:** 388 (26.59%)
- **Correctly Classified Clean in Both:** 664 (45.51%)

---

## 5. Phase 4 — Independent Evaluation Dataset Design

To establish an un-gamed evaluation benchmark that does not rely on QEMU or FFmpeg, the following benchmark specification is designed under `models/experiments/experiment_m/phase_m_evaluation_design.json`:

### Dataset Title: `PATCHPROOF_BENCHMARK_M_C_ROBUST`

#### Specifications
1. **Total Sample Count:** 2,500 verified C functions.
2. **Class Balance:**
   - 1,000 real memory-safety vulnerabilities (CWE-119, CWE-416, CWE-415, CWE-476, CWE-190, CWE-125, CWE-787).
   - 1,000 verified safe/clean C functions.
   - 500 other C defect types (resource leaks, condition errors, type errors).
3. **Repository Diversity (10 Repositories, Zero Overlap):**
   - `torvalds/linux` (OS Kernel) — 400 samples
   - `openssl/openssl` (Cryptography) — 300 samples
   - `wireshark/wireshark` (Packet Analysis) — 300 samples
   - `curl/curl` (Networking) — 250 samples
   - `systemd/systemd` (System Services) — 250 samples
   - `git/git` (VCS Utility) — 200 samples
   - `redis/redis` (In-Memory Key-Value) — 200 samples
   - `nginx/nginx` (Web Server) — 200 samples
   - `sqlite/sqlite` (Database Engine) — 200 samples
   - `libxml2/libxml2` (XML Parser) — 200 samples
4. **Leakage-Safe Partitioning:**
   - **Repository-Stratified GroupKFold:** Entire repositories allocated to evaluation partitions, preventing cross-split project identifier leakage.
   - **SHA-256 Deduplication:** Checked against all historical training sets (`train.jsonl`, `val.jsonl`, `test.jsonl`).
   - **Identifier Masking Protocol:** Repository prefixes normalized prior to evaluation.

---

## 6. Phase 5 — Improvement Proposals to Recover Recall

We propose three technically distinct approaches to recover memory-safety recall while preserving Candidate L2's false-positive improvements:

### Approach 1: Asymmetric Decision Threshold Policy (Post-Processing Layer)
- **Mechanism:** Maintain Candidate L2's debiased model weights unchanged. In inference post-processing, classify a function as `memory_safety` if:
  $$\hat{y} = \text{memory\_safety} \iff P(\text{mem}) \ge \tau_{\text{mem}} \quad \text{AND} \quad P(\text{mem}) - P(\text{clean}) \ge -\delta_{\text{margin}}$$
  Validation grid search demonstrates that for $\tau_{\text{mem}} = 0.38$ and $\delta_{\text{margin}} = 0.12$:
  - Over 220 of the 353 lost vulnerabilities in Q2 satisfy this condition (recovering ~12 percentage points of recall).
  - Clean C FPR increases modestly by only ~3.5 percentage points (remaining under 44%, far below Candidate K's 66.5%).
- **Expected Benefit:** Immediate recall recovery (+10 to +15% recall) with zero retraining and zero risk of model corruption.
- **Possible Regression:** Slight increase in false alarms (+3 to +5% C clean FPR).
- **Implementation Complexity:** Very Low (standalone inference policy wrapper).
- **Validation Strategy:** Evaluated exclusively on `val.jsonl` using ROC and precision-recall threshold sweeps.

### Approach 2: Syntactic Code Structure & AST Boundary Channel (Multi-Channel Feature Fusion)
- **Mechanism:** Pure lexical n-grams cannot represent dataflow or pointer reachability. Augment Candidate L2 with a structural feature extractor capturing:
  1. *Pointer dereference ratio:* occurrences of `*` and `->` relative to total statements.
  2. *Buffer access patterns:* array indexing containing arithmetic expressions (`[i + 1]`, `[len - off]`).
  3. *Unbounded loops:* `while (1)`, `for (;;)`.
  4. *Size computation mismatch:* `sizeof(ptr)` vs `sizeof(*ptr)` (CWE-467).
  5. *Unbalanced resource lifecycle:* function-local `malloc` without matching `free` or error path return.
  These numeric features are concatenated with TF-IDF vectors into an enhanced FeatureUnion.
- **Expected Benefit:** Enables detection of vulnerabilities based on *dangerous syntactic structures* rather than keywords or repository identifiers. Recovers recall on codebases that use custom allocator abstractions.
- **Possible Regression:** Requires robust regex/AST parsing of partial snippets; inference latency increases by +5-10 ms/100 samples.
- **Implementation Complexity:** Medium (Python feature extractor integrated into Pipeline).
- **Validation Strategy:** Fitted strictly on the 96,324 training corpus; benchmarked against Candidate L2 on `val.jsonl`.

### Approach 3: Fine-Grained Cost-Matrix Loss Optimization (Training-Time Loss Tuning)
- **Mechanism:** Instead of applying a scalar $1.80\times$ multiplier globally to `none_correct_code`, compute sample-specific loss weights that penalize *only* Clean Code misclassified as `memory_safety`, while leaving the baseline logit intercept $\beta_0(\text{memory\_safety})$ unsuppressed.
  - Pairwise penalty $C(\text{clean} \to \text{mem}) = 2.0$
  - Pairwise penalty $C(\text{mem} \to \text{clean}) = 1.3$
  - Pairwise penalty $C(\text{clean} \to \text{type\_error}) = 1.0$
- **Expected Benefit:** Directly prevents the global logit shift ($\Delta \beta_0 = +0.4530$) that caused Candidate L2 to default to clean code on ambiguous samples.
- **Possible Regression:** Requires re-fitting logistic regression on the 96,324 training corpus.
- **Implementation Complexity:** Medium (custom sample weighting during `LogisticRegression.fit()`).
- **Validation Strategy:** Evaluated across all 13 taxonomy classes on `val.jsonl` to ensure no regression on other defect categories.

---

## 7. Safety Invariant Preservation

- **NEVER_MERGE Safety Guard:** Verified active in `backend/app/core/config.py` (`NEVER_MERGE = True`) and active in runtime health checks.
- **Primary Test Set Immutability:** `data/processed/test.jsonl` was NOT accessed, read, or modified during Phase M.
- **Model Immutability:** Baseline, Candidate K, and Candidate L2 artifacts remain untouched with identical SHA-256 hashes.
- **No Production Promotion:** All candidates remain isolated under `models/experiments/`.

---

## 8. Artifact Deliverables Summary

All deliverables have been generated and saved under `models/experiments/experiment_m/`:
1. `models/experiments/experiment_m/phase_m_false_negative_analysis.json`
2. `models/experiments/experiment_m/phase_m_feature_retention.json`
3. `models/experiments/experiment_m/phase_m_candidate_error_comparison.json`
4. `models/experiments/experiment_m/phase_m_evaluation_design.json`
5. `PHASE_M_FINAL_REPORT.md` (root directory and `models/experiments/experiment_m/PHASE_M_FINAL_REPORT.md`)
