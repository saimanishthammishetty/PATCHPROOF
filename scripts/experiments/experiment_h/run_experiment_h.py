"""
Experiment H: Dual-Channel Architecture & Multi-Dataset Evaluation Harness.
Strict Rules:
- Baseline (models/bug_detector.joblib) must NOT be modified or overwritten.
- F2, G1, G2, G3 preserved intact in their respective experiment folders.
- All Candidate H artifacts isolated under models/experiments/experiment_h/.
- Untouched test set (test.jsonl) evaluated strictly for testing, never used for training or tuning.
- Hyperparameter tuning (e.g. alpha for H4/H5) performed strictly on val.jsonl.
Evaluates:
  1. Baseline (Production Reference)
  2. Candidate F2 (Experiment F Reference)
  3. Candidate G2 (Experiment G Reference)
  4. Candidate H1 (AST-Only Control)
  5. Candidate H2 (Lexical-Only Control)
  6. Candidate H3 (Early Feature Concatenation)
  7. Candidate H4 (Late Probability Fusion)
  8. Candidate H5 (Class-Specific Channel Routing)
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
from scripts.experiments.experiment_h.dual_channel import extract_channel_b_lexical
from scripts.experiments.experiment_h.fusion_models import (
    EarlyFusionClassifier, LateProbabilityFusion, ClassSpecificChannelRouter
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ExperimentH")

EXP_H_DIR = Path("C:/PATCHPROOF/models/experiments/experiment_h")
EXP_H_DIR.mkdir(parents=True, exist_ok=True)
EXP_G_DIR = Path("C:/PATCHPROOF/models/experiments/experiment_g")

PROCESSED_DIR = Path("C:/PATCHPROOF/data/processed")

def get_ast_cached_dataset(split_name: str):
    """Loads AST normalized data from EXP_G_DIR cache or builds and caches it."""
    cache_file_g = EXP_G_DIR / f"cache_{split_name}_ast.joblib"
    cache_file_h = EXP_H_DIR / f"cache_{split_name}_ast.joblib"
    
    if cache_file_h.exists():
        logger.info(f"Loading cached AST data from {cache_file_h}...")
        return joblib.load(cache_file_h)
    if cache_file_g.exists():
        logger.info(f"Loading cached AST data from {cache_file_g}...")
        data = joblib.load(cache_file_g)
        joblib.dump(data, cache_file_h)
        return data
        
    in_file = PROCESSED_DIR / f"{split_name}.jsonl"
    logger.info(f"Normalizing and caching {split_name}.jsonl from scratch...")
    
    X_orig, X_norm, y, langs = [], [], [], []
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
            langs.append(ex.language)
            
    data_tuple = (X_orig, X_norm, y, langs, stats)
    joblib.dump(data_tuple, cache_file_h)
    logger.info(f"Saved AST cache to {cache_file_h}")
    return data_tuple

def get_lexical_cached_dataset(split_name: str, X_orig: list, langs: list, y: list):
    """Extracts and caches Channel B lexical features."""
    cache_file = EXP_H_DIR / f"cache_{split_name}_lexical.joblib"
    if cache_file.exists():
        logger.info(f"Loading cached Lexical data from {cache_file}...")
        return joblib.load(cache_file)
        
    logger.info(f"Extracting Channel B Lexical features for {split_name} ({len(X_orig)} samples)...")
    X_lex = []
    for code, lang in zip(X_orig, langs):
        X_lex.append(extract_channel_b_lexical(code, lang))
        
    joblib.dump(X_lex, cache_file)
    logger.info(f"Saved Lexical cache to {cache_file}")
    return X_lex

def compute_calibration_metrics(probs: np.ndarray, y_true: list, classes: list):
    """Computes Multi-class Brier score and Expected Calibration Error (ECE)."""
    n_samples = len(y_true)
    class_to_idx = {c: i for i, c in enumerate(classes)}
    
    # 1. Brier Score
    one_hot = np.zeros_like(probs)
    for i, t in enumerate(y_true):
        if t in class_to_idx:
            one_hot[i, class_to_idx[t]] = 1.0
            
    brier_score = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
    
    # 2. Expected Calibration Error (10 bins)
    confidences = np.max(probs, axis=1)
    predictions = [classes[idx] for idx in np.argmax(probs, axis=1)]
    accuracies = np.array([1.0 if str(p) == str(t) else 0.0 for p, t in zip(predictions, y_true)])
    
    bin_boundaries = np.linspace(0, 1, 11)
    ece = 0.0
    for i in range(10):
        bin_lower, bin_upper = bin_boundaries[i], bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            avg_acc = np.mean(accuracies[in_bin])
            avg_conf = np.mean(confidences[in_bin])
            ece += prop_in_bin * np.abs(avg_acc - avg_conf)
            
    return round(brier_score, 4), round(float(ece), 4)

def evaluate_model_comprehensive(model, X_ast, X_lex, y_eval, langs_eval, dataset_name, model_type):
    # Predict
    if model_type in ("fusion_early", "fusion_late", "fusion_routed"):
        preds = model.predict(X_ast, X_lex)
        probs = model.predict_proba(X_ast, X_lex)
        classes = list(model.classes_)
    elif model_type == "ast_only":
        preds = model.predict(X_ast)
        probs = model.predict_proba(X_ast)
        classes = list(model.classes_)
    elif model_type in ("lexical_only", "baseline_raw"):
        preds = model.predict(X_lex)
        probs = model.predict_proba(X_lex)
        classes = list(model.classes_)
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

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

    # Calibration
    brier, ece = compute_calibration_metrics(probs, y_eval, classes)

    # Language breakdown
    lang_acc = {}
    for l in sorted(list(set(langs_eval))):
        idx_l = [i for i, lg in enumerate(langs_eval) if lg == l]
        if idx_l:
            l_acc = sum(1 for i in idx_l if preds[i] == y_eval[i]) / len(idx_l)
            lang_acc[l] = round(float(l_acc), 4)

    return {
        "dataset": dataset_name,
        "sample_count": len(y_eval),
        "accuracy": round(float(acc), 4),
        "weighted_f1": round(float(f1_w), 4),
        "macro_f1": round(float(f1_m), 4),
        "clean_code_fpr": clean_fpr,
        "bug_false_negative_rate": bug_fnr,
        "bug_detection_recall": bug_recall,
        "brier_score": brier,
        "ece": ece,
        "language_accuracy": lang_acc,
        "per_class": per_class,
        "labels": labels,
        "confusion_matrix": cm,
        "predictions": [str(p) for p in preds]
    }

def main():
    logger.info("=" * 80)
    logger.info("STARTING EXPERIMENT H: DUAL-CHANNEL FEATURE PIPELINE & EVALUATION")
    logger.info("=" * 80)

    # 1. Strict Integrity Checks
    base_bytes = open("models/bug_detector.joblib", "rb").read()
    base_h = hashlib.sha256(base_bytes).hexdigest()
    assert base_h.startswith("5f93bba9ce457fe9"), f"Integrity Failure: Baseline modified ({base_h})!"
    logger.info(f"Verified Production Baseline SHA-256: {base_h[:16]}... (INTACT)")

    test_bytes = open("data/processed/test.jsonl", "rb").read()
    test_h = hashlib.sha256(test_bytes).hexdigest()
    assert test_h.startswith("9aad8de8b09b0e2f"), f"Integrity Failure: test.jsonl modified ({test_h})!"
    logger.info(f"Verified Test Dataset SHA-256: {test_h[:16]}... (INTACT)")

    # 2. Load and Prepare Datasets
    # Train
    train_data = get_ast_cached_dataset("train")
    if len(train_data) == 5:
        X_train_orig, X_train_ast, y_train, train_langs, train_stats = train_data
    else:
        X_train_orig, X_train_ast, y_train, train_stats = train_data
        train_langs = [json.loads(l)["language"] for l in open(PROCESSED_DIR / "train.jsonl", encoding="utf-8") if l.strip()]
    X_train_lex = get_lexical_cached_dataset("train", X_train_orig, train_langs, y_train)

    # Val (for tuning hyperparameter alpha without touching test set)
    val_data = get_ast_cached_dataset("val")
    if len(val_data) == 5:
        X_val_orig, X_val_ast, y_val, val_langs, val_stats = val_data
    else:
        X_val_orig, X_val_ast, y_val, val_stats = val_data
        val_langs = [json.loads(l)["language"] for l in open(PROCESSED_DIR / "val.jsonl", encoding="utf-8") if l.strip()]
    X_val_lex = get_lexical_cached_dataset("val", X_val_orig, val_langs, y_val)

    # Test Untouched (strictly for final testing)
    test_data = get_ast_cached_dataset("test")
    if len(test_data) == 5:
        X_test_orig, X_test_ast, y_test, test_langs, test_stats = test_data
    else:
        X_test_orig, X_test_ast, y_test, test_stats = test_data
        test_langs = [json.loads(l)["language"] for l in open(PROCESSED_DIR / "test.jsonl", encoding="utf-8") if l.strip()]
    X_test_lex = get_lexical_cached_dataset("test", X_test_orig, test_langs, y_test)

    # Robust Held-Out (1,226 samples)
    rob_data = get_ast_cached_dataset("robust_heldout_test")
    if len(rob_data) == 5:
        X_rob_orig, X_rob_ast, y_rob, rob_langs, rob_stats = rob_data
    else:
        X_rob_orig, X_rob_ast, y_rob, rob_stats = rob_data
        rob_langs = [json.loads(l)["language"] for l in open(PROCESSED_DIR / "robust_heldout_test.jsonl", encoding="utf-8") if l.strip()]
    X_rob_lex = get_lexical_cached_dataset("robust_heldout_test", X_rob_orig, rob_langs, y_rob)

    # Benchmark 50 Suite
    X_bench_orig = [c["code"] for c in BENCHMARK_SUITE]
    X_bench_ast = [normalize_snippet(c["code"], c["lang"])[0] for c in BENCHMARK_SUITE]
    bench_langs = [c["lang"] for c in BENCHMARK_SUITE]
    y_bench = [c["expected_cat"] for c in BENCHMARK_SUITE]
    X_bench_lex = [extract_channel_b_lexical(c["code"], c["lang"]) for c in BENCHMARK_SUITE]

    # Balanced class weights computation
    class_counts = Counter(y_train)
    total_samples = len(y_train)
    num_classes = len(class_counts)
    base_weights = {cls: total_samples / (num_classes * count) for cls, count in class_counts.items()}
    
    # Balanced Recall weights
    balanced_weights = {}
    for cls, w in base_weights.items():
        if cls == "none_correct_code":
            balanced_weights[cls] = w * 0.35
        elif cls in ("exception_handling", "type_error"):
            balanced_weights[cls] = w * 1.75
        elif cls == "async_error":
            balanced_weights[cls] = w * 1.60
        elif cls in ("api_misuse", "resource_leak", "loop_error", "undefined_behavior", "state_management"):
            balanced_weights[cls] = w * 1.45
        else:
            balanced_weights[cls] = w * 1.15

    # 3. Train Candidate H1 (AST-Only Control)
    h1_path = EXP_H_DIR / "candidate_h1_ast_only.joblib"
    if h1_path.exists():
        logger.info(f"Loading existing Candidate H1 from {h1_path}...")
        pipe_h1 = joblib.load(h1_path)
    else:
        logger.info("\n--- Training Candidate H1 (AST-Only Control) ---")
        vec_h1 = TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )
        clf_h1 = LogisticRegression(class_weight=balanced_weights, C=1.0, max_iter=500, random_state=42)
        pipe_h1 = Pipeline([("tfidf", vec_h1), ("clf", clf_h1)])
        pipe_h1.fit(X_train_ast, y_train)
        joblib.dump(pipe_h1, h1_path)
        logger.info("Saved Candidate H1 to candidate_h1_ast_only.joblib")

    # 4. Train Candidate H2 (Lexical-Only Control)
    h2_path = EXP_H_DIR / "candidate_h2_lexical_only.joblib"
    if h2_path.exists():
        logger.info(f"Loading existing Candidate H2 from {h2_path}...")
        pipe_h2 = joblib.load(h2_path)
    else:
        logger.info("\n--- Training Candidate H2 (Lexical-Only Control) ---")
        vec_h2 = TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%]+|__\w+__",
            max_features=5000,
            sublinear_tf=True
        )
        clf_h2 = LogisticRegression(class_weight=balanced_weights, C=1.0, max_iter=500, random_state=42)
        pipe_h2 = Pipeline([("tfidf", vec_h2), ("clf", clf_h2)])
        pipe_h2.fit(X_train_lex, y_train)
        joblib.dump(pipe_h2, h2_path)
        logger.info("Saved Candidate H2 to candidate_h2_lexical_only.joblib")

    # 5. Train Candidate H3 (Early Feature Concatenation)
    logger.info("\n--- Training Candidate H3 (Early Feature Concatenation) ---")
    vec_h3_ast = TfidfVectorizer(
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
        max_features=4000,
        sublinear_tf=True
    )
    vec_h3_lex = TfidfVectorizer(
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%]+|__\w+__",
        max_features=4000,
        sublinear_tf=True
    )
    clf_h3 = LogisticRegression(class_weight=balanced_weights, C=1.0, max_iter=500, random_state=42)
    model_h3 = EarlyFusionClassifier(vec_h3_ast, vec_h3_lex, clf_h3)
    model_h3.fit(X_train_ast, X_train_lex, y_train)
    joblib.dump(model_h3, EXP_H_DIR / "candidate_h3_early_fusion.joblib")
    logger.info("Saved Candidate H3 to candidate_h3_early_fusion.joblib")

    # 6. Validate & Tune Candidate H4 (Late Probability Fusion)
    logger.info("\n--- Tuning Candidate H4 (Late Probability Fusion) on val.jsonl ---")
    best_alpha = 0.5
    best_val_f1 = -1.0
    for alpha in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        h4_temp = LateProbabilityFusion(pipe_h1, pipe_h2, alpha=alpha)
        val_eval = evaluate_model_comprehensive(h4_temp, X_val_ast, X_val_lex, y_val, val_langs, "val", "fusion_late")
        logger.info(f"  alpha={alpha:.1f} -> Val Acc: {val_eval['accuracy']*100:.2f}%, Val Macro F1: {val_eval['macro_f1']:.4f}")
        if val_eval["macro_f1"] > best_val_f1:
            best_val_f1 = val_eval["macro_f1"]
            best_alpha = alpha
            
    logger.info(f"Optimal alpha for H4 selected strictly on validation set: alpha* = {best_alpha}")
    model_h4 = LateProbabilityFusion(pipe_h1, pipe_h2, alpha=best_alpha)
    joblib.dump(model_h4, EXP_H_DIR / "candidate_h4_late_fusion.joblib")
    logger.info("Saved Candidate H4 to candidate_h4_late_fusion.joblib")

    # 7. Candidate H5 (Class-Specific Channel Routing)
    logger.info("\n--- Validating Candidate H5 (Class-Specific Channel Routing) ---")
    model_h5 = ClassSpecificChannelRouter(pipe_h1, pipe_h2)
    val_eval_h5 = evaluate_model_comprehensive(model_h5, X_val_ast, X_val_lex, y_val, val_langs, "val", "fusion_routed")
    logger.info(f"H5 Val Acc: {val_eval_h5['accuracy']*100:.2f}%, Val Macro F1: {val_eval_h5['macro_f1']:.4f}")
    joblib.dump(model_h5, EXP_H_DIR / "candidate_h5_routed_fusion.joblib")
    logger.info("Saved Candidate H5 to candidate_h5_routed_fusion.joblib")

    # 8. Multi-Dataset Evaluation Across All Models
    base_model = joblib.load("models/bug_detector.joblib")
    f2_model = joblib.load("models/experiments/experiment_f/candidate_f2_ast_weighted.joblib")
    g2_model = joblib.load("models/experiments/experiment_g/candidate_g2_aggressive_recall.joblib")

    models_to_evaluate = [
        ("Baseline (Production)", base_model, "baseline_raw"),
        ("Candidate F2 (Staged Ref)", f2_model, "ast_only"),
        ("Candidate G2 (Aggressive Ref)", g2_model, "ast_only"),
        ("Candidate H1 (AST-Only)", pipe_h1, "ast_only"),
        ("Candidate H2 (Lexical-Only)", pipe_h2, "lexical_only"),
        ("Candidate H3 (Early Fusion)", model_h3, "fusion_early"),
        ("Candidate H4 (Late Fusion)", model_h4, "fusion_late"),
        ("Candidate H5 (Routed Fusion)", model_h5, "fusion_routed"),
    ]

    all_results = {
        "validation_tuning": {
            "h4_optimal_alpha": best_alpha,
            "h4_val_macro_f1": best_val_f1,
            "h5_val_macro_f1": val_eval_h5["macro_f1"]
        },
        "evaluations": {}
    }

    py_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["lang"] == "python" and not c["id"].startswith("CLEAN")]
    js_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("JS-ASYNC")]
    c_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("C-") and not c["id"].startswith("CLEAN")]

    for name, model, m_type in models_to_evaluate:
        logger.info(f"\nEvaluating {name}...")
        
        bench_eval = evaluate_model_comprehensive(
            model, X_bench_ast, X_bench_lex, y_bench, bench_langs, "benchmark_50", m_type
        )
        bench_preds = bench_eval["predictions"]
        bench_eval["sub_categories"] = {
            "python_novel_identifiers (13)": round(sum(1 for i in py_indices if bench_preds[i] == y_bench[i]) / len(py_indices), 4),
            "js_async_coverage (10)": round(sum(1 for i in js_indices if bench_preds[i] == y_bench[i]) / len(js_indices), 4),
            "c_defect_patterns (10)": round(sum(1 for i in c_indices if bench_preds[i] == y_bench[i]) / len(c_indices), 4)
        }

        test_eval = evaluate_model_comprehensive(
            model, X_test_ast, X_test_lex, y_test, test_langs, "untouched_test_8353", m_type
        )

        rob_eval = evaluate_model_comprehensive(
            model, X_rob_ast, X_rob_lex, y_rob, rob_langs, "robust_heldout_1226", m_type
        )

        all_results["evaluations"][name] = {
            "benchmark_50": bench_eval,
            "untouched_test_8353": test_eval,
            "robust_heldout_1226": rob_eval
        }

        logger.info(
            f"{name:32} | BenchAcc: {bench_eval['accuracy']*100:5.1f}% | "
            f"MacroF1: {bench_eval['macro_f1']:6.4f} | "
            f"CleanFPR: {bench_eval['clean_code_fpr']*100:5.1f}% | "
            f"BugRecall: {bench_eval['bug_detection_recall']*100:5.1f}% | "
            f"PyNovel: {bench_eval['sub_categories']['python_novel_identifiers (13)']*100:5.1f}% | "
            f"JSAsync: {bench_eval['sub_categories']['js_async_coverage (10)']*100:5.1f}% | "
            f"TestAcc: {test_eval['accuracy']*100:5.1f}% | "
            f"RobHeldAcc: {rob_eval['accuracy']*100:5.1f}% | "
            f"ECE: {bench_eval['ece']:.4f}"
        )

    out_file = EXP_H_DIR / "experiment_h_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"\nSaved complete Experiment H results to {out_file}")

if __name__ == "__main__":
    main()

