"""
Controlled Experiments Harness for PATCHPROOF ML Generalization Recovery.
Strict Isolation:
- Never touches models/bug_detector.joblib
- Saves experiment artifacts to models/experiments/
- Evaluates on:
    1. 50-snippet generalization benchmark (BENCHMARK_SUITE)
    2. Original untouched test set (data/processed/test.jsonl, 8,353 records)
    3. Robust held-out test set (data/processed/robust_heldout_test.jsonl, 1,226 records)
"""

import sys
import re
import json
import logging
from pathlib import Path
from collections import Counter
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.datasets.schema import CodeDebuggingExample
from scripts.benchmark_novel_eval import BENCHMARK_SUITE

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GeneralizationExperiments")

EXPERIMENTS_DIR = Path("C:/PATCHPROOF/models/experiments")
EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

PROCESSED_DIR = Path("C:/PATCHPROOF/data/processed")
BACKUP_DIR = Path("C:/PATCHPROOF/data/processed_v2_backup")

# Keywords in Python, JS, C that should NOT be anonymized
RESERVED_KEYWORDS = set([
    "def", "class", "return", "if", "else", "elif", "for", "while", "in", "is", "not",
    "and", "or", "try", "except", "finally", "with", "as", "import", "from", "pass",
    "break", "continue", "async", "await", "yield", "lambda", "None", "True", "False",
    "function", "const", "let", "var", "new", "typeof", "instanceof", "catch", "throw",
    "Promise", "resolve", "reject", "then", "int", "char", "float", "double", "void",
    "unsigned", "long", "short", "struct", "sizeof", "malloc", "free", "calloc", "realloc",
    "FILE", "fopen", "fclose", "fread", "fwrite", "printf", "sprintf", "strcpy", "strncpy"
])

def normalize_identifiers(code: str) -> str:
    """
    Experiment A: Abstract non-keyword variable and function identifiers
    to generic tokens while preserving keywords, strings, numbers, and operators.
    """
    def repl(match):
        token = match.group(0)
        if token in RESERVED_KEYWORDS or token.isdigit():
            return token
        return "ID_VAR"
    
    # Tokenize words vs symbols
    return re.sub(r'\b[a-zA-Z_]\w*\b', repl, code)

def load_data(split="train", sample_cap_none=None, use_anonymization=False):
    """Loads dataset from train.jsonl with optional class capping and identifier anonymization."""
    file_path = PROCESSED_DIR / f"{split}.jsonl"
    X = []
    y = []
    none_count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ex = CodeDebuggingExample.from_jsonl(line)
            
            # Controlled sampling for none_correct_code
            if sample_cap_none and ex.bug_category == "none_correct_code":
                if none_count >= sample_cap_none:
                    continue
                none_count += 1
            
            code = ex.original_code
            if use_anonymization:
                code = normalize_identifiers(code)
            
            X.append(code)
            y.append(ex.bug_category)
    return X, y

