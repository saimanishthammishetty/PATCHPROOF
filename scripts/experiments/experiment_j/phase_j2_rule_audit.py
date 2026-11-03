"""
Phase J2: Static Analyzer Rule-Level Audit
Runs each static rule against test.jsonl to measure TP/FP/FN per rule.
Confirms whether static rules are causing regression or are innocent.
"""
import json
import sys
import os
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_i"))

from static_analyzer import StaticAnalyzer
from collections import defaultdict, Counter

analyzer = StaticAnalyzer()

# Load test data
records = []
with open("data/processed/test.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))

print(f"Loaded {len(records)} test records")
print(f"Class distribution: {Counter(r['bug_category'] for r in records)}")

# Per-rule tracking
rule_stats = defaultdict(lambda: {"fires": 0, "tp": 0, "fp": 0})

# Aggregate
static_preds = []
ground_truths = []
provenance_list = []

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

for rec in records:
    code = rec["original_code"]
    lang = rec["language"]
    true_label = rec["bug_category"]

    findings = analyzer.analyze(code, lang)

    if findings:
        top = findings[0]
        pred_label = CATEGORY_MAP.get(top.category, top.category)
        rule_fired = top.rule_id
        provenance = "static_rule"
    else:
        pred_label = "none_correct_code"
        rule_fired = None
        provenance = "no_rule"

    static_preds.append(pred_label)
    ground_truths.append(true_label)
    provenance_list.append(provenance)

    if rule_fired:
        rule_stats[rule_fired]["fires"] += 1
        if pred_label == true_label:
            rule_stats[rule_fired]["tp"] += 1
        else:
            rule_stats[rule_fired]["fp"] += 1

total = len(records)
correct = sum(1 for p, t in zip(static_preds, ground_truths) if p == t)
print(f"\nStatic-Only Accuracy: {correct}/{total} = {correct/total*100:.2f}%")

print("\n=== Per-Rule Statistics ===")
print(f"  {'Rule':50s} {'Fires':>6} {'TP':>6} {'FP':>6} {'Prec':>7}")
for rule, stats in sorted(rule_stats.items(), key=lambda x: -x[1]["fires"]):
    fires = stats["fires"]
    tp = stats["tp"]
    fp = stats["fp"]
    precision = tp / fires if fires > 0 else 0
    print(f"  {rule:50s} {fires:6d} {tp:6d} {fp:6d} {precision:7.3f}")

# Per-class static-only performance
class_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
for pred, true in zip(static_preds, ground_truths):
    if pred == true:
        class_stats[true]["tp"] += 1
    else:
        class_stats[pred]["fp"] += 1
        class_stats[true]["fn"] += 1

print("\n=== Per-Class Static-Only Performance ===")
print(f"  {'Class':30s} {'TP':>6} {'FP':>6} {'FN':>6} {'Prec':>7} {'Rec':>7} {'F1':>7}")
all_classes = sorted(set(ground_truths))
for cls in all_classes:
    tp = class_stats[cls]["tp"]
    fp = class_stats[cls]["fp"]
    fn = class_stats[cls]["fn"]
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    print(f"  {cls:30s} {tp:6d} {fp:6d} {fn:6d} {prec:7.3f} {rec:7.3f} {f1:7.3f}")

# Identify memory_safety false positives (rules firing on non-memory_safety)
print("\n=== Sample Memory-Safety FP Cases ===")
count = 0
for rec, pred, true in zip(records, static_preds, ground_truths):
    if pred == "memory_safety" and true != "memory_safety" and count < 5:
        print(f"  True: {true:20s} Lang: {rec['language']:10s} Template: {rec.get('template_family','?')}")
        print(f"  Code: {rec['original_code'][:150]!r}")
        print()
        count += 1

# Show type_error static coverage
te_total = sum(1 for t in ground_truths if t == "type_error")
te_correct = sum(1 for p, t in zip(static_preds, ground_truths) if t == "type_error" and p == t)
print(f"\ntype_error: static correctly identifies {te_correct}/{te_total} = {te_correct/te_total*100:.1f}%")

# Save summary
os.makedirs("models/experiments/experiment_j", exist_ok=True)
summary = {
    "static_accuracy": correct / total,
    "total_records": total,
    "rule_stats": {k: v for k, v in rule_stats.items()},
    "per_class": {
        cls: {
            "tp": class_stats[cls]["tp"],
            "fp": class_stats[cls]["fp"],
            "fn": class_stats[cls]["fn"]
        } for cls in all_classes
    }
}
with open("models/experiments/experiment_j/phase_j2_rule_audit.json", "w") as f:
    json.dump(summary, f, indent=2)
print("\nSaved: models/experiments/experiment_j/phase_j2_rule_audit.json")
