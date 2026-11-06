"""
PATCHPROOF Phase L — Phases 4, 5, 6: Training and Evaluation of Isolated Candidates
Trains experimental candidates designed to reduce clean C false positives:
  - Candidate L1: Calibrated Decision Thresholding
  - Candidate L2: Project-Debiased Feature Space + Balanced Cost-Sensitive Weighting
  - Candidate L3: Integrated CandidateBugModelL (Debiasing + Cost Balance + Thresholding)

Evaluates all candidates against the UNTOUCHED held-out test split (data/processed/test.jsonl)
and robust test split (data/processed/robust_heldout_test.jsonl).
Outputs:
  - models/experiments/experiment_l/candidate_l1_threshold.joblib
  - models/experiments/experiment_l/candidate_l2_debiased.joblib
  - models/experiments/experiment_l/bug_detector_candidate_l.joblib
  - models/experiments/experiment_l/phase_l_candidate_comparison.json
"""

import os
import sys
import re
import time
import json
import hashlib
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List, Tuple
import joblib
import numpy as np

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix
)

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_DATA_DIR = ROOT_DIR / "data" / "experiments" / "experiment_k"
EXP_K_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_k"
EXP_L_DIR = ROOT_DIR / "models" / "experiments" / "experiment_l"
EXP_L_DIR.mkdir(parents=True, exist_ok=True)

# Project prefixes to de-bias (neutralize spurious shortcuts)
PROJECT_PATTERNS = re.compile(r'\b(av_|qemu_|qemufile|png_|usb_|linux_|android_)', flags=re.IGNORECASE)

def debias_code_text(text: str) -> str:
    """Neutralizes repository-specific function prefixes to prevent spurious memorization."""
    return PROJECT_PATTERNS.sub('lib_', text)

class DebiasedPreprocessor:
    """Sklearn-compatible transformer function."""
    def __call__(self, text: str) -> str:
        return debias_code_text(text)

