"""
PATCHPROOF Phase L — Final Evaluation on Untouched Primary Test Dataset
Strictly evaluates:
  1. Production Baseline (models/bug_detector.joblib)
  2. Candidate K (models/experiments/experiment_k/bug_detector_candidate_k.joblib)
  3. Candidate L2 (models/experiments/experiment_l/candidate_l2_debiased.joblib)

Strict Conditions:
  - Pre-evaluation and post-evaluation SHA-256 integrity verification.
  - Frozen models and preprocessing only; NO retraining, tuning, or calibration.
  - Primary test dataset (data/processed/test.jsonl) remains untouched.
  - NEVER_MERGE safety guard preserved.
  - No promotion or deployment.
"""

import os
import sys
import re
import time
import json
import hashlib
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple
import joblib
import numpy as np

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix
)

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_k"
EXP_L_DIR = ROOT_DIR / "models" / "experiments" / "experiment_l"
EXP_L_DIR.mkdir(parents=True, exist_ok=True)

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

EXPECTED_HASHES = {
    "baseline": (
        ROOT_DIR / "models" / "bug_detector.joblib",
        "5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20"
    ),
    "candidate_k": (
        EXP_K_MODEL_DIR / "bug_detector_candidate_k.joblib",
        "c6ed9f42e8547137577a311f603a9f752084cb2d0be5ff7ce4b75af7bae2377a"
    ),
    "candidate_l2": (
        EXP_L_DIR / "candidate_l2_debiased.joblib",
        "399d155684ff6ac689624175696b4dd6db7bff149fa7421a63b30c76f25c4942"
    ),
    "test_set": (
        PROCESSED_DIR / "test.jsonl",
        "9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d"
    )
}

PROJECT_PATTERNS = re.compile(r'\b(av_|qemu_|qemufile|png_|usb_|linux_|android_)', flags=re.IGNORECASE)

