"""
PATCHPROOF Experiment K — Phase K3: Hybrid Fusion Ablation Study
Systematic ablation comparing 5 architectures:
  A. ML-Only Baseline (Candidate H1)
  B. Static-Only Baseline (Deterministic AST rules)
  C. Existing Hybrid Fusion (Rule-first with fixed ML threshold 0.35)
  D. Confidence-Aware Hybrid Fusion (Direct comparison of static vs ML probabilities)
  E. Reliability-Weighted Hybrid Fusion (Static confidence scaled by val-set precision)

Evaluates performance on:
  - All supported classes across test.jsonl (8,353 samples)
  - Rare classes (null_pointer, async_error, resource_leak, condition_error)
  - Previously unseen patterns (50-snippet Novel Benchmark)
  - Adversarial & edge cases (29 generalization tests)
"""

import json
import os
import sys
import joblib
import numpy as np
from collections import Counter, defaultdict
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_i"))
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_f"))

from static_analyzer import StaticAnalyzer
from ast_normalizer import normalize_snippet

# Rule reliability weights derived EXCLUSIVELY on val.jsonl in Phase K1/K2
VAL_RULE_RELIABILITY = {
    "PY_STR_NUM_CONCAT": 0.999,
    "PY_BARE_EXCEPT": 0.980,
    "C_RETURNING_STACK_ADDRESS": 1.000,
    "JS_UNHANDLED_PROMISE": 0.950,
    "JS_MISSING_AWAIT": 0.900,
    "C_PRINTF_STR_SPEC_ON_INT": 0.050,  # Fails on general C printf
    "PY_EXCEPTION_SWALLOWED": 0.050,
    "PY_MUTABLE_DEFAULT": 0.050,
    "C_OFF_BY_ONE_LOOP": 0.050,
    "C_RESOURCE_LEAK_ON_RETURN": 0.050,
}
DEFAULT_RULE_RELIABILITY = 0.10

# Category mapping from static findings to canonical taxonomy
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

# 50-snippet Novel Benchmark
from phase_k2_cross_dataset import BENCHMARK_SUITE

# 29 Generalization / Adversarial Tests
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_j"))
from phase_j5_generalization import GENERALIZATION_TESTS

class FusionArchitectures:
    def __init__(self, h1_model, analyzer, ml_threshold=0.35):
        self.model = h1_model
        self.classes = [str(c) for c in h1_model.classes_]
        self.analyzer = analyzer
        self.ml_threshold = ml_threshold

    def predict_ml_only(self, code: str, lang: str):
        norm_code, _ = normalize_snippet(code, lang)
        probs = self.model.predict_proba([norm_code])[0]
        top_idx = int(np.argmax(probs))
        top_cls = self.classes[top_idx]
        top_prob = float(probs[top_idx])
        if top_cls != "none_correct_code" and top_prob >= self.ml_threshold:
            return top_cls, top_prob
        return "none_correct_code", 1.0 - top_prob if top_cls != "none_correct_code" else top_prob

    def predict_static_only(self, code: str, lang: str):
        findings = self.analyzer.analyze(code, lang)
        if findings:
            top = findings[0]
            cat = CATEGORY_MAP.get(top.category, top.category)
            return cat, top.confidence
        return "none_correct_code", 1.0

    def predict_existing_hybrid(self, code: str, lang: str):
        # Rule-first: any finding overrides ML
        findings = self.analyzer.analyze(code, lang)
        if findings and findings[0].confidence >= 0.85:
            cat = CATEGORY_MAP.get(findings[0].category, findings[0].category)
            return cat, findings[0].confidence
        return self.predict_ml_only(code, lang)

    def predict_confidence_aware(self, code: str, lang: str):
        # Compare raw static confidence vs ML probability
        findings = self.analyzer.analyze(code, lang)
        static_cat = None
        static_conf = 0.0
        if findings:
            static_cat = CATEGORY_MAP.get(findings[0].category, findings[0].category)
            static_conf = findings[0].confidence

        ml_cat, ml_conf = self.predict_ml_only(code, lang)

        if static_cat and static_conf > ml_conf:
            return static_cat, static_conf
        return ml_cat, ml_conf

    def predict_reliability_weighted(self, code: str, lang: str):
        # Scale static confidence by validation empirical precision
        findings = self.analyzer.analyze(code, lang)
        static_cat = None
        weighted_conf = 0.0
        if findings:
            rule_id = findings[0].rule_id
            rel = VAL_RULE_RELIABILITY.get(rule_id, DEFAULT_RULE_RELIABILITY)
            raw_conf = findings[0].confidence
            weighted_conf = raw_conf * rel
            static_cat = CATEGORY_MAP.get(findings[0].category, findings[0].category)

        ml_cat, ml_conf = self.predict_ml_only(code, lang)

        # If static rule is high-reliability and high-confidence, trust it
        if static_cat and weighted_conf >= 0.70 and weighted_conf >= ml_conf:
            return static_cat, weighted_conf
        return ml_cat, ml_conf

