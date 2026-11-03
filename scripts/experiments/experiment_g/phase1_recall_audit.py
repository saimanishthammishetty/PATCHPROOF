import sys
import json
from pathlib import Path
import joblib
import numpy as np

sys.path.insert(0, str(Path.cwd()))
from scripts.benchmark_novel_eval import BENCHMARK_SUITE
from scripts.experiments.experiment_f.ast_normalizer import normalize_snippet

base_model = joblib.load("models/bug_detector.joblib")
f2_model = joblib.load("models/experiments/experiment_f/candidate_f2_ast_weighted.joblib")

print("="*80)
print("PHASE 1: SAMPLE-BY-SAMPLE BENCHMARK COMPARISON (BASELINE vs CANDIDATE F2)")
print("="*80)

f2_missed_bugs = []
baseline_wins = []
f2_wins = []
both_missed = []
both_correct = []

for idx, c in enumerate(BENCHMARK_SUITE):
    code_raw = c["code"]
    lang = c["lang"]
    expected = c["expected_cat"]
    case_id = c["id"]
    
    # Baseline raw prediction
    base_pred = base_model.predict([code_raw])[0]
    base_prob = base_model.predict_proba([code_raw])[0]
    base_classes = list(base_model.classes_)
    base_conf = float(np.max(base_prob))
    
    # F2 AST normalized prediction
    code_norm, norm_ok = normalize_snippet(code_raw, lang)
    f2_pred = f2_model.predict([code_norm])[0]
    f2_prob = f2_model.predict_proba([code_norm])[0]
    f2_classes = list(f2_model.classes_)
    f2_conf = float(np.max(f2_prob))
    
    is_base_correct = (base_pred == expected)
    is_f2_correct = (f2_pred == expected)
    is_bug = (expected != "none_correct_code")
    
    # Top 3 probabilities for F2
    top3_idx = np.argsort(f2_prob)[-3:][::-1]
    f2_top3 = [(f2_classes[i], round(float(f2_prob[i]), 4)) for i in top3_idx]
    
    # none_correct_code prob for F2
    none_idx = f2_classes.index("none_correct_code")
    f2_none_prob = round(float(f2_prob[none_idx]), 4)
    
    # expected prob for F2
    exp_idx = f2_classes.index(expected) if expected in f2_classes else -1
    f2_exp_prob = round(float(f2_prob[exp_idx]), 4) if exp_idx != -1 else 0.0
    
    info = {
        "id": case_id,
        "lang": lang,
        "expected": expected,
        "base_pred": base_pred,
        "base_conf": round(base_conf, 4),
        "f2_pred": f2_pred,
        "f2_conf": round(f2_conf, 4),
        "f2_none_prob": f2_none_prob,
        "f2_exp_prob": f2_exp_prob,
        "f2_top3": f2_top3,
        "norm_applied": norm_ok and (code_norm != code_raw),
        "code_snippet": code_raw.strip()
    }
    
    if is_bug and not is_f2_correct:
        f2_missed_bugs.append(info)
        
    if is_base_correct and not is_f2_correct:
        baseline_wins.append(info)
    elif not is_base_correct and is_f2_correct:
        f2_wins.append(info)
    elif is_base_correct and is_f2_correct:
        both_correct.append(info)
    else:
        both_missed.append(info)

print(f"\nSummary of 50 Benchmark Cases:")
print(f"  Both Correct:    {len(both_correct)}")
print(f"  F2 Wins:         {len(f2_wins)} (Cases F2 fixed that Baseline got wrong)")
print(f"  Baseline Wins:   {len(baseline_wins)} (Cases Baseline got right that F2 missed)")
print(f"  Both Missed:     {len(both_missed)}")
print(f"  Total Bugs Missed by F2: {len(f2_missed_bugs)} (out of 35 bug cases -> F2 recall = {(35 - len(f2_missed_bugs))/35*100:.1f}%)")

print("\n" + "="*80)
print(f"CASES WHERE BASELINE WAS CORRECT BUT F2 FAILED ({len(baseline_wins)} cases)")
print("="*80)
for w in baseline_wins:
    print(f"\n[{w['id']}] ({w['lang']}) Expected: {w['expected']}")
    print(f"  Baseline: {w['base_pred']} (conf={w['base_conf']:.2%}) -> PASS")
    print(f"  F2:       {w['f2_pred']} (conf={w['f2_conf']:.2%}) -> FAIL")
    print(f"  F2 Probs: Expected={w['f2_exp_prob']:.2%}, NoneCorrect={w['f2_none_prob']:.2%}")
    print(f"  F2 Top 3: {w['f2_top3']}")
    print(f"  Snippet:\n{w['code_snippet']}")

print("\n" + "="*80)
print(f"CASES WHERE F2 WAS CORRECT BUT BASELINE FAILED ({len(f2_wins)} cases)")
print("="*80)
for w in f2_wins:
    print(f"\n[{w['id']}] ({w['lang']}) Expected: {w['expected']}")
    print(f"  Baseline: {w['base_pred']} (conf={w['base_conf']:.2%}) -> FAIL")
    print(f"  F2:       {w['f2_pred']} (conf={w['f2_conf']:.2%}) -> PASS")
    print(f"  Snippet:\n{w['code_snippet']}")

print("\n" + "="*80)
print(f"ALL 11 DEFECTS MISSED BY CANDIDATE F2 ({len(f2_missed_bugs)} cases)")
print("="*80)
by_lang = {}
by_class = {}
for m in f2_missed_bugs:
    by_lang[m['lang']] = by_lang.get(m['lang'], 0) + 1
    by_class[m['expected']] = by_class.get(m['expected'], 0) + 1
    print(f"  [{m['id']:<12}] Lang: {m['lang']:<10} Expected: {m['expected']:<20} F2 Predicted: {m['f2_pred']:<20} (none_prob={m['f2_none_prob']:.2%}, exp_prob={m['f2_exp_prob']:.2%})")

print(f"\nMissed by Language: {by_lang}")
print(f"Missed by Category: {by_class}")

