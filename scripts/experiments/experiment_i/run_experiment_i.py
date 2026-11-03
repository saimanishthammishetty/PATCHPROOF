"""
Experiment I: Hybrid Static Analysis + ML Architecture Evaluation Harness.
Strict Rules:
- Baseline (models/bug_detector.joblib) must NOT be modified or overwritten.
- Candidates F2, G1, G2, G3, H1..H5 preserved intact.
- All Candidate I artifacts isolated under models/experiments/experiment_i/.
- Untouched test set (test.jsonl) evaluated strictly for testing.
Evaluates:
  1. Baseline (Production Reference)
  2. Candidate H1 (ML-Only Control)
  3. Static-Only Engine (Deterministic Rule Baseline)
  4. Hybrid Engine (Experiment I - Static Rules + Candidate H1)
Across:
  - 50-snippet novel benchmark (BENCHMARK_SUITE)
  - 8,353-record untouched test set (test.jsonl)
  - 1,226-record robust held-out test set (robust_heldout_test.jsonl)
  - Real-world repository fixtures (fixtures/)
"""

import sys
import json
import logging
import hashlib
from pathlib import Path
from collections import Counter
import joblib
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, str(Path.cwd()))
from scripts.datasets.schema import CodeDebuggingExample
from scripts.benchmark_novel_eval import BENCHMARK_SUITE
from scripts.experiments.experiment_f.ast_normalizer import normalize_snippet
from scripts.experiments.experiment_i.static_analyzer import StaticAnalyzer
from scripts.experiments.experiment_i.hybrid_engine import HybridBugDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ExperimentI")

EXP_I_DIR = Path("C:/PATCHPROOF/models/experiments/experiment_i")
EXP_I_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR = Path("C:/PATCHPROOF/data/processed")

def evaluate_predictions(preds, probs, y_eval, dataset_name, classes=None):
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

    # Calibration if probs available
    brier, ece = 0.0, 0.0
    if probs is not None and classes is not None and len(probs) == len(y_eval):
        class_to_idx = {c: i for i, c in enumerate(classes)}
        one_hot = np.zeros_like(probs)
        for i, t in enumerate(y_eval):
            if t in class_to_idx:
                one_hot[i, class_to_idx[t]] = 1.0
        brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
        
        confidences = np.max(probs, axis=1)
        accuracies = np.array([1.0 if str(p) == str(t) else 0.0 for p, t in zip(preds, y_eval)])
        bin_boundaries = np.linspace(0, 1, 11)
        for i in range(10):
            bin_lower, bin_upper = bin_boundaries[i], bin_boundaries[i + 1]
            in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
            prop_in_bin = np.mean(in_bin)
            if prop_in_bin > 0:
                avg_acc = np.mean(accuracies[in_bin])
                avg_conf = np.mean(confidences[in_bin])
                ece += prop_in_bin * np.abs(avg_acc - avg_conf)

    return {
        "dataset": dataset_name,
        "sample_count": len(y_eval),
        "accuracy": round(float(acc), 4),
        "weighted_f1": round(float(f1_w), 4),
        "macro_f1": round(float(f1_m), 4),
        "clean_code_fpr": clean_fpr,
        "bug_false_negative_rate": bug_fnr,
        "bug_detection_recall": bug_recall,
        "brier_score": round(brier, 4),
        "ece": round(float(ece), 4),
        "per_class": per_class,
        "labels": labels,
        "confusion_matrix": cm,
        "predictions": [str(p) for p in preds]
    }