def evaluate_model(model, name, use_anonymization=False):
    """Evaluates a trained model across Benchmark, Original Test, and Robust Test."""
    # 1. 50-snippet Benchmark
    X_bench = [c["code"] for c in BENCHMARK_SUITE]
    if use_anonymization:
        X_bench = [normalize_identifiers(c) for c in X_bench]
    y_bench = [c["expected_cat"] for c in BENCHMARK_SUITE]
    
    bench_preds = model.predict(X_bench)
    bench_acc = accuracy_score(y_bench, bench_preds)
    p_w, r_w, f1_w, _ = precision_recall_fscore_support(y_bench, bench_preds, average="weighted", zero_division=0)
    p_m, r_m, f1_m, _ = precision_recall_fscore_support(y_bench, bench_preds, average="macro", zero_division=0)
    
    # Clean code false positive rate (15 clean cases)
    clean_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["expected_cat"] == "none_correct_code"]
    clean_false_alarms = sum(1 for i in clean_indices if bench_preds[i] != "none_correct_code")
    clean_fpr = clean_false_alarms / len(clean_indices)
    
    # Bug false negative rate (35 bug cases)
    bug_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["expected_cat"] != "none_correct_code"]
    bug_false_negatives = sum(1 for i in bug_indices if bench_preds[i] == "none_correct_code")
    bug_fnr = bug_false_negatives / len(bug_indices)
    
    # Python novel identifier accuracy (13 cases)
    py_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["lang"] == "python" and not c["id"].startswith("CLEAN")]
    py_correct = sum(1 for i in py_indices if bench_preds[i] == y_bench[i])
    py_acc = py_correct / len(py_indices)
    
    # JS Async accuracy (10 cases)
    js_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("JS-ASYNC")]
    js_correct = sum(1 for i in js_indices if bench_preds[i] == y_bench[i])
    js_acc = js_correct / len(js_indices)
    
    # C Defect accuracy (10 cases)
    c_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("C-") and not c["id"].startswith("CLEAN")]
    c_correct = sum(1 for i in c_indices if bench_preds[i] == y_bench[i])
    c_acc = c_correct / len(c_indices)
    
    # 2. Original Untouched Test Set (8,353 records)
    X_orig, y_orig = load_data("test", use_anonymization=use_anonymization)
    orig_preds = model.predict(X_orig)
    orig_acc = accuracy_score(y_orig, orig_preds)
    _, _, orig_f1_w, _ = precision_recall_fscore_support(y_orig, orig_preds, average="weighted", zero_division=0)
    _, _, orig_f1_m, _ = precision_recall_fscore_support(y_orig, orig_preds, average="macro", zero_division=0)
    
    # 3. Robust Held-out Test Set (1,226 records)
    X_rob, y_rob = load_data("robust_heldout_test", use_anonymization=use_anonymization)
    rob_preds = model.predict(X_rob)
    rob_acc = accuracy_score(y_rob, rob_preds)
    _, _, rob_f1_w, _ = precision_recall_fscore_support(y_rob, rob_preds, average="weighted", zero_division=0)
    _, _, rob_f1_m, _ = precision_recall_fscore_support(y_rob, rob_preds, average="macro", zero_division=0)
    
    labels = sorted(list(set(y_bench)))
    cm = confusion_matrix(y_bench, bench_preds, labels=labels).tolist()
    
    # Per-class metrics
    p_class, r_class, f1_class, supp_class = precision_recall_fscore_support(y_bench, bench_preds, labels=labels, zero_division=0)
    per_class = {}
    for idx, lbl in enumerate(labels):
        per_class[lbl] = {
            "precision": round(float(p_class[idx]), 3),
            "recall": round(float(r_class[idx]), 3),
            "f1": round(float(f1_class[idx]), 3),
            "support": int(supp_class[idx])
        }
    
    results = {
        "experiment_name": name,
        "benchmark": {
            "accuracy": round(float(bench_acc), 4),
            "weighted_f1": round(float(f1_w), 4),
            "macro_f1": round(float(f1_m), 4),
            "clean_code_fpr": round(float(clean_fpr), 4),
            "bug_false_negative_rate": round(float(bug_fnr), 4),
            "sub_categories": {
                "py_novel_identifiers": round(float(py_acc), 4),
                "js_async_coverage": round(float(js_acc), 4),
                "c_defect_patterns": round(float(c_acc), 4)
            },
            "per_class": per_class,
            "labels": labels,
            "confusion_matrix": cm
        },
        "original_test_8353": {
            "accuracy": round(float(orig_acc), 4),
            "weighted_f1": round(float(orig_f1_w), 4),
            "macro_f1": round(float(orig_f1_m), 4)
        },
        "robust_test_1226": {
            "accuracy": round(float(rob_acc), 4),
            "weighted_f1": round(float(rob_f1_w), 4),
            "macro_f1": round(float(rob_f1_m), 4)
        }
    }
    return results