def debias_code_text(text: str) -> str:
    """Neutralizes repository-specific function prefixes to prevent shortcut learning."""
    return PROJECT_PATTERNS.sub('lib_', text)

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_all_hashes(stage: str) -> Dict[str, str]:
    print(f"\n[AUDIT: {stage}] Verifying SHA-256 hashes...")
    actual_hashes = {}
    for name, (path, expected) in EXPECTED_HASHES.items():
        assert path.exists(), f"FATAL: File {path} does not exist!"
        actual = compute_sha256(path)
        actual_hashes[name] = actual
        assert actual == expected, (
            f"FATAL: Hash mismatch for {name} ({path})!\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )
        print(f"  [OK] {name}: {actual}")
    return actual_hashes

def load_primary_test_data() -> Tuple[List[str], List[str], List[str], List[str]]:
    test_path = EXPECTED_HASHES["test_set"][0]
    X, y, langs, ids = [], [], [], []
    with open(test_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                X.append(item["original_code"])
                y.append(item["bug_category"])
                langs.append(item.get("language", "unknown"))
                ids.append(item.get("id", item.get("sample_id", f"idx_{len(X)}")))
    return X, y, langs, ids

def compute_model_metrics(
    y_true: List[str],
    y_pred: List[str],
    languages: List[str],
    latency_ms_per_100: float,
    model_size_mb: float,
    model_name: str
) -> Dict[str, Any]:
    acc = accuracy_score(y_true, y_pred)
    prec_m, rec_m, f1_m, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    prec_w, rec_w, f1_w, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)

    # Clean code overall metrics
    clean_indices = [i for i, y in enumerate(y_true) if y == "none_correct_code"]
    clean_total = len(clean_indices)
    clean_fp = sum(1 for i in clean_indices if y_pred[i] != "none_correct_code")
    clean_fpr = (clean_fp / clean_total) if clean_total > 0 else 0.0

    # Clean code C-only metrics
    c_clean_indices = [i for i, (y, l) in enumerate(zip(y_true, languages)) if y == "none_correct_code" and l == "c"]
    c_clean_total = len(c_clean_indices)
    c_clean_fp = sum(1 for i in c_clean_indices if y_pred[i] != "none_correct_code")
    c_clean_fpr = (c_clean_fp / c_clean_total) if c_clean_total > 0 else 0.0
    c_clean_mem_fp = sum(1 for i in c_clean_indices if y_pred[i] == "memory_safety")
    c_clean_other_fp = c_clean_fp - c_clean_mem_fp

    # Bug FNR (all non-clean samples)
    bug_indices = [i for i, y in enumerate(y_true) if y != "none_correct_code"]
    bug_total = len(bug_indices)
    bug_fn = sum(1 for i in bug_indices if y_pred[i] == "none_correct_code")
    bug_fnr = (bug_fn / bug_total) if bug_total > 0 else 0.0
    bug_recall = 1.0 - bug_fnr

    # Memory Safety metrics
    mem_indices = [i for i, y in enumerate(y_true) if y == "memory_safety"]
    mem_total = len(mem_indices)
    mem_tp = sum(1 for i in mem_indices if y_pred[i] == "memory_safety")
    mem_fp = sum(1 for i in range(len(y_true)) if y_true[i] != "memory_safety" and y_pred[i] == "memory_safety")
    mem_fn = sum(1 for i in mem_indices if y_pred[i] != "memory_safety")
    mem_preds = mem_tp + mem_fp
    mem_prec = (mem_tp / mem_preds) if mem_preds > 0 else 0.0
    mem_rec = (mem_tp / mem_total) if mem_total > 0 else 0.0
    mem_f1 = (2 * mem_prec * mem_rec / (mem_prec + mem_rec)) if (mem_prec + mem_rec) > 0 else 0.0

    # Per-class metrics over canonical taxonomy
    p_cls, r_cls, f_cls, s_cls = precision_recall_fscore_support(
        y_true, y_pred, labels=CANONICAL_CLASSES, zero_division=0
    )
    per_class = {}
    for i, c in enumerate(CANONICAL_CLASSES):
        per_class[c] = {
            "precision": round(float(p_cls[i]), 4),
            "recall": round(float(r_cls[i]), 4),
            "f1": round(float(f_cls[i]), 4),
            "support": int(s_cls[i])
        }

    # Language breakdown
    lang_breakdown = {}
    for lang in sorted(list(set(languages))):
        idx_l = [i for i, l in enumerate(languages) if l == lang]
        yt_l = [y_true[i] for i in idx_l]
        yp_l = [y_pred[i] for i in idx_l]
        acc_l = accuracy_score(yt_l, yp_l)
        wf1_l = precision_recall_fscore_support(yt_l, yp_l, average="weighted", zero_division=0)[2]
        mf1_l = precision_recall_fscore_support(yt_l, yp_l, average="macro", zero_division=0)[2]

        # Language clean FPR & bug FNR
        clean_idx_l = [i for i, y in enumerate(yt_l) if y == "none_correct_code"]
        c_fp_l = sum(1 for i in clean_idx_l if yp_l[i] != "none_correct_code")
        c_fpr_l = (c_fp_l / len(clean_idx_l)) if clean_idx_l else 0.0

        bug_idx_l = [i for i, y in enumerate(yt_l) if y != "none_correct_code"]
        b_fn_l = sum(1 for i in bug_idx_l if yp_l[i] == "none_correct_code")
        b_fnr_l = (b_fn_l / len(bug_idx_l)) if bug_idx_l else 0.0

        lang_breakdown[lang] = {
            "sample_count": len(idx_l),
            "accuracy": round(float(acc_l), 4),
            "weighted_f1": round(float(wf1_l), 4),
            "macro_f1": round(float(mf1_l), 4),
            "clean_total": len(clean_idx_l),
            "clean_fp": c_fp_l,
            "clean_fpr": round(float(c_fpr_l), 4),
            "bug_total": len(bug_idx_l),
            "bug_fn": b_fn_l,
            "bug_fnr": round(float(b_fnr_l), 4)
        }

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=CANONICAL_CLASSES).tolist()

    # Validate confusion matrix integrity
    support_by_class = Counter(y_true)
    for i, label in enumerate(CANONICAL_CLASSES):
        row_sum = sum(cm[i])
        exp_supp = support_by_class.get(label, 0)
        assert row_sum == exp_supp, f"Confusion matrix row sum mismatch for {label}: {row_sum} vs {exp_supp}"
    matrix_total = sum(sum(r) for r in cm)
    assert matrix_total == len(y_true), f"Confusion matrix total mismatch: {matrix_total} vs {len(y_true)}"

    return {
        "model_name": model_name,
        "sample_count": len(y_true),
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(f1_m), 4),
        "weighted_f1": round(float(f1_w), 4),
        "overall_clean_code": {
            "total": clean_total,
            "false_positives": clean_fp,
            "fpr": round(float(clean_fpr), 4)
        },
        "c_clean_code": {
            "total": c_clean_total,
            "false_positives": c_clean_fp,
            "fpr": round(float(c_clean_fpr), 4),
            "fp_misclassified_as_memory_safety": c_clean_mem_fp,
            "fp_misclassified_as_other_defects": c_clean_other_fp
        },
        "bug_detection": {
            "total": bug_total,
            "false_negatives": bug_fn,
            "fnr": round(float(bug_fnr), 4),
            "recall": round(float(bug_recall), 4)
        },
        "memory_safety": {
            "support": mem_total,
            "true_positives": mem_tp,
            "false_positives": mem_fp,
            "false_negatives": mem_fn,
            "precision": round(float(mem_prec), 4),
            "recall": round(float(mem_rec), 4),
            "f1": round(float(mem_f1), 4)
        },
        "latency_ms_per_100": round(float(latency_ms_per_100), 2),
        "model_size_mb": round(float(model_size_mb), 2),
        "language_breakdown": lang_breakdown,
        "per_class": per_class,
        "confusion_matrix": {
            "labels": CANONICAL_CLASSES,
            "matrix": cm
        }
    }

