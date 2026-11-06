"""
PATCHPROOF Experiment K — Phase 6: Rigorous Baseline vs Candidate Evaluation
Evaluates baseline model (models/bug_detector.joblib) and candidate model
(models/experiments/experiment_k/bug_detector_candidate_k.joblib) on the
UNTOUCHED held-out test set (data/processed/test.jsonl).
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple
import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score, f1_score, precision_recall_fscore_support,
    confusion_matrix, classification_report
)

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_k"

CANONICAL_CLASSES = [
    "api_misuse", "async_error", "condition_error", "exception_handling",
    "loop_error", "memory_safety", "none_correct_code", "null_pointer",
    "off_by_one", "resource_leak", "state_management", "type_error",
    "undefined_behavior"
]

def load_test_set(file_path: Path) -> List[Dict[str, Any]]:
    assert file_path.exists(), f"FATAL: Test set {file_path} not found!"
    examples = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
    return examples

def evaluate_model_on_dataset(
    model,
    dataset: List[Dict[str, Any]],
    dataset_name: str
) -> Dict[str, Any]:
    X = [ex["original_code"] for ex in dataset]
    y_true = [ex["bug_category"] for ex in dataset]
    languages = [ex["language"] for ex in dataset]

    # Timing latency
    start_t = time.time()
    y_pred = model.predict(X)
    infer_duration = time.time() - start_t
    latency_per_100 = (infer_duration / len(X)) * 100 * 1000  # in ms

    acc = accuracy_score(y_true, y_pred)
    prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    prec_weighted, rec_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )

    # Per-class evaluation
    classes_present = sorted(list(set(y_true)))
    prec_cls, rec_cls, f1_cls, supp_cls = precision_recall_fscore_support(
        y_true, y_pred, labels=classes_present, zero_division=0
    )

    per_class_metrics = {}
    for i, c in enumerate(classes_present):
        per_class_metrics[c] = {
            "precision": round(float(prec_cls[i]), 4),
            "recall": round(float(rec_cls[i]), 4),
            "f1": round(float(f1_cls[i]), 4),
            "support": int(supp_cls[i])
        }

    # Clean-code False Positive Rate (FPR) and False Negative Rate (FNR)
    # clean code is 'none_correct_code'
    clean_indices = [i for i, true_l in enumerate(y_true) if true_l == "none_correct_code"]
    clean_total = len(clean_indices)
    clean_fp = sum(1 for i in clean_indices if y_pred[i] != "none_correct_code")
    clean_fpr = (clean_fp / clean_total) if clean_total > 0 else 0.0

    bug_indices = [i for i, true_l in enumerate(y_true) if true_l != "none_correct_code"]
    bug_total = len(bug_indices)
    bug_fn = sum(1 for i in bug_indices if y_pred[i] == "none_correct_code")
    bug_fnr = (bug_fn / bug_total) if bug_total > 0 else 0.0

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=classes_present).tolist()

    # Language breakdowns
    lang_metrics = {}
    by_lang = defaultdict(lambda: {"true": [], "pred": []})
    for l, yt, yp in zip(languages, y_true, y_pred):
        by_lang[l]["true"].append(yt)
        by_lang[l]["pred"].append(yp)

    for l, d in by_lang.items():
        l_acc = accuracy_score(d["true"], d["pred"])
        l_f1 = f1_score(d["true"], d["pred"], average="weighted", zero_division=0)
        lang_metrics[l] = {
            "sample_count": len(d["true"]),
            "accuracy": round(float(l_acc), 4),
            "f1_weighted": round(float(l_f1), 4)
        }

    return {
        "dataset_name": dataset_name,
        "sample_count": len(dataset),
        "classes_evaluated": classes_present,
        "accuracy": round(float(acc), 4),
        "macro_precision": round(float(prec_macro), 4),
        "macro_recall": round(float(rec_macro), 4),
        "macro_f1": round(float(f1_macro), 4),
        "weighted_precision": round(float(prec_weighted), 4),
        "weighted_recall": round(float(rec_weighted), 4),
        "weighted_f1": round(float(f1_weighted), 4),
        "clean_code_fpr": round(float(clean_fpr), 4),
        "clean_code_total": clean_total,
        "clean_code_false_positives": clean_fp,
        "bug_fnr": round(float(bug_fnr), 4),
        "bug_total": bug_total,
        "bug_false_negatives": bug_fn,
        "latency_ms_per_100": round(float(latency_per_100), 2),
        "per_class": per_class_metrics,
        "confusion_matrix": {
            "labels": classes_present,
            "matrix": cm
        },
        "by_language": lang_metrics
    }

def run_evaluation():
    print("="*80)
    print("PATCHPROOF EXPERIMENT K: PHASE 6 — RIGOROUS EVALUATION")
    print("="*80)

    baseline_path = ROOT_DIR / "models" / "bug_detector.joblib"
    candidate_path = EXP_K_MODEL_DIR / "bug_detector_candidate_k.joblib"

    assert baseline_path.exists(), f"FATAL: Baseline model {baseline_path} missing!"
    assert candidate_path.exists(), f"FATAL: Candidate model {candidate_path} missing!"

    # Verify hashes
    with open(baseline_path, "rb") as f:
        base_sha = hashlib.sha256(f.read()).hexdigest()
    with open(candidate_path, "rb") as f:
        cand_sha = hashlib.sha256(f.read()).hexdigest()

    print(f"[BASE] Baseline Model SHA-256: {base_sha}")
    print(f"[CAND] Candidate Model SHA-256: {cand_sha}")

    # Load Models
    print("[LOAD] Loading model artifacts into memory...")
    base_model = joblib.load(baseline_path)
    cand_model = joblib.load(candidate_path)

    # Load Untouched Held-Out Test Set
    test_path = PROCESSED_DIR / "test.jsonl"
    with open(test_path, "rb") as f:
        test_sha = hashlib.sha256(f.read()).hexdigest()
    print(f"[TEST] Test Set SHA-256: {test_sha}")
    assert test_sha == "9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d", \
        "FATAL: Test set checksum does not match ground truth!"

    test_set = load_test_set(test_path)
    print(f"[TEST] Loaded {len(test_set):,} test samples from {test_path}")

    # Evaluate Baseline on test.jsonl
    print("[EVAL] Evaluating BASELINE model on test.jsonl...")
    base_test_results = evaluate_model_on_dataset(base_model, test_set, "test.jsonl")

    # Evaluate Candidate on test.jsonl
    print("[EVAL] Evaluating CANDIDATE model on test.jsonl...")
    cand_test_results = evaluate_model_on_dataset(cand_model, test_set, "test.jsonl")

    # Also evaluate on robust_heldout_test.jsonl
    robust_test_path = PROCESSED_DIR / "robust_heldout_test.jsonl"
    robust_test_set = load_test_set(robust_test_path)
    print(f"[ROBUST TEST] Evaluating on {len(robust_test_set):,} robust test samples...")
    base_robust_results = evaluate_model_on_dataset(base_model, robust_test_set, "robust_heldout_test.jsonl")
    cand_robust_results = evaluate_model_on_dataset(cand_model, robust_test_set, "robust_heldout_test.jsonl")

    # Model Sizes
    base_size_mb = os.path.getsize(baseline_path) / (1024 * 1024)
    cand_size_mb = os.path.getsize(candidate_path) / (1024 * 1024)

    comparison = {
        "experiment": "Experiment K",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_dataset": "data/processed/test.jsonl",
        "test_dataset_sha256": test_sha,
        "models": {
            "baseline": {
                "name": "Phase 2 Baseline MLBugModel",
                "sha256": base_sha,
                "size_mb": round(base_size_mb, 2),
                "test_results": base_test_results,
                "robust_test_results": base_robust_results
            },
            "candidate": {
                "name": "Experiment K CandidateBugModelK",
                "sha256": cand_sha,
                "size_mb": round(cand_size_mb, 2),
                "test_results": cand_test_results,
                "robust_test_results": cand_robust_results
            }
        },
        "deltas_test": {
            "accuracy_delta": round(cand_test_results["accuracy"] - base_test_results["accuracy"], 4),
            "macro_f1_delta": round(cand_test_results["macro_f1"] - base_test_results["macro_f1"], 4),
            "weighted_f1_delta": round(cand_test_results["weighted_f1"] - base_test_results["weighted_f1"], 4),
            "clean_fpr_delta": round(cand_test_results["clean_code_fpr"] - base_test_results["clean_code_fpr"], 4),
            "bug_fnr_delta": round(cand_test_results["bug_fnr"] - base_test_results["bug_fnr"], 4)
        },
        "deltas_robust": {
            "accuracy_delta": round(cand_robust_results["accuracy"] - base_robust_results["accuracy"], 4),
            "macro_f1_delta": round(cand_robust_results["macro_f1"] - base_robust_results["macro_f1"], 4),
            "weighted_f1_delta": round(cand_robust_results["weighted_f1"] - base_robust_results["weighted_f1"], 4)
        }
    }

    # Save comparison to JSON
    report_file = EXP_K_MODEL_DIR / "evaluation_results.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print("\n" + "="*80)
    print("EXPERIMENT K: FINAL EVALUATION SUMMARY")
    print("="*80)
    print(f"Held-out Test Set Accuracy : Baseline={base_test_results['accuracy']:.4f} | Candidate={cand_test_results['accuracy']:.4f} (Delta: {comparison['deltas_test']['accuracy_delta']:+.4f})")
    print(f"Held-out Test Set Macro F1 : Baseline={base_test_results['macro_f1']:.4f} | Candidate={cand_test_results['macro_f1']:.4f} (Delta: {comparison['deltas_test']['macro_f1_delta']:+.4f})")
    print(f"Held-out Test Weighted F1  : Baseline={base_test_results['weighted_f1']:.4f} | Candidate={cand_test_results['weighted_f1']:.4f} (Delta: {comparison['deltas_test']['weighted_f1_delta']:+.4f})")
    print(f"Clean-Code False Pos Rate  : Baseline={base_test_results['clean_code_fpr']:.4f} | Candidate={cand_test_results['clean_code_fpr']:.4f} (Delta: {comparison['deltas_test']['clean_fpr_delta']:+.4f})")
    print(f"Bug False Negative Rate    : Baseline={base_test_results['bug_fnr']:.4f} | Candidate={cand_test_results['bug_fnr']:.4f} (Delta: {comparison['deltas_test']['bug_fnr_delta']:+.4f})")
    print(f"Robust Test Weighted F1    : Baseline={base_robust_results['weighted_f1']:.4f} | Candidate={cand_robust_results['weighted_f1']:.4f} (Delta: {comparison['deltas_robust']['weighted_f1_delta']:+.4f})")
    print(f"Latency per 100 samples    : Baseline={base_test_results['latency_ms_per_100']:.1f}ms | Candidate={cand_test_results['latency_ms_per_100']:.1f}ms")
    print(f"[OK] Full evaluation results written to {report_file}")

if __name__ == "__main__":
    run_evaluation()