def run_all_experiments():
    logger.info("Loading training data from train.jsonl...")
    X_train_raw, y_train_raw = load_data("train")
    logger.info(f"Loaded {len(X_train_raw)} training examples.")
    
    results_summary = []
    
    # -------------------------------------------------------------
    # BASELINE REFERENCE (Production Model)
    # -------------------------------------------------------------
    base_model = joblib.load("models/bug_detector.joblib")
    base_res = evaluate_model(base_model, "Baseline Reference (Production)")
    results_summary.append(base_res)
    logger.info(f"Baseline Reference: BenchAcc={base_res['benchmark']['accuracy']*100:.1f}%, BenchMacroF1={base_res['benchmark']['macro_f1']:.4f}, OrigAcc={base_res['original_test_8353']['accuracy']*100:.1f}%")
    
    # -------------------------------------------------------------
    # EXPERIMENT A: Identifier Normalization
    # -------------------------------------------------------------
    logger.info("Running Experiment A: Identifier Normalization...")
    X_train_anon, y_train_anon = load_data("train", use_anonymization=True)
    pipe_a = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=500, random_state=42))
    ])
    pipe_a.fit(X_train_anon, y_train_anon)
    joblib.dump(pipe_a, EXPERIMENTS_DIR / "exp_a_identifier_normalization.joblib")
    res_a = evaluate_model(pipe_a, "Exp A: Identifier Normalization", use_anonymization=True)
    results_summary.append(res_a)
    logger.info(f"Exp A Results: BenchAcc={res_a['benchmark']['accuracy']*100:.1f}%, BenchMacroF1={res_a['benchmark']['macro_f1']:.4f}, PyAcc={res_a['benchmark']['sub_categories']['py_novel_identifiers']*100:.1f}%")
    
    # -------------------------------------------------------------
    # EXPERIMENT B: Alternative Feature Weighting (Word-focused with df bounds)
    # -------------------------------------------------------------
    logger.info("Running Experiment B: Alternative Feature Weighting (min_df=3, max_df=0.80, max_features=6000)...")
    pipe_b = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            min_df=3,
            max_df=0.80,
            max_features=6000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=500, random_state=42))
    ])
    pipe_b.fit(X_train_raw, y_train_raw)
    joblib.dump(pipe_b, EXPERIMENTS_DIR / "exp_b_feature_weighting.joblib")
    res_b = evaluate_model(pipe_b, "Exp B: Alternative Feature Weighting (Word min/max_df)")
    results_summary.append(res_b)
    logger.info(f"Exp B Results: BenchAcc={res_b['benchmark']['accuracy']*100:.1f}%, BenchMacroF1={res_b['benchmark']['macro_f1']:.4f}, PyAcc={res_b['benchmark']['sub_categories']['py_novel_identifiers']*100:.1f}%")
    
    # -------------------------------------------------------------
    # EXPERIMENT C: Controlled Hard-Negative Sampling (Cap none_correct_code to 10,000)
    # -------------------------------------------------------------
    logger.info("Running Experiment C: Controlled Hard-Negative Sampling (Cap none_correct_code to 10k)...")
    X_train_c, y_train_c = load_data("train", sample_cap_none=10000)
    logger.info(f"Exp C: Loaded {len(X_train_c)} samples with capped none_correct_code.")
    pipe_c = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=500, random_state=42))
    ])
    pipe_c.fit(X_train_c, y_train_c)
    joblib.dump(pipe_c, EXPERIMENTS_DIR / "exp_c_controlled_hard_negative.joblib")
    res_c = evaluate_model(pipe_c, "Exp C: Controlled Hard-Negative Sampling (Cap none=10k)")
    results_summary.append(res_c)
    logger.info(f"Exp C Results: BenchAcc={res_c['benchmark']['accuracy']*100:.1f}%, BenchMacroF1={res_c['benchmark']['macro_f1']:.4f}, CleanFPR={res_c['benchmark']['clean_code_fpr']*100:.1f}%, PyAcc={res_c['benchmark']['sub_categories']['py_novel_identifiers']*100:.1f}%")

    # -------------------------------------------------------------
    # EXPERIMENT D: Class-Weight Tuning (Dampen none_correct_code weight, C=1.0)
    # -------------------------------------------------------------
    logger.info("Running Experiment D: Class-Weight Tuning...")
    # Compute inverse class frequencies, but dampen none_correct_code by 0.5x
    class_counts = Counter(y_train_raw)
    total_samples = len(y_train_raw)
    custom_weights = {}
    for cls_name, count in class_counts.items():
        base_w = total_samples / (len(class_counts) * count)
        if cls_name == "none_correct_code":
            custom_weights[cls_name] = base_w * 0.45  # Reduce bias towards none_correct_code
        elif cls_name in ("async_error", "resource_leak", "api_misuse"):
            custom_weights[cls_name] = base_w * 1.35  # Boost critical minority bug categories
        else:
            custom_weights[cls_name] = base_w

    pipe_d = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight=custom_weights, C=1.0, max_iter=500, random_state=42))
    ])
    pipe_d.fit(X_train_raw, y_train_raw)
    joblib.dump(pipe_d, EXPERIMENTS_DIR / "exp_d_class_weight_tuning.joblib")
    res_d = evaluate_model(pipe_d, "Exp D: Class-Weight Tuning (Damped none + Boosted minority)")
    results_summary.append(res_d)
    logger.info(f"Exp D Results: BenchAcc={res_d['benchmark']['accuracy']*100:.1f}%, BenchMacroF1={res_d['benchmark']['macro_f1']:.4f}, PyAcc={res_d['benchmark']['sub_categories']['py_novel_identifiers']*100:.1f}%, CleanFPR={res_d['benchmark']['clean_code_fpr']*100:.1f}%")

    # -------------------------------------------------------------
    # EXPERIMENT E: Feature Ablation (Word-only vs Char-only vs Balanced Union)
    # -------------------------------------------------------------
    logger.info("Running Experiment E1: Feature Ablation (Word-only, max_features=5000)...")
    pipe_e1 = Pipeline([
        ("word", TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight="balanced", C=1.0, max_iter=500, random_state=42))
    ])
    pipe_e1.fit(X_train_raw, y_train_raw)
    joblib.dump(pipe_e1, EXPERIMENTS_DIR / "exp_e1_word_only.joblib")
    res_e1 = evaluate_model(pipe_e1, "Exp E1: Word-only (5000 features)")
    results_summary.append(res_e1)

    logger.info("Running Experiment E2: Feature Ablation (Char-only, ngram 3-5, max_features=5000)...")
    pipe_e2 = Pipeline([
        ("char", TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=5000,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(class_weight="balanced", C=1.0, max_iter=500, random_state=42))
    ])
    pipe_e2.fit(X_train_raw, y_train_raw)
    joblib.dump(pipe_e2, EXPERIMENTS_DIR / "exp_e2_char_only.joblib")
    res_e2 = evaluate_model(pipe_e2, "Exp E2: Char-only (5000 features)")
    results_summary.append(res_e2)

    logger.info("Running Experiment E3: Feature Ablation (Balanced Union: 4000 Word + 1000 Char)...")
    features_e3 = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+", max_features=4000, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=1000, sublinear_tf=True))
    ])
    pipe_e3 = Pipeline([
        ("features", features_e3),
        ("clf", LogisticRegression(class_weight="balanced", C=1.0, max_iter=500, random_state=42))
    ])
    pipe_e3.fit(X_train_raw, y_train_raw)
    joblib.dump(pipe_e3, EXPERIMENTS_DIR / "exp_e3_balanced_union.joblib")
    res_e3 = evaluate_model(pipe_e3, "Exp E3: Balanced Union (4k Word + 1k Char)")
    results_summary.append(res_e3)

    # Save complete JSON summary
    summary_path = EXPERIMENTS_DIR / "experiments_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)
    logger.info(f"Saved complete experiments summary to {summary_path}")

    return results_summary

if __name__ == "__main__":
    run_all_experiments()