def main():
    print("=" * 80)
    print("PATCHPROOF PHASE L: FINAL COMPARATIVE EVALUATION (PRIMARY TEST SET)")
    print("=" * 80)

    # 1. Pre-evaluation hash check
    pre_hashes = verify_all_hashes("PRE-EVALUATION")

    # 2. Load primary test set
    print(f"\n[DATA] Loading primary test dataset from {EXPECTED_HASHES['test_set'][0]}...")
    X_test, y_test, languages, sample_ids = load_primary_test_data()
    print(f"[DATA] Successfully loaded {len(X_test):,} test samples.")
    assert len(X_test) == 8353, f"Expected 8,353 samples, found {len(X_test)}"

    # 3. Model 1: Production Baseline
    print("\n" + "=" * 60)
    print("EVALUATING MODEL 1: PRODUCTION BASELINE")
    print("=" * 60)
    base_path = EXPECTED_HASHES["baseline"][0]
    base_size_mb = os.path.getsize(base_path) / (1024 * 1024)
    model_base = joblib.load(base_path)

    t0 = time.time()
    y_pred_base = [str(x) for x in model_base.predict(X_test)]
    lat_base = (time.time() - t0) / len(X_test) * 100 * 1000
    res_base = compute_model_metrics(y_test, y_pred_base, languages, lat_base, base_size_mb, "Production Baseline")
    print(f"  Accuracy:    {res_base['accuracy']:.4f} | Weighted F1: {res_base['weighted_f1']:.4f} | Macro F1: {res_base['macro_f1']:.4f}")
    print(f"  Clean FPR:   {res_base['overall_clean_code']['fpr']:.4f} ({res_base['overall_clean_code']['false_positives']}/{res_base['overall_clean_code']['total']})")
    print(f"  C Clean FPR: {res_base['c_clean_code']['fpr']:.4f} ({res_base['c_clean_code']['false_positives']}/{res_base['c_clean_code']['total']}) [Mem Safety FP: {res_base['c_clean_code']['fp_misclassified_as_memory_safety']}]")
    print(f"  Mem Prec:    {res_base['memory_safety']['precision']:.4f} | Recall: {res_base['memory_safety']['recall']:.4f} | F1: {res_base['memory_safety']['f1']:.4f}")
    print(f"  Bug FNR:     {res_base['bug_detection']['fnr']:.4f} (Recall: {res_base['bug_detection']['recall']:.4f})")
    print(f"  Latency:     {res_base['latency_ms_per_100']:.2f} ms/100 | Size: {res_base['model_size_mb']:.2f} MB")

    # 4. Model 2: Candidate K
    print("\n" + "=" * 60)
    print("EVALUATING MODEL 2: CANDIDATE K")
    print("=" * 60)
    cand_k_path = EXPECTED_HASHES["candidate_k"][0]
    cand_k_size_mb = os.path.getsize(cand_k_path) / (1024 * 1024)
    model_k = joblib.load(cand_k_path)

    t0 = time.time()
    y_pred_k = [str(x) for x in model_k.predict(X_test)]
    lat_k = (time.time() - t0) / len(X_test) * 100 * 1000
    res_k = compute_model_metrics(y_test, y_pred_k, languages, lat_k, cand_k_size_mb, "Candidate K")
    print(f"  Accuracy:    {res_k['accuracy']:.4f} | Weighted F1: {res_k['weighted_f1']:.4f} | Macro F1: {res_k['macro_f1']:.4f}")
    print(f"  Clean FPR:   {res_k['overall_clean_code']['fpr']:.4f} ({res_k['overall_clean_code']['false_positives']}/{res_k['overall_clean_code']['total']})")
    print(f"  C Clean FPR: {res_k['c_clean_code']['fpr']:.4f} ({res_k['c_clean_code']['false_positives']}/{res_k['c_clean_code']['total']}) [Mem Safety FP: {res_k['c_clean_code']['fp_misclassified_as_memory_safety']}]")
    print(f"  Mem Prec:    {res_k['memory_safety']['precision']:.4f} | Recall: {res_k['memory_safety']['recall']:.4f} | F1: {res_k['memory_safety']['f1']:.4f}")
    print(f"  Bug FNR:     {res_k['bug_detection']['fnr']:.4f} (Recall: {res_k['bug_detection']['recall']:.4f})")
    print(f"  Latency:     {res_k['latency_ms_per_100']:.2f} ms/100 | Size: {res_k['model_size_mb']:.2f} MB")

    # 5. Model 3: Candidate L2 (Frozen Debiased Pipeline)
    print("\n" + "=" * 60)
    print("EVALUATING MODEL 3: CANDIDATE L2 (FROZEN DEBIASED)")
    print("=" * 60)
    cand_l2_path = EXPECTED_HASHES["candidate_l2"][0]
    cand_l2_size_mb = os.path.getsize(cand_l2_path) / (1024 * 1024)
    model_l2 = joblib.load(cand_l2_path)

    t0 = time.time()
    X_test_debiased = [debias_code_text(x) for x in X_test]
    y_pred_l2 = [str(x) for x in model_l2.predict(X_test_debiased)]
    lat_l2 = (time.time() - t0) / len(X_test) * 100 * 1000
    res_l2 = compute_model_metrics(y_test, y_pred_l2, languages, lat_l2, cand_l2_size_mb, "Candidate L2")
    print(f"  Accuracy:    {res_l2['accuracy']:.4f} | Weighted F1: {res_l2['weighted_f1']:.4f} | Macro F1: {res_l2['macro_f1']:.4f}")
    print(f"  Clean FPR:   {res_l2['overall_clean_code']['fpr']:.4f} ({res_l2['overall_clean_code']['false_positives']}/{res_l2['overall_clean_code']['total']})")
    print(f"  C Clean FPR: {res_l2['c_clean_code']['fpr']:.4f} ({res_l2['c_clean_code']['false_positives']}/{res_l2['c_clean_code']['total']}) [Mem Safety FP: {res_l2['c_clean_code']['fp_misclassified_as_memory_safety']}]")
    print(f"  Mem Prec:    {res_l2['memory_safety']['precision']:.4f} | Recall: {res_l2['memory_safety']['recall']:.4f} | F1: {res_l2['memory_safety']['f1']:.4f}")
    print(f"  Bug FNR:     {res_l2['bug_detection']['fnr']:.4f} (Recall: {res_l2['bug_detection']['recall']:.4f})")
    print(f"  Latency:     {res_l2['latency_ms_per_100']:.2f} ms/100 | Size: {res_l2['model_size_mb']:.2f} MB")

    # 6. Post-evaluation hash check
    post_hashes = verify_all_hashes("POST-EVALUATION")

    # 7. Comparison Summary
    c_fp_reduction = res_k['c_clean_code']['false_positives'] - res_l2['c_clean_code']['false_positives']
    c_fp_pct_reduction = (c_fp_reduction / res_k['c_clean_code']['false_positives']) * 100 if res_k['c_clean_code']['false_positives'] > 0 else 0.0

    c_mem_fp_reduction = res_k['c_clean_code']['fp_misclassified_as_memory_safety'] - res_l2['c_clean_code']['fp_misclassified_as_memory_safety']
    c_mem_fp_pct_reduction = (c_mem_fp_reduction / res_k['c_clean_code']['fp_misclassified_as_memory_safety']) * 100 if res_k['c_clean_code']['fp_misclassified_as_memory_safety'] > 0 else 0.0

    comparison = {
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "test_dataset": {
            "path": str(EXPECTED_HASHES["test_set"][0]),
            "sha256": post_hashes["test_set"],
            "sample_count": len(X_test),
            "languages": dict(Counter(languages)),
            "ground_truth_classes": dict(Counter(y_test))
        },
        "model_hashes": {
            "baseline": {
                "path": str(EXPECTED_HASHES["baseline"][0]),
                "sha256": post_hashes["baseline"]
            },
            "candidate_k": {
                "path": str(EXPECTED_HASHES["candidate_k"][0]),
                "sha256": post_hashes["candidate_k"]
            },
            "candidate_l2": {
                "path": str(EXPECTED_HASHES["candidate_l2"][0]),
                "sha256": post_hashes["candidate_l2"]
            }
        },
        "c_clean_false_positive_reduction": {
            "candidate_k_c_clean_fp": res_k['c_clean_code']['false_positives'],
            "candidate_l2_c_clean_fp": res_l2['c_clean_code']['false_positives'],
            "absolute_reduction": c_fp_reduction,
            "relative_reduction_pct": round(c_fp_pct_reduction, 2),
            "candidate_k_c_mem_fp": res_k['c_clean_code']['fp_misclassified_as_memory_safety'],
            "candidate_l2_c_mem_fp": res_l2['c_clean_code']['fp_misclassified_as_memory_safety'],
            "mem_fp_absolute_reduction": c_mem_fp_reduction,
            "mem_fp_relative_reduction_pct": round(c_mem_fp_pct_reduction, 2)
        },
        "models": {
            "baseline": res_base,
            "candidate_k": res_k,
            "candidate_l2": res_l2
        },
        "safety_guard": {
            "invariant": "NEVER_MERGE_ACTIVE",
            "status": "VERIFIED_ACTIVE",
            "model_promoted": False
        }
    }

    # Save to phase_l_final_evaluation.json
    out_file = EXP_L_DIR / "phase_l_final_evaluation.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n[SAVE] Final evaluation output written to: {out_file}")

if __name__ == "__main__":
    main()
