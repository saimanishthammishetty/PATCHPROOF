"""
PATCHPROOF Phase L — Investigation B: Clean C False Positive Diagnosis
Analyzes the 1,240 clean C samples incorrectly classified as memory_safety.
Compares them against True Negatives, True Positives, and False Negatives.
Outputs: models/experiments/experiment_l/phase_l_false_positive_analysis.json
"""

import os
import sys
import json
import re
import numpy as np
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List
import joblib

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_k"
EXP_L_DIR = ROOT_DIR / "models" / "experiments" / "experiment_l"
EXP_L_DIR.mkdir(parents=True, exist_ok=True)

PROBE_TOKENS = [
    "malloc", "free", "calloc", "realloc", "sizeof", "memcpy", "memset", "memmove",
    "strcpy", "strncpy", "sprintf", "snprintf", "strlen", "strcmp", "strcat",
    "NULL", "return", "if", "for", "while", "switch", "case", "break", "goto",
    "*", "->", "&", "[", "]", "(", ")", "{", "}", ";", ",", "=", "==", "!=",
    "char", "int", "void", "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "size_t", "ssize_t", "struct", "static", "const", "unsigned", "long", "short"
]

def analyze_tokens_and_syntax(code_list: List[str]) -> Dict[str, Any]:
    token_counts = Counter()
    line_lengths = []
    char_lengths = []

    for code in code_list:
        lines = code.split("\n")
        line_lengths.append(len(lines))
        char_lengths.append(len(code))

        # Word and symbol tokenization
        tokens = re.findall(r'[a-zA-Z_]\w+|->|[<>=!+\-*/&|~^%]+|[\[\]{}();,]', code)
        for t in tokens:
            if t in PROBE_TOKENS:
                token_counts[t] += 1

    n = max(1, len(code_list))
    # Frequency per sample
    freq_per_sample = {t: round(token_counts[t] / n, 4) for t in PROBE_TOKENS}

    return {
        "sample_count": len(code_list),
        "mean_lines": round(float(np.mean(line_lengths)), 2) if line_lengths else 0,
        "median_lines": round(float(np.median(line_lengths)), 2) if line_lengths else 0,
        "mean_chars": round(float(np.mean(char_lengths)), 2) if char_lengths else 0,
        "token_frequencies_per_sample": freq_per_sample,
        "top_probe_tokens": dict(sorted(freq_per_sample.items(), key=lambda x: -x[1])[:15])
    }

