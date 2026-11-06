#!/usr/bin/env python3
"""
scripts/experiments/experiment_o/evaluate_phase_o2.py

Phase O.2: Frozen Evaluation on Independent C Benchmark O.
Evaluates four configurations:
1. Production Baseline
2. Candidate K
3. Candidate L2
4. Phase N Decision Boundary Policy (tau=0.30, delta=-0.12 applied to L2)

Enforces strict preflight checks, post-run verification, Wilson score CIs,
bootstrap CIs, subgroup analysis, and generates all required deliverables.
"""

import os
import sys
import json
import time
import math
import hashlib
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import joblib
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix
)

ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.core import config

EXPECTED_HASHES = {
    "baseline_model": (
        ROOT_DIR / "models" / "bug_detector.joblib",
        "5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20"
    ),
    "candidate_k_model": (
        ROOT_DIR / "models" / "experiments" / "experiment_k" / "bug_detector_candidate_k.joblib",
        "c6ed9f42e8547137577a311f603a9f752084cb2d0be5ff7ce4b75af7bae2377a"
    ),
    "candidate_l2_model": (
        ROOT_DIR / "models" / "experiments" / "experiment_l" / "candidate_l2_debiased.joblib",
        "399d155684ff6ac689624175696b4dd6db7bff149fa7421a63b30c76f25c4942"
    ),
    "train_split": (
        ROOT_DIR / "data" / "processed" / "train.jsonl",
        "6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad"
    ),
    "val_split": (
        ROOT_DIR / "data" / "processed" / "val.jsonl",
        "935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f"
    ),
    "test_split": (
        ROOT_DIR / "data" / "processed" / "test.jsonl",
        "9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d"
    ),
    "robust_test_split": (
        ROOT_DIR / "data" / "processed" / "robust_heldout_test.jsonl",
        "e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1"
    ),
    "benchmark_dataset": (
        ROOT_DIR / "models" / "experiments" / "experiment_o" / "phase_o_benchmark_dataset.jsonl",
        "caa7abe4f0dc22eefebf39a042934f3a3eaf8994290c4c6a057abd25f6e3d0dc"
    )
}

PROJECT_PATTERNS = re.compile(r'\b(av_|qemu_|qemufile|png_|usb_|linux_|android_)', flags=re.IGNORECASE)

def debias_code_text(text: str) -> str:
    return PROJECT_PATTERNS.sub('lib_', text)

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_all_hashes(stage: str) -> Dict[str, Dict[str, Any]]:
    print(f"\n[HASH AUDIT: {stage}] Verifying cryptographic checksums...")
    results = {}
    for name, (path, expected) in EXPECTED_HASHES.items():
        assert path.exists(), f"File missing: {path}"
        actual = compute_sha256(path)
        is_match = (actual == expected)
        print(f"  [{'MATCH' if is_match else 'FAIL'}] {name}: {actual[:16]}... (exp: {expected[:16]}...)")
        assert is_match, f"Hash mismatch for {name}! Actual: {actual}, Expected: {expected}"
        results[name] = {"path": str(path), "expected": expected, "actual": actual, "match": is_match}

    never_merge = getattr(config, "NEVER_MERGE", None)
    print(f"  [NEVER_MERGE] Status: {never_merge}")
    assert never_merge is True, "NEVER_MERGE invariant violated!"
    results["NEVER_MERGE"] = {"status": never_merge, "match": (never_merge is True)}
    return results

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.959963984540054  # 95%
    p = successes / total
    denominator = 1.0 + z * z / total
    centre_adjusted_probability = p + z * z / (2.0 * total)
    adjusted_std_dev = math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    lower = max(0.0, (centre_adjusted_probability - z * adjusted_std_dev) / denominator)
    upper = min(1.0, (centre_adjusted_probability + z * adjusted_std_dev) / denominator)
    return round(lower, 4), round(upper, 4)

def bootstrap_f1_cis(y_true: List[str], y_pred: List[str], n_bootstraps: int = 1000, seed: int = 42) -> Dict[str, Tuple[float, float]]:
    rng = np.random.RandomState(seed)
    n = len(y_true)
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)

    macro_f1s = []
    weighted_f1s = []

    for _ in range(n_bootstraps):
        boot_idx = rng.randint(0, n, size=n)
        yt_boot = y_true_arr[boot_idx]
        yp_boot = y_pred_arr[boot_idx]

        mf1 = precision_recall_fscore_support(yt_boot, yp_boot, average="macro", zero_division=0)[2]
        wf1 = precision_recall_fscore_support(yt_boot, yp_boot, average="weighted", zero_division=0)[2]
        macro_f1s.append(mf1)
        weighted_f1s.append(wf1)

    return {
        "macro_f1_ci": (round(float(np.percentile(macro_f1s, 2.5)), 4), round(float(np.percentile(macro_f1s, 97.5)), 4)),
        "weighted_f1_ci": (round(float(np.percentile(weighted_f1s, 2.5)), 4), round(float(np.percentile(weighted_f1s, 97.5)), 4))
    }

