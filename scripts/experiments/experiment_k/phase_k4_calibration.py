"""
PATCHPROOF Experiment K — Phase K4: Calibration, Confidence & Selective Prediction
Investigates:
  1. Multi-class Probability Calibration & Expected Calibration Error (ECE)
  2. Brier Score across validation and test datasets
  3. Reliability Diagram Bins (Accuracy vs Confidence)
  4. Selective Prediction & Abstention Analysis (threshold sweep on val.jsonl)
  5. Evaluation of optimal abstention thresholds on untouched test.jsonl
"""

import json
import os
import sys
import joblib
import numpy as np
from collections import Counter, defaultdict

sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_f"))
from ast_normalizer import normalize_snippet

def compute_calibration_metrics(probs_matrix, y_true, classes, n_bins=10):
    """
    Computes Expected Calibration Error (ECE), Maximum Calibration Error (MCE),
    Brier Score, and reliability diagram bin statistics.
    """
    n_samples, n_classes = probs_matrix.shape
    y_true_str = [str(y) for y in y_true]
    class_to_idx = {c: i for i, c in enumerate(classes)}

    # Multi-class one-hot matrix
    y_one_hot = np.zeros((n_samples, n_classes), dtype=float)
    for i, y in enumerate(y_true_str):
        if y in class_to_idx:
            y_one_hot[i, class_to_idx[y]] = 1.0

    # Multi-class Brier score
    brier_score = float(np.mean(np.sum((probs_matrix - y_one_hot) ** 2, axis=1)))

    # Top-1 Confidence and Correctness
    top_indices = np.argmax(probs_matrix, axis=1)
    top_confidences = np.max(probs_matrix, axis=1)
    pred_labels = [classes[idx] for idx in top_indices]
    correct = np.array([1.0 if pred == true else 0.0 for pred, true in zip(pred_labels, y_true_str)])

    # Binning
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    bin_stats = []
    ece = 0.0
    mce = 0.0

    for m in range(n_bins):
        bin_lower = bin_boundaries[m]
        bin_upper = bin_boundaries[m + 1]

        if m == n_bins - 1:
            in_bin = (top_confidences >= bin_lower) & (top_confidences <= bin_upper)
        else:
            in_bin = (top_confidences >= bin_lower) & (top_confidences < bin_upper)

        bin_count = int(np.sum(in_bin))

        if bin_count > 0:
            bin_acc = float(np.mean(correct[in_bin]))
            bin_conf = float(np.mean(top_confidences[in_bin]))
            diff = abs(bin_acc - bin_conf)
            weight = bin_count / n_samples
            ece += weight * diff
            if diff > mce:
                mce = diff
        else:
            bin_acc = 0.0
            bin_conf = float((bin_lower + bin_upper) / 2.0)
            diff = 0.0

        bin_stats.append({
            "bin_index": m,
            "bin_lower": round(bin_lower, 2),
            "bin_upper": round(bin_upper, 2),
            "count": bin_count,
            "pct_of_total": round(bin_count / n_samples * 100, 2),
            "observed_accuracy": round(bin_acc, 4),
            "average_confidence": round(bin_conf, 4),
            "calibration_gap": round(bin_acc - bin_conf, 4)
        })

    overall_acc = float(np.mean(correct))
    mean_conf = float(np.mean(top_confidences))

    return {
        "sample_count": n_samples,
        "overall_accuracy": round(overall_acc, 4),
        "mean_confidence": round(mean_conf, 4),
        "expected_calibration_error": round(float(ece), 4),
        "max_calibration_error": round(float(mce), 4),
        "brier_score": round(brier_score, 4),
        "bins": bin_stats
    }

def sweep_selective_prediction(probs_matrix, y_true, classes, thresholds):
    """Evaluates coverage vs accuracy for various confidence thresholds."""
    top_indices = np.argmax(probs_matrix, axis=1)
    top_confidences = np.max(probs_matrix, axis=1)
    pred_labels = [classes[idx] for idx in top_indices]
    y_true_str = [str(y) for y in y_true]
    n_total = len(y_true)

    curve = []
    for tau in thresholds:
        accepted = top_confidences >= tau
        n_accepted = int(np.sum(accepted))
        coverage = float(n_accepted / n_total)

        if n_accepted > 0:
            sub_preds = [pred_labels[i] for i in range(n_total) if accepted[i]]
            sub_trues = [y_true_str[i] for i in range(n_total) if accepted[i]]
            sel_acc = float(np.mean([1.0 if p == t else 0.0 for p, t in zip(sub_preds, sub_trues)]))
            risk = 1.0 - sel_acc
        else:
            sel_acc = 0.0
            risk = 0.0

        curve.append({
            "threshold": round(float(tau), 2),
            "coverage": round(coverage, 4),
            "accepted_count": n_accepted,
            "selective_accuracy": round(sel_acc, 4),
            "risk": round(risk, 4)
        })
    return curve

