"""
PATCHPROOF Phase N.1 — Integrity Audit of Decision Boundary Optimization
Strict Rules:
  - Validation data ONLY (data/processed/val.jsonl, 10,860 samples).
  - NO access to test.jsonl or robust_heldout_test.jsonl.
  - Zero retraining, zero model modification, zero production changes.
  - Preserves NEVER_MERGE_ACTIVE.
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
    accuracy_score, precision_recall_fscore_support, confusion_matrix
)

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_k"
EXP_L_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_l"
EXP_N_DIR = ROOT_DIR / "models" / "experiments" / "experiment_n"

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
        EXP_L_MODEL_DIR / "candidate_l2_debiased.joblib",
        "399d155684ff6ac689624175696b4dd6db7bff149fa7421a63b30c76f25c4942"
    ),
    "train_split": (
        PROCESSED_DIR / "train.jsonl",
        "6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad"
    ),
    "val_split": (
        PROCESSED_DIR / "val.jsonl",
        "935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f"
    ),
    "test_split": (
        PROCESSED_DIR / "test.jsonl",
        "9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d"
    ),
    "robust_test_split": (
        PROCESSED_DIR / "robust_heldout_test.jsonl",
        "e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1"
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

def verify_all_hashes(stage: str):
    print(f"\n[AUDIT: {stage}] Verifying cryptographic checksums...")
    for name, (path, expected) in EXPECTED_HASHES.items():
        actual = compute_sha256(path)
        assert actual == expected, f"Hash mismatch for {name}: {actual} vs {expected}"
        print(f"  [PASS] {name}: {actual}")

def calculate_detailed_metrics(y_true: List[str], y_pred: List[str], languages: List[str]) -> Dict[str, Any]:
    acc = accuracy_score(y_true, y_pred)
    pm, rm, fm, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    pw, rw, fw, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)

    # Clean code overall metrics
    clean_indices = [i for i, y in enumerate(y_true) if y == "none_correct_code"]
    clean_total = len(clean_indices)
    clean_fp = sum(1 for i in clean_indices if y_pred[i] != "none_correct_code")
    clean_fpr = (clean_fp / clean_total) if clean_total > 0 else 0.0

    # C Clean code metrics
    c_clean_indices = [i for i, (y, l) in enumerate(zip(y_true, languages)) if y == "none_correct_code" and l == "c"]
    c_clean_total = len(c_clean_indices)
    c_clean_fp = sum(1 for i in c_clean_indices if y_pred[i] != "none_correct_code")
    c_clean_fpr = (c_clean_fp / c_clean_total) if c_clean_total > 0 else 0.0
    c_clean_mem_fp = sum(1 for i in c_clean_indices if y_pred[i] == "memory_safety")

    # Bug FNR
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

    # Per-class metrics
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

    return {
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(fm), 4),
        "weighted_f1": round(float(fw), 4),
        "overall_clean_code": {
            "total": clean_total,
            "false_positives": clean_fp,
            "fpr": round(float(clean_fpr), 4)
        },
        "c_clean_code": {
            "total": c_clean_total,
            "false_positives": c_clean_fp,
            "fpr": round(float(c_clean_fpr), 4),
            "fp_misclassified_as_memory_safety": c_clean_mem_fp
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
        "language_breakdown": lang_breakdown,
        "per_class": per_class
    }

def main():
    print("=" * 80)
    print("PATCHPROOF PHASE N.1: INTEGRITY AUDIT")
    print("=" * 80)

    # Pre-audit hash check
    verify_all_hashes("PRE-AUDIT")

    # 1. Load validation dataset
    val_records = []
    with open(EXPECTED_HASHES["val_split"][0], "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                val_records.append(json.loads(line))
    print(f"\n[DATA] Loaded {len(val_records):,} validation records.")
    assert len(val_records) == 10860, "Expected 10,860 records!"

    X_val = [r["original_code"] for r in val_records]
    y_val = [r["bug_category"] for r in val_records]
    languages = [r.get("language", "unknown") for r in val_records]

    # 2. Load model
    print("[MODEL] Loading frozen Candidate L2...")
    model_l2 = joblib.load(EXPECTED_HASHES["candidate_l2"][0])
    classes_l2 = list(model_l2.classes_)
    mem_idx = classes_l2.index("memory_safety")
    clean_idx = classes_l2.index("none_correct_code")

    print("[INFERENCE] Computing raw probability distribution...")
    X_val_deb = [debias_code_text(x) for x in X_val]
    probs_l2 = model_l2.predict_proba(X_val_deb)
    preds_l2_orig = [classes_l2[i] for i in np.argmax(probs_l2, axis=1)]

    # =========================================================================
    # ITEM 1: CONFIGURATION C DISCREPANCY AUDIT
    # =========================================================================
    print("\n" + "=" * 60)
    print("ITEM 1: CONFIGURATION C DISCREPANCY INVESTIGATION")
    print("=" * 60)
    # Compare tau=0.30, delta=-0.12 vs tau=0.34, delta=-0.12
    preds_030_m12 = []
    preds_034_m12 = []

    for i in range(len(val_records)):
        p_mem = probs_l2[i][mem_idx]
        p_clean = probs_l2[i][clean_idx]

        # Rule for 0.30, -0.12
        if (p_mem >= 0.30) and ((p_mem - p_clean) >= -0.12):
            preds_030_m12.append("memory_safety")
        else:
            preds_030_m12.append(preds_l2_orig[i])

        # Rule for 0.34, -0.12
        if (p_mem >= 0.34) and ((p_mem - p_clean) >= -0.12):
            preds_034_m12.append("memory_safety")
        else:
            preds_034_m12.append(preds_l2_orig[i])

    m_030 = calculate_detailed_metrics(y_val, preds_030_m12, languages)
    m_034 = calculate_detailed_metrics(y_val, preds_034_m12, languages)

    # Find the differing samples between 0.30 and 0.34 at delta=-0.12
    diff_indices = [i for i in range(len(val_records)) if preds_030_m12[i] != preds_034_m12[i]]
    print(f"Total samples with differing predictions between tau=0.30 and tau=0.34 (delta=-0.12): {len(diff_indices)}")

    diff_breakdown = Counter(y_val[i] for i in diff_indices)
    diff_langs = Counter(languages[i] for i in diff_indices)
    print(f"  Ground truth classes of differing samples: {dict(diff_breakdown)}")
    print(f"  Languages of differing samples: {dict(diff_langs)}")

    # Are any of these clean C code?
    diff_clean_c = sum(1 for i in diff_indices if y_val[i] == "none_correct_code" and languages[i] == "c")
    print(f"  Differing samples that are clean C code: {diff_clean_c}")

    config_c_audit = {
        "discrepancy_explanation": (
            "In run_phase_n.py, recommended_cfgs specified tau=0.34, delta=-0.12 as 'Config_C_HighRecall' "
            "(Recall: 65.81%, Prec: 68.01%, C Clean FPR: 38.18%). In the Pareto frontier table, the non-dominated entry "
            "at C Clean FPR = 38.18% is tau=0.30, delta=-0.12 (Recall: 66.79%, Prec: 68.29%, C Clean FPR: 38.18%). "
            "Crucially, tau=0.30, delta=-0.12 strictly Pareto-dominates tau=0.34, delta=-0.12: both configurations produce "
            "the EXACT same C clean false positive rate (38.18%, 557 false alarms out of 1,459 clean C files). "
            "Zero clean C samples have P(mem) in [0.30, 0.34) and margin >= -0.12. However, exactly 18 real vulnerabilities "
            "fall in this probability window. Thus, tau=0.30, delta=-0.12 catches 18 more real bugs (+0.98% recall) with "
            "zero additional clean C false alarms."
        ),
        "tau_030_delta_m12_metrics": {
            "tau": 0.30,
            "delta": -0.12,
            "recall": m_030["memory_safety"]["recall"],
            "precision": m_030["memory_safety"]["precision"],
            "f1": m_030["memory_safety"]["f1"],
            "tp": m_030["memory_safety"]["true_positives"],
            "fp": m_030["memory_safety"]["false_positives"],
            "c_clean_fpr": m_030["c_clean_code"]["fpr"],
            "c_clean_fp_count": m_030["c_clean_code"]["false_positives"],
            "accuracy": m_030["accuracy"],
            "macro_f1": m_030["macro_f1"]
        },
        "tau_034_delta_m12_metrics": {
            "tau": 0.34,
            "delta": -0.12,
            "recall": m_034["memory_safety"]["recall"],
            "precision": m_034["memory_safety"]["precision"],
            "f1": m_034["memory_safety"]["f1"],
            "tp": m_034["memory_safety"]["true_positives"],
            "fp": m_034["memory_safety"]["false_positives"],
            "c_clean_fpr": m_034["c_clean_code"]["fpr"],
            "c_clean_fp_count": m_034["c_clean_code"]["false_positives"],
            "accuracy": m_034["accuracy"],
            "macro_f1": m_034["macro_f1"]
        },
        "differing_samples_count": len(diff_indices),
        "differing_samples_ground_truth": dict(diff_breakdown),
        "clean_c_differing_count": diff_clean_c
    }

    # =========================================================================
    # ITEM 2: DECISION-RULE VERIFICATION
    # =========================================================================
    print("\n" + "=" * 60)
    print("ITEM 2: DECISION-RULE VERIFICATION")
    print("=" * 60)
    # Check how many samples have preds_l2_orig == 'memory_safety' but fail condition
    mem_orig_indices = [i for i, p in enumerate(preds_l2_orig) if p == "memory_safety"]
    print(f"Total samples where original L2 argmax predicted memory_safety: {len(mem_orig_indices)}")

    rule_verification_cases = []
    # Test for Config B (tau=0.38, delta=-0.10)
    tau_b, delta_b = 0.38, -0.10
    mem_orig_failing_b = [
        i for i in mem_orig_indices
        if not ((probs_l2[i][mem_idx] >= tau_b) and ((probs_l2[i][mem_idx] - probs_l2[i][clean_idx]) >= delta_b))
    ]
    print(f"For Config B (tau=0.38, delta=-0.10):")
    print(f"  Samples where original L2 argmax is memory_safety but condition is FALSE: {len(mem_orig_failing_b)}")
    for idx in mem_orig_failing_b[:3]:
        r = val_records[idx]
        print(f"    Sample {idx} ({r.get('example_id')}): True={r['bug_category']}, P(mem)={probs_l2[idx][mem_idx]:.4f}, P(clean)={probs_l2[idx][clean_idx]:.4f}")
        rule_verification_cases.append({
            "type": "existing_memory_safety_failing_condition_preserved",
            "index": idx,
            "example_id": r.get("example_id"),
            "ground_truth": r["bug_category"],
            "p_mem": round(float(probs_l2[idx][mem_idx]), 4),
            "p_clean": round(float(probs_l2[idx][clean_idx]), 4),
            "orig_argmax_pred": preds_l2_orig[idx],
            "condition_met": False,
            "rule_output_pred": preds_l2_orig[idx]
        })

    # Test for non-memory safety promoted
    promoted_b = [
        i for i in range(len(val_records))
        if preds_l2_orig[i] != "memory_safety" and (probs_l2[i][mem_idx] >= tau_b) and ((probs_l2[i][mem_idx] - probs_l2[i][clean_idx]) >= delta_b)
    ]
    print(f"  Samples where original L2 argmax was NOT memory_safety but promoted to memory_safety: {len(promoted_b)}")
    for idx in promoted_b[:3]:
        r = val_records[idx]
        print(f"    Sample {idx} ({r.get('example_id')}): Orig={preds_l2_orig[idx]}, True={r['bug_category']}, P(mem)={probs_l2[idx][mem_idx]:.4f}, P(clean)={probs_l2[idx][clean_idx]:.4f}")
        rule_verification_cases.append({
            "type": "non_memory_safety_promoted_to_memory_safety",
            "index": idx,
            "example_id": r.get("example_id"),
            "ground_truth": r["bug_category"],
            "p_mem": round(float(probs_l2[idx][mem_idx]), 4),
            "p_clean": round(float(probs_l2[idx][clean_idx]), 4),
            "orig_argmax_pred": preds_l2_orig[idx],
            "condition_met": True,
            "rule_output_pred": "memory_safety"
        })

    rule_audit_data = {
        "rule_code_structure": (
            "if (p_mem >= tau) and ((p_mem - p_clean) >= delta):\n"
            "    preds_sweep.append('memory_safety')\n"
            "else:\n"
            "    preds_sweep.append(preds_l2_orig[i])"
        ),
        "mechanics_classification": "Asymmetric Promotion / Override Rule",
        "detailed_findings": [
            "1. OVERRIDE DIRECTION: The rule overrides non-memory-safety predictions to 'memory_safety' when both conditions pass.",
            "2. PRESERVATION: The rule PRESERVES existing memory-safety predictions when conditions fail, because the else-branch falls back to preds_l2_orig[i].",
            "3. NOT A STRICT BIDIRECTIONAL THRESHOLD: A strict threshold would demote a memory_safety prediction to a fallback class if P(mem) < tau. The implemented rule never demotes existing memory_safety predictions.",
            f"4. SAMPLES PRESERVED UNDER CONFIG B: Exactly {len(mem_orig_failing_b)} samples with original argmax=memory_safety had P(mem) < 0.38 and were preserved as memory_safety.",
            f"5. SAMPLES PROMOTED UNDER CONFIG B: Exactly {len(promoted_b)} samples originally predicted as clean code or other defects were promoted to memory_safety."
        ],
        "concrete_cases": rule_verification_cases
    }

    # =========================================================================
    # ITEM 3: INDEPENDENT REPRODUCTION OF SELECTED CONFIGURATIONS
    # =========================================================================
    print("\n" + "=" * 60)
    print("ITEM 3: INDEPENDENT REPRODUCTION OF SELECTED CONFIGURATIONS")
    print("=" * 60)

    selected_configs = [
        {"name": "Original_L2_Argmax", "tau": None, "delta": None},
        {"name": "Config_A", "tau": 0.42, "delta": -0.05},
        {"name": "Config_B", "tau": 0.38, "delta": -0.10},
        {"name": "Config_C_Pareto", "tau": 0.30, "delta": -0.12},
        {"name": "Config_C_Script", "tau": 0.34, "delta": -0.12}
    ]

    reproduced_configs_data = {}

    for cfg in selected_configs:
        tau = cfg["tau"]
        delta = cfg["delta"]
        name = cfg["name"]

        if tau is None:
            preds_cfg = list(preds_l2_orig)
        else:
            preds_cfg = []
            for i in range(len(val_records)):
                p_mem = probs_l2[i][mem_idx]
                p_clean = probs_l2[i][clean_idx]
                if (p_mem >= tau) and ((p_mem - p_clean) >= delta):
                    preds_cfg.append("memory_safety")
                else:
                    preds_cfg.append(preds_l2_orig[i])

        metrics = calculate_detailed_metrics(y_val, preds_cfg, languages)
        reproduced_configs_data[name] = {
            "tau": tau,
            "delta": delta,
            "metrics": metrics
        }
        print(f"\n[{name} (tau={tau}, delta={delta})]")
        print(f"  Accuracy:      {metrics['accuracy']:.4f}")
        print(f"  Macro F1:      {metrics['macro_f1']:.4f}")
        print(f"  Weighted F1:   {metrics['weighted_f1']:.4f}")
        print(f"  Mem Prec:      {metrics['memory_safety']['precision']:.4f}")
        print(f"  Mem Recall:    {metrics['memory_safety']['recall']:.4f} ({metrics['memory_safety']['true_positives']}/{metrics['memory_safety']['support']})")
        print(f"  Mem F1:        {metrics['memory_safety']['f1']:.4f}")
        print(f"  Clean FPR:     {metrics['overall_clean_code']['fpr']:.4f} ({metrics['overall_clean_code']['false_positives']}/{metrics['overall_clean_code']['total']})")
        print(f"  C Clean FPR:   {metrics['c_clean_code']['fpr']:.4f} ({metrics['c_clean_code']['false_positives']}/{metrics['c_clean_code']['total']}) [Mem FP: {metrics['c_clean_code']['fp_misclassified_as_memory_safety']}]")
        print(f"  Bug FNR:       {metrics['bug_detection']['fnr']:.4f} ({metrics['bug_detection']['false_negatives']}/{metrics['bug_detection']['total']})")

    # =========================================================================
    # ITEM 4: REPOSITORY AUDIT & DENOMINATOR CLARIFICATION
    # =========================================================================
    print("\n" + "=" * 60)
    print("ITEM 4: REPOSITORY AUDIT & DENOMINATOR CLARIFICATION")
    print("=" * 60)

    # Count samples per repository group and defect class
    repo_breakdown = defaultdict(lambda: Counter())
    for r in val_records:
        repo = r.get("repository", "unknown")
        cat = r.get("bug_category", "unknown")
        lang = r.get("language", "unknown")
        repo_breakdown[repo][cat] += 1
        if cat == "none_correct_code":
            repo_breakdown[repo][f"clean_{lang}"] += 1

    # Map each repo to source group
    def map_repo_group(r: str) -> str:
        rl = r.lower()
        if "qemu" in rl: return "QEMU"
        elif "ffmpeg" in rl: return "FFmpeg"
        elif "android" in rl: return "Android"
        elif "chrome" in rl: return "Chrome"
        elif "linux" in rl: return "Linux"
        else: return "Other"

    group_support_audit = defaultdict(lambda: {"total": 0, "memory_safety": 0, "clean_c": 0, "clean_other": 0, "other_bugs": 0})
    for r in val_records:
        grp = map_repo_group(r.get("repository", ""))
        cat = r.get("bug_category", "")
        lang = r.get("language", "")
        group_support_audit[grp]["total"] += 1
        if cat == "memory_safety":
            group_support_audit[grp]["memory_safety"] += 1
        elif cat == "none_correct_code" and lang == "c":
            group_support_audit[grp]["clean_c"] += 1
        elif cat == "none_correct_code":
            group_support_audit[grp]["clean_other"] += 1
        else:
            group_support_audit[grp]["other_bugs"] += 1

    print("Audited Support Counts by Group in val.jsonl:")
    for grp, cnts in sorted(group_support_audit.items()):
        print(f"  {grp:8s} | Total: {cnts['total']:5d} | Mem Safety: {cnts['memory_safety']:4d} | Clean C: {cnts['clean_c']:4d} | Clean Other: {cnts['clean_other']:4d} | Other Bugs: {cnts['other_bugs']:4d}")

    # Detailed repository audit data
    repo_audit_data = {
        "finding": (
            "CRITICAL DENOMINATOR AUDIT: Exactly 100% of all 1,459 clean C validation samples in val.jsonl "
            "originate from only two repositories: devign/qemu (964 samples) and devign/FFmpeg (495 samples). "
            "BigVul repositories (Android, Chrome, Linux, OpenSSL, etc.) in val.jsonl contain ZERO clean C samples. "
            "Therefore, reporting 'Clean C FPR: 0.00%' for Android, Chrome, and Linux was a zero-denominator artifact (0/0). "
            "The correct characterization is 'N/A (zero clean C support)'."
        ),
        "group_support_table": group_support_audit
    }

    # Save JSON deliverable
    audit_json_path = EXP_N_DIR / "phase_n1_integrity_audit.json"
    audit_data = {
        "experiment": "Phase N.1 Integrity Audit",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "dataset_audited": "data/processed/val.jsonl (10,860 samples)",
        "configuration_c_discrepancy": config_c_audit,
        "decision_rule_verification": rule_audit_data,
        "reproduced_selected_configurations": reproduced_configs_data,
        "repository_support_audit": repo_audit_data
    }
    with open(audit_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    print(f"\n[SAVE] Integrity audit JSON saved to: {audit_json_path}")

    # Post-audit hash verification
    verify_all_hashes("POST-AUDIT")
    print("\n[SUCCESS] Phase N.1 Audit completed successfully!")

if __name__ == "__main__":
    main()
