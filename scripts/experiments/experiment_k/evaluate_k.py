
"""
PATCHPROOF Experiment K — Phase 6: Rigorous Baseline vs Candidate Evaluation

Evaluates:
  1. Baseline model: models/bug_detector.joblib
  2. Candidate model: models/experiments/experiment_k/bug_detector_candidate_k.joblib

Datasets:
  1. Untouched held-out test set: data/processed/test.jsonl
  2. Robust held-out test set: data/processed/robust_heldout_test.jsonl

SAFETY:
  - Does not train either model.
  - Does not modify either model artifact.
  - Does not modify either test dataset.
  - Preserves the NEVER_MERGE_ACTIVE principle.
  - Writes evaluation results only after successful evaluation.
"""

import os
import sys
import time
import json
import hashlib

from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Any

import joblib
import numpy as np

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report
)


# ============================================================
# CONFIGURATION
# ============================================================

ROOT_DIR = Path("C:/PATCHPROOF")

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_k"

CANONICAL_CLASSES = [
    "api_misuse",
    "async_error",
    "condition_error",
    "exception_handling",
    "loop_error",
    "memory_safety",
    "none_correct_code",
    "null_pointer",
    "off_by_one",
    "resource_leak",
    "state_management",
    "type_error",
    "undefined_behavior"
]

