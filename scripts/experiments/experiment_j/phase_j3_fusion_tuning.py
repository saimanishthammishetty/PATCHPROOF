"""
Phase J3: Hybrid Fusion Parameter Optimization on val.jsonl ONLY.
Sweeps ML confidence threshold from 0.35 to 0.75 in steps of 0.05.
Selects optimal threshold by Macro F1 on val set.
NEVER touches test.jsonl for threshold selection.
"""
import json
import sys
import os
import joblib
import numpy as np
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_i"))

from static_analyzer import StaticAnalyzer
from hybrid_engine import HybridBugDetector
from sklearn.metrics import f1_score, accuracy_score
from collections import Counter

# Load val data
val_records = []
with open("data/processed/val.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        val_records.append(json.loads(line))
print(f"Loaded {len(val_records)} validation records")

# Load H1 model to get raw probabilities
h1_model = joblib.load("models/experiments/experiment_h/candidate_h1_ast_only.joblib")
h1_classes = list(h1_model.classes_)
print(f"H1 classes: {h1_classes}")

# Import normalize_snippet from experiment_i (same as hybrid engine uses)
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_f"))
try:
    from ast_normalizer import normalize_snippet
    print("Loaded normalize_snippet from experiment_f")
except ImportError:
    # fallback: identity
    def normalize_snippet(code, lang):
        return code, {}
    print("WARNING: Using identity normalize_snippet fallback")

analyzer = StaticAnalyzer()

val_true_labels = [rec["bug_category"] for rec in val_records]
print(f"Val class distribution: {Counter(val_true_labels)}")

# Pre-compute static findings and H1 probabilities for all val records
print("\nPre-computing static and H1 results for val set...")
static_findings_all = []
h1_probs_all = []

for i, rec in enumerate(val_records):
    if i % 1000 == 0:
        print(f"  Processing {i}/{len(val_records)}...")
    code = rec["original_code"]
    lang = rec["language"]
    findings = analyzer.analyze(code, lang)
    static_findings_all.append(findings)

    norm_code, _ = normalize_snippet(code, lang)
    probs = h1_model.predict_proba([norm_code])[0]
    h1_probs_all.append(probs)

h1_probs_all = np.array(h1_probs_all)
print("Pre-computation complete.")

CATEGORY_MAP = {
    "api_misuse": "type_error",
    "exception_handling": "condition_error",
    "type_error": "type_error",
    "memory_safety": "memory_safety",
    "resource_leak": "resource_leak",
    "null_pointer": "null_pointer",
    "async_error": "async_error",
    "condition_error": "condition_error",
    "none_correct_code": "none_correct_code",
}

def evaluate_threshold(threshold, static_min_confidence=0.85):
    """Evaluate hybrid system on val set with given ML threshold."""
    preds = []
    for i, (rec, findings) in enumerate(zip(val_records, static_findings_all)):
        # Static first
        if findings and findings[0].confidence >= static_min_confidence:
            pred = CATEGORY_MAP.get(findings[0].category, findings[0].category)
            preds.append(pred)
            continue

        # ML with threshold
        probs = h1_probs_all[i]
        max_prob = probs.max()
        ml_class = h1_classes[probs.argmax()]
        if ml_class != "none_correct_code" and max_prob >= threshold:
            preds.append(ml_class)
        else:
            # Fallback to static, which defaults to none_correct_code if no findings
            if findings:
                preds.append(CATEGORY_MAP.get(findings[0].category, findings[0].category))
            else:
                preds.append("none_correct_code")
    return preds

# Threshold sweep
thresholds = [round(t, 2) for t in np.arange(0.35, 0.80, 0.05)]
results = []

print("\n=== Threshold Sweep on val.jsonl ===")
print(f"  {'Threshold':>10} {'Accuracy':>10} {'MacroF1':>10} {'BugRec':>9} {'CleanFPR':>10}")

best_macro_f1 = -1
best_threshold = 0.40
best_result = None

clean_total = sum(1 for l in val_true_labels if l == "none_correct_code")
bug_total = sum(1 for l in val_true_labels if l != "none_correct_code")

for threshold in thresholds:
    preds = evaluate_threshold(threshold)
    acc = accuracy_score(val_true_labels, preds)
    macro_f1 = f1_score(val_true_labels, preds, average="macro", zero_division=0)

    tp_bug = sum(1 for t, p in zip(val_true_labels, preds) if t != "none_correct_code" and p != "none_correct_code")
    bug_recall = tp_bug / bug_total if bug_total > 0 else 0

    clean_fp = sum(1 for t, p in zip(val_true_labels, preds) if t == "none_correct_code" and p != "none_correct_code")
    clean_fpr = clean_fp / clean_total if clean_total > 0 else 0

    print(f"  {threshold:>10.2f} {acc*100:>10.2f}% {macro_f1:>10.4f} {bug_recall*100:>9.2f}% {clean_fpr*100:>10.2f}%")

    result = {
        "threshold": threshold,
        "val_accuracy": round(acc, 6),
        "val_macro_f1": round(macro_f1, 6),
        "val_bug_recall": round(bug_recall, 6),
        "val_clean_fpr": round(clean_fpr, 6)
    }
    results.append(result)

    if macro_f1 > best_macro_f1:
        best_macro_f1 = macro_f1
        best_threshold = threshold
        best_result = result

print(f"\n>>> Best threshold (by val Macro F1): {best_threshold}")
print(f">>> Val Macro F1:    {best_macro_f1:.4f}")
print(f">>> Val Accuracy:    {best_result['val_accuracy']*100:.2f}%")
print(f">>> Val Bug Recall:  {best_result['val_bug_recall']*100:.2f}%")
print(f">>> Val Clean FPR:   {best_result['val_clean_fpr']*100:.2f}%")

# Save optimal config
os.makedirs("models/experiments/experiment_j", exist_ok=True)
optimal_config = {
    "optimal_ml_threshold": best_threshold,
    "static_confidence_threshold": 0.85,
    "selection_metric": "val_macro_f1",
    "val_macro_f1": best_macro_f1,
    "val_accuracy": best_result["val_accuracy"],
    "val_bug_recall": best_result["val_bug_recall"],
    "val_clean_fpr": best_result["val_clean_fpr"],
    "sweep_results": results,
    "note": "Threshold selected exclusively on val.jsonl. test.jsonl not touched."
}
with open("models/experiments/experiment_j/optimal_config.json", "w") as f:
    json.dump(optimal_config, f, indent=2)
print("\nSaved: models/experiments/experiment_j/optimal_config.json")
