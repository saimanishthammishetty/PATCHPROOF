"""
Experiment I - Phase 1: Comprehensive Audit of Candidate H1.
Analyzes:
1. Exact predictions and confidence distributions on robust_heldout_test.jsonl.
2. Per-class and per-language metrics.
3. Analysis of dataset-specific structural patterns learned by H1.
4. Confidence margin between none_correct_code and expected defect classes.
"""

import sys
import json
from collections import Counter
from pathlib import Path
import joblib
import numpy as np

sys.path.insert(0, str(Path.cwd()))
from scripts.datasets.schema import CodeDebuggingExample
from scripts.experiments.experiment_f.ast_normalizer import normalize_snippet

def audit_h1():
    print("=" * 80)
    print("PHASE 1: CANDIDATE H1 ROBUST HELD-OUT AUDIT")
    print("=" * 80)

    # 1. Load H1 model
    h1_path = Path("models/experiments/experiment_h/candidate_h1_ast_only.joblib")
    assert h1_path.exists(), f"Candidate H1 not found at {h1_path}"
    model_h1 = joblib.load(h1_path)
    classes = list(model_h1.classes_)
    
    # 2. Load robust held-out dataset
    rob_path = Path("data/processed/robust_heldout_test.jsonl")
    records = []
    with open(rob_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            ex = CodeDebuggingExample.from_jsonl(line)
            records.append(ex)

    print(f"Total samples in robust held-out: {len(records)}")
    
    # 3. Normalize snippets
    X_ast = []
    y_true = []
    langs = []
    templates = []
    for r in records:
        norm_code, _ = normalize_snippet(r.original_code, r.language)
        X_ast.append(norm_code)
        y_true.append(r.bug_category)
        langs.append(r.language)
        templates.append(r.template_family)

    # 4. Predict
    probs = model_h1.predict_proba(X_ast)
    preds = [classes[idx] for idx in np.argmax(probs, axis=1)]
    confs = np.max(probs, axis=1)

    print(f"\nGround Truth Distribution: {Counter(y_true)}")
    print(f"Predicted Distribution:    {Counter(preds)}")
    print(f"Overall Accuracy:          {np.mean([1 if p==t else 0 for p,t in zip(preds, y_true)])*100:.2f}%")

    # 5. Breakdown by Language & Template Family
    for lang in sorted(list(set(langs))):
        idx_lang = [i for i, l in enumerate(langs) if l == lang]
        p_lang = [preds[i] for i in idx_lang]
        t_lang = [y_true[i] for i in idx_lang]
        c_lang = [confs[i] for i in idx_lang]
        print(f"\n--- Language: {lang.upper()} ({len(idx_lang)} samples) ---")
        print(f"  Ground truth: {Counter(t_lang)}")
        print(f"  Predictions:  {Counter(p_lang)}")
        print(f"  Avg Confidence: {np.mean(c_lang)*100:.2f}% (std={np.std(c_lang)*100:.2f}%)")
        print(f"  Min Conf: {np.min(c_lang)*100:.2f}%, Max Conf: {np.max(c_lang)*100:.2f}%")

        # Top 3 classes for this language
        avg_probs = np.mean(probs[idx_lang], axis=0)
        top3 = sorted(zip(classes, avg_probs), key=lambda x: -x[1])[:4]
        print(f"  Mean Class Probabilities:")
        for c_name, c_prob in top3:
            print(f"    {c_name:<20}: {c_prob*100:.2f}%")

    # 6. Inspection of what H1 learned: Top feature weights for none_correct_code, type_error, async_error
    vec = model_h1.named_steps["tfidf"]
    clf = model_h1.named_steps["clf"]
    
    print("\n" + "=" * 80)
    print("TOP POSITIVE FEATURE WEIGHTS FOR KEY CLASSES IN H1")
    print("=" * 80)
    for c_target in ["none_correct_code", "type_error", "async_error", "condition_error", "resource_leak"]:
        c_idx = classes.index(c_target)
        coefs = clf.coef_[c_idx]
        top_idx = np.argsort(coefs)[-10:][::-1]
        feature_names = vec.get_feature_names_out()
        top_feats = [(feature_names[i], round(float(coefs[i]), 3)) for i in top_idx]
        print(f"\nTop 10 features for '{c_target}':")
        for feat, val in top_feats:
            print(f"  {feat:<25}: +{val:.3f}")

if __name__ == "__main__":
    audit_h1()