def compute_detailed_metrics(
    y_true: List[str],
    y_pred: List[str],
    classes: List[str],
    elapsed_time: float,
    seed: int = 42
) -> Dict[str, Any]:
    n = len(y_true)
    acc = accuracy_score(y_true, y_pred)
    acc_ci = wilson_score_interval(sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp), n)

    pm, rm, fm, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    pw, rw, fw, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    boot_cis = bootstrap_f1_cis(y_true, y_pred, n_bootstraps=1000, seed=seed)

    # Clean Code (none_correct_code)
    clean_indices = [i for i, y in enumerate(y_true) if y == "none_correct_code"]
    clean_total = len(clean_indices)
    clean_fp = sum(1 for i in clean_indices if y_pred[i] != "none_correct_code")
    clean_fpr = (clean_fp / clean_total) if clean_total > 0 else 0.0
    clean_fpr_ci = wilson_score_interval(clean_fp, clean_total)

    # Overall Vulnerable (any non-clean)
    vuln_indices = [i for i, y in enumerate(y_true) if y != "none_correct_code"]
    vuln_total = len(vuln_indices)
    vuln_tp = sum(1 for i in vuln_indices if y_pred[i] != "none_correct_code")
    vuln_fn = sum(1 for i in vuln_indices if y_pred[i] == "none_correct_code")
    vuln_rec = (vuln_tp / vuln_total) if vuln_total > 0 else 0.0
    vuln_rec_ci = wilson_score_interval(vuln_tp, vuln_total)
    bug_fnr = (vuln_fn / vuln_total) if vuln_total > 0 else 0.0
    bug_fnr_ci = wilson_score_interval(vuln_fn, vuln_total)

    total_pred_vuln = sum(1 for p in y_pred if p != "none_correct_code")
    vuln_prec = (vuln_tp / total_pred_vuln) if total_pred_vuln > 0 else 0.0
    vuln_prec_ci = wilson_score_interval(vuln_tp, total_pred_vuln) if total_pred_vuln > 0 else (0.0, 0.0)
    vuln_f1 = (2 * vuln_prec * vuln_rec / (vuln_prec + vuln_rec)) if (vuln_prec + vuln_rec) > 0 else 0.0

    # Memory Safety Specific
    mem_indices = [i for i, y in enumerate(y_true) if y == "memory_safety"]
    mem_total = len(mem_indices)
    mem_tp = sum(1 for i in mem_indices if y_pred[i] == "memory_safety")
    mem_fn = sum(1 for i in mem_indices if y_pred[i] != "memory_safety")
    total_pred_mem = sum(1 for p in y_pred if p == "memory_safety")
    mem_fp = total_pred_mem - mem_tp
    mem_rec = (mem_tp / mem_total) if mem_total > 0 else 0.0
    mem_rec_ci = wilson_score_interval(mem_tp, mem_total)
    mem_prec = (mem_tp / total_pred_mem) if total_pred_mem > 0 else 0.0
    mem_prec_ci = wilson_score_interval(mem_tp, total_pred_mem) if total_pred_mem > 0 else (0.0, 0.0)
    mem_f1 = (2 * mem_prec * mem_rec / (mem_prec + mem_rec)) if (mem_prec + mem_rec) > 0 else 0.0

    # Per-Class Precision, Recall, F1
    p_cls, r_cls, f_cls, s_cls = precision_recall_fscore_support(
        y_true, y_pred, labels=classes, zero_division=0
    )
    per_class = {}
    for idx, c in enumerate(classes):
        per_class[c] = {
            "precision": round(float(p_cls[idx]), 4),
            "recall": round(float(r_cls[idx]), 4),
            "f1": round(float(f_cls[idx]), 4),
            "support": int(s_cls[idx])
        }

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=classes).tolist()

    return {
        "overall": {
            "accuracy": round(float(acc), 4),
            "accuracy_95_ci": acc_ci,
            "macro_f1": round(float(fm), 4),
            "macro_f1_95_ci": boot_cis["macro_f1_ci"],
            "weighted_f1": round(float(fw), 4),
            "weighted_f1_95_ci": boot_cis["weighted_f1_ci"],
            "inference_latency_seconds": round(float(elapsed_time), 4),
            "latency_ms_per_sample": round(float((elapsed_time / n) * 1000), 2),
            "total_samples": n,
            "prediction_failures": 0
        },
        "security_detection": {
            "vulnerable_total": vuln_total,
            "vulnerable_tp": vuln_tp,
            "vulnerable_fn": vuln_fn,
            "vulnerable_recall": round(float(vuln_rec), 4),
            "vulnerable_recall_95_ci": vuln_rec_ci,
            "vulnerable_precision": round(float(vuln_prec), 4),
            "vulnerable_precision_95_ci": vuln_prec_ci,
            "vulnerable_f1": round(float(vuln_f1), 4),
            "bug_false_negative_rate": round(float(bug_fnr), 4),
            "bug_fnr_95_ci": bug_fnr_ci,
            "clean_total": clean_total,
            "clean_fp": clean_fp,
            "clean_false_positive_rate": round(float(clean_fpr), 4),
            "clean_fpr_95_ci": clean_fpr_ci
        },
        "memory_safety": {
            "support": mem_total,
            "true_positives": mem_tp,
            "false_positives": mem_fp,
            "false_negatives": mem_fn,
            "precision": round(float(mem_prec), 4),
            "precision_95_ci": mem_prec_ci,
            "recall": round(float(mem_rec), 4),
            "recall_95_ci": mem_rec_ci,
            "f1": round(float(mem_f1), 4)
        },
        "per_class": per_class,
        "confusion_matrix": {
            "classes": classes,
            "matrix": cm
        }
    }

