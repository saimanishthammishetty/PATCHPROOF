import sys
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path.cwd()))
from scripts.benchmark_novel_eval import BENCHMARK_SUITE
from scripts.experiments.experiment_i.static_analyzer import StaticAnalyzer

def test_benchmark():
    print("=" * 80)
    print("TESTING STATIC ANALYZER ON 50-SNIPPET BENCHMARK SUITE")
    print("=" * 80)
    
    tp = 0
    fp = 0
    fn = 0
    clean_total = 0
    clean_fa = 0
    by_rule = Counter()
    by_cat = Counter()
    
    for case in BENCHMARK_SUITE:
        code = case["code"]
        lang = case["lang"]
        expected = case["expected_cat"]
        case_id = case["id"]
        is_clean = (expected == "none_correct_code")
        
        findings = StaticAnalyzer.analyze(code, lang)
        
        if is_clean:
            clean_total += 1
            if findings:
                clean_fa += 1
                print(f"[FALSE ALARM] Clean snippet '{case_id}' flagged by {findings[0].rule_id} as {findings[0].category}")
        else:
            if findings:
                # Top finding
                pred_cat = findings[0].category
                by_rule[findings[0].rule_id] += 1
                by_cat[pred_cat] += 1
                if pred_cat == expected:
                    tp += 1
                    print(f"[HIT] {case_id} ({lang}): {pred_cat} by {findings[0].rule_id}")
                else:
                    fp += 1
                    print(f"[MISMATCH] {case_id} ({lang}): Expected {expected}, got {pred_cat} by {findings[0].rule_id}")
            else:
                fn += 1
                # print(f"[MISSED] {case_id} ({lang}): Expected {expected} (No static rule triggered)")

    print(f"\nBenchmark 50 Static Analyzer Results:")
    print(f"  Clean Snippets Evaluated: {clean_total}")
    print(f"  Clean False Alarms:       {clean_fa} (FPR: {clean_fa/clean_total*100:.1f}%)")
    print(f"  Defect Cases Triggered:   {tp + fp} / 35")
    print(f"  Exact Matches (TP):       {tp}")
    print(f"  Mismatches (FP):          {fp}")
    print(f"  Missed Defects (FN):      {fn}")
    print(f"  Rules Triggered:          {dict(by_rule)}")

def test_robust_heldout():
    print("\n" + "=" * 80)
    print("TESTING STATIC ANALYZER ON 1,226-RECORD ROBUST HELDOUT DATASET")
    print("=" * 80)
    
    rob_path = Path("data/processed/robust_heldout_test.jsonl")
    correct = 0
    total = 0
    by_cat_hits = Counter()
    by_rule_hits = Counter()
    
    with open(rob_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            total += 1
            d = json.loads(line)
            code = d["original_code"]
            lang = d["language"]
            expected = d["bug_category"]
            
            findings = StaticAnalyzer.analyze(code, lang)
            if findings:
                pred = findings[0].category
                if pred == expected:
                    correct += 1
                    by_cat_hits[pred] += 1
                    by_rule_hits[findings[0].rule_id] += 1

    print(f"Total Robust Samples: {total}")
    print(f"Correct Detections:   {correct} / {total} ({correct/total*100:.2f}%)")
    print(f"Detections by Cat:    {dict(by_cat_hits)}")
    print(f"Detections by Rule:   {dict(by_rule_hits)}")

if __name__ == "__main__":
    test_benchmark()
    test_robust_heldout()