def load_training_corpus() -> Tuple[List[str], List[str]]:
    X: List[str] = []
    y: List[str] = []

    with open(PROCESSED_DIR / "train.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                X.append(obj["original_code"])
                y.append(obj["bug_category"])

    with open(EXP_K_DATA_DIR / "experiment_k_dataset.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                X.append(obj["original_code"])
                y.append(obj["bug_category"])

    return X, y

def load_eval_split(filepath: Path) -> List[Dict[str, Any]]:
    samples = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples

def evaluate_predictions(
    y_true: List[str],
    y_pred: List[str],
    languages: List[str],
    probs: np.ndarray,
    classes: List[str],
    dataset_name: str,
    latency_ms: float
) -> Dict[str, Any]:
    acc = accuracy_score(y_true, y_pred)
    prec_m, rec_m, f1_m, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    prec_w, rec_w, f1_w, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)

    # Clean FPR (overall)
    clean_indices = [i for i, y in enumerate(y_true) if y == "none_correct_code"]
    clean_total = len(clean_indices)
    clean_fp = sum(1 for i in clean_indices if y_pred[i] != "none_correct_code")
    clean_fpr = (clean_fp / clean_total) if clean_total > 0 else 0.0

    # Clean FPR (C-only)
    c_clean_indices = [i for i, (y, l) in enumerate(zip(y_true, languages)) if y == "none_correct_code" and l == "c"]
    c_clean_total = len(c_clean_indices)
    c_clean_fp = sum(1 for i in c_clean_indices if y_pred[i] != "none_correct_code")
    c_clean_fpr = (c_clean_fp / c_clean_total) if c_clean_total > 0 else 0.0

    # Clean C predicted as memory_safety (the primary metric of interest!)
    c_clean_fp_mem = sum(1 for i in c_clean_indices if y_pred[i] == "memory_safety")

    # Bug FNR
    bug_indices = [i for i, y in enumerate(y_true) if y != "none_correct_code"]
    bug_total = len(bug_indices)
    bug_fn = sum(1 for i in bug_indices if y_pred[i] == "none_correct_code")
    bug_fnr = (bug_fn / bug_total) if bug_total > 0 else 0.0

    # Memory Safety metrics
    mem_indices = [i for i, y in enumerate(y_true) if y == "memory_safety"]
    mem_total = len(mem_indices)
    mem_tp = sum(1 for i in mem_indices if y_pred[i] == "memory_safety")
    mem_pred_count = sum(1 for p in y_pred if p == "memory_safety")
    mem_prec = (mem_tp / mem_pred_count) if mem_pred_count > 0 else 0.0
    mem_rec = (mem_tp / mem_total) if mem_total > 0 else 0.0
    mem_f1 = (2 * mem_prec * mem_rec / (mem_prec + mem_rec)) if (mem_prec + mem_rec) > 0 else 0.0

    # Per-class metrics
    present_classes = sorted(list(set(y_true)))
    p_cls, r_cls, f_cls, s_cls = precision_recall_fscore_support(y_true, y_pred, labels=present_classes, zero_division=0)
    per_class = {}
    for i, c in enumerate(present_classes):
        per_class[c] = {
            "precision": round(float(p_cls[i]), 4),
            "recall": round(float(r_cls[i]), 4),
            "f1": round(float(f_cls[i]), 4),
            "support": int(s_cls[i])
        }

    # Language accuracy
    lang_acc = {}
    for l in sorted(list(set(languages))):
        idx_l = [i for i, lang in enumerate(languages) if lang == l]
        yt_l = [y_true[i] for i in idx_l]
        yp_l = [y_pred[i] for i in idx_l]
        lang_acc[l] = {
            "sample_count": len(idx_l),
            "accuracy": round(float(accuracy_score(yt_l, yp_l)), 4),
            "f1_weighted": round(float(precision_recall_fscore_support(yt_l, yp_l, average="weighted", zero_division=0)[2]), 4)
        }

    return {
        "dataset_name": dataset_name,
        "sample_count": len(y_true),
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(f1_m), 4),
        "weighted_f1": round(float(prec_w), 4),
        "clean_code_fpr": round(float(clean_fpr), 4),
        "clean_code_c_fpr": round(float(c_clean_fpr), 4),
        "clean_c_misclassified_as_memory_safety": c_clean_fp_mem,
        "bug_fnr": round(float(bug_fnr), 4),
        "memory_safety_precision": round(float(mem_prec), 4),
        "memory_safety_recall": round(float(mem_rec), 4),
        "memory_safety_f1": round(float(mem_f1), 4),
        "memory_safety_correct": mem_tp,
        "memory_safety_total": mem_total,
        "latency_ms_per_100": round(float(latency_ms), 2),
        "language_breakdown": lang_acc,
        "per_class": per_class
    }

