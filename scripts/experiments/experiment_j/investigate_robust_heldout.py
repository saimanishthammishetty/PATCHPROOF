"""Investigate why Static-Only gets 100% on robust heldout (only async_error + type_error classes)."""
import json
import sys
import os
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_i"))
from static_analyzer import StaticAnalyzer
from collections import Counter

analyzer = StaticAnalyzer()
records = []
with open("data/processed/robust_heldout_test.jsonl", encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))

print(f"Robust heldout: {len(records)} records")
print(f"Labels: {Counter(r['bug_category'] for r in records)}")
print(f"Languages: {Counter(r['language'] for r in records)}")

STATIC_CAT_MAP = {
    "api_misuse": "type_error", "exception_handling": "condition_error",
    "type_error": "type_error", "memory_safety": "memory_safety",
    "resource_leak": "resource_leak", "null_pointer": "null_pointer",
    "async_error": "async_error", "condition_error": "condition_error",
    "none_correct_code": "none_correct_code",
}

# Check what static predicts
preds = []
for rec in records:
    findings = analyzer.analyze(rec["original_code"], rec["language"])
    if findings and findings[0].confidence >= 0.85:
        pred = STATIC_CAT_MAP.get(findings[0].category, findings[0].category)
    else:
        pred = "none_correct_code"
    preds.append(pred)

print(f"\nStatic predictions: {Counter(preds)}")
correct = sum(1 for p, r in zip(preds, records) if p == r["bug_category"])
print(f"Static accuracy: {correct}/{len(records)} = {correct/len(records)*100:.1f}%")

# Show first 5 samples and their predictions
print("\nSample inspection:")
for i, (rec, pred) in enumerate(zip(records[:5], preds[:5])):
    print(f"  #{i} true={rec['bug_category']} pred={pred} lang={rec['language']}")
    print(f"     template={rec.get('template_family','?')}")
    print(f"     code: {rec['original_code'][:100]!r}")

