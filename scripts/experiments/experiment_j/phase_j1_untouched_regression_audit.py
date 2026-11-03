"""
Phase J1: Untouched Test Regression Investigation.
Analyzes the 2.74 percentage-point drop between Baseline (42.97%) and Hybrid (40.23%) on the 8,353 untouched test records.
"""

import sys
import json
from pathlib import Path
from collections import Counter
import numpy as np

sys.path.insert(0, str(Path.cwd()))
from scripts.datasets.schema import CodeDebuggingExample
from scripts.experiments.experiment_i.static_analyzer import StaticAnalyzer

def main():
    print("=" * 80)
    print("PHASE J1: UNTOUCHED TEST SET (8,353 RECORDS) REGRESSION AUDIT")
    print("=" * 80)

    # 1. Load Experiment I Results
    res_path = Path("models/experiments/experiment_i/experiment_i_results.json")
    assert res_path.exists(), f"Experiment I results missing at {res_path}"
    with open(res_path, "r", encoding="utf-8") as f:
        exp_i = json.load(f)

    # Load test ground truth
    test_path = Path("data/processed/test.jsonl")
    records = []
    with open(test_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            records.append(CodeDebuggingExample.from_jsonl(line))
            
    y_true = [r.bug_category for r in records]
    langs = [r.language for r in records]
    codes = [r.original_code for r in records]
    n_samples = len(y_true)
    print(f"Total Untouched Test Records: {n_samples}")
    print(f"Class Support in Test Set: {Counter(y_true)}")
    print(f"Language Distribution:     {Counter(langs)}")

    # Extract predictions from Experiment I
    preds_base = exp_i["untouched_test_8353"]["Baseline (Production)"]["predictions"]
    preds_h1 = exp_i["untouched_test_8353"]["Candidate H1 (ML-Only)"]["predictions"]
    preds_static = exp_i["untouched_test_8353"]["Static-Only Engine"]["predictions"]
    preds_hybrid = exp_i["untouched_test_8353"]["Hybrid Engine (Experiment I)"]["predictions"]

    acc_base = np.mean([1 if p == t else 0 for p, t in zip(preds_base, y_true)])
    acc_h1 = np.mean([1 if p == t else 0 for p, t in zip(preds_h1, y_true)])
    acc_static = np.mean([1 if p == t else 0 for p, t in zip(preds_static, y_true)])
    acc_hybrid = np.mean([1 if p == t else 0 for p, t in zip(preds_hybrid, y_true)])

    print(f"\nOverall Accuracies:")
    print(f"  Baseline (Production):        {acc_base*100:.2f}% ({sum(1 for p,t in zip(preds_base, y_true) if p==t)}/{n_samples})")
    print(f"  Candidate H1 (ML-Only):       {acc_h1*100:.2f}% ({sum(1 for p,t in zip(preds_h1, y_true) if p==t)}/{n_samples})")
    print(f"  Static-Only Engine:           {acc_static*100:.2f}% ({sum(1 for p,t in zip(preds_static, y_true) if p==t)}/{n_samples})")
    print(f"  Hybrid Engine (Experiment I): {acc_hybrid*100:.2f}% ({sum(1 for p,t in zip(preds_hybrid, y_true) if p==t)}/{n_samples})")
    print(f"  Regression (Base - Hybrid):   {(acc_base - acc_hybrid)*100:.2f}% ({sum(1 for p,t in zip(preds_base, y_true) if p==t) - sum(1 for p,t in zip(preds_hybrid, y_true) if p==t)} samples)")

    # 2. Per-Class Accuracy and Correct Counts Breakdown
    classes = sorted(list(set(y_true)))
    print("\n" + "=" * 90)
    print(f"{'Class':<22} | {'Support':<8} | {'Base Acc (Corr)':<17} | {'Hyb Acc (Corr)':<17} | {'Delta (Hyb - Base)':<18}")
    print("=" * 90)
    
    delta_by_class = {}
    for cls in classes:
        idx_cls = [i for i, t in enumerate(y_true) if t == cls]
        supp = len(idx_cls)
        c_base = sum(1 for i in idx_cls if preds_base[i] == cls)
        c_hyb = sum(1 for i in idx_cls if preds_hybrid[i] == cls)
        
        acc_b = c_base / supp if supp > 0 else 0.0
        acc_h = c_hyb / supp if supp > 0 else 0.0
        diff = c_hyb - c_base
        delta_by_class[cls] = diff
        diff_str = f"{diff:+d} ({(acc_h - acc_b)*100:+.2f}%)"
        print(f"{cls:<22} | {supp:<8} | {acc_b*100:5.2f}% ({c_base:5d}) | {acc_h*100:5.2f}% ({c_hyb:5d}) | {diff_str:<18}")

    print("\nTop Classes Driving Regression (Most Negative Delta):")
    for cls, d in sorted(delta_by_class.items(), key=lambda x: x[1]):
        if d < 0:
            print(f"  {cls:<22}: {d:+d} net correct samples")

    # 3. Identify Root Cause: Is Static Rule Firing Incorrectly or ML Failing?
    print("\n" + "=" * 90)
    print("ANALYSIS OF DISAGREEMENT CASES: BASELINE CORRECT vs HYBRID INCORRECT")
    print("=" * 90)
    
    # Cases where Baseline was correct but Hybrid was wrong
    base_win_indices = [i for i in range(n_samples) if preds_base[i] == y_true[i] and preds_hybrid[i] != y_true[i]]
    print(f"Total samples where Baseline was CORRECT and Hybrid was WRONG: {len(base_win_indices)}")

    # What did Static-Only predict on these cases?
    static_on_base_wins = Counter([preds_static[i] for i in base_win_indices])
    h1_on_base_wins = Counter([preds_h1[i] for i in base_win_indices])
    hybrid_on_base_wins = Counter([preds_hybrid[i] for i in base_win_indices])
    
    print(f"Ground truth of Baseline wins: {Counter([y_true[i] for i in base_win_indices])}")
    print(f"What Hybrid predicted on these: {hybrid_on_base_wins}")
    print(f"What Static predicted on these: {static_on_base_wins}")
    print(f"What H1 (ML) predicted on these: {h1_on_base_wins}")

    # Inspect sample disagreements
    print("\nSample Baseline-Win Disagreements (first 5):")
    for i in base_win_indices[:5]:
        r = records[i]
        print(f"\n[Sample #{i}] Lang: {r.language}, True Class: {r.bug_category}")
        print(f"  Baseline: {preds_base[i]} -> CORRECT")
        print(f"  Static:   {preds_static[i]}")
        print(f"  H1 (ML):  {preds_h1[i]}")
        print(f"  Hybrid:   {preds_hybrid[i]} -> WRONG")
        print(f"  Snippet:\n{r.original_code.strip()[:200]}")

    # Cases where Hybrid was correct but Baseline was wrong
    hyb_win_indices = [i for i in range(n_samples) if preds_hybrid[i] == y_true[i] and preds_base[i] != y_true[i]]
    print(f"\nTotal samples where Hybrid was CORRECT and Baseline was WRONG: {len(hyb_win_indices)}")
    print(f"Ground truth of Hybrid wins: {Counter([y_true[i] for i in hyb_win_indices])}")

if __name__ == "__main__":
    main()