def diagnose_c_false_positives():
    print("=" * 80)
    print("PHASE L: INVESTIGATION B — CLEAN C FALSE POSITIVE DIAGNOSIS")
    print("=" * 80)

    # Load candidate model
    candidate_path = EXP_K_MODEL_DIR / "bug_detector_candidate_k.joblib"
    assert candidate_path.exists(), f"FATAL: Candidate model {candidate_path} missing!"
    print(f"[LOAD] Loading candidate model from {candidate_path}...")
    model = joblib.load(candidate_path)

    # Load test split
    test_path = PROCESSED_DIR / "test.jsonl"
    test_samples = []
    with open(test_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_samples.append(json.loads(line))

    # Filter to C samples
    c_samples = [s for s in test_samples if s["language"] == "c"]
    print(f"[TEST] Extracted {len(c_samples):,} C samples from test.jsonl")

    # Get model predictions and probabilities
    X_c = [s["original_code"] for s in c_samples]
    y_true_c = [s["bug_category"] for s in c_samples]

    print("[EVAL] Running inference and extracting class probabilities...")
    y_pred_c = model.predict(X_c)
    probs_c = model.predict_proba(X_c)
    classes = list(model.classes_)

    mem_idx = classes.index("memory_safety")
    clean_idx = classes.index("none_correct_code")

    # Group samples into 4 cohorts
    clean_c_fp_mem = []  # True = clean, Pred = memory_safety (THE 1,240 FP SAMPLES)
    clean_c_tn = []      # True = clean, Pred = clean (TN)
    mem_c_tp = []        # True = memory_safety, Pred = memory_safety (TP)
    mem_c_fn_clean = []  # True = memory_safety, Pred = clean (FN)
    mem_c_fn_other = []  # True = memory_safety, Pred = other bug (FN)

    fp_confidences = []
    fp_clean_margins = []  # P(mem) - P(clean)
    tn_confidences = []
    tp_confidences = []

    fp_repos = Counter()
    tn_repos = Counter()

    for i, s in enumerate(c_samples):
        true_l = y_true_c[i]
        pred_l = y_pred_c[i]
        p_mem = probs_c[i][mem_idx]
        p_clean = probs_c[i][clean_idx]
        repo = s.get("repository", "unknown")

        if true_l == "none_correct_code":
            if pred_l == "memory_safety":
                clean_c_fp_mem.append(s["original_code"])
                fp_confidences.append(float(p_mem))
                fp_clean_margins.append(float(p_mem - p_clean))
                fp_repos[repo] += 1
            elif pred_l == "none_correct_code":
                clean_c_tn.append(s["original_code"])
                tn_confidences.append(float(p_clean))
                tn_repos[repo] += 1
        elif true_l == "memory_safety":
            if pred_l == "memory_safety":
                mem_c_tp.append(s["original_code"])
                tp_confidences.append(float(p_mem))
            elif pred_l == "none_correct_code":
                mem_c_fn_clean.append(s["original_code"])
            else:
                mem_c_fn_other.append(s["original_code"])

    print(f"\nCohort Sizes:")
    print(f"  Clean C -> Memory Safety (False Positives): {len(clean_c_fp_mem):,}")
    print(f"  Clean C -> Clean Code   (True Negatives)  : {len(clean_c_tn):,}")
    print(f"  Memory Safety -> Memory Safety (True Pos) : {len(mem_c_tp):,}")
    print(f"  Memory Safety -> Clean Code (False Negs)  : {len(mem_c_fn_clean):,}")
    print(f"  Memory Safety -> Other Bug (False Negs)   : {len(mem_c_fn_other):,}")

    # Analyze syntactic and token patterns for each cohort
    print("\n[ANALYSIS] Analyzing syntactic and token patterns across cohorts...")
    fp_stats = analyze_tokens_and_syntax(clean_c_fp_mem)
    tn_stats = analyze_tokens_and_syntax(clean_c_tn)
    tp_stats = analyze_tokens_and_syntax(mem_c_tp)
    fn_stats = analyze_tokens_and_syntax(mem_c_fn_clean)

    # Calculate token elevation ratios (FP / TN frequency ratio)
    token_elevations = {}
    for t in PROBE_TOKENS:
        fp_freq = fp_stats["token_frequencies_per_sample"].get(t, 0)
        tn_freq = tn_stats["token_frequencies_per_sample"].get(t, 0)
        ratio = (fp_freq / tn_freq) if tn_freq > 0.001 else (fp_freq / 0.001)
        token_elevations[t] = {
            "fp_freq_per_sample": fp_freq,
            "tn_freq_per_sample": tn_freq,
            "elevation_ratio_fp_over_tn": round(ratio, 2)
        }

    # Sort by highest elevation
    sorted_elevations = sorted(token_elevations.items(), key=lambda x: -x[1]["elevation_ratio_fp_over_tn"])

    # Margin analysis on False Positives
    fp_margins = np.array(fp_clean_margins)
    margin_close = float(np.sum((fp_margins > 0) & (fp_margins < 0.20)) / len(fp_margins)) * 100
    margin_medium = float(np.sum((fp_margins >= 0.20) & (fp_margins < 0.40)) / len(fp_margins)) * 100
    margin_large = float(np.sum(fp_margins >= 0.40) / len(fp_margins)) * 100

    print("\n--- Key False Positive Findings ---")
    print(f"Clean C False Positive Count: {len(clean_c_fp_mem)}")
    print(f"Mean Confidence on FP: {np.mean(fp_confidences):.4f} (Median: {np.median(fp_confidences):.4f})")
    print(f"Mean FP Margin P(mem) - P(clean): {np.mean(fp_clean_margins):.4f}")
    print(f"  FPs with close margin (< 0.20) : {margin_close:.1f}%")
    print(f"  FPs with medium margin (0.2-0.4): {margin_medium:.1f}%")
    print(f"  FPs with large margin (>= 0.40): {margin_large:.1f}%")
    print("\nTop 10 Tokens Most Elevated in False Positives vs True Negatives (FP/TN Ratio):")
    for t, d in sorted_elevations[:10]:
        print(f"  {t:12s}: FP={d['fp_freq_per_sample']:6.2f}/fn vs TN={d['tn_freq_per_sample']:6.2f}/fn | Ratio = {d['elevation_ratio_fp_over_tn']:.2f}x")

    print(f"\nMean Function Size (Lines): FP={fp_stats['mean_lines']:.1f} vs TN={tn_stats['mean_lines']:.1f} vs TP={tp_stats['mean_lines']:.1f}")

    diagnosis_results = {
        "experiment": "Phase L — Investigation B",
        "cohort_counts": {
            "clean_c_false_positives_memory_safety": len(clean_c_fp_mem),
            "clean_c_true_negatives": len(clean_c_tn),
            "memory_safety_true_positives": len(mem_c_tp),
            "memory_safety_false_negatives_clean": len(mem_c_fn_clean),
            "memory_safety_false_negatives_other": len(mem_c_fn_other)
        },
        "confidence_and_margins": {
            "mean_fp_confidence": round(float(np.mean(fp_confidences)), 4),
            "median_fp_confidence": round(float(np.median(fp_confidences)), 4),
            "std_fp_confidence": round(float(np.std(fp_confidences)), 4),
            "mean_fp_clean_margin": round(float(np.mean(fp_clean_margins)), 4),
            "median_fp_clean_margin": round(float(np.median(fp_clean_margins)), 4),
            "fp_margin_brackets_pct": {
                "tight_margin_under_0_20": round(margin_close, 2),
                "medium_margin_0_20_to_0_40": round(margin_medium, 2),
                "wide_margin_over_0_40": round(margin_large, 2)
            }
        },
        "token_elevation_analysis": {t: d for t, d in sorted_elevations},
        "cohort_statistics": {
            "false_positives": fp_stats,
            "true_negatives": tn_stats,
            "true_positives": tp_stats,
            "false_negatives": fn_stats
        },
        "repository_distribution": {
            "fp_repositories": dict(fp_repos.most_common(10)),
            "tn_repositories": dict(tn_repos.most_common(10))
        }
    }

    out_file = EXP_L_DIR / "phase_l_false_positive_analysis.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(diagnosis_results, f, indent=2)
    print(f"\n[OK] Phase L False Positive Analysis written to {out_file}")

if __name__ == "__main__":
    diagnose_c_false_positives()
