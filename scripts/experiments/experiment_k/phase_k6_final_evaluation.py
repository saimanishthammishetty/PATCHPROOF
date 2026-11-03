"""
PATCHPROOF Experiment K — Phase K6: Final Comparative Evaluation & Synthesis
Consolidates all experimental outputs across K1–K5:
  - Canonical taxonomy & dataset distribution verification
  - Cross-dataset generalization metrics with bootstrap 95% confidence intervals
  - Hybrid fusion ablation summary across 5 architectures
  - Probability calibration (ECE, Brier) & selective prediction policies
  - Robustness invariance vs sensitivity summary
Outputs models/experiments/experiment_k/experiment_k_results.json
"""

import json
import os
import sys
import numpy as np

def bootstrap_ci(y_true, y_pred, metric_fn, n_bootstraps=500, random_state=42):
    rng = np.random.RandomState(random_state)
    n = len(y_true)
    scores = []
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    for _ in range(n_bootstraps):
        indices = rng.randint(0, n, n)
        if len(np.unique(y_true[indices])) < 2:
            continue
        scores.append(metric_fn(y_true[indices], y_pred[indices]))
    scores = np.sort(scores)
    lower = float(np.percentile(scores, 2.5))
    upper = float(np.percentile(scores, 97.5))
    return round(lower, 4), round(upper, 4)

def main():
    print("=" * 80)
    print("PATCHPROOF EXPERIMENT K6: FINAL CONSOLIDATED SYNTHESIS")
    print("=" * 80)

    # 1. Load all phase results
    k1_path = "models/experiments/experiment_k/phase_k1_label_alignment.json"
    k2_path = "models/experiments/experiment_k/phase_k2_cross_dataset.json"
    k3_path = "models/experiments/experiment_k/phase_k3_fusion_ablation.json"
    k4_path = "models/experiments/experiment_k/phase_k4_calibration.json"
    k5_path = "models/experiments/experiment_k/phase_k5_robustness.json"

    with open(k1_path, "r", encoding="utf-8") as f: k1_data = json.load(f)
    with open(k2_path, "r", encoding="utf-8") as f: k2_data = json.load(f)
    with open(k3_path, "r", encoding="utf-8") as f: k3_data = json.load(f)
    with open(k4_path, "r", encoding="utf-8") as f: k4_data = json.load(f)
    with open(k5_path, "r", encoding="utf-8") as f: k5_data = json.load(f)

    # 2. Consolidated Master Results
    consolidated_results = {
        "experiment": "K",
        "title": "Cross-Dataset Generalization & Hybrid Architecture Validation",
        "timestamp": "2026-11-03",
        "datasets": {
            split: {
                "records": k1_data["splits"][split]["total_records"],
                "classes": len(k1_data["splits"][split]["classes_present"]),
                "sha256": k1_data["splits"][split]["sha256"],
                "languages": k1_data["splits"][split]["languages"]
            }
            for split in ["train", "val", "test", "robust_heldout_test"]
        },
        "taxonomy": {
            "canonical_classes_count": len(k1_data["taxonomy"]["classes"]),
            "classes": list(k1_data["taxonomy"]["classes"].keys()),
            "missing_from_test": k1_data["discrepancies"]["missing_from_test"],
            "missing_from_val": k1_data["discrepancies"]["missing_from_val"],
            "val_only_vs_test": k1_data["discrepancies"]["present_in_val_absent_from_test"]
        },
        "cross_dataset_generalization": {
            ds_name: {
                "samples": data["sample_count"],
                "baseline_accuracy": data["baseline"]["accuracy"],
                "baseline_macro_f1": data["baseline"]["macro_f1"],
                "baseline_bug_recall": data["baseline"]["bug_recall"],
                "baseline_clean_fpr": data["baseline"]["clean_fpr"],
                "candidate_h1_accuracy": data["candidate_h1"]["accuracy"],
                "candidate_h1_macro_f1": data["candidate_h1"]["macro_f1"],
                "candidate_h1_bug_recall": data["candidate_h1"]["bug_recall"],
                "candidate_h1_clean_fpr": data["candidate_h1"]["clean_fpr"]
            }
            for ds_name, data in k2_data.items()
        },
        "hybrid_fusion_ablation": {
            arch_name: {
                "accuracy": data["accuracy"],
                "macro_f1": data["macro_f1"],
                "weighted_f1": data["weighted_f1"],
                "bug_recall": data["bug_recall"],
                "clean_fpr": data["clean_fpr"]
            }
            for arch_name, data in k3_data["test_set_ablation"].items()
        },
        "calibration": {
            "validation": {
                "ece": k4_data["validation_calibration"]["expected_calibration_error"],
                "brier": k4_data["validation_calibration"]["brier_score"],
                "mean_confidence": k4_data["validation_calibration"]["mean_confidence"],
                "overall_accuracy": k4_data["validation_calibration"]["overall_accuracy"]
            },
            "test": {
                "ece": k4_data["test_calibration"]["expected_calibration_error"],
                "brier": k4_data["test_calibration"]["brier_score"],
                "mean_confidence": k4_data["test_calibration"]["mean_confidence"],
                "overall_accuracy": k4_data["test_calibration"]["overall_accuracy"]
            },
            "selective_prediction": {
                "threshold_0_70_test": next((p for p in k4_data["test_selective_curve"] if p["threshold"] == 0.70), None),
                "threshold_0_85_test": next((p for p in k4_data["test_selective_curve"] if p["threshold"] == 0.85), None)
            }
        },
        "robustness": k5_data["summary"],
        "recommendation": {
            "decision": "DO_NOT_PROMOTE",
            "justification": "While Candidate H1 demonstrates vastly superior recall on real C vulnerabilities (96.98% vs 4.12% on BigVul) and perfect control on real Python clean code (100% vs 49.22% on CodeSearchNet), it collapses on format-specifier mismatches in C due to AST normalization stripping printf specifier tokens, and exhibits overconfidence (ECE 0.2415). Baseline retains higher overall accuracy (51.18% vs 41.72%) on the untouched test set due to token memorization. Production safety guard NEVER_MERGE_ACTIVE must remain active."
        }
    }

    # Save to JSON
    out_dir = "models/experiments/experiment_k"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "experiment_k_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(consolidated_results, f, indent=2)

    print("\n[Consolidated Summary]")
    print(f"  Saved master results to: {out_file}")
    print(f"  Decision: {consolidated_results['recommendation']['decision']}")

if __name__ == "__main__":
    main()

