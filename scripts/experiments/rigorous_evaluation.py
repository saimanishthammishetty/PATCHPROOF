import sys
import json
import logging
import hashlib
from pathlib import Path
from collections import Counter
import joblib
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report

sys.path.insert(0, str(Path.cwd()))
from scripts.datasets.schema import CodeDebuggingExample
from scripts.benchmark_novel_eval import BENCHMARK_SUITE
from scripts.experiments.run_generalization_experiments import normalize_identifiers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RigorousEvaluation")

EXPERIMENTS_DIR = Path("C:/PATCHPROOF/models/experiments")
PROCESSED_DIR = Path("C:/PATCHPROOF/data/processed")

# Models to evaluate
MODEL_ENTRIES = [
    ("Baseline (Production)", Path("models/bug_detector.joblib"), False),
    ("Exp A (Identifier Normalization)", EXPERIMENTS_DIR / "exp_a_identifier_normalization.joblib", True),
    ("Exp B (Feature Weighting min/max_df)", EXPERIMENTS_DIR / "exp_b_feature_weighting.joblib", False),
    ("Exp C (Controlled Hard-Negative Capping)", EXPERIMENTS_DIR / "exp_c_controlled_hard_negative.joblib", False),
    ("Exp D (Class-Weight Tuning)", EXPERIMENTS_DIR / "exp_d_class_weight_tuning.joblib", False),
    ("Exp E1 (Word-Only 5k)", EXPERIMENTS_DIR / "exp_e1_word_only.joblib", False),
    ("Exp E2 (Char-Only 5k)", EXPERIMENTS_DIR / "exp_e2_char_only.joblib", False),
    ("Exp E3 (Balanced Union 4k W + 1k C)", EXPERIMENTS_DIR / "exp_e3_balanced_union.joblib", False),
]

def load_data(path, is_anon=False):
    X, y = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            ex = CodeDebuggingExample.from_jsonl(line)
            code = ex.original_code
            if is_anon:
                code = normalize_identifiers(code)
            X.append(code)
            y.append(ex.bug_category)
    return X, y

def evaluate_dataset(model, X, y, dataset_name):
    preds = model.predict(X)
    acc = accuracy_score(y, preds)
    p_w, r_w, f1_w, _ = precision_recall_fscore_support(y, preds, average="weighted", zero_division=0)
    p_m, r_m, f1_m, _ = precision_recall_fscore_support(y, preds, average="macro", zero_division=0)
    
    labels = sorted(list(set(y)))
    cm = confusion_matrix(y, preds, labels=labels).tolist()
    
    p_c, r_c, f1_c, supp_c = precision_recall_fscore_support(y, preds, labels=labels, zero_division=0)
    per_class = {}
    for idx, lbl in enumerate(labels):
        per_class[lbl] = {
            "precision": round(float(p_c[idx]), 4),
            "recall": round(float(r_c[idx]), 4),
            "f1": round(float(f1_c[idx]), 4),
            "support": int(supp_c[idx])
        }
        
    # Clean FPR
    clean_indices = [i for i, actual in enumerate(y) if actual == "none_correct_code"]
    clean_fpr = 0.0
    if clean_indices:
        clean_false_alarms = sum(1 for i in clean_indices if preds[i] != "none_correct_code")
        clean_fpr = round(clean_false_alarms / len(clean_indices), 4)
        
    # Bug FNR (missed bugs classified as none_correct_code)
    bug_indices = [i for i, actual in enumerate(y) if actual != "none_correct_code"]
    bug_fnr = 0.0
    bug_recall = 0.0
    if bug_indices:
        bug_false_negatives = sum(1 for i in bug_indices if preds[i] == "none_correct_code")
        bug_fnr = round(bug_false_negatives / len(bug_indices), 4)
        bug_recall = round(1.0 - bug_fnr, 4)
        
    return {
        "dataset": dataset_name,
        "sample_count": len(y),
        "accuracy": round(float(acc), 4),
        "weighted_f1": round(float(f1_w), 4),
        "macro_f1": round(float(f1_m), 4),
        "clean_code_fpr": clean_fpr,
        "bug_false_negative_rate": bug_fnr,
        "bug_detection_recall": bug_recall,
        "per_class": per_class,
        "labels": labels,
        "confusion_matrix": cm
    }