def main():
    print("=" * 80)
    print("PATCHPROOF EXPERIMENT K4: PROBABILITY CALIBRATION & SELECTIVE PREDICTION")
    print("=" * 80)

    # Load Candidate H1
    h1_path = "models/experiments/experiment_h/candidate_h1_ast_only.joblib"
    print(f"Loading Candidate H1: {h1_path}...")
    h1_model = joblib.load(h1_path)
    classes = [str(c) for c in h1_model.classes_]

    # 1. Load validation set (Strictly used for calibration analysis & threshold tuning)
    print("\nLoading and normalizing validation set (val.jsonl)...")
    val_records = []
    with open("data/processed/val.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            val_records.append(json.loads(line))

    val_codes = [r["original_code"] for r in val_records]
    val_langs = [r["language"] for r in val_records]
    val_labels = [r["bug_category"] for r in val_records]

    val_norm = [normalize_snippet(c, l)[0] for c, l in zip(val_codes, val_langs)]
    print(f"Computing predict_proba on {len(val_norm)} validation samples...")
    val_probs = h1_model.predict_proba(val_norm)

    val_cal = compute_calibration_metrics(val_probs, val_labels, classes)
    print(f"\n[Validation Calibration]")
    print(f"  Overall Accuracy:            {val_cal['overall_accuracy']*100:.2f}%")
    print(f"  Mean Confidence:             {val_cal['mean_confidence']*100:.2f}%")
    print(f"  Expected Calibration Error:  {val_cal['expected_calibration_error']:.4f}")
    print(f"  Max Calibration Error (MCE): {val_cal['max_calibration_error']:.4f}")
    print(f"  Brier Score:                 {val_cal['brier_score']:.4f}")

    # Threshold sweep on val
    thresholds = np.arange(0.20, 0.95, 0.05)
    val_selective_curve = sweep_selective_prediction(val_probs, val_labels, classes, thresholds)

    print("\n[Selective Prediction on Validation]")
    print(f"{'Threshold':>10} | {'Coverage':>10} | {'Accepted':>9} | {'Sel Acc':>10} | {'Risk (1-Acc)':>12}")
    print("-" * 62)
    for pt in val_selective_curve:
        print(f"{pt['threshold']:10.2f} | {pt['coverage']*100:9.2f}% | {pt['accepted_count']:9d} | {pt['selective_accuracy']*100:9.2f}% | {pt['risk']*100:11.2f}%")

    # Select optimal operating points from val
    # Operating point 1: Balanced (Acc >= 60% with max coverage)
    # Operating point 2: High Confidence (Acc >= 70% with max coverage)
    # Operating point 3: Ultra Conservative (Threshold = 0.70)
    op_balanced = next((p for p in val_selective_curve if p["selective_accuracy"] >= 0.60), val_selective_curve[0])
    op_high_conf = next((p for p in val_selective_curve if p["selective_accuracy"] >= 0.70), val_selective_curve[-1])

    print(f"\nSelected from Validation:")
    print(f"  Balanced Threshold:        tau = {op_balanced['threshold']} (Val Cov: {op_balanced['coverage']*100:.1f}%, Val Acc: {op_balanced['selective_accuracy']*100:.1f}%)")
    print(f"  High-Precision Threshold: tau = {op_high_conf['threshold']} (Val Cov: {op_high_conf['coverage']*100:.1f}%, Val Acc: {op_high_conf['selective_accuracy']*100:.1f}%)")

    # 2. Evaluate on Untouched Test Set
    print("\n" + "=" * 80)
    print("Evaluating Calibration on Untouched Test Set (test.jsonl, 8,353 records)...")
    test_records = []
    with open("data/processed/test.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            test_records.append(json.loads(line))

    test_codes = [r["original_code"] for r in test_records]
    test_langs = [r["language"] for r in test_records]
    test_labels = [r["bug_category"] for r in test_records]

    test_norm = [normalize_snippet(c, l)[0] for c, l in zip(test_codes, test_langs)]
    test_probs = h1_model.predict_proba(test_norm)

    test_cal = compute_calibration_metrics(test_probs, test_labels, classes)
    print(f"\n[Test Calibration]")
    print(f"  Overall Accuracy:            {test_cal['overall_accuracy']*100:.2f}%")
    print(f"  Mean Confidence:             {test_cal['mean_confidence']*100:.2f}%")
    print(f"  Expected Calibration Error:  {test_cal['expected_calibration_error']:.4f}")
    print(f"  Max Calibration Error (MCE): {test_cal['max_calibration_error']:.4f}")
    print(f"  Brier Score:                 {test_cal['brier_score']:.4f}")

    test_selective_curve = sweep_selective_prediction(test_probs, test_labels, classes, thresholds)

    print("\n[Selective Prediction Generalization on Test Set]")
    print(f"{'Threshold':>10} | {'Coverage':>10} | {'Accepted':>9} | {'Sel Acc':>10} | {'Risk (1-Acc)':>12}")
    print("-" * 62)
    for pt in test_selective_curve:
        print(f"{pt['threshold']:10.2f} | {pt['coverage']*100:9.2f}% | {pt['accepted_count']:9d} | {pt['selective_accuracy']*100:9.2f}% | {pt['risk']*100:11.2f}%")

    # Save to JSON
    out_dir = "models/experiments/experiment_k"
    os.makedirs(out_dir, exist_ok=True)
    report = {
        "experiment": "K4",
        "description": "Model Calibration & Selective Prediction Analysis",
        "validation_calibration": val_cal,
        "validation_selective_curve": val_selective_curve,
        "test_calibration": test_cal,
        "test_selective_curve": test_selective_curve,
        "selected_policies": {
            "balanced": op_balanced,
            "high_precision": op_high_conf
        }
    }
    out_file = os.path.join(out_dir, "phase_k4_calibration.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nSaved calibration report to: {out_file}")

if __name__ == "__main__":
    main()

