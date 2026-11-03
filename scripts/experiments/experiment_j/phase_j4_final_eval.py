"""
Phase J4: Final Comparative Evaluation on all three datasets.
Uses optimal threshold from Phase J3 (val-only tuning).
Evaluates 5 systems on:
  1. 50-snippet novel benchmark
  2. 8353-record untouched test set (test.jsonl)
  3. 1226-record robust held-out set

Systems:
  A. Production Baseline (models/bug_detector.joblib)
  B. Candidate H1 ML-Only
  C. Static-Only Engine
  D. Experiment I Hybrid (threshold=0.40)
  E. Experiment J Hybrid (threshold=0.35, val-tuned)

CONSTRAINT: test.jsonl was NOT used for threshold selection.
"""
import json
import sys
import os
import joblib
import numpy as np
from collections import Counter
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    confusion_matrix, classification_report
)

sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_i"))
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_f"))

from static_analyzer import StaticAnalyzer
from hybrid_engine import HybridBugDetector

# ── Load models ─────────────────────────────────────────────────────────────
print("Loading models...")
baseline = joblib.load("models/bug_detector.joblib")
h1_model = joblib.load("models/experiments/experiment_h/candidate_h1_ast_only.joblib")
h1_classes = list(h1_model.classes_)
analyzer = StaticAnalyzer()

# Load optimal config (val-tuned)
with open("models/experiments/experiment_j/optimal_config.json") as f:
    opt_cfg = json.load(f)
OPTIMAL_THRESHOLD = opt_cfg["optimal_ml_threshold"]
print(f"Optimal ML threshold (val-tuned): {OPTIMAL_THRESHOLD}")

# ── Normalization ────────────────────────────────────────────────────────────
try:
    from ast_normalizer import normalize_snippet
    print("Using AST normalizer from experiment_f")
except ImportError:
    def normalize_snippet(code, lang): return code, {}
    print("WARNING: using identity normalizer")

