"""
Experiment F: AST Scope-Aware Identifier Normalization & Training Harness.
Evaluates:
- Baseline Reference (Production)
- Experiment D (Class-Weight Tuning Reference)
- Candidate F1 (AST-Normalized Representation Only, balanced weights)
- Candidate F2 (AST-Normalized Representation + Exp D Class Weighting)
Across:
- 50-snippet novel benchmark
- Original untouched 8,353-record test set
- 1,226-record robust held-out test set
"""

import sys
import json
import logging
import hashlib
from pathlib import Path
from collections import Counter
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, str(Path.cwd()))
from scripts.datasets.schema import CodeDebuggingExample
from scripts.benchmark_novel_eval import BENCHMARK_SUITE
from scripts.experiments.experiment_f.ast_normalizer import normalize_snippet

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ExperimentF")

EXP_F_DIR = Path("C:/PATCHPROOF/models/experiments/experiment_f")
EXP_F_DIR.mkdir(parents=True, exist_ok=True)

PROCESSED_DIR = Path("C:/PATCHPROOF/data/processed")

def prepare_ast_dataset(split_name: str):
    """Loads and normalizes code snippets with fallback tracking."""
    in_file = PROCESSED_DIR / f"{split_name}.jsonl"
    logger.info(f"Loading and normalizing {split_name}.jsonl...")
    
    X_orig, X_norm, y = [], [], []
    stats = {"total": 0, "normalized": 0, "fallback": 0, "by_lang": Counter()}
    
    with open(in_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            ex = CodeDebuggingExample.from_jsonl(line)
            norm_code, ok = normalize_snippet(ex.original_code, ex.language)
            
            stats["total"] += 1
            if ok and norm_code != ex.original_code:
                stats["normalized"] += 1
                stats["by_lang"][ex.language] += 1
            else:
                stats["fallback"] += 1
                
            X_orig.append(ex.original_code)
            X_norm.append(norm_code)
            y.append(ex.bug_category)
            
    logger.info(f"{split_name} normalized: {stats['normalized']}/{stats['total']} ({stats['normalized']/stats['total']*100:.1f}%), fallbacks={stats['fallback']}")
    return X_orig, X_norm, y, stats

def evaluate_model(model, X_eval, y_eval, dataset_name):
    preds = model.predict(X_eval)
    acc = accuracy_score(y_eval, preds)
    p_w, r_w, f1_w, _ = precision_recall_fscore_support(y_eval, preds, average="weighted", zero_division=0)
    p_m, r_m, f1_m, _ = precision_recall_fscore_support(y_eval, preds, average="macro", zero_division=0)
    
    labels = sorted(list(set(y_eval)))
    cm = confusion_matrix(y_eval, preds, labels=labels).tolist()
    
    p_c, r_c, f1_c, supp_c = precision_recall_fscore_support(y_eval, preds, labels=labels, zero_division=0)
    per_class = {}
    for idx, lbl in enumerate(labels):
        per_class[lbl] = {
            "precision": round(float(p_c[idx]), 4),
            "recall": round(float(r_c[idx]), 4),
            "f1": round(float(f1_c[idx]), 4),
            "support": int(supp_c[idx])
        }
        
    clean_indices = [i for i, a in enumerate(y_eval) if a == "none_correct_code"]
    clean_fpr = 0.0
    if clean_indices:
        clean_false_alarms = sum(1 for i in clean_indices if preds[i] != "none_correct_code")
        clean_fpr = round(clean_false_alarms / len(clean_indices), 4)
        
    bug_indices = [i for i, a in enumerate(y_eval) if a != "none_correct_code"]
    bug_fnr = 0.0
    bug_recall = 0.0
    if bug_indices:
        bug_false_negatives = sum(1 for i in bug_indices if preds[i] == "none_correct_code")
        bug_fnr = round(bug_false_negatives / len(bug_indices), 4)
        bug_recall = round(1.0 - bug_fnr, 4)
        
    return {
        "dataset": dataset_name,
        "sample_count": len(y_eval),
        "accuracy": round(float(acc), 4),
        "weighted_f1": round(float(f1_w), 4),
        "macro_f1": round(float(f1_m), 4),
        "clean_code_fpr": clean_fpr,
        "bug_false_negative_rate": bug_fnr,
        "bug_detection_recall": bug_recall,
        "per_class": per_class,
        "labels": labels,
        "confusion_matrix": cm,
        "predictions": [str(p) for p in preds]
    }

def main():
    logger.info("Starting Experiment F Training & Evaluation...")
    
    # Verify baseline SHA256
    base_h = hashlib.sha256(open("models/bug_detector.joblib", "rb").read()).hexdigest()
    assert base_h.startswith("5f93bba9ce457fe9"), "Baseline model was modified!"
    
    # Verify test.jsonl SHA256
    test_h = hashlib.sha256(open("data/processed/test.jsonl", "rb").read()).hexdigest()
    assert test_h.startswith("9aad8de8b09b0e2f"), "test.jsonl was modified!"
    
    # 1. Prepare Datasets
    X_train_raw, X_train_norm, y_train, train_stats = prepare_ast_dataset("train")
    X_orig_raw, X_orig_norm, y_orig, test_stats = prepare_ast_dataset("test")
    X_rob_raw, X_rob_norm, y_rob, rob_stats = prepare_ast_dataset("robust_heldout_test")
    
    # Benchmark 50
    X_bench_raw = [c["code"] for c in BENCHMARK_SUITE]
    X_bench_norm = [normalize_snippet(c["code"], c["lang"])[0] for c in BENCHMARK_SUITE]
    y_bench = [c["expected_cat"] for c in BENCHMARK_SUITE]
    
    # 2. Train Candidate F1 (AST-normalized representation only, balanced weights)
    logger.info("Training Candidate F1 (AST-Normalized Only, balanced weights)...")
    pipe_f1 = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight="balanced", C=1.0, max_iter=500, random_state=42))
    ])
    pipe_f1.fit(X_train_norm, y_train)
    cand_f1_path = EXP_F_DIR / "candidate_f1_ast_only.joblib"
    joblib.dump(pipe_f1, cand_f1_path)
    logger.info(f"Saved Candidate F1 to {cand_f1_path}")
    
    # 3. Train Candidate F2 (AST-normalized representation + Experiment D class weights)
    logger.info("Training Candidate F2 (AST-Normalized + Exp D Class Weights)...")
    class_counts = Counter(y_train)
    total_samples = len(y_train)
    custom_weights = {}
    for cls_name, count in class_counts.items():
        base_w = total_samples / (len(class_counts) * count)
        if cls_name == "none_correct_code":
            custom_weights[cls_name] = base_w * 0.45
        elif cls_name in ("async_error", "resource_leak", "api_misuse"):
            custom_weights[cls_name] = base_w * 1.35
        else:
            custom_weights[cls_name] = base_w

    pipe_f2 = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight=custom_weights, C=1.0, max_iter=500, random_state=42))
    ])
    pipe_f2.fit(X_train_norm, y_train)
    cand_f2_path = EXP_F_DIR / "candidate_f2_ast_weighted.joblib"
    joblib.dump(pipe_f2, cand_f2_path)
    logger.info(f"Saved Candidate F2 to {cand_f2_path}")
    
    # 4. Load Reference Models
    base_model = joblib.load("models/bug_detector.joblib")
    exp_d_model = joblib.load("models/experiments/exp_d_class_weight_tuning.joblib")
    
    models_to_eval = [
        ("Baseline (Production)", base_model, False),
        ("Experiment D (Reference)", exp_d_model, False),
        ("Candidate F1 (AST Only)", pipe_f1, True),
        ("Candidate F2 (AST + Exp D Weights)", pipe_f2, True)
    ]
    
    all_results = {
        "dataset_statistics": {
            "train": train_stats,
            "test_untouched": test_stats,
            "robust_heldout": rob_stats
        },
        "evaluations": {}
    }
    
    py_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["lang"] == "python" and not c["id"].startswith("CLEAN")]
    js_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("JS-ASYNC")]
    c_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("C-") and not c["id"].startswith("CLEAN")]
    
    for name, model, is_ast in models_to_eval:
        logger.info(f"Evaluating {name}...")
        X_b = X_bench_norm if is_ast else X_bench_raw
        X_o = X_orig_norm if is_ast else X_orig_raw
        X_r = X_rob_norm if is_ast else X_rob_raw
        
        bench_eval = evaluate_model(model, X_b, y_bench, "benchmark_50")
        bench_preds = bench_eval["predictions"]
        
        bench_eval["sub_categories"] = {
            "python_novel_identifiers (13)": round(sum(1 for i in py_indices if bench_preds[i] == y_bench[i]) / len(py_indices), 4),
            "js_async_coverage (10)": round(sum(1 for i in js_indices if bench_preds[i] == y_bench[i]) / len(js_indices), 4),
            "c_defect_patterns (10)": round(sum(1 for i in c_indices if bench_preds[i] == y_bench[i]) / len(c_indices), 4)
        }
        
        orig_eval = evaluate_model(model, X_o, y_orig, "untouched_test_8353")
        rob_eval = evaluate_model(model, X_r, y_rob, "robust_heldout_1226")
        
        all_results["evaluations"][name] = {
            "benchmark_50": bench_eval,
            "untouched_test_8353": orig_eval,
            "robust_heldout_1226": rob_eval
        }
        
        logger.info(f"{name} -> BenchAcc: {bench_eval['accuracy']*100:.1f}%, MacroF1: {bench_eval['macro_f1']:.4f}, CleanFPR: {bench_eval['clean_code_fpr']*100:.1f}%, BugRecall: {bench_eval['bug_detection_recall']*100:.1f}%, PyNovel: {bench_eval['sub_categories']['python_novel_identifiers (13)']*100:.1f}%")

    out_file = EXP_F_DIR / "experiment_f_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Saved complete results to {out_file}")

if __name__ == "__main__":
    main()

