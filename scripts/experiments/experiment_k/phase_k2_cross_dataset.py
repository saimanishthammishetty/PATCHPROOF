"""
PATCHPROOF Experiment K — Phase K2: Cross-Dataset Generalization
Evaluates the ML baseline and Candidate H1 across 7 independent dataset distributions:
1. Untouched Test Set (full 8,353 samples)
2. BigVul Real C Vulnerabilities (1,091 samples)
3. CodeXGLUE Devign Real C Functions (3,577 samples)
4. CodeSearchNet Real Clean Controls (1,282 samples)
5. Synthetic Patchproof Held-Out (2,403 samples)
6. Robust Held-Out Synthetic (1,226 samples)
7. Novel Benchmark Suite (50 curated samples)

Strictly respects dataset-level separation. Measures Accuracy, Macro/Weighted F1,
Precision, Recall, Per-Class performance, Confusion Matrices, and Unknown-Class behavior.
"""

import json
import os
import sys
import joblib
import numpy as np
from collections import Counter, defaultdict
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

# Add experiment path for AST normalizer
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_f"))
try:
    from ast_normalizer import normalize_snippet
except ImportError:
    def normalize_snippet(code, lang): return code, {}

# Benchmark Suite (50 samples)
BENCHMARK_SUITE = [
    # Python defects
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
    # Python clean controls
    {"code": "def add(a, b):\n    return a + b", "lang": "python", "label": "none_correct_code"},
    {"code": "with open('f') as fp:\n    data = fp.read()", "lang": "python", "label": "none_correct_code"},
    {"code": "try:\n    x = int(input())\nexcept ValueError:\n    x = 0", "lang": "python", "label": "none_correct_code"},
    {"code": "items = [i*2 for i in range(10)]", "lang": "python", "label": "none_correct_code"},
    {"code": "async def f():\n    await asyncio.sleep(1)", "lang": "python", "label": "none_correct_code"},
    # JavaScript defects
    {"code": "fetch('/api').then(r => r.json()).then(d => d.id.toFixed())", "lang": "javascript", "label": "null_pointer"},
    {"code": "async function f() { return fetch('/api'); }", "lang": "javascript", "label": "async_error"},
    {"code": "var x = null; console.log(x.length);", "lang": "javascript", "label": "null_pointer"},
    {"code": "setTimeout(myFunc, 0);", "lang": "javascript", "label": "async_error"},
    {"code": "if (x == null) { return; }", "lang": "javascript", "label": "condition_error"},
    # JavaScript clean controls
    {"code": "const x = 5;\nconst y = x * 2;\nconsole.log(y);", "lang": "javascript", "label": "none_correct_code"},
    {"code": "async function f() { const r = await fetch('/api'); return r.json(); }", "lang": "javascript", "label": "none_correct_code"},
    {"code": "const arr = [1,2,3]; for (const x of arr) { console.log(x); }", "lang": "javascript", "label": "none_correct_code"},
    {"code": "try { JSON.parse(s); } catch(e) { console.error(e); }", "lang": "javascript", "label": "none_correct_code"},
    {"code": "if (x !== null && x !== undefined) { process(x); }", "lang": "javascript", "label": "none_correct_code"},
    # C defects
    {"code": "void f() {\n    char buf[8];\n    return buf;\n}", "lang": "c", "label": "memory_safety"},
    {"code": "FILE* f = fopen('x','r');\nif (!f) return -1;\n// no fclose", "lang": "c", "label": "resource_leak"},
    {"code": "int *p = malloc(10);\nif (!p) return;\n// no free", "lang": "c", "label": "memory_safety"},
    {"code": "void f(long n) { printf(\"%d\", n); }", "lang": "c", "label": "type_error"},
    {"code": "int arr[5];\nfor(int i=0; i<=5; i++) arr[i]=i;", "lang": "c", "label": "memory_safety"},
    # C clean controls
    {"code": "int add(int a, int b) { return a + b; }", "lang": "c", "label": "none_correct_code"},
    {"code": "FILE* f = fopen('x','r');\nif (!f) return;\nfclose(f);", "lang": "c", "label": "none_correct_code"},
    {"code": "int *p = malloc(10);\nif (!p) return;\nfree(p);", "lang": "c", "label": "none_correct_code"},
    {"code": "void f(int n) { printf(\"%d\", n); }", "lang": "c", "label": "none_correct_code"},
    {"code": "for (int i = 0; i < 5; i++) { arr[i] = i; }", "lang": "c", "label": "none_correct_code"},
    # Novel identifiers (unseen function/variable names)
    {"code": "def zylox_process(qfrm=[]):\n    qfrm.append(99)\n    return qfrm", "lang": "python", "label": "memory_safety"},
    {"code": "try:\n    vanthorpe_load()\nexcept:\n    pass", "lang": "python", "label": "condition_error"},
    {"code": "async def brixler():\n    asyncio.sleep(0.5)", "lang": "python", "label": "async_error"},
    {"code": "int *kraxton = malloc(64);\nif (!kraxton) return;\n// leaked", "lang": "c", "label": "memory_safety"},
    {"code": "void lumvex_log(long total) { printf(\"%d\", total); }", "lang": "c", "label": "type_error"},
    # Clean code resembling defects
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

def load_jsonl(filepath):
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records

def evaluate_predictions(y_true, y_pred, all_taxonomy_classes):
    """Computes comprehensive metrics handling full taxonomy and unseen classes."""
    y_true = [str(y) for y in y_true]
    y_pred = [str(y) for y in y_pred]

    present_in_true = sorted(list(set(y_true)))
    present_in_pred = sorted(list(set(y_pred)))
    all_eval_labels = sorted(list(set(y_true) | set(y_pred)))

    acc = float(accuracy_score(y_true, y_pred))
    macro_p = float(precision_score(y_true, y_pred, labels=all_eval_labels, average="macro", zero_division=0))
    macro_r = float(recall_score(y_true, y_pred, labels=all_eval_labels, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, labels=all_eval_labels, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, labels=all_eval_labels, average="weighted", zero_division=0))

    # Bug detection recall (any defect detected as non-clean)
    bug_true = [1 if y != "none_correct_code" else 0 for y in y_true]
    bug_pred = [1 if y != "none_correct_code" else 0 for y in y_pred]
    bug_total = sum(bug_true)
    tp_bug = sum(1 for t, p in zip(bug_true, bug_pred) if t == 1 and p == 1)
    bug_recall = float(tp_bug / bug_total) if bug_total > 0 else 0.0

    # Clean code false positive rate
    clean_true = [1 if y == "none_correct_code" else 0 for y in y_true]
    clean_total = sum(clean_true)
    fp_clean = sum(1 for t, p in zip(y_true, y_pred) if t == "none_correct_code" and p != "none_correct_code")
    clean_fpr = float(fp_clean / clean_total) if clean_total > 0 else 0.0

    # Unknown / Out-of-groundtruth predictions
    unknown_preds = Counter([p for p in y_pred if p not in present_in_true])
    total_unknown = sum(unknown_preds.values())

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=all_eval_labels)

    # Per-class report
    clf_rep = classification_report(y_true, y_pred, labels=all_eval_labels, zero_division=0, output_dict=True)

    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "bug_recall": round(bug_recall, 4),
        "clean_fpr": round(clean_fpr, 4),
        "total_samples": len(y_true),
        "unknown_predictions_count": total_unknown,
        "unknown_predictions_by_class": dict(unknown_preds),
        "confusion_matrix": cm.tolist(),
        "cm_labels": all_eval_labels,
        "per_class": {
            cls: {
                "precision": round(clf_rep[cls]["precision"], 4),
                "recall": round(clf_rep[cls]["recall"], 4),
                "f1": round(clf_rep[cls]["f1-score"], 4),
                "support": int(clf_rep[cls]["support"])
            }
            for cls in all_eval_labels if cls in clf_rep
        }
    }

