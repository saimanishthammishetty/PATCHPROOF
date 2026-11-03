"""
Phase 0 Investigation: Robust Held-Out 0% Accuracy Audit.
Examines:
1. Prediction counts vs sample counts.
2. Label representations, types, and string equality against model.classes_.
3. Raw code evaluation vs AST-normalized evaluation for all models.
4. Probability distributions, logit margins, and top predicted classes.
5. Detection of silent fallback or default label substitution.
6. Sample-by-sample analysis.
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

def main():
    print("=" * 80)
    print("PHASE 0: ROBUST HELD-OUT DATASET AUDIT & PREDICTION INVESTIGATION")
    print("=" * 80)

    # 1. Load Ground Truth
    rob_path = Path("data/processed/robust_heldout_test.jsonl")
    raw_samples = []
    norm_samples = []
    y_true = []
    templates = []
    langs = []

    with open(rob_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            ex = CodeDebuggingExample.from_jsonl(line)
            raw_samples.append(ex.original_code)
            norm_code, ok = normalize_snippet(ex.original_code, ex.language)
            norm_samples.append(norm_code)
            y_true.append(ex.bug_category)
            templates.append(ex.template_family)
            langs.append(ex.language)

    print(f"Total samples loaded from robust_heldout_test.jsonl: {len(y_true)}")
    print(f"Language distribution: {Counter(langs)}")
    print(f"Ground-truth class distribution: {Counter(y_true)}")
    print(f"Template family distribution: {Counter(templates)}")

    # 2. Load Models
    models = {
        "Baseline (Production)": ("models/bug_detector.joblib", False),
        "Candidate F2 (Staged Ref)": ("models/experiments/experiment_f/candidate_f2_ast_weighted.joblib", True),
        "Candidate G1 (Balanced Recall)": ("models/experiments/experiment_g/candidate_g1_balanced_recall.joblib", True),
        "Candidate G2 (Aggressive Recall)": ("models/experiments/experiment_g/candidate_g2_aggressive_recall.joblib", True),
        "Candidate G3 (Clean Tokens)": ("models/experiments/experiment_g/candidate_g3_clean_tokens.joblib", True),
    }

    loaded_models = {}
    for name, (path, is_ast) in models.items():
        m = joblib.load(path)
        loaded_models[name] = (m, is_ast)

    # 3. Class Mappings & Types Audit
    print("\n" + "=" * 80)
    print("CLASS MAPPINGS & TYPE CONSISTENCY AUDIT")
    print("=" * 80)

    unique_y_true = set(y_true)
    print(f"Ground truth unique classes ({len(unique_y_true)}): {sorted(list(unique_y_true))}")

    for name, (m, is_ast) in loaded_models.items():
        clf = m.named_steps["clf"]
        classes = list(clf.classes_)
        class_types = [type(c).__name__ for c in classes]
        print(f"\nModel: {name}")
        print(f"  Number of classes: {len(classes)}")
        print(f"  Class list: {classes}")
        print(f"  Class types: {set(class_types)}")
        
        # Check if ground truth classes exist in model.classes_
        for gt_cls in unique_y_true:
            match = [c for c in classes if c == gt_cls]
            exact_str_match = [c for c in classes if str(c) == str(gt_cls)]
            print(f"    GT '{gt_cls}' in model.classes_: equality={bool(match)}, str_equality={bool(exact_str_match)}")

    # 4. Pipeline Execution & Prediction Count Audit
    print("\n" + "=" * 80)
    print("PREDICTION COUNTS, RAW VS NORM COMPARISON, AND ACCURACY")
    print("=" * 80)

    for name, (m, is_ast) in loaded_models.items():
        # Evaluate on normalized (intended for AST models)
        preds_norm = m.predict(norm_samples)
        # Evaluate on raw (control)
        preds_raw = m.predict(raw_samples)
        
        # Verify length
        assert len(preds_norm) == len(y_true), f"Mismatch in norm preds count: {len(preds_norm)} vs {len(y_true)}"
        assert len(preds_raw) == len(y_true), f"Mismatch in raw preds count: {len(preds_raw)} vs {len(y_true)}"
        
        # Accuracies
        acc_norm = np.mean([1 if str(p) == str(t) else 0 for p, t in zip(preds_norm, y_true)])
        acc_raw = np.mean([1 if str(p) == str(t) else 0 for p, t in zip(preds_raw, y_true)])
        
        counts_norm = Counter([str(p) for p in preds_norm])
        counts_raw = Counter([str(p) for p in preds_raw])
        
        print(f"\nModel: {name}")
        print(f"  Evaluation on AST-Normalized Code (intended mode for AST models):")
        print(f"    Accuracy: {acc_norm*100:.2f}% ({sum(1 for p, t in zip(preds_norm, y_true) if str(p)==str(t))}/{len(y_true)})")
        print(f"    Predicted class distribution: {counts_norm}")
        print(f"  Evaluation on RAW Unnormalized Code (control mode):")
        print(f"    Accuracy: {acc_raw*100:.2f}% ({sum(1 for p, t in zip(preds_raw, y_true) if str(p)==str(t))}/{len(y_true)})")
        print(f"    Predicted class distribution: {counts_raw}")

    # 5. Probability Analysis & Margin Audit
    print("\n" + "=" * 80)
    print("DETAILED PROBABILITY & MARGIN AUDIT FOR F2 AND G2")
    print("=" * 80)

    f2_m = loaded_models["Candidate F2 (Staged Ref)"][0]
    g2_m = loaded_models["Candidate G2 (Aggressive Recall)"][0]
    base_m = loaded_models["Baseline (Production)"][0]

    # Python type_error slice (indices 0..593)
    # JS async_error slice (indices 594..1225)
    py_indices = [i for i, l in enumerate(langs) if l == "python"]
    js_indices = [i for i, l in enumerate(langs) if l == "javascript"]

    print(f"Python slice: {len(py_indices)} samples (all type_error)")
    print(f"JavaScript slice: {len(js_indices)} samples (all async_error)")

    for slice_name, idx_list, expected_cls in [("Python type_error", py_indices, "type_error"), ("JavaScript async_error", js_indices, "async_error")]:
        print(f"\n--- {slice_name} ({len(idx_list)} samples) ---")
        
        # Test sample 0 in this slice
        s_idx = idx_list[0]
        code_r = raw_samples[s_idx]
        code_n = norm_samples[s_idx]
        
        print(f"Sample #{s_idx} Snippet (Raw):\n{code_r.strip()}")
        print(f"Sample #{s_idx} Snippet (Norm):\n{code_n.strip()}")
        
        # Check probs for Base (on raw)
        base_probs = base_m.predict_proba([code_r])[0]
        base_top = sorted(zip(base_m.classes_, base_probs), key=lambda x: -x[1])[:3]
        print(f"  Baseline (Raw) Top 3: {[(str(c), round(float(p), 4)) for c, p in base_top]}")
        
        # Check probs for F2 (on norm)
        f2_probs_n = f2_m.predict_proba([code_n])[0]
        f2_top_n = sorted(zip(f2_m.classes_, f2_probs_n), key=lambda x: -x[1])[:3]
        print(f"  F2 (Norm) Top 3:      {[(str(c), round(float(p), 4)) for c, p in f2_top_n]}")

        # Check probs for F2 (on raw)
        f2_probs_r = f2_m.predict_proba([code_r])[0]
        f2_top_r = sorted(zip(f2_m.classes_, f2_probs_r), key=lambda x: -x[1])[:3]
        print(f"  F2 (Raw) Top 3:       {[(str(c), round(float(p), 4)) for c, p in f2_top_r]}")

        # Check probs for G2 (on norm)
        g2_probs_n = g2_m.predict_proba([code_n])[0]
        g2_top_n = sorted(zip(g2_m.classes_, g2_probs_n), key=lambda x: -x[1])[:3]
        print(f"  G2 (Norm) Top 3:      {[(str(c), round(float(p), 4)) for c, p in g2_top_n]}")

    # 6. Feature vector sparsity and active vocabulary check
    print("\n" + "=" * 80)
    print("FEATURE VECTOR SPARSITY AUDIT")
    print("=" * 80)
    for model_name, (m, _) in [("Candidate F2", loaded_models["Candidate F2 (Staged Ref)"]), ("Candidate G2", loaded_models["Candidate G2 (Aggressive Recall)"])]:
        vec = m.named_steps["tfidf"]
        sample_py_norm = norm_samples[py_indices[0]]
        sample_js_norm = norm_samples[js_indices[0]]
        
        feats_py = vec.transform([sample_py_norm])
        feats_js = vec.transform([sample_js_norm])
        
        print(f"{model_name}:")
        print(f"  Py norm non-zero features: {feats_py.nnz} / {vec.max_features}")
        print(f"  Py active tokens: {[t for t in vec.build_analyzer()(sample_py_norm) if t in vec.vocabulary_]}")
        print(f"  JS norm non-zero features: {feats_js.nnz} / {vec.max_features}")
        print(f"  JS active tokens: {[t for t in vec.build_analyzer()(sample_js_norm) if t in vec.vocabulary_]}")

if __name__ == "__main__":
    main()