EXPECTED_TEST_SHA256 = (
    "9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d"
)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_test_set(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSONL dataset."""

    assert file_path.exists(), (
        f"FATAL: Test set {file_path} not found!"
    )

    examples = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))

    assert len(examples) > 0, (
        f"FATAL: Dataset {file_path} is empty!"
    )

    return examples


# ============================================================
# MODEL EVALUATION
# ============================================================

def evaluate_model_on_dataset(
    model,
    dataset: List[Dict[str, Any]],
    dataset_name: str
) -> Dict[str, Any]:

    print(f"\n[RUN] Evaluating {dataset_name}...")

    X = [ex["original_code"] for ex in dataset]

    y_true = [
        str(ex["bug_category"])
        for ex in dataset
    ]

    languages = [
        str(ex["language"])
        for ex in dataset
    ]

    # --------------------------------------------------------
    # Prediction and inference timing
    # --------------------------------------------------------

    start_t = time.time()

    y_pred = [
        str(label)
        for label in model.predict(X)
    ]

    infer_duration = time.time() - start_t

    latency_per_100 = (
        (infer_duration / len(X)) * 100 * 1000
    )

    assert len(y_pred) == len(y_true), (
        "FATAL: Prediction count does not match dataset size!"
    )

    # --------------------------------------------------------
    # Overall metrics
    # --------------------------------------------------------

    acc = accuracy_score(y_true, y_pred)

    (
        prec_macro,
        rec_macro,
        f1_macro,
        _
    ) = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="macro",
        zero_division=0
    )

    (
        prec_weighted,
        rec_weighted,
        f1_weighted,
        _
    ) = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0
    )

    # --------------------------------------------------------
    # Per-class metrics
    # --------------------------------------------------------

    classes_present = sorted(set(y_true))

    (
        prec_cls,
        rec_cls,
        f1_cls,
        supp_cls
    ) = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=classes_present,
        zero_division=0
    )

    per_class_metrics = {}

    for i, class_name in enumerate(classes_present):

        per_class_metrics[class_name] = {
            "precision": round(float(prec_cls[i]), 4),
            "recall": round(float(rec_cls[i]), 4),
            "f1": round(float(f1_cls[i]), 4),
            "support": int(supp_cls[i])
        }

    # --------------------------------------------------------
    # Clean-code False Positive Rate
    # --------------------------------------------------------

    clean_indices = [
        i
        for i, true_label in enumerate(y_true)
        if true_label == "none_correct_code"
    ]

    clean_total = len(clean_indices)

    clean_fp = sum(
        1
        for i in clean_indices
        if y_pred[i] != "none_correct_code"
    )

    clean_fpr = (
        clean_fp / clean_total
        if clean_total > 0
        else 0.0
    )

    # --------------------------------------------------------
    # Bug False Negative Rate
    # --------------------------------------------------------

    bug_indices = [
        i
        for i, true_label in enumerate(y_true)
        if true_label != "none_correct_code"
    ]

    bug_total = len(bug_indices)

    bug_fn = sum(
        1
        for i in bug_indices
        if y_pred[i] == "none_correct_code"
    )

    bug_fnr = (
        bug_fn / bug_total
        if bug_total > 0
        else 0.0
    )

    # --------------------------------------------------------
    # CORRECTED CONFUSION MATRIX
    #
    # IMPORTANT:
    # Previously, the matrix used only classes_present.
    # Predictions into classes absent from y_true were omitted.
    #
    # Now, include the union of actual and predicted labels.
    # This ensures every prediction is represented.
    # --------------------------------------------------------

    matrix_labels = sorted(
        set(y_true) | set(y_pred)
    )

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=matrix_labels
    ).tolist()

    # --------------------------------------------------------
    # CONFUSION MATRIX INTEGRITY VALIDATION
    #
    # Every row total must equal the actual support for that
    # class. Predicted-only classes must have zero row support.
    # --------------------------------------------------------

    support_by_class = Counter(y_true)

    for i, label in enumerate(matrix_labels):

        matrix_row_total = sum(cm[i])

        expected_support = support_by_class.get(label, 0)

        if matrix_row_total != expected_support:

            raise AssertionError(
                f"FATAL: Confusion matrix mismatch for {label}: "
                f"matrix={matrix_row_total}, "
                f"support={expected_support}"
            )

    matrix_total = sum(
        sum(row)
        for row in cm
    )

    if matrix_total != len(dataset):

        raise AssertionError(
            f"FATAL: Confusion matrix total mismatch: "
            f"matrix={matrix_total}, "
            f"samples={len(dataset)}"
        )

    print(
        f"[PASS] Confusion matrix integrity: "
        f"{matrix_total}/{len(dataset)} samples accounted for"
    )

    # --------------------------------------------------------
    # Prediction taxonomy audit
    # --------------------------------------------------------

    prediction_only_classes = sorted(
        set(y_pred) - set(y_true)
    )

    unexpected_prediction_classes = sorted(
        set(y_pred) - set(CANONICAL_CLASSES)
    )

    prediction_only_counts = {
        label: int(sum(1 for p in y_pred if p == label))
        for label in prediction_only_classes
    }

    if unexpected_prediction_classes:

        print(
            "[WARNING] Predictions outside canonical taxonomy:",
            unexpected_prediction_classes
        )

    else:

        print(
            "[PASS] All predictions belong to canonical taxonomy"
        )

    # --------------------------------------------------------
    # Language-wise evaluation
    # --------------------------------------------------------

    lang_metrics = {}

    by_lang = defaultdict(
        lambda: {
            "true": [],
            "pred": []
        }
    )

    for language, true_label, predicted_label in zip(
        languages,
        y_true,
        y_pred
    ):

        by_lang[language]["true"].append(true_label)
        by_lang[language]["pred"].append(predicted_label)

    for language, data in by_lang.items():

        lang_accuracy = accuracy_score(
            data["true"],
            data["pred"]
        )

        lang_f1 = f1_score(
            data["true"],
            data["pred"],
            average="weighted",
            zero_division=0
        )

        lang_metrics[language] = {
            "sample_count": len(data["true"]),
            "accuracy": round(float(lang_accuracy), 4),
            "f1_weighted": round(float(lang_f1), 4)
        }

    # --------------------------------------------------------
    # Final evaluation result
    # --------------------------------------------------------

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

        "latency_ms_per_100": round(
            float(latency_per_100),
            2
        ),

        "per_class": per_class_metrics,

        "confusion_matrix": {
            "labels": matrix_labels,
            "matrix": cm,
            "total_samples_accounted_for": matrix_total
        },

        "prediction_audit": {
            "prediction_only_classes": prediction_only_classes,
            "prediction_only_class_counts": prediction_only_counts,
            "unexpected_prediction_classes": unexpected_prediction_classes
        },

        "by_language": lang_metrics
    }


# ============================================================
# MAIN EVALUATION PIPELINE
# ============================================================

def run_evaluation():

    print("=" * 80)

    print(
        "PATCHPROOF EXPERIMENT K: "
        "PHASE 6 — RIGOROUS EVALUATION"
    )

    print("=" * 80)

    print(
        "[SAFETY] Evaluation only. "
        "No training or model promotion will occur."
    )

    # --------------------------------------------------------
    # Model paths
    # --------------------------------------------------------

    baseline_path = (
        ROOT_DIR / "models" / "bug_detector.joblib"
    )

    candidate_path = (
        EXP_K_MODEL_DIR / "bug_detector_candidate_k.joblib"
    )

    assert baseline_path.exists(), (
        f"FATAL: Baseline model {baseline_path} missing!"
    )

    assert candidate_path.exists(), (
        f"FATAL: Candidate model {candidate_path} missing!"
    )

    # --------------------------------------------------------
    # Model hashes
    # --------------------------------------------------------

    base_sha = calculate_sha256(baseline_path)

    cand_sha = calculate_sha256(candidate_path)

    print(
        f"[BASE] Baseline Model SHA-256: {base_sha}"
    )

    print(
        f"[CAND] Candidate Model SHA-256: {cand_sha}"
    )

    # --------------------------------------------------------
    # Load models
    # --------------------------------------------------------

    print(
        "[LOAD] Loading model artifacts into memory..."
    )

    base_model = joblib.load(baseline_path)

    cand_model = joblib.load(candidate_path)

    # --------------------------------------------------------
    # Verify untouched primary test dataset
    # --------------------------------------------------------

    test_path = PROCESSED_DIR / "test.jsonl"

    assert test_path.exists(), (
        f"FATAL: Primary test set missing: {test_path}"
    )

    test_sha = calculate_sha256(test_path)

    print(
        f"[TEST] Test Set SHA-256: {test_sha}"
    )

    assert test_sha == EXPECTED_TEST_SHA256, (
        "FATAL: Test set checksum does not match "
        "the expected ground truth!"
    )

    test_set = load_test_set(test_path)

    print(
        f"[TEST] Loaded {len(test_set):,} test samples "
        f"from {test_path}"
    )

    # --------------------------------------------------------
    # Evaluate baseline on primary test set
    # --------------------------------------------------------

    print(
        "\n[EVAL] Evaluating BASELINE model on test.jsonl..."
    )

    base_test_results = evaluate_model_on_dataset(
        base_model,
        test_set,
        "test.jsonl"
    )

    # --------------------------------------------------------
    # Evaluate candidate on primary test set
    # --------------------------------------------------------

    print(
        "\n[EVAL] Evaluating CANDIDATE model on test.jsonl..."
    )

    cand_test_results = evaluate_model_on_dataset(
        cand_model,
        test_set,
        "test.jsonl"
    )

    # --------------------------------------------------------
    # Robust held-out test set
    # --------------------------------------------------------

    robust_test_path = (
        PROCESSED_DIR / "robust_heldout_test.jsonl"
    )

    robust_test_set = load_test_set(
        robust_test_path
    )

    print(
        f"\n[ROBUST TEST] Loaded "
        f"{len(robust_test_set):,} robust test samples."
    )

    base_robust_results = evaluate_model_on_dataset(
        base_model,
        robust_test_set,
        "robust_heldout_test.jsonl"
    )

    cand_robust_results = evaluate_model_on_dataset(
        cand_model,
        robust_test_set,
        "robust_heldout_test.jsonl"
    )

    # --------------------------------------------------------
    # Verify model artifacts remain unchanged
    # --------------------------------------------------------

    base_sha_after = calculate_sha256(
        baseline_path
    )

    cand_sha_after = calculate_sha256(
        candidate_path
    )

    assert base_sha_after == base_sha, (
        "FATAL: Baseline model artifact changed during evaluation!"
    )

    assert cand_sha_after == cand_sha, (
        "FATAL: Candidate model artifact changed during evaluation!"
    )

    print(
        "\n[PASS] Both model artifacts remain unchanged."
    )

    # --------------------------------------------------------
    # Model sizes
    # --------------------------------------------------------

    base_size_mb = (
        os.path.getsize(baseline_path) / (1024 * 1024)
    )

    cand_size_mb = (
        os.path.getsize(candidate_path) / (1024 * 1024)
    )

    # --------------------------------------------------------
    # Comparison report
    # --------------------------------------------------------

    comparison = {

        "experiment": "Experiment K",

        "safety_status": "NEVER_MERGE_ACTIVE",

        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime()
        ),

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

            "accuracy_delta": round(
                cand_test_results["accuracy"]
                - base_test_results["accuracy"],
                4
            ),

            "macro_f1_delta": round(
                cand_test_results["macro_f1"]
                - base_test_results["macro_f1"],
                4
            ),

            "weighted_f1_delta": round(
                cand_test_results["weighted_f1"]
                - base_test_results["weighted_f1"],
                4
            ),

            "clean_fpr_delta": round(
                cand_test_results["clean_code_fpr"]
                - base_test_results["clean_code_fpr"],
                4
            ),

            "bug_fnr_delta": round(
                cand_test_results["bug_fnr"]
                - base_test_results["bug_fnr"],
                4
            )
        },

        "deltas_robust": {

            "accuracy_delta": round(
                cand_robust_results["accuracy"]
                - base_robust_results["accuracy"],
                4
            ),

            "macro_f1_delta": round(
                cand_robust_results["macro_f1"]
                - base_robust_results["macro_f1"],
                4
            ),

            "weighted_f1_delta": round(
                cand_robust_results["weighted_f1"]
                - base_robust_results["weighted_f1"],
                4
            )
        }
    }

    # --------------------------------------------------------
    # Final result validation
    # --------------------------------------------------------

    for model_name in ["baseline", "candidate"]:

        for split_name in [
            "test_results",
            "robust_test_results"
        ]:

            result = comparison["models"][model_name][split_name]

            matrix_total = result[
                "confusion_matrix"
            ]["total_samples_accounted_for"]

            sample_count = result["sample_count"]

            assert matrix_total == sample_count, (
                f"FATAL: {model_name}/{split_name} "
                f"confusion matrix does not account for "
                f"all samples!"
            )

    # --------------------------------------------------------
    # Save evaluation results
    # --------------------------------------------------------

    EXP_K_MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    report_file = (
        EXP_K_MODEL_DIR / "evaluation_results.json"
    )

    with open(
        report_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            comparison,
            f,
            indent=2
        )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n" + "=" * 80)

    print(
        "EXPERIMENT K: FINAL EVALUATION SUMMARY"
    )

    print("=" * 80)

    print(
        f"Held-out Test Set Accuracy : "
        f"Baseline={base_test_results['accuracy']:.4f} | "
        f"Candidate={cand_test_results['accuracy']:.4f} "
        f"(Delta: {comparison['deltas_test']['accuracy_delta']:+.4f})"
    )

    print(
        f"Held-out Test Set Macro F1 : "
        f"Baseline={base_test_results['macro_f1']:.4f} | "
        f"Candidate={cand_test_results['macro_f1']:.4f} "
        f"(Delta: {comparison['deltas_test']['macro_f1_delta']:+.4f})"
    )

    print(
        f"Held-out Test Weighted F1  : "
        f"Baseline={base_test_results['weighted_f1']:.4f} | "
        f"Candidate={cand_test_results['weighted_f1']:.4f} "
        f"(Delta: {comparison['deltas_test']['weighted_f1_delta']:+.4f})"
    )

    print(
        f"Clean-Code False Pos Rate  : "
        f"Baseline={base_test_results['clean_code_fpr']:.4f} | "
        f"Candidate={cand_test_results['clean_code_fpr']:.4f} "
        f"(Delta: {comparison['deltas_test']['clean_fpr_delta']:+.4f})"
    )

    print(
        f"Bug False Negative Rate    : "
        f"Baseline={base_test_results['bug_fnr']:.4f} | "
        f"Candidate={cand_test_results['bug_fnr']:.4f} "
        f"(Delta: {comparison['deltas_test']['bug_fnr_delta']:+.4f})"
    )

    print(
        f"Robust Test Weighted F1    : "
        f"Baseline={base_robust_results['weighted_f1']:.4f} | "
        f"Candidate={cand_robust_results['weighted_f1']:.4f} "
        f"(Delta: {comparison['deltas_robust']['weighted_f1_delta']:+.4f})"
    )

    print(
        f"Latency per 100 samples    : "
        f"Baseline={base_test_results['latency_ms_per_100']:.1f}ms | "
        f"Candidate={cand_test_results['latency_ms_per_100']:.1f}ms"
    )

    print("\n[CONFUSION MATRIX AUDIT]")

    for model_name in ["baseline", "candidate"]:

        for split_name in [
            "test_results",
            "robust_test_results"
        ]:

            result = comparison["models"][model_name][split_name]

            print(
                f"[PASS] {model_name}/{split_name}: "
                f"{result['confusion_matrix']['total_samples_accounted_for']}"
                f"/{result['sample_count']} samples"
            )

    print("\n[SAFETY] NEVER_MERGE_ACTIVE")

    print(
        "[PASS] Baseline model unchanged."
    )

    print(
        "[PASS] Candidate model unchanged."
    )

    print(
        "[PASS] Primary held-out dataset checksum verified."
    )

    print(
        f"\n[OK] Full evaluation results written to:\n{report_file}"
    )

    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_evaluation()