def main():
    print("=" * 80)
    print("PATCHPROOF EXPERIMENT K2: CROSS-DATASET GENERALIZATION EVALUATION")
    print("=" * 80)

    # Load models
    baseline_path = "models/bug_detector.joblib"
    h1_path = "models/experiments/experiment_h/candidate_h1_ast_only.joblib"

    print(f"Loading Production Baseline: {baseline_path}...")
    baseline = joblib.load(baseline_path)
    print(f"Loading Candidate H1:        {h1_path}...")
    h1_model = joblib.load(h1_path)

    taxonomy_classes = sorted(list(set(str(c) for c in baseline.classes_)))

    # Load datasets
    print("\nLoading datasets...")
    test_records = load_jsonl("data/processed/test.jsonl")
    robust_records = load_jsonl("data/processed/robust_heldout_test.jsonl")

    # Stratified test subsets
    bigvul_test = [r for r in test_records if r.get("source_dataset") == "big_vul"]
    devign_test = [r for r in test_records if r.get("source_dataset") == "codexglue_devign"]
    csn_test = [r for r in test_records if r.get("source_dataset") == "codesearchnet_controls"]
    synth_test = [r for r in test_records if r.get("source_dataset") == "synthetic_patchproof"]

    dataset_suite = {
        "full_untouched_test": {
            "name": "Full Untouched Test Set",
            "codes": [r["original_code"] for r in test_records],
            "langs": [r["language"] for r in test_records],
            "labels": [r["bug_category"] for r in test_records]
        },
        "big_vul_real_c": {
            "name": "BigVul Real C Vulnerabilities",
            "codes": [r["original_code"] for r in bigvul_test],
            "langs": [r["language"] for r in bigvul_test],
            "labels": [r["bug_category"] for r in bigvul_test]
        },
        "devign_real_c": {
            "name": "CodeXGLUE Devign Real C",
            "codes": [r["original_code"] for r in devign_test],
            "langs": [r["language"] for r in devign_test],
            "labels": [r["bug_category"] for r in devign_test]
        },
        "csn_real_python": {
            "name": "CodeSearchNet Real Clean Python",
            "codes": [r["original_code"] for r in csn_test],
            "langs": [r["language"] for r in csn_test],
            "labels": [r["bug_category"] for r in csn_test]
        },
        "synthetic_test_subsplit": {
            "name": "Synthetic Patchproof Held-Out",
            "codes": [r["original_code"] for r in synth_test],
            "langs": [r["language"] for r in synth_test],
            "labels": [r["bug_category"] for r in synth_test]
        },
        "robust_heldout_synthetic": {
            "name": "Robust Held-Out (Novel JS/Python)",
            "codes": [r["original_code"] for r in robust_records],
            "langs": [r["language"] for r in robust_records],
            "labels": [r["bug_category"] for r in robust_records]
        },
        "novel_benchmark_50": {
            "name": "Novel Benchmark Suite (50 snippets)",
            "codes": [b["code"] for b in BENCHMARK_SUITE],
            "langs": [b["lang"] for b in BENCHMARK_SUITE],
            "labels": [b["label"] for b in BENCHMARK_SUITE]
        }
    }

    # Run predictions
    evaluation_results = {}
    print("\n" + "=" * 90)
    print(f"{'Dataset':30s} | {'System':12s} | {'Acc':>7} | {'MacF1':>7} | {'WgtF1':>7} | {'BugRec':>7} | {'ClnFPR':>7} | {'Unknown':>7}")
    print("-" * 90)

    for ds_key, ds_info in dataset_suite.items():
        codes = ds_info["codes"]
        langs = ds_info["langs"]
        labels = ds_info["labels"]
        n = len(labels)

        # Baseline predictions (TF-IDF directly on raw code)
        base_preds = [str(p) for p in baseline.predict(codes)]
        base_metrics = evaluate_predictions(labels, base_preds, taxonomy_classes)

        # H1 predictions (AST-normalized code)
        h1_norm_codes = [normalize_snippet(c, l)[0] for c, l in zip(codes, langs)]
        h1_preds = [str(p) for p in h1_model.predict(h1_norm_codes)]
        h1_metrics = evaluate_predictions(labels, h1_preds, taxonomy_classes)

        evaluation_results[ds_key] = {
            "name": ds_info["name"],
            "sample_count": n,
            "ground_truth_distribution": dict(Counter(labels)),
            "baseline": base_metrics,
            "candidate_h1": h1_metrics
        }

        print(f"{ds_info['name'][:30]:30s} | {'Baseline':12s} | {base_metrics['accuracy']*100:6.2f}% | {base_metrics['macro_f1']:7.4f} | {base_metrics['weighted_f1']:7.4f} | {base_metrics['bug_recall']*100:6.2f}% | {base_metrics['clean_fpr']*100:6.2f}% | {base_metrics['unknown_predictions_count']:7d}")
        print(f"{'':30s} | {'Candidate H1':12s} | {h1_metrics['accuracy']*100:6.2f}% | {h1_metrics['macro_f1']:7.4f} | {h1_metrics['weighted_f1']:7.4f} | {h1_metrics['bug_recall']*100:6.2f}% | {h1_metrics['clean_fpr']*100:6.2f}% | {h1_metrics['unknown_predictions_count']:7d}")
        print("-" * 90)

    # Save to JSON
    out_dir = "models/experiments/experiment_k"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "phase_k2_cross_dataset.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(evaluation_results, f, indent=2)

    print(f"\nSaved cross-dataset generalization results to: {out_file}")

if __name__ == "__main__":
    main()