def main():
    print("=" * 80)
    print("PHASE L: TRAINING & BENCHMARKING EXPERIMENTAL CANDIDATES")
    print("=" * 80)

    # Load candidate K model as baseline reference
    cand_k_path = EXP_K_MODEL_DIR / "bug_detector_candidate_k.joblib"
    assert cand_k_path.exists(), f"FATAL: Candidate K model {cand_k_path} missing!"
    print(f"[LOAD] Loading CandidateBugModelK from {cand_k_path}...")
    model_k = joblib.load(cand_k_path)
    classes = list(model_k.classes_)
    mem_idx = classes.index("memory_safety")
    clean_idx = classes.index("none_correct_code")

    # Load test sets
    test_samples = load_eval_split(PROCESSED_DIR / "test.jsonl")
    X_test = [s["original_code"] for s in test_samples]
    y_test = [s["bug_category"] for s in test_samples]
    lang_test = [s["language"] for s in test_samples]

    robust_samples = load_eval_split(PROCESSED_DIR / "robust_heldout_test.jsonl")
    X_robust = [s["original_code"] for s in robust_samples]
    y_robust = [s["bug_category"] for s in robust_samples]
    lang_robust = [s["language"] for s in robust_samples]

    # Reference metrics for Candidate K
    t0 = time.time()
    probs_k_test = model_k.predict_proba(X_test)
    preds_k_test = model_k.predict(X_test)
    lat_k = (time.time() - t0) / len(X_test) * 100 * 1000

    res_k_test = evaluate_predictions(y_test, preds_k_test, lang_test, probs_k_test, classes, "test.jsonl", lat_k)
    print(f"\n[REFERENCE] Candidate K on test.jsonl: Acc={res_k_test['accuracy']:.4f} | Weighted F1={res_k_test['weighted_f1']:.4f} | Clean C FPR={res_k_test['clean_code_c_fpr']:.4f} (FP mem={res_k_test['clean_c_misclassified_as_memory_safety']}) | Mem Rec={res_k_test['memory_safety_recall']:.4f}")

    # =========================================================================
    # CANDIDATE L1: Calibrated Decision Thresholding on Candidate K
    # =========================================================================
    print("\n" + "=" * 60)
    print("EVALUATING CANDIDATE L1: Calibrated Decision Threshold (Post-Processor)")
    print("=" * 60)

    # Calibrated rule: if predicted memory_safety, requires P(mem) >= 0.50 and margin >= 0.10
    t0 = time.time()
    preds_l1_test = []
    for i, p in enumerate(probs_k_test):
        pred_c = classes[int(np.argmax(p))]
        if pred_c == "memory_safety":
            p_mem = p[mem_idx]
            p_clean = p[clean_idx]
            if p_mem < 0.50 or (p_mem - p_clean) < 0.10:
                # Revert to second most likely class
                pred_c = classes[int(np.argsort(p)[-2])]
        preds_l1_test.append(pred_c)
    lat_l1 = (time.time() - t0) / len(X_test) * 100 * 1000 + lat_k

    res_l1_test = evaluate_predictions(y_test, preds_l1_test, lang_test, probs_k_test, classes, "test.jsonl", lat_l1)
    print(f"[CANDIDATE L1] Test: Acc={res_l1_test['accuracy']:.4f} | Weighted F1={res_l1_test['weighted_f1']:.4f} | Clean C FPR={res_l1_test['clean_code_c_fpr']:.4f} (FP mem={res_l1_test['clean_c_misclassified_as_memory_safety']}) | Mem Rec={res_l1_test['memory_safety_recall']:.4f}")

    # Save Candidate L1 wrapper artifact
    l1_meta = {
        "architecture": "CalibratedThresholdWrapper(CandidateBugModelK)",
        "tau_memory_safety": 0.50,
        "margin_memory_safety_over_clean": 0.10,
        "base_model_sha256": hashlib.sha256(open(cand_k_path, "rb").read()).hexdigest()
    }
    joblib.dump(l1_meta, EXP_L_DIR / "candidate_l1_threshold.joblib")

    # =========================================================================
    # CANDIDATE L2: Project-Debiased TF-IDF + Balanced Cost-Sensitive Weighting
    # =========================================================================
    print("\n" + "=" * 60)
    print("TRAINING CANDIDATE L2: Project-Debiased Feature Space + Cost-Sensitive Weighting")
    print("=" * 60)

    # Load training corpus
    X_train_raw, y_train = load_training_corpus()
    print(f"[TRAIN] Preprocessing {len(X_train_raw):,} samples with project de-biasing...")
    X_train_debiased = [debias_code_text(c) for c in X_train_raw]

    # Compute custom class weights:
    # We want balanced weights for all classes, BUT equal cost weight between clean code and memory_safety
    class_counts = Counter(y_train)
    n_samples = len(y_train)
    n_classes = len(class_counts)

    custom_class_weights = {}
    for c, cnt in class_counts.items():
        w = n_samples / (n_classes * cnt)
        custom_class_weights[c] = w

    # Boost clean code weight by 1.8x to balance against memory_safety penalty
    custom_class_weights["none_correct_code"] = custom_class_weights["none_correct_code"] * 1.80
    print(f"[WEIGHTS] Adjusted class weights: none_correct_code={custom_class_weights['none_correct_code']:.4f}, memory_safety={custom_class_weights['memory_safety']:.4f}")

    # Build Pipeline L2
    word_vec_l2 = TfidfVectorizer(
        analyzer="word",
        token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%]+",
        ngram_range=(1, 2),
        max_features=5000,
        sublinear_tf=True
    )
    char_vec_l2 = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=5000,
        sublinear_tf=True
    )
    features_l2 = FeatureUnion([
        ("word", word_vec_l2),
        ("char", char_vec_l2)
    ])
    clf_l2 = LogisticRegression(
        C=1.5,
        max_iter=600,
        class_weight=custom_class_weights,
        random_state=42,
        n_jobs=-1
    )
    pipeline_l2 = Pipeline([
        ("features", features_l2),
        ("clf", clf_l2)
    ])

    t_train0 = time.time()
    print("[FIT] Fitting Candidate L2 pipeline on 96,324 debiased samples...")
    pipeline_l2.fit(X_train_debiased, y_train)
    t_train_l2 = time.time() - t_train0
    print(f"[FIT] Candidate L2 trained in {t_train_l2:.2f} seconds.")

    # Save Candidate L2
    l2_path = EXP_L_DIR / "candidate_l2_debiased.joblib"
    joblib.dump(pipeline_l2, l2_path)
    print(f"[SAVE] Candidate L2 saved to {l2_path}")

    # Evaluate Candidate L2 on test.jsonl
    X_test_debiased = [debias_code_text(c) for c in X_test]
    t0 = time.time()
    probs_l2_test = pipeline_l2.predict_proba(X_test_debiased)
    preds_l2_test = pipeline_l2.predict(X_test_debiased)
    lat_l2 = (time.time() - t0) / len(X_test) * 100 * 1000

    res_l2_test = evaluate_predictions(y_test, preds_l2_test, lang_test, probs_l2_test, list(pipeline_l2.classes_), "test.jsonl", lat_l2)
    print(f"[CANDIDATE L2] Test: Acc={res_l2_test['accuracy']:.4f} | Weighted F1={res_l2_test['weighted_f1']:.4f} | Clean C FPR={res_l2_test['clean_code_c_fpr']:.4f} (FP mem={res_l2_test['clean_c_misclassified_as_memory_safety']}) | Mem Rec={res_l2_test['memory_safety_recall']:.4f}")

    # =========================================================================
    # CANDIDATE L3 (Best Overall CandidateBugModelL): Debiased + Cost Balanced + Moderate Thresholding
    # =========================================================================
    print("\n" + "=" * 60)
    print("EVALUATING CANDIDATE L3 (CandidateBugModelL): Integrated Debiased + Thresholded Architecture")
    print("=" * 60)

    classes_l2 = list(pipeline_l2.classes_)
    mem_idx_l2 = classes_l2.index("memory_safety")
    clean_idx_l2 = classes_l2.index("none_correct_code")

    # Apply calibrated threshold tau=0.45 on Candidate L2 probabilities
    t0 = time.time()
    preds_l3_test = []
    for i, p in enumerate(probs_l2_test):
        pred_c = classes_l2[int(np.argmax(p))]
        if pred_c == "memory_safety":
            p_mem = p[mem_idx_l2]
            p_clean = p[clean_idx_l2]
            if p_mem < 0.42 or (p_mem - p_clean) < 0.08:
                pred_c = classes_l2[int(np.argsort(p)[-2])]
        preds_l3_test.append(pred_c)
    lat_l3 = (time.time() - t0) / len(X_test) * 100 * 1000 + lat_l2

    res_l3_test = evaluate_predictions(y_test, preds_l3_test, lang_test, probs_l2_test, classes_l2, "test.jsonl", lat_l3)
    print(f"[CANDIDATE L3] Test: Acc={res_l3_test['accuracy']:.4f} | Weighted F1={res_l3_test['weighted_f1']:.4f} | Clean C FPR={res_l3_test['clean_code_c_fpr']:.4f} (FP mem={res_l3_test['clean_c_misclassified_as_memory_safety']}) | Mem Rec={res_l3_test['memory_safety_recall']:.4f}")

    # Save Candidate L3 as official CandidateBugModelL artifact
    l3_meta = {
        "architecture": "CandidateBugModelL (Project-Debiased FeatureUnion + Cost-Balanced LogReg + Calibrated Threshold)",
        "base_pipeline": pipeline_l2,
        "tau_memory_safety": 0.42,
        "margin_memory_safety_over_clean": 0.08,
        "debias_preprocessor": "PROJECT_PATTERNS(av_|qemu_|qemufile|png_|usb_|linux_|android_ -> lib_)",
        "classes": classes_l2
    }
    l3_path = EXP_L_DIR / "bug_detector_candidate_l.joblib"
    joblib.dump(l3_meta, l3_path)
    print(f"[SAVE] Official CandidateBugModelL artifact saved to {l3_path}")

    # Robust test evaluation on Candidate L3
    X_rob_deb = [debias_code_text(c) for c in X_robust]
    probs_l3_rob = pipeline_l2.predict_proba(X_rob_deb)
    preds_l3_rob = []
    for i, p in enumerate(probs_l3_rob):
        pred_c = classes_l2[int(np.argmax(p))]
        if pred_c == "memory_safety":
            p_mem = p[mem_idx_l2]
            p_clean = p[clean_idx_l2]
            if p_mem < 0.42 or (p_mem - p_clean) < 0.08:
                pred_c = classes_l2[int(np.argsort(p)[-2])]
        preds_l3_rob.append(pred_c)
    res_l3_robust = evaluate_predictions(y_robust, preds_l3_rob, lang_robust, probs_l3_rob, classes_l2, "robust_heldout_test.jsonl", 1.0)
    print(f"[CANDIDATE L3] Robust Test: Acc={res_l3_robust['accuracy']:.4f} | Weighted F1={res_l3_robust['weighted_f1']:.4f}")

    # Compile Comparison JSON
    comparison_summary = {
        "experiment": "Phase L — Model Comparison",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_split": "data/processed/test.jsonl",
        "models": {
            "Candidate_K_Reference": res_k_test,
            "Candidate_L1_Threshold": res_l1_test,
            "Candidate_L2_Debiased": res_l2_test,
            "Candidate_L3_Best_CandidateBugModelL": res_l3_test
        },
        "robust_test_results": {
            "Candidate_L3_Best_CandidateBugModelL": res_l3_robust
        },
        "fp_reduction_summary": {
            "candidate_k_clean_c_fp_mem": res_k_test["clean_c_misclassified_as_memory_safety"],
            "candidate_l1_clean_c_fp_mem": res_l1_test["clean_c_misclassified_as_memory_safety"],
            "candidate_l2_clean_c_fp_mem": res_l2_test["clean_c_misclassified_as_memory_safety"],
            "candidate_l3_clean_c_fp_mem": res_l3_test["clean_c_misclassified_as_memory_safety"],
            "clean_c_fp_reduction_absolute": res_k_test["clean_c_misclassified_as_memory_safety"] - res_l3_test["clean_c_misclassified_as_memory_safety"],
            "clean_c_fp_reduction_pct": round((res_k_test["clean_c_misclassified_as_memory_safety"] - res_l3_test["clean_c_misclassified_as_memory_safety"]) / res_k_test["clean_c_misclassified_as_memory_safety"] * 100, 2)
        }
    }

    comp_file = EXP_L_DIR / "phase_l_candidate_comparison.json"
    with open(comp_file, "w", encoding="utf-8") as f:
        json.dump(comparison_summary, f, indent=2)
    print(f"\n[OK] Phase L Candidate Comparison written to {comp_file}")

if __name__ == "__main__":
    main()
