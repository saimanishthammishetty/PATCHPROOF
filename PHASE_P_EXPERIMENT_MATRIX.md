# PATCHPROOF — PHASE P: EXPERIMENTAL MATRIX & BENCHMARK O EVALUATION

**Document:** Complete Experimental Matrix & Frozen Benchmark O Evaluation
**Phase:** Phase P — Comprehensive Evidence-Based Project Synthesis
**Date:** 2026-11-06 01:20:00 UTC
**Safety Invariant:** `NEVER_MERGE_ACTIVE = True` (Globally Enforced)
**Root Repository:** [`C:\PATCHPROOF`](file:///C:/PATCHPROOF)

---

## 1. CHRONOLOGICAL EXPERIMENTAL HISTORY (EXPERIMENTS A THROUGH O.2.1)

This matrix consolidates all experimental phases conducted throughout the development of PATCHPROOF's machine learning components. Unverified or unavailable details are explicitly marked.

| Phase / Exp | Objective | Method | Dataset Used | Key Metric / Main Result | Critical Limitations | Final Decision |
|---|---|---|---|---|---|:---:|
| **Baseline (Prod)** | Establish multi-class static defect classifier for code snippets. | TF-IDF (char 3–5, word 1–2, 10k max features) + Logistic Regression ($C=1.0$). | Initial processed split (`train.jsonl` ~24k–78k, `val.jsonl`). | Macro F1: ~0.59 on internal test; Benchmark O Acc: 33.38%, Clean FPR: 61.52%, Mem Recall: 1.82%. | Severe memory-safety under-detection (1.82% recall); 61.52% false alarm rate on clean C code. | **Preserved in Production** (Isolated baseline artifact `bug_detector.joblib`). |
| **Exp A** | Reduce identifier overfitting via lexical normalization. | Regex replacement of identifiers with abstract tokens (`var_0`, `func_0`). | Processed training subset. | Neutral to negative Macro F1 shift (-0.02); reduced syntax nuance. | Stripped critical domain tokens and standard library semantics (`malloc`, `free`). | **REJECTED** |
| **Exp B** | Filter corpus-specific vocabulary via frequency cutoffs. | Tuned `min_df` and `max_df` bounds in `TfidfVectorizer`. | Processed training subset. | Marginal shift in vocabulary size; no meaningful recall recovery. | Did not resolve severe class imbalance or memory safety failure. | **REJECTED** |
| **Exp C** | Mitigate clean-code dominance in training distribution. | Controlled hard-negative sampling; capped `none_correct_code` at 10k samples. | Downsampled training split. | Increased bug recall (+4.2 pp), but clean-code false positive rate surged. | Shifted operating threshold without improving underlying discriminative power. | **REJECTED** |
| **Exp D** | Prioritize minority defect classes via loss weighting. | Tuned scikit-learn `class_weight` multipliers (damped clean, boosted minority). | Processed training split. | Boosted minority class recall on in-distribution validation set. | Generalized poorly across external unseen repositories; elevated clean FPR. | **REJECTED** |
| **Exp E (E1–E3)** | Determine optimal n-gram feature representation. | Ablated E1 (Word-only, 5k), E2 (Char-only, 5k), and E3 (Balanced Union: 4k Word + 1k Char). | Training split + held-out evaluation. | E3 achieved superior balance; char n-grams capture syntax tokens (`*`, `->`), word captures keywords. | Lexical bias persisted regardless of n-gram parameterization. | **ADOPTED FOR CANDIDATES** (E3 adopted as feature baseline). |
| **Exp F (F1–F2)** | AST scope-aware normalization across Python, JS, and C. | Python `ast` visitor, JS/C regex grammar replacement; F1 (AST only) vs F2 (AST weighted). | Multi-dataset validation. | F1 normalized scope successfully, but F2 suffered severe recall regression on novel C syntax. | Rigid AST parser failed on diverse external coding conventions. | **PARTIALLY ADOPTED** (Retained for Python in `DebugService`; rejected for C ML). |
| **Exp G (G1–G3)** | Investigate recall-focused loss and threshold candidates. | G1 (Balanced recall), G2 (Aggressive recall), G3 (Clean tokens). | Held-out evaluation set. | G2 achieved higher recall (>70%), but clean-code FPR exceeded 50%. | Unacceptable false alarm fatigue for real developer workflows. | **REJECTED** (G2 abandoned; baseline retained). |
| **Exp H** | Audit robust evaluation suite and explore dual-channel features. | Audited `robust_heldout_test.jsonl`; separated lexical vocabulary from structural syntax. | Robust held-out test set ($N=1,226$). | Diagnosed widespread performance degradation on out-of-distribution repos. | Exposed vulnerability of purely lexical classifiers to repository style shifts. | **CONFIRMED FINDING** (Motivated Experiment I and J). |
| **Exp I** | Combine static AST rules with statistical ML classification. | Hybrid architecture: deterministic AST rules for high-confidence syntax patterns + ML fallback. | Multi-language validation snippets. | Precision reached 100% on specific patterns (Python mutable defaults, JS loose equality). | Limited to narrow defect patterns with deterministic AST signatures. | **INTEGRATED INTO APPLICATION** (`DebugService._localize_python_defect`). |
| **Exp J** | Investigate cross-split leakage and develop curated adapter. | Audited commit and symbol overlap; discovered QEMU/FFmpeg data leakage in historical splits. | Training and primary test splits. | Proved that models learned repository-specific tokens rather than generalizable defect patterns. | Cross-dataset leakage invalidated earlier high benchmark scores. | **POLICY CREATED** (Strict repository isolation mandated). |
| **Exp K** | Retrain candidate model with curated Big-Vul data augmentation. | Big-Vul curated adapter + class weighting; trained Candidate K (`bug_detector_candidate_k.joblib`). | Curated Big-Vul + Devign ($N \approx 96\text{k}$). | High memory-safety recall (49.09% on Benchmark O; 60.50% overall bug recall). | **Lexical Project Bias:** Learned spurious correlations with C kernel tokens (`lib_`, `dev_`); 40.00% clean FPR. | **ISOLATED / NOT PROMOTED** (Kept as high-recall reference). |
| **Phase L (L1–L2)** | Diagnose and eliminate lexical project bias in Candidate K. | L1: Feature weight audit identified `lib_` bias; L2: Token masking and dual-channel debiased fusion. | Processed training and validation sets. | Candidate L2 slashed clean-code FPR to **22.00%** (275/1,250 on Benchmark O — 18.0 pp lower than K). | Over-correction: Suppressed posterior probability $p(\text{memory\_safety})$, reducing recall to 21.82%. | **ISOLATED / NOT PROMOTED** (Kept as high-precision candidate). |
| **Phase M** | Validation analysis of Candidate L2 recall suppression. | Analyzed posterior distributions; confirmed probabilities clustered in $[0.20, 0.40]$ range. | Validation set only (`val.jsonl`). | Proved defect discrimination remained active, but was masked by standard argmax decision rule. | Did not test inference-time boundary adjustments. | **FOUNDATION FOR PHASE N** |
| **Phase N** | Decision-boundary optimization without retraining. | Grid sweep over $\tau \in [0.15, 0.45]$ and $\delta \in [-0.25, 0.10]$ applied to Candidate L2. | Validation set only (`val.jsonl`). | Identified optimal Pareto boundary: $\tau = 0.30, \delta = -0.12$. | Validation data optimization required independent frozen verification. | **FROZEN FOR PHASE O** |
| **Phase N.1** | Results integrity audit of Phase N sweep. | Audited script `run_phase_n.py` and raw JSON logs; verified monotonic promotion properties. | Validation set results. | Resolved parameter discrepancy ($\tau=0.30$ vs $0.34$ Pareto); confirmed demotion impossibility. | Evaluated only on validation split. | **PASSED AUDIT** |
| **Phase O** | Design independent C security benchmark excluding QEMU & FFmpeg. | Established strict protocol: 7 target repos, verified CVE/CWE provenance, 0% test overlap. | Target repositories (Linux, OpenSSL, curl, Redis, Wireshark, nginx, SQLite). | Designed 1,450-sample benchmark specification; quarantined nginx/SQLite as unavailable offline. | Restricted to offline sources. | **APPROVED PROTOCOL** |
| **Phase O.1** | Data acquisition & ground-truth verification under quarantine policy. | Option B curated acquisition: 41 core unseen-commit + 159 curated same-commit distinct functions. | Linux, OpenSSL, Wireshark, curl, Redis. | Built `phase_o_benchmark_dataset.jsonl` (1,250 clean, 200 vulnerable, 55 memory safety). | High repository concentration (86.28% Linux). | **DATASET FROZEN** (SHA-256: `caa7abe4...`). |
| **Phase O.1.1** | Exhaustive benchmark integrity and leakage audit. | 14-task verification: exact counts, JSONL syntax, CWE mapping, 0% commit/symbol leakage. | `phase_o_benchmark_dataset.jsonl` vs historical sets. | 14/14 audits passed; verified 0% leakage into test or validation sets; explained -1 CWE-388 drafting typo. | Dependent on negative static filtering for clean code. | **BENCHMARK CERTIFIED** |
| **Phase O.2** | Frozen non-tuned evaluation across all 4 candidate configurations. | Evaluated Baseline, Candidate K, Candidate L2, and Phase N Policy on Benchmark O. | `phase_o_benchmark_dataset.jsonl` ($N=1,450$). | Baseline: 33.38% Acc, 1.82% Mem Rec; K: 55.03% Acc, 49.09% Mem Rec; L2: 69.17% Acc, 22.00% FPR; Phase N: 64.83% Acc, 29.09% Mem Rec, 27.36% FPR. | Small memory-safety support ($N=55$); Linux dominance. | **EVALUATION COMPLETED** |
| **Phase O.2.1** | Strictly read-only mathematical consistency audit. | Verified all 15 report claims directly from 13x13 confusion matrices; analyzed Macro F1 denominators. | Saved Phase O.2 confusion matrices. | **15 / 15 claims PASSED**; Macro F1 rankings invariant to denominator (11 vs 13 vs 8 classes). | Row-by-row prediction vectors not serialized in separate flat file. | **AUDIT PASSED / CERTIFIED** |

---

## 2. CONSOLIDATED BENCHMARK O PERFORMANCE COMPARISON

The frozen evaluation on [`models/experiments/experiment_o/phase_o_benchmark_dataset.jsonl`](file:///C:/PATCHPROOF/models/experiments/experiment_o/phase_o_benchmark_dataset.jsonl) ($N=1,450$; 1,250 clean, 200 vulnerable, 55 memory-safety) yielded the following audited results:

| Metric | Production Baseline | Candidate K | Candidate L2 | Phase N Policy (`tau=0.30`, `delta=-0.12`) |
|---|:---:|:---:|:---:|:---:|
| **Overall Accuracy** | 33.38% (484 / 1,450) | 55.03% (798 / 1,450) | **69.17% (1,003 / 1,450)** | 64.83% (940 / 1,450) |
| **Weighted F1** | 45.03% | 63.70% | **72.99%** | 70.33% |
| **Clean Code False Positive Count** | 769 / 1,250 | 500 / 1,250 | **275 / 1,250** | 342 / 1,250 |
| **Clean Code False Positive Rate (FPR)** | 61.52% | 40.00% | **22.00%** | 27.36% |
| **Overall Vulnerable False Negatives** | 114 / 200 | **79 / 200** | 122 / 200 | 112 / 200 |
| **Overall Bug False Negative Rate (FNR)** | 57.00% | **39.50%** | 61.00% | 56.00% |
| **Overall Vulnerable Recall** | 43.00% (86 / 200) | **60.50% (121 / 200)** | 39.00% (78 / 200) | 44.00% (88 / 200) |
| **Overall Vulnerable Precision** | 10.06% (86 / 855) | 19.48% (121 / 621) | **22.10% (78 / 353)** | 20.47% (88 / 430) |
| **Overall Vulnerable F1** | 16.30% | **29.48%** | 28.21% | 27.94% |
| **Memory-Safety True Positives** | 1 / 55 | **27 / 55** | 12 / 55 | 16 / 55 |
| **Memory-Safety Recall** | 1.82% | **49.09%** | 21.82% | 29.09% |
| **Memory-Safety Precision** | 1.89% (1 / 53) | **7.05% (27 / 383)** | 6.74% (12 / 178) | 6.23% (16 / 257) |
| **Memory-Safety F1** | 1.85% | **12.33%** | 10.30% | 10.26% |
| **Macro F1 (Union 11 Classes)** | 4.99% | 9.79% | **10.39%** | 10.12% |
| **Macro F1 (Taxonomy 13 Classes)** | 4.22% | 8.29% | **8.79%** | 8.56% |
| **Macro F1 (Supported 8 Classes)** | 6.86% | 13.47% | **14.28%** | 13.91% |

---

## 3. DEEP-DIVE ANALYSIS OF KEY EXPERIMENTAL FINDINGS

### 3.1 Candidate K's Detection Advantage vs. Lexical Shortcut Learning
Candidate K achieved the highest raw vulnerable recall on Benchmark O: detecting **121 of 200 vulnerable functions (60.50%)** and **27 of 55 memory-safety flaws (49.09%)**.

However, Phase L diagnostics revealed that this apparent sensitivity was driven largely by **lexical shortcut learning**:
- Candidate K learned massive positive weights on ubiquitous C identifiers and Linux kernel subsystem prefixes (such as `lib_`, `dev_`, `sys_`, `kzalloc`, `spin_lock`).
- Because training data from Devign and Big-Vul featured real C vulnerabilities containing these standard kernel tokens, the classifier learned that the presence of `lib_` indicated a high probability of a memory safety defect.
- When evaluated against 1,250 clean C functions from Linux and OpenSSL, Candidate K triggered false alarms on **500 clean functions (40.00% FPR)**. In a real-world developer environment, an SCA tool that flags 4 out of every 10 clean functions is operationally unusable due to alert fatigue.

### 3.2 Candidate L2's Clean-Code Specificity Advantage
Candidate L2 was engineered specifically to dismantle this shortcut by masking `lib_` tokens and applying dual-channel feature fusion.

The debiasing intervention succeeded emphatically at its primary objective:
- Clean-code false alarms dropped from 500 down to **275 (22.00% FPR)** — an **18.0 percentage point reduction** in false alarms.
- Overall accuracy increased to **69.17%**, and Candidate L2 attained the highest Weighted F1 (72.99%) and highest Macro F1 across all denominator variants (10.39% across 11 union classes; 14.28% across 8 supported classes).

### 3.3 Phase N's Intermediate Operational Trade-Off
The trade-off of Candidate L2's debiasing was **recall compression**: eliminating spurious features depressed $p(\text{memory\_safety})$ below standard argmax thresholds, causing memory-safety recall to fall to 21.82% (12/55).

Phase N resolved this trade-off through an inference-time threshold policy ($\tau=0.30, \delta=-0.12$):
- **Recall Recovery:** Memory-safety true positives increased from 12 to **16 (29.09% recall, a +7.27 pp recovery)**. Total vulnerable detections increased from 78 to **88 (44.00% recall)**.
- **Controlled FPR Cost:** Clean-code false alarms rose modestly by 67 (from 275 to 342, or 27.36% FPR), which remains **12.64 percentage points lower than Candidate K's 40.00% FPR (avoiding 158 of K's false alarms)**.
- **Epistemological Correction:** Phase N is an **intermediate operational compromise**, not a mathematical Pareto improvement over K or L2. Candidate K still possesses higher recall (49.09%), while Candidate L2 retains lower FPR (22.00%). Phase N offers a balanced operating point for security teams willing to accept 67 additional reviews to detect 10 additional confirmed vulnerabilities.

### 3.4 Linux-Heavy Benchmark Composition (86.28%)
Benchmark O's composition must be evaluated with strict scientific restraint:
- Total records: 1,450.
- Linux: 1,251 records (**86.28%**; 1,066 clean, 185 vulnerable).
- OpenSSL: 193 records (**13.31%**; 178 clean, 15 vulnerable).
- Wireshark: 2 records (clean).
- curl: 2 records (clean).
- Redis: 2 records (clean).
- **Implication:** While Benchmark O proves repository independence relative to QEMU and FFmpeg, it is predominantly a **Linux kernel benchmark** with secondary OpenSSL coverage. Claims of universal multi-repository generalization across the C ecosystem cannot be supported by the data.

### 3.5 Small Memory-Safety Sample Size ($N=55$)
Across the 200 vulnerable functions in Benchmark O, exactly **55 functions** belong to the `memory_safety` category.
- With $N=55$, each single true positive represents approximately **1.82 percentage points** of recall.
- Candidate L2's 12 detections vs Phase N's 16 detections represents a delta of only **4 individual functions**.
- The 95% Wilson score confidence interval for Phase N memory-safety recall ($16/55$) spans $[18.72\%, 42.14\%]$, while Candidate K ($27/55$) spans $[36.37\%, 61.94\%]$.
- Because these confidence intervals overlap, performance differences on memory safety must be interpreted as directional indicators rather than conclusive, statistically separable margins.

### 3.6 Limitations of Clean-Label Assurance
All 1,250 clean functions in Benchmark O were verified using:
1. Negative defect filtering via static analysis rules (`StaticAnalyzer.analyze_c`).
2. Release and commit history inspection confirming absence of subsequent vulnerability disclosures.
- **Caveat:** Negative static analysis proves only that code does not trigger existing heuristic rule patterns; it does not constitute a mathematical proof of total bug freedom.

### 3.7 Absence of Saved Row-Level Predictions
During Phase O.2, full evaluation results were captured via 13x13 confusion matrices, per-class summaries, repository breakdowns, and subgroup files. However, flat per-sample prediction arrays (e.g. sample-by-sample tabular predictions) were not written to a standalone flat file. Phase O.2.1 successfully audited all mathematical claims directly from the contingency matrices, but saving raw row-level predictions is identified as an immediate technical enhancement for future evaluation protocols.