def main():
    total_start = time.time()
    print("=" * 80)
    print("PATCHPROOF PHASE O.2: FROZEN EVALUATION ON INDEPENDENT C BENCHMARK O")
    print("=" * 80)

    out_dir = ROOT_DIR / "models" / "experiments" / "experiment_o" / "phase_o2"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Preflight Verification
    preflight_hashes = verify_all_hashes("PRE-EVALUATION")

    # 2. Load Benchmark Dataset
    print("\n[DATASET] Loading locked independent C benchmark dataset...")
    benchmark_file = EXPECTED_HASHES["benchmark_dataset"][0]
    records = []
    with open(benchmark_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"  Loaded {len(records)} benchmark records.")
    assert len(records) == 1450, f"Expected 1,450 records, got {len(records)}"

    clean_records = [r for r in records if not r["is_vulnerable"]]
    vuln_records = [r for r in records if r["is_vulnerable"]]
    core_vuln = [r for r in records if r["is_vulnerable"] and r["source_tier"] == "CORE_ACCEPTED_UNSEEN_COMMIT"]
    curated_vuln = [r for r in records if r["is_vulnerable"] and r["source_tier"] == "CURATED_SAME_COMMIT_DISTINCT_FUNCTION"]

    assert len(clean_records) == 1250, f"Expected 1,250 clean, got {len(clean_records)}"
    assert len(vuln_records) == 200, f"Expected 200 vuln, got {len(vuln_records)}"
    assert len(core_vuln) == 41, f"Expected 41 core vuln, got {len(core_vuln)}"
    assert len(curated_vuln) == 159, f"Expected 159 curated vuln, got {len(curated_vuln)}"

    X_raw = [r["original_code"] for r in records]
    y_true = [r["bug_category"] for r in records]

    # 3. Load Models
    print("\n[MODELS] Loading frozen models...")
    model_base = joblib.load(EXPECTED_HASHES["baseline_model"][0])
    model_k = joblib.load(EXPECTED_HASHES["candidate_k_model"][0])
    model_l2 = joblib.load(EXPECTED_HASHES["candidate_l2_model"][0])

    classes = list(model_base.classes_)
    assert list(model_k.classes_) == classes, "Class list mismatch for Candidate K"
    assert list(model_l2.classes_) == classes, "Class list mismatch for Candidate L2"

    mem_idx = classes.index("memory_safety")
    clean_idx = classes.index("none_correct_code")

    # 4. Run Frozen Inference
    print("\n[EVALUATION] Executing frozen inference across all 4 configurations...")

    # Config 1: Production Baseline
    t0 = time.time()
    preds_base = model_base.predict(X_raw)
    lat_base = time.time() - t0
    print(f"  [1/4] Baseline evaluated in {lat_base:.3f}s")

    # Config 2: Candidate K
    t0 = time.time()
    preds_k = model_k.predict(X_raw)
    lat_k = time.time() - t0
    print(f"  [2/4] Candidate K evaluated in {lat_k:.3f}s")

    # Config 3: Candidate L2
    t0 = time.time()
    X_deb = [debias_code_text(x) for x in X_raw]
    probs_l2 = model_l2.predict_proba(X_deb)
    preds_l2 = [classes[i] for i in np.argmax(probs_l2, axis=1)]
    lat_l2 = time.time() - t0
    print(f"  [3/4] Candidate L2 evaluated in {lat_l2:.3f}s")

    # Config 4: Phase N Policy (tau=0.30, delta=-0.12)
    t0 = time.time()
    tau = 0.30
    delta = -0.12
    preds_n = []
    for i in range(len(records)):
        p_mem = probs_l2[i][mem_idx]
        p_clean = probs_l2[i][clean_idx]
        if (p_mem >= tau) and ((p_mem - p_clean) >= delta):
            preds_n.append("memory_safety")
        else:
            preds_n.append(preds_l2[i])
    lat_n = (time.time() - t0) + lat_l2  # includes L2 probability generation
    print(f"  [4/4] Phase N Policy (tau=0.30, delta=-0.12) evaluated in {lat_n:.3f}s")

    # 5. Calculate Metrics
    print("\n[METRICS] Computing metrics, Wilson score CIs, and Bootstrap F1 intervals...")
    eval_results = {
        "production_baseline": compute_detailed_metrics(y_true, preds_base, classes, lat_base),
        "candidate_k": compute_detailed_metrics(y_true, preds_k, classes, lat_k),
        "candidate_l2": compute_detailed_metrics(y_true, preds_l2, classes, lat_l2),
        "phase_n_policy": compute_detailed_metrics(y_true, preds_n, classes, lat_n)
    }

    # 6. Subgroup Analysis
    print("\n[SUBGROUPS] Computing subgroup performance...")
    subgroup_definitions = {
        "core_unseen_vuln": [i for i, r in enumerate(records) if r["source_tier"] == "CORE_ACCEPTED_UNSEEN_COMMIT" and r["is_vulnerable"]],
        "curated_same_commit_vuln": [i for i, r in enumerate(records) if r["source_tier"] == "CURATED_SAME_COMMIT_DISTINCT_FUNCTION" and r["is_vulnerable"]],
        "clean_samples": [i for i, r in enumerate(records) if not r["is_vulnerable"]],
        "memory_safety_ground_truth": [i for i, r in enumerate(records) if r["bug_category"] == "memory_safety"]
    }

    # By repository
    repos = sorted(list(set(r["repository"] for r in records)))
    for repo in repos:
        subgroup_definitions[f"repo_{repo.replace('/', '_')}"] = [i for i, r in enumerate(records) if r["repository"] == repo]

    subgroup_metrics = {}
    for sg_name, indices in subgroup_definitions.items():
        yt_sg = [y_true[i] for i in indices]
        sg_entry = {"sample_count": len(indices), "configurations": {}}
        for cfg_name, preds_arr in [
            ("production_baseline", preds_base),
            ("candidate_k", preds_k),
            ("candidate_l2", preds_l2),
            ("phase_n_policy", preds_n)
        ]:
            yp_sg = [preds_arr[i] for i in indices]
            # Calculate specific subgroup metrics
            if "clean" in sg_name:
                fp_count = sum(1 for p in yp_sg if p != "none_correct_code")
                sg_entry["configurations"][cfg_name] = {
                    "false_positives": fp_count,
                    "false_positive_rate": round(fp_count / len(indices), 4) if indices else 0.0
                }
            elif "vuln" in sg_name:
                tp_count = sum(1 for p in yp_sg if p != "none_correct_code")
                fn_count = sum(1 for p in yp_sg if p == "none_correct_code")
                mem_tp = sum(1 for yt, yp in zip(yt_sg, yp_sg) if yt == "memory_safety" and yp == "memory_safety")
                sg_entry["configurations"][cfg_name] = {
                    "bug_detected_tp": tp_count,
                    "bug_missed_fn": fn_count,
                    "detection_recall": round(tp_count / len(indices), 4) if indices else 0.0,
                    "memory_safety_tp": mem_tp
                }
            elif "memory_safety" in sg_name:
                tp_count = sum(1 for p in yp_sg if p == "memory_safety")
                sg_entry["configurations"][cfg_name] = {
                    "memory_safety_tp": tp_count,
                    "memory_safety_recall": round(tp_count / len(indices), 4) if indices else 0.0
                }
            else: # Repo level
                clean_idx_repo = [j for j, idx in enumerate(indices) if y_true[idx] == "none_correct_code"]
                vuln_idx_repo = [j for j, idx in enumerate(indices) if y_true[idx] != "none_correct_code"]
                mem_idx_repo = [j for j, idx in enumerate(indices) if y_true[idx] == "memory_safety"]

                fp_count = sum(1 for j in clean_idx_repo if yp_sg[j] != "none_correct_code")
                fn_count = sum(1 for j in vuln_idx_repo if yp_sg[j] == "none_correct_code")
                mem_tp = sum(1 for j in mem_idx_repo if yp_sg[j] == "memory_safety")

                sg_entry["configurations"][cfg_name] = {
                    "clean_total": len(clean_idx_repo),
                    "clean_fp": fp_count,
                    "clean_fpr": round(fp_count / len(clean_idx_repo), 4) if clean_idx_repo else 0.0,
                    "vuln_total": len(vuln_idx_repo),
                    "vuln_fn": fn_count,
                    "bug_fnr": round(fn_count / len(vuln_idx_repo), 4) if vuln_idx_repo else 0.0,
                    "memory_safety_support": len(mem_idx_repo),
                    "memory_safety_tp": mem_tp,
                    "memory_safety_recall": round(mem_tp / len(mem_idx_repo), 4) if mem_idx_repo else 0.0
                }
        subgroup_metrics[sg_name] = sg_entry

    # 7. Post-Run Cryptographic Verification
    post_hashes = verify_all_hashes("POST-EVALUATION")

    # 8. Save JSON Outputs
    print("\n[OUTPUTS] Writing evaluation outputs...")

    # 1. phase_o2_metrics.json
    metrics_doc = {
        "evaluation_name": "PATCHPROOF Phase O.2 Independent C Benchmark Evaluation",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "dataset_sha256": EXPECTED_HASHES["benchmark_dataset"][1],
        "configurations": {
            k: {
                "overall": v["overall"],
                "security_detection": v["security_detection"],
                "memory_safety": v["memory_safety"]
            }
            for k, v in eval_results.items()
        }
    }
    with open(out_dir / "phase_o2_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_doc, f, indent=2)

    # 2. phase_o2_confusion_matrices.json
    cm_doc = {
        "classes": classes,
        "confusion_matrices": {k: v["confusion_matrix"]["matrix"] for k, v in eval_results.items()}
    }
    with open(out_dir / "phase_o2_confusion_matrices.json", "w", encoding="utf-8") as f:
        json.dump(cm_doc, f, indent=2)

    # 3. phase_o2_per_class_metrics.json
    per_class_doc = {k: v["per_class"] for k, v in eval_results.items()}
    with open(out_dir / "phase_o2_per_class_metrics.json", "w", encoding="utf-8") as f:
        json.dump(per_class_doc, f, indent=2)

    # 4. phase_o2_repository_metrics.json
    repo_metrics_doc = {
        sg: data for sg, data in subgroup_metrics.items() if sg.startswith("repo_")
    }
    with open(out_dir / "phase_o2_repository_metrics.json", "w", encoding="utf-8") as f:
        json.dump(repo_metrics_doc, f, indent=2)

    # 5. phase_o2_subgroup_metrics.json
    with open(out_dir / "phase_o2_subgroup_metrics.json", "w", encoding="utf-8") as f:
        json.dump(subgroup_metrics, f, indent=2)

    # 6. phase_o2_integrity_verification.json
    integrity_doc = {
        "evaluation_phase": "Phase O.2 Frozen Evaluation",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "preflight_hashes": preflight_hashes,
        "post_evaluation_hashes": post_hashes,
        "all_hashes_matched": True,
        "never_merge_active": True,
        "frozen_protocol_enforced": True
    }
    with open(out_dir / "phase_o2_integrity_verification.json", "w", encoding="utf-8") as f:
        json.dump(integrity_doc, f, indent=2)

    total_duration = time.time() - total_start
    print(f"\n[COMPLETE] Phase O.2 Frozen Evaluation completed in {total_duration:.2f} seconds.")
    print("=" * 80)

    # Return results for report generation
    return eval_results, subgroup_metrics, metrics_doc

if __name__ == "__main__":
    main()
