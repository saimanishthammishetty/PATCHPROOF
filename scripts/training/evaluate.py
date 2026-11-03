import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from sklearn.metrics import precision_recall_fscore_support, accuracy_score, confusion_matrix
import joblib
from scripts.datasets.schema import CodeDebuggingExample
from scripts.training.train import BaselineBugDetector, load_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EvaluateModel")

MODELS_DIR = Path("C:/PATCHPROOF/models")

def run_evaluation() -> Dict[str, Any]:
    test_ex = load_split("test")
    X_test = [ex.original_code for ex in test_ex]
    y_test = [ex.bug_category for ex in test_ex]

    # Load Baseline Model (Phase 2 model)
    baseline_path = MODELS_DIR / "bug_detector_v1_baseline.joblib"
    if not baseline_path.exists():
        baseline_path = MODELS_DIR / "bug_detector.joblib"
    base_ml_pipeline = joblib.load(baseline_path)
    base_ml_preds = base_ml_pipeline.predict(X_test)

    # Load Candidate Model (Phase 3 model)
    candidate_path = MODELS_DIR / "bug_detector_candidate.joblib"
    if not candidate_path.exists():
        candidate_path = MODELS_DIR / "bug_detector.joblib"
    cand_pipeline = joblib.load(candidate_path)
    cand_preds = cand_pipeline.predict(X_test)

    # Heuristic Rule Baseline
    rule_baseline = BaselineBugDetector()
    rule_preds = rule_baseline.predict(X_test)

    # Overall Metrics
    base_acc = accuracy_score(y_test, base_ml_preds)
    cand_acc = accuracy_score(y_test, cand_preds)
    rule_acc = accuracy_score(y_test, rule_preds)

    p_base, r_base, f1_base, _ = precision_recall_fscore_support(y_test, base_ml_preds, average="weighted", zero_division=0)
    p_cand, r_cand, f1_cand, _ = precision_recall_fscore_support(y_test, cand_preds, average="weighted", zero_division=0)
    p_rule, r_rule, f1_rule, _ = precision_recall_fscore_support(y_test, rule_preds, average="weighted", zero_division=0)

    # False Positive Rate on clean controls (none_correct_code)
    clean_indices = [i for i, y in enumerate(y_test) if y == "none_correct_code"]
    if clean_indices:
        base_clean_errors = sum(1 for i in clean_indices if base_ml_preds[i] != "none_correct_code")
        cand_clean_errors = sum(1 for i in clean_indices if cand_preds[i] != "none_correct_code")
        rule_clean_errors = sum(1 for i in clean_indices if rule_preds[i] != "none_correct_code")
        base_fpr = round(base_clean_errors / len(clean_indices), 4)
        cand_fpr = round(cand_clean_errors / len(clean_indices), 4)
        rule_fpr = round(rule_clean_errors / len(clean_indices), 4)
    else:
        base_fpr, cand_fpr, rule_fpr = 0.0, 0.0, 0.0

    # Breakdown by language
    languages = sorted(list(set(ex.language for ex in test_ex)))
    lang_breakdown = {}
    for lang in languages:
        indices = [i for i, ex in enumerate(test_ex) if ex.language == lang]
        if indices:
            y_sub = [y_test[i] for i in indices]
            base_sub = [base_ml_preds[i] for i in indices]
            cand_sub = [cand_preds[i] for i in indices]
            lang_breakdown[lang] = {
                "samples": len(indices),
                "baseline_f1": round(float(precision_recall_fscore_support(y_sub, base_sub, average="weighted", zero_division=0)[2]), 4),
                "candidate_f1": round(float(precision_recall_fscore_support(y_sub, cand_sub, average="weighted", zero_division=0)[2]), 4),
                "candidate_accuracy": round(float(accuracy_score(y_sub, cand_sub)), 4)
            }

    # Breakdown by source dataset
    sources = sorted(list(set(ex.source_dataset for ex in test_ex)))
    source_breakdown = {}
    for src in sources:
        indices = [i for i, ex in enumerate(test_ex) if ex.source_dataset == src]
        if indices:
            y_sub = [y_test[i] for i in indices]
            base_sub = [base_ml_preds[i] for i in indices]
            cand_sub = [cand_preds[i] for i in indices]
            source_breakdown[src] = {
                "samples": len(indices),
                "baseline_f1": round(float(precision_recall_fscore_support(y_sub, base_sub, average="weighted", zero_division=0)[2]), 4),
                "candidate_f1": round(float(precision_recall_fscore_support(y_sub, cand_sub, average="weighted", zero_division=0)[2]), 4),
                "candidate_accuracy": round(float(accuracy_score(y_sub, cand_sub)), 4)
            }

    eval_report = {
        "test_samples": len(test_ex),
        "overall": {
            "heuristic_rule_baseline": {
                "accuracy": round(float(rule_acc), 4),
                "f1_weighted": round(float(f1_rule), 4),
                "false_positive_rate": rule_fpr
            },
            "phase2_baseline_model": {
                "accuracy": round(float(base_acc), 4),
                "precision_weighted": round(float(p_base), 4),
                "recall_weighted": round(float(r_base), 4),
                "f1_weighted": round(float(f1_base), 4),
                "false_positive_rate": base_fpr
            },
            "phase3_candidate_model": {
                "accuracy": round(float(cand_acc), 4),
                "precision_weighted": round(float(p_cand), 4),
                "recall_weighted": round(float(r_cand), 4),
                "f1_weighted": round(float(f1_cand), 4),
                "false_positive_rate": cand_fpr
            },
            "candidate_vs_baseline_delta": {
                "accuracy_delta": round(float(cand_acc - base_acc), 4),
                "f1_delta": round(float(f1_cand - f1_base), 4),
                "fpr_reduction": round(float(base_fpr - cand_fpr), 4)
            }
        },
        "by_language": lang_breakdown,
        "by_source_dataset": source_breakdown
    }

    report_path = MODELS_DIR / "baseline_vs_candidate_evaluation.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)

    logger.info(f"Evaluation report generated:\n{json.dumps(eval_report, indent=2)}")
    return eval_report

if __name__ == "__main__":
    run_evaluation()
