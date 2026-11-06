"""
PATCHPROOF Phase L — Investigation C: Model Diagnostics, Feature Analysis & Calibration
Analyzes feature weights, project-specific token biases, and tests probability calibration
and decision thresholding on validation data.
Outputs:
  - models/experiments/experiment_l/phase_l_feature_analysis.json
  - models/experiments/experiment_l/phase_l_calibration_results.json
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple
import joblib
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    brier_score_loss, confusion_matrix
)

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_k"
EXP_L_DIR = ROOT_DIR / "models" / "experiments" / "experiment_l"
EXP_L_DIR.mkdir(parents=True, exist_ok=True)

def compute_ece(probs: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> Tuple[float, float, List[Dict[str, Any]]]:
    """Computes Expected Calibration Error and Maximum Calibration Error."""
    confidences = np.max(probs, axis=1)
    accuracies = (y_pred == y_true).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    mce = 0.0
    bin_details = []

    for i in range(n_bins):
        lower = bin_boundaries[i]
        upper = bin_boundaries[i + 1]
        in_bin = (confidences > lower) & (confidences <= upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            acc_in_bin = np.mean(accuracies[in_bin])
            avg_conf_in_bin = np.mean(confidences[in_bin])
            gap = abs(avg_conf_in_bin - acc_in_bin)
            ece += prop_in_bin * gap
            mce = max(mce, gap)
            bin_details.append({
                "bin": f"{lower:.1f}-{upper:.1f}",
                "count": int(np.sum(in_bin)),
                "acc": round(float(acc_in_bin), 4),
                "conf": round(float(avg_conf_in_bin), 4),
                "gap": round(float(gap), 4)
            })

    return float(ece), float(mce), bin_details

def analyze_features_and_calibration():
    print("=" * 80)
    print("PHASE L: INVESTIGATION C — FEATURE ANALYSIS & PROBABILITY CALIBRATION")
    print("=" * 80)

    candidate_path = EXP_K_MODEL_DIR / "bug_detector_candidate_k.joblib"
    assert candidate_path.exists(), f"FATAL: Candidate model {candidate_path} missing!"
    print(f"[LOAD] Loading candidate model from {candidate_path}...")
    pipeline = joblib.load(candidate_path)

    features = pipeline.named_steps["features"]
    clf = pipeline.named_steps["clf"]
    feature_names = features.get_feature_names_out()
    classes = list(clf.classes_)

    mem_idx = classes.index("memory_safety")
    clean_idx = classes.index("none_correct_code")

    # 1. Feature Attribution Analysis
    print("[FEATURES] Extracting top positive and negative features...")
    mem_coefs = clf.coef_[mem_idx]
    clean_coefs = clf.coef_[clean_idx]

    top_mem_pos_indices = np.argsort(mem_coefs)[::-1][:50]
    top_mem_neg_indices = np.argsort(mem_coefs)[:50]
    top_clean_pos_indices = np.argsort(clean_coefs)[::-1][:50]
    top_clean_neg_indices = np.argsort(clean_coefs)[:50]

    # Identify project-specific tokens
    project_tokens = ["qemu", "av_", "ffmpeg", "png", "usb", "linux", "chrome", "android"]
    project_token_impact = []

    for idx, fname in enumerate(feature_names):
        clean_fname = fname.split("__")[-1]
        for p in project_tokens:
            if p in clean_fname:
                project_token_impact.append({
                    "feature": fname,
                    "project_pattern": p,
                    "coef_memory_safety": round(float(mem_coefs[idx]), 4),
                    "coef_none_correct": round(float(clean_coefs[idx]), 4),
                    "bias_towards_memory_safety": round(float(mem_coefs[idx] - clean_coefs[idx]), 4)
                })
                break

    # Sort project tokens by memory safety bias
    project_token_impact.sort(key=lambda x: -x["bias_towards_memory_safety"])

    print(f"\nIdentified {len(project_token_impact)} project-specific tokens in model vocabulary.")
    print("Top 10 Project-Specific Tokens with Highest Memory-Safety Bias:")
    for item in project_token_impact[:10]:
        print(f"  {item['feature']:35s} | MemCoef={item['coef_memory_safety']:+6.4f} | CleanCoef={item['coef_none_correct']:+6.4f} | Bias={item['bias_towards_memory_safety']:+6.4f}")

    feature_analysis_out = {
        "experiment": "Phase L — Investigation C",
        "total_features": len(feature_names),
        "classes": classes,
        "top_features_memory_safety_positive": [
            {"feature": feature_names[i], "coef": round(float(mem_coefs[i]), 4)} for i in top_mem_pos_indices[:30]
        ],
        "top_features_memory_safety_negative": [
            {"feature": feature_names[i], "coef": round(float(mem_coefs[i]), 4)} for i in top_mem_neg_indices[:30]
        ],
        "top_features_none_correct_positive": [
            {"feature": feature_names[i], "coef": round(float(clean_coefs[i]), 4)} for i in top_clean_pos_indices[:30]
        ],
        "project_token_bias_analysis": {
            "total_project_tokens_found": len(project_token_impact),
            "top_biased_project_features": project_token_impact[:30]
        }
    }

    feature_file = EXP_L_DIR / "phase_l_feature_analysis.json"
    with open(feature_file, "w", encoding="utf-8") as f:
        json.dump(feature_analysis_out, f, indent=2)
    print(f"[OK] Feature Analysis written to {feature_file}")

    # 2. Calibration & Decision Thresholding on Validation Split
    print("\n[CALIBRATION] Loading validation split (val.jsonl) for decision boundary analysis...")
    val_path = PROCESSED_DIR / "val.jsonl"
    val_samples = []
    with open(val_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                val_samples.append(json.loads(line))

    X_val = [s["original_code"] for s in val_samples]
    y_val = [s["bug_category"] for s in val_samples]
    lang_val = [s["language"] for s in val_samples]

    print(f"[VAL] Extracted {len(val_samples):,} validation samples.")
    val_probs = pipeline.predict_proba(X_val)
    val_preds_default = pipeline.predict(X_val)

    # Overall validation ECE
    ece_val, mce_val, bins_val = compute_ece(val_probs, np.array(y_val), np.array(val_preds_default))
    print(f"Validation ECE: {ece_val:.4f} | MCE: {mce_val:.4f}")

    # Validation C-only cohort analysis
    c_indices = [i for i, l in enumerate(lang_val) if l == "c"]
    c_y_val = [y_val[i] for i in c_indices]
    c_probs_val = val_probs[c_indices]
    c_preds_val = [val_preds_default[i] for i in c_indices]

    # Decision Threshold Grid Search on Validation Split
    # We test thresholds for predicting memory_safety vs defaulting to clean / second-best
    print("\n[GRID SEARCH] Evaluating decision thresholds for memory_safety on validation split...")
    threshold_results = []

    # Candidate thresholds tau on P(memory_safety)
    taus = [0.10, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

    # Clean code index in classes
    for tau in taus:
        adjusted_preds = []
        for i in range(len(val_probs)):
            p = val_probs[i]
            # default prediction is argmax
            pred_class = classes[int(np.argmax(p))]

            # If predicted class is memory_safety but P(memory_safety) <= tau, revert to second highest or clean
            if pred_class == "memory_safety" and p[mem_idx] <= tau:
                # Select best non-memory-safety class
                sorted_class_indices = np.argsort(p)[::-1]
                pred_class = classes[sorted_class_indices[1]]

            adjusted_preds.append(pred_class)

        # Compute metrics on validation set
        acc = accuracy_score(y_val, adjusted_preds)
        prec_w, rec_w, f1_w, _ = precision_recall_fscore_support(y_val, adjusted_preds, average="weighted", zero_division=0)

        # Clean FPR and Mem Recall
        clean_mask = [y == "none_correct_code" for y in y_val]
        clean_fp = sum(1 for i, is_clean in enumerate(clean_mask) if is_clean and adjusted_preds[i] != "none_correct_code")
        clean_fpr = clean_fp / sum(clean_mask) if sum(clean_mask) > 0 else 0

        mem_mask = [y == "memory_safety" for y in y_val]
        mem_tp = sum(1 for i, is_mem in enumerate(mem_mask) if is_mem and adjusted_preds[i] == "memory_safety")
        mem_recall = mem_tp / sum(mem_mask) if sum(mem_mask) > 0 else 0
        mem_prec = (mem_tp / sum(1 for p in adjusted_preds if p == "memory_safety")) if sum(1 for p in adjusted_preds if p == "memory_safety") > 0 else 0
        mem_f1 = (2 * mem_prec * mem_recall) / (mem_prec + mem_recall) if (mem_prec + mem_recall) > 0 else 0

        threshold_results.append({
            "tau_threshold": tau,
            "val_accuracy": round(float(acc), 4),
            "val_weighted_f1": round(float(f1_w), 4),
            "val_clean_fpr": round(float(clean_fpr), 4),
            "val_memory_safety_precision": round(float(mem_prec), 4),
            "val_memory_safety_recall": round(float(mem_recall), 4),
            "val_memory_safety_f1": round(float(mem_f1), 4)
        })
        print(f"  Tau={tau:.2f} | Val Acc={acc:.4f} | F1={f1_w:.4f} | Clean FPR={clean_fpr:.4f} | Mem Prec={mem_prec:.4f} | Mem Rec={mem_recall:.4f}")

    calibration_out = {
        "experiment": "Phase L — Investigation C",
        "validation_calibration": {
            "expected_calibration_error": round(float(ece_val), 4),
            "max_calibration_error": round(float(mce_val), 4),
            "bins": bins_val
        },
        "threshold_tuning_grid_search_val": threshold_results
    }

    cal_file = EXP_L_DIR / "phase_l_calibration_results.json"
    with open(cal_file, "w", encoding="utf-8") as f:
        json.dump(calibration_out, f, indent=2)
    print(f"\n[OK] Calibration Results written to {cal_file}")

if __name__ == "__main__":
    analyze_features_and_calibration()