# ── Category mapping (static -> test labels) ─────────────────────────────────
STATIC_CAT_MAP = {
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

# H1 class mapping to test-set labels
H1_CAT_MAP = {
    "api_misuse": "type_error",
    "exception_handling": "condition_error",
    "loop_error": "condition_error",
    "off_by_one": "condition_error",
    "state_management": "memory_safety",
    "undefined_behavior": "memory_safety",
    "async_error": "async_error",
    "condition_error": "condition_error",
    "memory_safety": "memory_safety",
    "none_correct_code": "none_correct_code",
    "null_pointer": "null_pointer",
    "resource_leak": "resource_leak",
    "type_error": "type_error",
}

def static_predict(code, lang):
    findings = analyzer.analyze(code, lang)
    if findings and findings[0].confidence >= 0.85:
        return STATIC_CAT_MAP.get(findings[0].category, findings[0].category)
    return "none_correct_code"

def h1_predict(code, lang, threshold=0.40):
    norm_code, _ = normalize_snippet(code, lang)
    probs = h1_model.predict_proba([norm_code])[0]
    top_idx = np.argmax(probs)
    top_cls = h1_classes[top_idx]
    top_prob = probs[top_idx]
    mapped = H1_CAT_MAP.get(top_cls, top_cls)
    if mapped != "none_correct_code" and top_prob >= threshold:
        return mapped
    return "none_correct_code"

def hybrid_predict(code, lang, threshold):
    """Static-first, fallback to H1 ML."""
    findings = analyzer.analyze(code, lang)
    if findings and findings[0].confidence >= 0.85:
        return STATIC_CAT_MAP.get(findings[0].category, findings[0].category)
    return h1_predict(code, lang, threshold)

def baseline_predict(code, lang):
    return baseline.predict([code])[0]

def evaluate_system(name, predict_fn, codes, langs, true_labels):
    """Run predict_fn and return metrics dict."""
    preds = [predict_fn(c, l) for c, l in zip(codes, langs)]
    # Map preds to known labels (clip unknown to none_correct_code)
    known = set(true_labels)
    preds_clipped = [p if p in known else "none_correct_code" for p in preds]

    all_labels = sorted(set(true_labels) | set(preds_clipped))
    acc = accuracy_score(true_labels, preds_clipped)
    macro_f1 = f1_score(true_labels, preds_clipped, average="macro", zero_division=0)
    macro_prec = precision_score(true_labels, preds_clipped, average="macro", zero_division=0)
    macro_rec = recall_score(true_labels, preds_clipped, average="macro", zero_division=0)

    bug_total = sum(1 for l in true_labels if l != "none_correct_code")
    bug_detected = sum(1 for t, p in zip(true_labels, preds_clipped) if t != "none_correct_code" and p != "none_correct_code")
    bug_recall = bug_detected / bug_total if bug_total > 0 else 0

    clean_total = sum(1 for l in true_labels if l == "none_correct_code")
    clean_fp = sum(1 for t, p in zip(true_labels, preds_clipped) if t == "none_correct_code" and p != "none_correct_code")
    clean_fpr = clean_fp / clean_total if clean_total > 0 else 0

    cm = confusion_matrix(true_labels, preds_clipped, labels=all_labels)
    report = classification_report(true_labels, preds_clipped, labels=all_labels, zero_division=0, output_dict=True)

    print(f"\n  [{name}]")
    print(f"    Accuracy:   {acc*100:.2f}%")
    print(f"    Macro F1:   {macro_f1:.4f}")
    print(f"    Macro Prec: {macro_prec:.4f}")
    print(f"    Macro Rec:  {macro_rec:.4f}")
    print(f"    Bug Recall: {bug_recall*100:.2f}%")
    print(f"    Clean FPR:  {clean_fpr*100:.2f}%")

    return {
        "system": name,
        "accuracy": round(acc, 6),
        "macro_f1": round(macro_f1, 6),
        "macro_precision": round(macro_prec, 6),
        "macro_recall": round(macro_rec, 6),
        "bug_recall": round(bug_recall, 6),
        "clean_fpr": round(clean_fpr, 6),
        "predictions": preds_clipped,
        "confusion_matrix": cm.tolist(),
        "cm_labels": all_labels,
        "per_class_report": report
    }

# ── BENCHMARK SUITE (50 snippets) ────────────────────────────────────────────
BENCHMARK = [
    # Python bugs
    {"code": "def f(x=[]):\n    x.append(1)\n    return x", "lang": "python", "label": "memory_safety"},
    {"code": "try:\n    open('f')\nexcept:\n    pass", "lang": "python", "label": "condition_error"},
    {"code": "x = None\nprint(x.upper())", "lang": "python", "label": "null_pointer"},
    {"code": "for i in range(len(lst)+1):\n    print(lst[i])", "lang": "python", "label": "condition_error"},
    {"code": "import asyncio\nasync def f():\n    asyncio.sleep(1)", "lang": "python", "label": "async_error"},
    {"code": "def g(d={}):\n    d['k']='v'\n    return d", "lang": "python", "label": "memory_safety"},
    {"code": "x = '5' + 5", "lang": "python", "label": "type_error"},
    {"code": "try:\n    int('a')\nexcept Exception:\n    pass", "lang": "python", "label": "condition_error"},
    {"code": "def f():\n    x=None\n    return x.strip()", "lang": "python", "label": "null_pointer"},
    {"code": "lst=[1,2,3]\nprint(lst[3])", "lang": "python", "label": "condition_error"},
    # Python clean
    {"code": "def add(a, b):\n    return a + b", "lang": "python", "label": "none_correct_code"},
    {"code": "with open('f') as fp:\n    data = fp.read()", "lang": "python", "label": "none_correct_code"},
    {"code": "try:\n    x = int(input())\nexcept ValueError:\n    x = 0", "lang": "python", "label": "none_correct_code"},
    {"code": "items = [i*2 for i in range(10)]", "lang": "python", "label": "none_correct_code"},
    {"code": "async def f():\n    await asyncio.sleep(1)", "lang": "python", "label": "none_correct_code"},
    # JavaScript bugs
    {"code": "fetch('/api').then(r => r.json()).then(d => d.id.toFixed())", "lang": "javascript", "label": "null_pointer"},
    {"code": "async function f() { return fetch('/api'); }", "lang": "javascript", "label": "async_error"},
    {"code": "var x = null; console.log(x.length);", "lang": "javascript", "label": "null_pointer"},
    {"code": "setTimeout(myFunc, 0);", "lang": "javascript", "label": "async_error"},
    {"code": "if (x == null) { return; }", "lang": "javascript", "label": "condition_error"},
    # JavaScript clean
    {"code": "const x = 5;\nconst y = x * 2;\nconsole.log(y);", "lang": "javascript", "label": "none_correct_code"},
    {"code": "async function f() { const r = await fetch('/api'); return r.json(); }", "lang": "javascript", "label": "none_correct_code"},
    {"code": "const arr = [1,2,3]; for (const x of arr) { console.log(x); }", "lang": "javascript", "label": "none_correct_code"},
    {"code": "try { JSON.parse(s); } catch(e) { console.error(e); }", "lang": "javascript", "label": "none_correct_code"},
    {"code": "if (x !== null && x !== undefined) { process(x); }", "lang": "javascript", "label": "none_correct_code"},
    # C bugs
    {"code": "void f() {\n    char buf[8];\n    return buf;\n}", "lang": "c", "label": "memory_safety"},
    {"code": "FILE* f = fopen('x','r');\nif (!f) return -1;\n// no fclose", "lang": "c", "label": "resource_leak"},
    {"code": "int *p = malloc(10);\nif (!p) return;\n// no free", "lang": "c", "label": "memory_safety"},
    {"code": "void f(long n) { printf(\"%d\", n); }", "lang": "c", "label": "type_error"},
    {"code": "int arr[5];\nfor(int i=0; i<=5; i++) arr[i]=i;", "lang": "c", "label": "memory_safety"},
    # C clean
    {"code": "int add(int a, int b) { return a + b; }", "lang": "c", "label": "none_correct_code"},
    {"code": "FILE* f = fopen('x','r');\nif (!f) return;\nfclose(f);", "lang": "c", "label": "none_correct_code"},
    {"code": "int *p = malloc(10);\nif (!p) return;\nfree(p);", "lang": "c", "label": "none_correct_code"},
    {"code": "void f(int n) { printf(\"%d\", n); }", "lang": "c", "label": "none_correct_code"},
    {"code": "for (int i = 0; i < 5; i++) { arr[i] = i; }", "lang": "c", "label": "none_correct_code"},
    # Novel identifiers (unseen function/var names)
    {"code": "def zylox_process(qfrm=[]):\n    qfrm.append(99)\n    return qfrm", "lang": "python", "label": "memory_safety"},
    {"code": "try:\n    vanthorpe_load()\nexcept:\n    pass", "lang": "python", "label": "condition_error"},
    {"code": "async def brixler():\n    asyncio.sleep(0.5)", "lang": "python", "label": "async_error"},
    {"code": "int *kraxton = malloc(64);\nif (!kraxton) return;\n// leaked", "lang": "c", "label": "memory_safety"},
    {"code": "void lumvex_log(long total) { printf(\"%d\", total); }", "lang": "c", "label": "type_error"},
    # Clean code resembling bugs
    {"code": "def f(items=None):\n    if items is None:\n        items = []\n    return items", "lang": "python", "label": "none_correct_code"},
    {"code": "try:\n    x = risky()\nexcept SpecificError as e:\n    logger.error(e)", "lang": "python", "label": "none_correct_code"},
    {"code": "int *p = malloc(sz);\nif (!p) { free(p); return -1; }\nuse(p);\nfree(p);", "lang": "c", "label": "none_correct_code"},
    {"code": "async function safe() { try { await fetch('/x'); } catch(e) { log(e); } }", "lang": "javascript", "label": "none_correct_code"},
    {"code": "void g(long n) { printf(\"%ld\", n); }", "lang": "c", "label": "none_correct_code"},
    # Edge cases
    {"code": "x = {'a': 1}\nprint(x['b'])", "lang": "python", "label": "null_pointer"},
    {"code": "FILE *f = fopen(path, 'rb');\nprocess(f);\nif (err) return -1;\nfclose(f);", "lang": "c", "label": "resource_leak"},
    {"code": "Promise.all([a(), b()]);", "lang": "javascript", "label": "async_error"},
    {"code": "const result = arr[arr.length];", "lang": "javascript", "label": "null_pointer"},
    {"code": "for (int i=1; i<=n; i++) total += arr[i];", "lang": "c", "label": "memory_safety"},
]

# ── Load datasets ────────────────────────────────────────────────────────────
print("\nLoading datasets...")

test_records = []
with open("data/processed/test.jsonl", encoding="utf-8") as f:
    for line in f:
        test_records.append(json.loads(line))
print(f"Test set: {len(test_records)} records")

robust_records = []
with open("data/processed/robust_heldout_test.jsonl", encoding="utf-8") as f:
    for line in f:
        robust_records.append(json.loads(line))
print(f"Robust heldout: {len(robust_records)} records")

bench_codes = [b["code"] for b in BENCHMARK]
bench_langs = [b["lang"] for b in BENCHMARK]
bench_labels = [b["label"] for b in BENCHMARK]

test_codes = [r["original_code"] for r in test_records]
test_langs = [r["language"] for r in test_records]
test_labels = [r["bug_category"] for r in test_records]

robust_codes = [r["original_code"] for r in robust_records]
robust_langs = [r["language"] for r in robust_records]
robust_labels = [r["bug_category"] for r in robust_records]

# ── System definitions ────────────────────────────────────────────────────────
systems = [
    ("Baseline_Production", lambda c, l: baseline_predict(c, l)),
    ("H1_ML_Only",          lambda c, l: h1_predict(c, l, threshold=0.35)),
    ("Static_Only",         lambda c, l: static_predict(c, l)),
    ("Hybrid_I_thresh040",  lambda c, l: hybrid_predict(c, l, threshold=0.40)),
    ("Hybrid_J_thresh035",  lambda c, l: hybrid_predict(c, l, threshold=OPTIMAL_THRESHOLD)),
]

results = {}

# ── BENCHMARK ────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("BENCHMARK SUITE (50 snippets)")
print("="*60)
bench_results = {}
for name, fn in systems:
    print(f"\nEvaluating {name} on benchmark...")
    r = evaluate_system(name, fn, bench_codes, bench_langs, bench_labels)
    bench_results[name] = r
results["benchmark"] = bench_results

# ── TEST SET ─────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"UNTOUCHED TEST SET ({len(test_records)} records)")
print("="*60)
test_results = {}
for name, fn in systems:
    print(f"\nEvaluating {name} on test set...")
    r = evaluate_system(name, fn, test_codes, test_langs, test_labels)
    test_results[name] = r
results["test"] = test_results

# ── ROBUST HELDOUT ───────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"ROBUST HELDOUT ({len(robust_records)} records)")
print("="*60)
robust_results = {}
for name, fn in systems:
    print(f"\nEvaluating {name} on robust heldout...")
    r = evaluate_system(name, fn, robust_codes, robust_langs, robust_labels)
    robust_results[name] = r
results["robust_heldout"] = robust_results

# ── Summary table ─────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("FINAL COMPARISON SUMMARY")
print("="*70)
print(f"{'System':<25} {'BenchAcc':>9} {'BenchF1':>9} {'TestAcc':>9} {'TestF1':>9} {'RobAcc':>9} {'RobF1':>9}")
print("-"*70)
for name, _ in systems:
    ba = bench_results[name]["accuracy"]*100
    bf = bench_results[name]["macro_f1"]
    ta = test_results[name]["accuracy"]*100
    tf = test_results[name]["macro_f1"]
    ra = robust_results[name]["accuracy"]*100
    rf = robust_results[name]["macro_f1"]
    print(f"  {name:<23} {ba:9.2f}% {bf:9.4f} {ta:9.2f}% {tf:9.4f} {ra:9.2f}% {rf:9.4f}")

# ── Failure analysis for best system on benchmark ────────────────────────────
print("\n" + "="*60)
print("FAILURE ANALYSIS — Hybrid_J on Benchmark")
print("="*60)
j_preds = bench_results["Hybrid_J_thresh035"]["predictions"]
for i, (b, pred) in enumerate(zip(BENCHMARK, j_preds)):
    if pred != b["label"]:
        print(f"  #{i:02d} [{b['lang']:12s}] True: {b['label']:20s} Pred: {pred}")
        print(f"        Code: {b['code'][:80]!r}")

# ── Save full results ─────────────────────────────────────────────────────────
os.makedirs("models/experiments/experiment_j", exist_ok=True)

# Strip predictions arrays to keep file size manageable
def slim(r):
    out = {k: v for k, v in r.items() if k != "predictions"}
    return out

save_results = {
    "experiment": "J",
    "optimal_threshold": OPTIMAL_THRESHOLD,
    "benchmark": {k: slim(v) for k, v in bench_results.items()},
    "test": {k: slim(v) for k, v in test_results.items()},
    "robust_heldout": {k: slim(v) for k, v in robust_results.items()},
}
with open("models/experiments/experiment_j/experiment_j_results.json", "w") as f:
    json.dump(save_results, f, indent=2)
print("\nSaved: models/experiments/experiment_j/experiment_j_results.json")

# Also save full predictions for failure analysis
full_results = {
    "test_preds": {k: v["predictions"] for k, v in test_results.items()},
    "test_labels": test_labels,
    "robust_preds": {k: v["predictions"] for k, v in robust_results.items()},
    "robust_labels": robust_labels,
}
with open("models/experiments/experiment_j/experiment_j_full_preds.json", "w") as f:
    json.dump(full_results, f)
print("Saved: models/experiments/experiment_j/experiment_j_full_preds.json")