def main():
    logger.info("Starting rigorous comparative evaluation...")
    
    # 1. Prepare Datasets
    # 50-snippet Benchmark
    X_bench_raw = [c["code"] for c in BENCHMARK_SUITE]
    X_bench_anon = [normalize_identifiers(c["code"]) for c in BENCHMARK_SUITE]
    y_bench = [c["expected_cat"] for c in BENCHMARK_SUITE]
    
    # Original Test (8,353)
    orig_test_path = PROCESSED_DIR / "test.jsonl"
    X_orig_raw, y_orig = load_data(orig_test_path, is_anon=False)
    X_orig_anon, _ = load_data(orig_test_path, is_anon=True)
    
    # Robust Test (1,226)
    rob_test_path = PROCESSED_DIR / "robust_heldout_test.jsonl"
    X_rob_raw, y_rob = load_data(rob_test_path, is_anon=False)
    X_rob_anon, _ = load_data(rob_test_path, is_anon=True)
    
    all_evaluations = {}
    
    for name, path, is_anon in MODEL_ENTRIES:
        logger.info(f"Evaluating {name} ({path})...")
        model = joblib.load(path)
        
        # Select data representation
        X_bench = X_bench_anon if is_anon else X_bench_raw
        X_orig = X_orig_anon if is_anon else X_orig_raw
        X_rob = X_rob_anon if is_anon else X_rob_raw
        
        eval_bench = evaluate_dataset(model, X_bench, y_bench, "50-snippet_benchmark")
        
        # Sub-category accuracies on benchmark
        py_idx = [i for i, c in enumerate(BENCHMARK_SUITE) if c["lang"] == "python" and not c["id"].startswith("CLEAN")]
        js_idx = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("JS-ASYNC")]
        c_idx = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("C-") and not c["id"].startswith("CLEAN")]
        
        bench_preds = model.predict(X_bench)
        eval_bench["sub_categories"] = {
            "python_novel_identifiers (13)": round(sum(1 for i in py_idx if bench_preds[i] == y_bench[i]) / len(py_idx), 4),
            "js_async_coverage (10)": round(sum(1 for i in js_idx if bench_preds[i] == y_bench[i]) / len(js_idx), 4),
            "c_defect_patterns (10)": round(sum(1 for i in c_idx if bench_preds[i] == y_bench[i]) / len(c_idx), 4)
        }
        
        eval_orig = evaluate_dataset(model, X_orig, y_orig, "untouched_test_8353")
        eval_rob = evaluate_dataset(model, X_rob, y_rob, "robust_heldout_1226")
        
        all_evaluations[name] = {
            "model_path": str(path),
            "is_anonymized": is_anon,
            "benchmark_50": eval_bench,
            "untouched_test_8353": eval_orig,
            "robust_heldout_1226": eval_rob
        }
        
    # Save results
    out_file = EXPERIMENTS_DIR / "rigorous_evaluation_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_evaluations, f, indent=2)
    logger.info(f"Saved complete evaluation report to {out_file}")
    
    # 2. Syntax Damage Investigation for Identifier Normalization
    logger.info("Investigating identifier normalization on syntax...")
    sample_py = "def calculate_tax(order_total, user_role='guest'):\n    if order_total is None:\n        return 0.0\n    return order_total * 0.15"
    sample_js = "async function fetchUser(userId) {\n    const res = fetch('/api/user/' + userId);\n    return res.json();\n}"
    sample_c = "char* get_buffer() {\n    char local_buf[64];\n    return local_buf;\n}"
    
    print("\n--- SYNTAX NORMALIZATION CHECK ---")
    print("[Python Original]\n", sample_py)
    print("[Python Normalized]\n", normalize_identifiers(sample_py))
    print("[JS Original]\n", sample_js)
    print("[JS Normalized]\n", normalize_identifiers(sample_js))
    print("[C Original]\n", sample_c)
    print("[C Normalized]\n", normalize_identifiers(sample_c))

if __name__ == "__main__":
    main()