def evaluate_predictions(y_true, y_pred):
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    bug_true = [1 if y != "none_correct_code" else 0 for y in y_true]
    bug_pred = [1 if y != "none_correct_code" else 0 for y in y_pred]
    bug_total = sum(bug_true)
    tp_bug = sum(1 for t, p in zip(bug_true, bug_pred) if t == 1 and p == 1)
    bug_recall = float(tp_bug / bug_total) if bug_total > 0 else 0.0

    clean_total = sum(1 for y in y_true if y == "none_correct_code")
    fp_clean = sum(1 for t, p in zip(y_true, y_pred) if t == "none_correct_code" and p != "none_correct_code")
    clean_fpr = float(fp_clean / clean_total) if clean_total > 0 else 0.0

    rep = classification_report(y_true, y_pred, zero_division=0, output_dict=True)
    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "bug_recall": round(bug_recall, 4),
        "clean_fpr": round(clean_fpr, 4),
        "per_class": rep
    }

def main():
    print("=" * 80)
    print("PATCHPROOF EXPERIMENT K3: HYBRID FUSION ABLATION STUDY")
    print("=" * 80)

    # Load components
    h1_path = "models/experiments/experiment_h/candidate_h1_ast_only.joblib"
    h1_model = joblib.load(h1_path)
    analyzer = StaticAnalyzer()
    fusion = FusionArchitectures(h1_model, analyzer, ml_threshold=0.35)

    architectures = [
        ("A_ML_Only",              lambda c, l: fusion.predict_ml_only(c, l)[0]),
        ("B_Static_Only",          lambda c, l: fusion.predict_static_only(c, l)[0]),
        ("C_Existing_Hybrid",      lambda c, l: fusion.predict_existing_hybrid(c, l)[0]),
        ("D_Confidence_Aware",     lambda c, l: fusion.predict_confidence_aware(c, l)[0]),
        ("E_Reliability_Weighted", lambda c, l: fusion.predict_reliability_weighted(c, l)[0]),
    ]

    # Load test dataset
    print("Loading test.jsonl...")
    test_records = []
    with open("data/processed/test.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            test_records.append(json.loads(line))
    test_codes = [r["original_code"] for r in test_records]
    test_langs = [r["language"] for r in test_records]
    test_labels = [r["bug_category"] for r in test_records]

    # Evaluate on Untouched Test Set
    print("\n" + "=" * 80)
    print("1. EVALUATION ON UNTOUCHED TEST SET (8,353 samples)")
    print("=" * 80)
    print(f"{'Architecture':25s} | {'Accuracy':>9} | {'Macro F1':>9} | {'Wgt F1':>9} | {'Bug Recall':>11} | {'Clean FPR':>10}")
    print("-" * 80)

    ablation_test_results = {}
    for arch_name, fn in architectures:
        preds = [fn(c, l) for c, l in zip(test_codes, test_langs)]
        m = evaluate_predictions(test_labels, preds)
        ablation_test_results[arch_name] = m
        print(f"{arch_name:25s} | {m['accuracy']*100:8.2f}% | {m['macro_f1']:9.4f} | {m['weighted_f1']:9.4f} | {m['bug_recall']*100:10.2f}% | {m['clean_fpr']*100:9.2f}%")

    # Evaluate on Rare Classes
    rare_classes = ["null_pointer", "async_error", "resource_leak", "condition_error"]
    print("\n" + "=" * 80)
    print("2. EVALUATION ON RARE DEFECT CLASSES (Test Set)")
    print("=" * 80)
    print(f"{'Architecture':25s} | " + " | ".join([f"{c[:10]:>10}" for c in rare_classes]))
    print("-" * 80)

    rare_results = defaultdict(dict)
    for arch_name, res in ablation_test_results.items():
        row = []
        for c in rare_classes:
            f1 = res["per_class"].get(c, {}).get("f1-score", 0.0)
            rec = res["per_class"].get(c, {}).get("recall", 0.0)
            row.append(f"{f1:.2f}/{rec:.2f}")
            rare_results[arch_name][c] = {"f1": f1, "recall": rec}
        print(f"{arch_name:25s} | " + " | ".join([f"{r:>10}" for r in row]))

    # Evaluate on Novel Benchmark (50 snippets)
    print("\n" + "=" * 80)
    print("3. EVALUATION ON NOVEL BENCHMARK (50 snippets with unseen identifiers)")
    print("=" * 80)
    bench_codes = [b["code"] for b in BENCHMARK_SUITE]
    bench_langs = [b["lang"] for b in BENCHMARK_SUITE]
    bench_labels = [b["label"] for b in BENCHMARK_SUITE]

    ablation_bench_results = {}
    for arch_name, fn in architectures:
        preds = [fn(c, l) for c, l in zip(bench_codes, bench_langs)]
        m = evaluate_predictions(bench_labels, preds)
        ablation_bench_results[arch_name] = m
        print(f"{arch_name:25s} | Acc: {m['accuracy']*100:6.2f}% | Macro F1: {m['macro_f1']:.4f} | Bug Recall: {m['bug_recall']*100:6.2f}% | Clean FPR: {m['clean_fpr']*100:6.2f}%")

    # Evaluate on Adversarial / Edge Cases (Generalization suite)
    print("\n" + "=" * 80)
    print("4. EVALUATION ON ADVERSARIAL & EDGE CASES (29 tests)")
    print("=" * 80)
    flat_tests = []
    for cat, tests in GENERALIZATION_TESTS.items():
        for t in tests:
            t["category_group"] = cat
            flat_tests.append(t)

    gen_codes = [t["code"] for t in flat_tests]
    gen_langs = [t["lang"] for t in flat_tests]
    gen_labels = [t["label"] for t in flat_tests]

    ablation_gen_results = {}
    for arch_name, fn in architectures:
        preds = [fn(c, l) for c, l in zip(gen_codes, gen_langs)]
        m = evaluate_predictions(gen_labels, preds)
        ablation_gen_results[arch_name] = m
        print(f"{arch_name:25s} | Acc: {m['accuracy']*100:6.2f}% ({int(m['accuracy']*len(gen_labels))}/{len(gen_labels)}) | Bug Recall: {m['bug_recall']*100:6.2f}% | Clean FPR: {m['clean_fpr']*100:6.2f}%")

    # Save to JSON
    out_dir = "models/experiments/experiment_k"
    os.makedirs(out_dir, exist_ok=True)
    report = {
        "experiment": "K3",
        "description": "Hybrid Fusion Ablation Study",
        "test_set_ablation": ablation_test_results,
        "rare_classes_ablation": rare_results,
        "novel_benchmark_ablation": ablation_bench_results,
        "adversarial_ablation": ablation_gen_results,
        "validation_rule_reliabilities": VAL_RULE_RELIABILITY
    }
    out_file = os.path.join(out_dir, "phase_k3_fusion_ablation.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved ablation report to: {out_file}")

if __name__ == "__main__":
    main()

