"""
Experiment G: Recall-Focused Candidate Training & Rigorous Multi-Dataset Evaluation Harness.
Strict Rules:
- Baseline (models/bug_detector.joblib) must NOT be modified or overwritten.
- Candidate F2 (models/experiments/experiment_f/candidate_f2_ast_weighted.joblib) remains intact.
- All Candidate G artifacts are isolated under models/experiments/experiment_g/.
- Evaluates:
  1. Baseline (Production Reference)
  2. Candidate F2 (Staged Reference)
  3. Candidate G1 (AST + Balanced Recall Minority Rebalancing)
  4. Candidate G2 (AST + Aggressive Recall Prioritization)
  5. Candidate G3 (AST + Clean Token Pattern + Calibrated Regularization)
Across:
  - 50-snippet novel benchmark (BENCHMARK_SUITE)
  - 8,353-record untouched test set (test.jsonl)
  - 1,226-record robust held-out test set (robust_heldout_test.jsonl)
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
logger = logging.getLogger("ExperimentG")

EXP_G_DIR = Path("C:/PATCHPROOF/models/experiments/experiment_g")
EXP_G_DIR.mkdir(parents=True, exist_ok=True)

PROCESSED_DIR = Path("C:/PATCHPROOF/data/processed")

def get_ast_cached_dataset(split_name: str):
    """Loads dataset and uses joblib cache in EXP_G_DIR if available to save repeated AST parsing time."""
    cache_file = EXP_G_DIR / f"cache_{split_name}_ast.joblib"
    if cache_file.exists():
        logger.info(f"Loading cached AST data from {cache_file}...")
        return joblib.load(cache_file)
    
    in_file = PROCESSED_DIR / f"{split_name}.jsonl"
    logger.info(f"Normalizing and caching {split_name}.jsonl from scratch...")
    
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
    data_tuple = (X_orig, X_norm, y, stats)
    joblib.dump(data_tuple, cache_file)
    logger.info(f"Cached AST data saved to {cache_file}")
    return data_tuple

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
    logger.info("="*80)
    logger.info("STARTING EXPERIMENT G: RECALL-FOCUSED CANDIDATE INVESTIGATION")
    logger.info("="*80)
    
    # 1. Strict Integrity Checks
    base_bytes = open("models/bug_detector.joblib", "rb").read()
    base_h = hashlib.sha256(base_bytes).hexdigest()
    assert base_h.startswith("5f93bba9ce457fe9"), f"Integrity Failure: Baseline modified ({base_h})!"
    logger.info(f"Verified Production Baseline SHA-256: {base_h[:16]}... (INTACT)")
    
    test_bytes = open("data/processed/test.jsonl", "rb").read()
    test_h = hashlib.sha256(test_bytes).hexdigest()
    assert test_h.startswith("9aad8de8b09b0e2f"), f"Integrity Failure: test.jsonl modified ({test_h})!"
    logger.info(f"Verified Test Dataset SHA-256: {test_h[:16]}... (INTACT)")
    
    # 2. Load Datasets
    X_train_raw, X_train_norm, y_train, train_stats = get_ast_cached_dataset("train")
    X_orig_raw, X_orig_norm, y_orig, test_stats = get_ast_cached_dataset("test")
    X_rob_raw, X_rob_norm, y_rob, rob_stats = get_ast_cached_dataset("robust_heldout_test")
    
    # Benchmark 50
    X_bench_raw = [c["code"] for c in BENCHMARK_SUITE]
    X_bench_norm = [normalize_snippet(c["code"], c["lang"])[0] for c in BENCHMARK_SUITE]
    y_bench = [c["expected_cat"] for c in BENCHMARK_SUITE]
    
    # 3. Base class weight calculation
    class_counts = Counter(y_train)
    total_samples = len(y_train)
    num_classes = len(class_counts)
    
    base_weights = {cls: total_samples / (num_classes * count) for cls, count in class_counts.items()}
    logger.info("Base balanced weights:")
    for cls, w in sorted(base_weights.items()):
        logger.info(f"  {cls:<20}: count={class_counts[cls]:5d}, base_weight={w:.4f}")
        
    # --- CANDIDATE G1: Balanced Recall Minority Rebalancing ---
    # Dampen clean code to 0.30x; Boost minority defect classes (1.50x - 1.80x); other bugs 1.15x
    logger.info("\n--- Training Candidate G1 (Balanced Recall Minority Rebalancing) ---")
    weights_g1 = {}
    for cls, w in base_weights.items():
        if cls == "none_correct_code":
            weights_g1[cls] = w * 0.30
        elif cls in ("exception_handling", "type_error"):
            weights_g1[cls] = w * 1.80
        elif cls == "async_error":
            weights_g1[cls] = w * 1.65
        elif cls in ("api_misuse", "resource_leak", "loop_error", "undefined_behavior", "state_management"):
            weights_g1[cls] = w * 1.50
        else:
            weights_g1[cls] = w * 1.15

    pipe_g1 = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight=weights_g1, C=1.0, max_iter=500, random_state=42))
    ])
    pipe_g1.fit(X_train_norm, y_train)
    cand_g1_path = EXP_G_DIR / "candidate_g1_balanced_recall.joblib"
    joblib.dump(pipe_g1, cand_g1_path)
    logger.info(f"Saved Candidate G1 to {cand_g1_path}")
    
    # --- CANDIDATE G2: Aggressive Recall Prioritization ---
    # Heavily dampen clean code to 0.18x; Boost minority bugs to 2.20x; other bugs 1.30x
    logger.info("\n--- Training Candidate G2 (Aggressive Recall Prioritization) ---")
    weights_g2 = {}
    for cls, w in base_weights.items():
        if cls == "none_correct_code":
            weights_g2[cls] = w * 0.18
        elif cls in ("exception_handling", "type_error"):
            weights_g2[cls] = w * 2.20
        elif cls in ("async_error", "api_misuse", "resource_leak", "loop_error", "undefined_behavior", "state_management"):
            weights_g2[cls] = w * 2.00
        else:
            weights_g2[cls] = w * 1.30

    pipe_g2 = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight=weights_g2, C=1.0, max_iter=500, random_state=42))
    ])
    pipe_g2.fit(X_train_norm, y_train)
    cand_g2_path = EXP_G_DIR / "candidate_g2_aggressive_recall.joblib"
    joblib.dump(pipe_g2, cand_g2_path)
    logger.info(f"Saved Candidate G2 to {cand_g2_path}")

    # --- CANDIDATE G3: AST + Clean Token Pattern + Calibrated Regularization ---
    # Uses baseline's cleaner token pattern r"(?u)\b\w+\b|[<>=!+\-*/&|~^%]+" (excluding raw punctuation)
    # Balanced minority weights, C=1.5
    logger.info("\n--- Training Candidate G3 (Clean Token Pattern + Calibrated C=1.5) ---")
    weights_g3 = {}
    for cls, w in base_weights.items():
        if cls == "none_correct_code":
            weights_g3[cls] = w * 0.28
        elif cls in ("exception_handling", "type_error"):
            weights_g3[cls] = w * 1.85
        elif cls == "async_error":
            weights_g3[cls] = w * 1.70
        elif cls in ("api_misuse", "resource_leak", "loop_error", "undefined_behavior", "state_management"):
            weights_g3[cls] = w * 1.55
        else:
            weights_g3[cls] = w * 1.15

    pipe_g3 = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight=weights_g3, C=1.5, max_iter=500, random_state=42))
    ])
    pipe_g3.fit(X_train_norm, y_train)
    cand_g3_path = EXP_G_DIR / "candidate_g3_clean_tokens.joblib"
    joblib.dump(pipe_g3, cand_g3_path)
    logger.info(f"Saved Candidate G3 to {cand_g3_path}")

    # 4. Load Reference Models
    base_model = joblib.load("models/bug_detector.joblib")
    f2_model = joblib.load("models/experiments/experiment_f/candidate_f2_ast_weighted.joblib")

    models_to_eval = [
        ("Baseline (Production)", base_model, False),
        ("Candidate F2 (Staged Ref)", f2_model, True),
        ("Candidate G1 (Balanced Recall)", pipe_g1, True),
        ("Candidate G2 (Aggressive Recall)", pipe_g2, True),
        ("Candidate G3 (Clean Tokens + C=1.5)", pipe_g3, True),
    ]

    all_results = {
        "dataset_statistics": {
            "train": train_stats,
            "test_untouched": test_stats,
            "robust_heldout": rob_stats
        },
        "intercepts": {},
        "evaluations": {}
    }

    # Record intercepts for models
    for name, model, is_ast in models_to_eval:
        clf = model.named_steps["clf"]
        all_results["intercepts"][name] = {
            cls: round(float(clf.intercept_[idx]), 4) for idx, cls in enumerate(clf.classes_)
        }

    py_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["lang"] == "python" and not c["id"].startswith("CLEAN")]
    js_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("JS-ASYNC")]
    c_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("C-") and not c["id"].startswith("CLEAN")]

    for name, model, is_ast in models_to_eval:
        logger.info(f"\nEvaluating {name}...")
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
        
        logger.info(
            f"{name:32} | BenchAcc: {bench_eval['accuracy']*100:5.1f}% | "
            f"MacroF1: {bench_eval['macro_f1']:6.4f} | "
            f"CleanFPR: {bench_eval['clean_code_fpr']*100:5.1f}% | "
            f"BugRecall: {bench_eval['bug_detection_recall']*100:5.1f}% | "
            f"PyNovel: {bench_eval['sub_categories']['python_novel_identifiers (13)']*100:5.1f}% | "
            f"JSAsync: {bench_eval['sub_categories']['js_async_coverage (10)']*100:5.1f}% | "
            f"UntouchedAcc: {orig_eval['accuracy']*100:5.1f}% | "
            f"RobHeldAcc: {rob_eval['accuracy']*100:5.1f}%"
        )

    out_file = EXP_G_DIR / "experiment_g_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"\nSaved complete results to {out_file}")

if __name__ == "__main__":
    main()