def main():
    logger.info("=" * 80)
    logger.info("STARTING EXPERIMENT I: HYBRID STATIC ANALYSIS + ML ARCHITECTURE")
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

    # 2. Instantiate Systems
    base_model = joblib.load("models/bug_detector.joblib")
    h1_model = joblib.load("models/experiments/experiment_h/candidate_h1_ast_only.joblib")
    hybrid_engine = HybridBugDetector("models/experiments/experiment_h/candidate_h1_ast_only.joblib", ml_threshold=0.40)
    all_classes = list(h1_model.classes_)

    # 3. Load Datasets
    # 3.1 Benchmark 50 Suite
    X_bench_raw = [c["code"] for c in BENCHMARK_SUITE]
    X_bench_ast = [normalize_snippet(c["code"], c["lang"])[0] for c in BENCHMARK_SUITE]
    y_bench = [c["expected_cat"] for c in BENCHMARK_SUITE]
    bench_langs = [c["lang"] for c in BENCHMARK_SUITE]

    # 3.2 Robust Held-out Dataset (1,226 records)
    rob_records = [CodeDebuggingExample.from_jsonl(l) for l in open(PROCESSED_DIR / "robust_heldout_test.jsonl", encoding="utf-8") if l.strip()]
    X_rob_raw = [r.original_code for r in rob_records]
    X_rob_ast = [normalize_snippet(r.original_code, r.language)[0] for r in rob_records]
    y_rob = [r.bug_category for r in rob_records]
    rob_langs = [r.language for r in rob_records]

    # 3.3 Untouched Test Dataset (8,353 records)
    test_records = [CodeDebuggingExample.from_jsonl(l) for l in open(PROCESSED_DIR / "test.jsonl", encoding="utf-8") if l.strip()]
    X_test_raw = [r.original_code for r in test_records]
    X_test_ast = [normalize_snippet(r.original_code, r.language)[0] for r in test_records]
    y_test = [r.bug_category for r in test_records]
    test_langs = [r.language for r in test_records]

    # 4. Generate Predictions for the 4 Comparison Modes
    systems = ["Baseline (Production)", "Candidate H1 (ML-Only)", "Static-Only Engine", "Hybrid Engine (Experiment I)"]
    all_results = {
        "benchmark_50": {},
        "robust_heldout_1226": {},
        "untouched_test_8353": {},
        "real_world_fixtures": {},
        "rule_performance": {}
    }

    # Evaluate Benchmark 50
    logger.info("\n--- Evaluating on 50-Snippet Benchmark ---")
    py_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["lang"] == "python" and not c["id"].startswith("CLEAN")]
    js_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("JS-ASYNC")]
    c_indices = [i for i, c in enumerate(BENCHMARK_SUITE) if c["id"].startswith("C-") and not c["id"].startswith("CLEAN")]

    rule_stats = Counter()

    for sys_name in systems:
        if sys_name == "Baseline (Production)":
            probs = base_model.predict_proba(X_bench_raw)
            preds = base_model.predict(X_bench_raw)
            classes = list(base_model.classes_)
        elif sys_name == "Candidate H1 (ML-Only)":
            probs = h1_model.predict_proba(X_bench_ast)
            preds = h1_model.predict(X_bench_ast)
            classes = all_classes
        elif sys_name == "Static-Only Engine":
            preds = []
            probs = None
            classes = all_classes
            for c, l in zip(X_bench_raw, bench_langs):
                findings = StaticAnalyzer.analyze(c, l)
                if findings:
                    preds.append(findings[0].category)
                    rule_stats[findings[0].rule_id] += 1
                else:
                    preds.append("none_correct_code")
        elif sys_name == "Hybrid Engine (Experiment I)":
            diagnoses = [hybrid_engine.diagnose(c, l) for c, l in zip(X_bench_raw, bench_langs)]
            preds = [d.category for d in diagnoses]
            classes = all_classes
            # Construct hybrid probability matrix for calibration
            probs = []
            for d in diagnoses:
                if d.ml_probabilities:
                    p_vec = [d.ml_probabilities.get(c, 0.0) for c in classes]
                    if d.provenance == "deterministic_static_rule":
                        # Set top static category to high confidence
                        idx = classes.index(d.category)
                        p_vec = [0.01] * len(classes)
                        p_vec[idx] = d.confidence
                    p_sum = sum(p_vec)
                    probs.append([p / p_sum for p in p_vec])
                else:
                    probs.append([1.0 / len(classes)] * len(classes))
            probs = np.array(probs)

        res = evaluate_predictions(preds, probs, y_bench, "benchmark_50", classes)
        res["sub_categories"] = {
            "python_novel_identifiers (13)": round(sum(1 for i in py_indices if preds[i] == y_bench[i]) / len(py_indices), 4),
            "js_async_coverage (10)": round(sum(1 for i in js_indices if preds[i] == y_bench[i]) / len(js_indices), 4),
            "c_defect_patterns (10)": round(sum(1 for i in c_indices if preds[i] == y_bench[i]) / len(c_indices), 4)
        }
        all_results["benchmark_50"][sys_name] = res
        logger.info(
            f"{sys_name:30} | Acc: {res['accuracy']*100:5.1f}% | "
            f"MacroF1: {res['macro_f1']:6.4f} | "
            f"CleanFPR: {res['clean_code_fpr']*100:5.1f}% | "
            f"BugRecall: {res['bug_detection_recall']*100:5.1f}% | "
            f"PyNovel: {res['sub_categories']['python_novel_identifiers (13)']*100:5.1f}% | "
            f"JSAsync: {res['sub_categories']['js_async_coverage (10)']*100:5.1f}% | "
            f"ECE: {res['ece']:.4f}"
        )

    # Evaluate Robust Held-out Dataset (1,226 records)
    logger.info("\n--- Evaluating on Robust Held-Out Dataset (1,226 records) ---")
    for sys_name in systems:
        if sys_name == "Baseline (Production)":
            probs = base_model.predict_proba(X_rob_raw)
            preds = base_model.predict(X_rob_raw)
            classes = list(base_model.classes_)
        elif sys_name == "Candidate H1 (ML-Only)":
            probs = h1_model.predict_proba(X_rob_ast)
            preds = h1_model.predict(X_rob_ast)
            classes = all_classes
        elif sys_name == "Static-Only Engine":
            preds = []
            probs = None
            classes = all_classes
            for c, l in zip(X_rob_raw, rob_langs):
                findings = StaticAnalyzer.analyze(c, l)
                preds.append(findings[0].category if findings else "none_correct_code")
        elif sys_name == "Hybrid Engine (Experiment I)":
            diagnoses = [hybrid_engine.diagnose(c, l) for c, l in zip(X_rob_raw, rob_langs)]
            preds = [d.category for d in diagnoses]
            probs = None
            classes = all_classes

        res = evaluate_predictions(preds, probs, y_rob, "robust_heldout_1226", classes)
        all_results["robust_heldout_1226"][sys_name] = res
        logger.info(f"{sys_name:30} | RobHeldAcc: {res['accuracy']*100:5.2f}% | MacroF1: {res['macro_f1']:6.4f} | BugRecall: {res['bug_detection_recall']*100:5.2f}%")

    # Evaluate Untouched Test Dataset (8,353 records)
    logger.info("\n--- Evaluating on Untouched Test Dataset (8,353 records) ---")
    for sys_name in systems:
        if sys_name == "Baseline (Production)":
            probs = base_model.predict_proba(X_test_raw)
            preds = base_model.predict(X_test_raw)
            classes = list(base_model.classes_)
        elif sys_name == "Candidate H1 (ML-Only)":
            probs = h1_model.predict_proba(X_test_ast)
            preds = h1_model.predict(X_test_ast)
            classes = all_classes
        elif sys_name == "Static-Only Engine":
            preds = []
            probs = None
            classes = all_classes
            for c, l in zip(X_test_raw, test_langs):
                findings = StaticAnalyzer.analyze(c, l)
                preds.append(findings[0].category if findings else "none_correct_code")
        elif sys_name == "Hybrid Engine (Experiment I)":
            diagnoses = [hybrid_engine.diagnose(c, l) for c, l in zip(X_test_raw, test_langs)]
            preds = [d.category for d in diagnoses]
            probs = None
            classes = all_classes

        res = evaluate_predictions(preds, probs, y_test, "untouched_test_8353", classes)
        all_results["untouched_test_8353"][sys_name] = res
        logger.info(f"{sys_name:30} | TestAcc: {res['accuracy']*100:5.2f}% | MacroF1: {res['macro_f1']:6.4f} | CleanFPR: {res['clean_code_fpr']*100:5.2f}% | BugRecall: {res['bug_detection_recall']*100:5.2f}%")

    # Evaluate Real-World Fixtures (fixtures/)
    logger.info("\n--- Evaluating on Real-World Repository Fixtures ---")
    fixture_files = [
        ("fixtures/vulnerable-python-repo/app.py", "python", "api_misuse"),
        ("fixtures/vulnerable-python-repo/tests/test_app.py", "python", "none_correct_code"),
        ("fixtures/vulnerable-node-repo/server.js", "javascript", "condition_error"),
        ("fixtures/secure-go-repo/main.go", "go", "none_correct_code"),
    ]
    fixture_results = []
    for f_path, lang, exp_cat in fixture_files:
        p = Path(f_path)
        if p.exists():
            code_text = p.read_text(encoding="utf-8")
            diag = hybrid_engine.diagnose(code_text, lang)
            fixture_results.append({
                "file": f_path,
                "language": lang,
                "expected": exp_cat,
                "predicted": diag.category,
                "confidence": diag.confidence,
                "provenance": diag.provenance,
                "rule_id": diag.rule_id,
                "correct": (diag.category == exp_cat or (exp_cat != "none_correct_code" and diag.category != "none_correct_code"))
            })
            logger.info(f"Fixture {f_path:<40} -> Pred: {diag.category:<18} (conf={diag.confidence*100:.1f}%, prov={diag.provenance})")

    all_results["real_world_fixtures"] = fixture_results

    out_file = EXP_I_DIR / "experiment_i_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"\nSaved complete Experiment I results to {out_file}")

if __name__ == "__main__":
    main()

