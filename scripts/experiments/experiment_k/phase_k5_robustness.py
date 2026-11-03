"""
PATCHPROOF Experiment K — Phase K5: Robustness & Semantic Invariance Study
Evaluates robustness of PATCHPROOF models across systematic transformations:
1. Semantic-Preserving Invariance (Label should NOT change):
   - Whitespace & Formatting (indentation, line breaks, one-liners)
   - Identifier Renaming (alpha-conversion of local variables)
   - Equivalent Syntax Transformations (syntactic sugar, alternate idioms)
   - Misleading Comments & Adversarial Docstrings (deceptive comments)
2. Semantic-Mutating Sensitivity (Label SHOULD change):
   - Removing resource cleanup (free/fclose) -> turns clean into leak
   - Introducing fencepost error (range(len+1)) -> turns clean into boundary defect
   - Stripping await keyword -> turns clean into async defect
   - Adding mutable default argument -> turns clean into state/api defect

Measures Invariance Rate, Sensitivity Rate, and Flip Rates.
"""

import json
import os
import sys
import joblib
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_f"))
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_i"))

from ast_normalizer import normalize_snippet
from static_analyzer import StaticAnalyzer

# Define Base Code Snippets
BASE_SUITE = [
    {
        "id": "c_clean_buffer",
        "code": "void process_data(int count) {\n    int sum = 0;\n    for (int i = 0; i < count; i++) {\n        sum += i;\n    }\n    printf(\"Sum: %d\\n\", sum);\n}",
        "lang": "c",
        "label": "none_correct_code"
    },
    {
        "id": "c_malloc_leak",
        "code": "int* allocate_buffer(size_t size) {\n    int *ptr = (int*)malloc(size * sizeof(int));\n    if (!ptr) return NULL;\n    ptr[0] = 42;\n    return ptr;\n}",
        "lang": "c",
        "label": "none_correct_code"
    },
    {
        "id": "py_clean_iter",
        "code": "def calculate_average(numbers):\n    if not numbers:\n        return 0.0\n    total = 0\n    for n in numbers:\n        total += n\n    return total / len(numbers)",
        "lang": "python",
        "label": "none_correct_code"
    },
    {
        "id": "py_bare_except",
        "code": "def read_config(path):\n    try:\n        with open(path, 'r') as fp:\n            return json.load(fp)\n    except:\n        return None",
        "lang": "python",
        "label": "condition_error"
    },
    {
        "id": "js_clean_async",
        "code": "async function fetchUser(userId) {\n    try {\n        const response = await fetch('/api/users/' + userId);\n        return await response.json();\n    } catch (err) {\n        console.error(err);\n        return null;\n    }\n}",
        "lang": "javascript",
        "label": "none_correct_code"
    },
    {
        "id": "js_missing_await",
        "code": "async function logEvent(name) {\n    fetch('/api/events', { method: 'POST', body: JSON.stringify({ name }) });\n}",
        "lang": "javascript",
        "label": "async_error"
    }
]

# Systematic Transformation Suite
def generate_robustness_testcases():
    testcases = []

    # 1. Formatting & Whitespace (Preserving)
    testcases.append({
        "type": "semantic_preserving",
        "perturbation": "whitespace_indent_tabs",
        "base_id": "c_clean_buffer",
        "lang": "c",
        "expected_label": "none_correct_code",
        "code": "void process_data(int count){\n\tint sum=0;\n\tfor(int i=0;i<count;i++){\n\t\tsum+=i;\n\t}\n\tprintf(\"Sum: %d\\n\",sum);\n}"
    })
    testcases.append({
        "type": "semantic_preserving",
        "perturbation": "whitespace_oneliner",
        "base_id": "py_bare_except",
        "lang": "python",
        "expected_label": "condition_error",
        "code": "def read_config(path):\n    try: open(path)\n    except: return None"
    })

    # 2. Identifier Renaming (Preserving)
    testcases.append({
        "type": "semantic_preserving",
        "perturbation": "identifier_alpha_renaming",
        "base_id": "py_clean_iter",
        "lang": "python",
        "expected_label": "none_correct_code",
        "code": "def compute_tally_metric(unseen_collection_var):\n    if not unseen_collection_var:\n        return 0.0\n    accumulator_val = 0\n    for element_item in unseen_collection_var:\n        accumulator_val += element_item\n    return accumulator_val / len(unseen_collection_var)"
    })
    testcases.append({
        "type": "semantic_preserving",
        "perturbation": "identifier_alpha_renaming",
        "base_id": "c_malloc_leak",
        "lang": "c",
        "expected_label": "none_correct_code",
        "code": "int* acquire_memory_segment(size_t chunk_length) {\n    int *raw_ptr = (int*)malloc(chunk_length * sizeof(int));\n    if (!raw_ptr) return NULL;\n    raw_ptr[0] = 42;\n    return raw_ptr;\n}"
    })

    # 3. Equivalent Syntax Transformations (Preserving)
    testcases.append({
        "type": "semantic_preserving",
        "perturbation": "syntax_expansion",
        "base_id": "c_clean_buffer",
        "lang": "c",
        "expected_label": "none_correct_code",
        "code": "void process_data(int count) {\n    int sum = 0;\n    int i = 0;\n    while (i < count) {\n        sum = sum + i;\n        i = i + 1;\n    }\n    printf(\"Sum: %d\\n\", sum);\n}"
    })
    testcases.append({
        "type": "semantic_preserving",
        "perturbation": "syntax_comprehension",
        "base_id": "py_clean_iter",
        "lang": "python",
        "expected_label": "none_correct_code",
        "code": "def calculate_average(numbers):\n    if len(numbers) == 0:\n        return 0.0\n    return sum(n for n in numbers) / float(len(numbers))"
    })

    # 4. Misleading Comments & Adversarial Docstrings (Preserving)
    testcases.append({
        "type": "semantic_preserving",
        "perturbation": "misleading_safe_comment",
        "base_id": "py_bare_except",
        "lang": "python",
        "expected_label": "condition_error",
        "code": "# AUDITED AND CERTIFIED 100% BUG FREE AND SAFE\n# NO EXCEPTIONS CAN POSSIBLY OCCUR HERE\ndef read_config(path):\n    try:\n        with open(path, 'r') as fp:\n            return json.load(fp)\n    except:\n        return None"
    })
    testcases.append({
        "type": "semantic_preserving",
        "perturbation": "misleading_vulnerable_comment",
        "base_id": "c_clean_buffer",
        "lang": "c",
        "expected_label": "none_correct_code",
        "code": "// WARNING: CRITICAL BUFFER OVERFLOW AND MEMORY CORRUPTION IN THIS FUNCTION\n// CVE-2024-99999\nvoid process_data(int count) {\n    int sum = 0;\n    for (int i = 0; i < count; i++) {\n        sum += i;\n    }\n    printf(\"Sum: %d\\n\", sum);\n}"
    })

    # 5. Semantic Mutating Transformations (Label SHOULD CHANGE to defect)
    testcases.append({
        "type": "semantic_mutating",
        "perturbation": "leak_injection",
        "base_id": "c_clean_buffer",
        "lang": "c",
        "expected_label": "memory_safety",
        "code": "void process_data(int count) {\n    char *heap_buf = (char*)malloc(1024);\n    int sum = 0;\n    for (int i = 0; i < count; i++) {\n        sum += i;\n    }\n    printf(\"Sum: %d\\n\", sum);\n    // heap_buf leaked without free\n}"
    })
    testcases.append({
        "type": "semantic_mutating",
        "perturbation": "boundary_inversion",
        "base_id": "c_clean_buffer",
        "lang": "c",
        "expected_label": "condition_error",
        "code": "void process_data(int count) {\n    int sum = 0;\n    int arr[10];\n    for (int i = 0; i <= 10; i++) {\n        arr[i] = i;\n    }\n    printf(\"Done\\n\");\n}"
    })
    testcases.append({
        "type": "semantic_mutating",
        "perturbation": "mutable_default_injection",
        "base_id": "py_clean_iter",
        "lang": "python",
        "expected_label": "type_error",
        "code": "def calculate_average(numbers, cache=[]):\n    cache.append(numbers)\n    if not numbers:\n        return 0.0\n    return sum(numbers) / len(numbers)"
    })
    testcases.append({
        "type": "semantic_mutating",
        "perturbation": "await_removal",
        "base_id": "js_clean_async",
        "lang": "javascript",
        "expected_label": "async_error",
        "code": "async function fetchUser(userId) {\n    const response = fetch('/api/users/' + userId);\n    return response.json();\n}"
    })

    return testcases

def main():
    print("=" * 80)
    print("PATCHPROOF EXPERIMENT K5: ROBUSTNESS & INVARIANCE AUDIT")
    print("=" * 80)

    # Load Baseline and Candidate H1
    baseline = joblib.load("models/bug_detector.joblib")
    h1_model = joblib.load("models/experiments/experiment_h/candidate_h1_ast_only.joblib")
    classes = [str(c) for c in h1_model.classes_]

    testcases = generate_robustness_testcases()
    print(f"Loaded {len(testcases)} controlled transformation test cases.")

    results = []
    preserving_correct_base = 0
    preserving_correct_h1 = 0
    preserving_total = 0

    mutating_detected_base = 0
    mutating_detected_h1 = 0
    mutating_total = 0

    print("\n" + "=" * 90)
    print(f"{'Perturbation':30s} | {'Lang':4s} | {'Exp Label':17s} | {'Base Pred':15s} | {'H1 Pred':15s} | Status")
    print("-" * 90)

    for tc in testcases:
        code = tc["code"]
        lang = tc["lang"]
        exp = tc["expected_label"]
        p_type = tc["type"]
        pert = tc["perturbation"]

        # Baseline prediction
        base_pred = str(baseline.predict([code])[0])

        # H1 prediction
        norm_code, _ = normalize_snippet(code, lang)
        h1_probs = h1_model.predict_proba([norm_code])[0]
        top_idx = int(np.argmax(h1_probs))
        top_prob = float(h1_probs[top_idx])
        h1_raw = classes[top_idx]
        h1_pred = h1_raw if h1_raw != "none_correct_code" and top_prob >= 0.35 else "none_correct_code"

        base_match = (base_pred == exp)
        h1_match = (h1_pred == exp)

        if p_type == "semantic_preserving":
            preserving_total += 1
            if base_match: preserving_correct_base += 1
            if h1_match: preserving_correct_h1 += 1
            status = f"H1: {'PASS' if h1_match else 'FLIP'}, Base: {'PASS' if base_match else 'FLIP'}"
        else:
            mutating_total += 1
            # For mutating, detecting defect (any non-clean prediction or matching expected)
            base_detected = (base_pred != "none_correct_code")
            h1_detected = (h1_pred != "none_correct_code")
            if base_detected: mutating_detected_base += 1
            if h1_detected: mutating_detected_h1 += 1
            status = f"Mutated -> H1 Bug: {'YES' if h1_detected else 'MISSED'}, Base Bug: {'YES' if base_detected else 'MISSED'}"

        print(f"{pert[:30]:30s} | {lang:4s} | {exp[:17]:17s} | {base_pred[:15]:15s} | {h1_pred[:15]:15s} | {status}")

        results.append({
            "perturbation": pert,
            "type": p_type,
            "language": lang,
            "expected_label": exp,
            "baseline_prediction": base_pred,
            "h1_prediction": h1_pred,
            "h1_top_probability": round(top_prob, 4),
            "h1_raw_class": h1_raw,
            "baseline_match": base_match,
            "h1_match": h1_match
        })

    base_invariance = preserving_correct_base / preserving_total if preserving_total > 0 else 0
    h1_invariance = preserving_correct_h1 / preserving_total if preserving_total > 0 else 0
    base_sensitivity = mutating_detected_base / mutating_total if mutating_total > 0 else 0
    h1_sensitivity = mutating_detected_h1 / mutating_total if mutating_total > 0 else 0

    print("\n" + "=" * 80)
    print("ROBUSTNESS SUMMARY METRICS")
    print("=" * 80)
    print(f"Semantic-Preserving Invariance Rate (Higher is better):")
    print(f"  Production Baseline: {base_invariance*100:6.2f}% ({preserving_correct_base}/{preserving_total})")
    print(f"  Candidate H1:        {h1_invariance*100:6.2f}% ({preserving_correct_h1}/{preserving_total})")
    print(f"\nSemantic-Mutating Sensitivity Rate (Higher is better):")
    print(f"  Production Baseline: {base_sensitivity*100:6.2f}% ({mutating_detected_base}/{mutating_total})")
    print(f"  Candidate H1:        {h1_sensitivity*100:6.2f}% ({mutating_detected_h1}/{mutating_total})")

    # Save to JSON
    out_dir = "models/experiments/experiment_k"
    os.makedirs(out_dir, exist_ok=True)
    report = {
        "experiment": "K5",
        "description": "Robustness, Invariance & Sensitivity Evaluation",
        "summary": {
            "semantic_preserving_invariance_rate": {
                "baseline": round(base_invariance, 4),
                "candidate_h1": round(h1_invariance, 4)
            },
            "semantic_mutating_sensitivity_rate": {
                "baseline": round(base_sensitivity, 4),
                "candidate_h1": round(h1_sensitivity, 4)
            }
        },
        "testcases": results
    }

    out_file = os.path.join(out_dir, "phase_k5_robustness.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved robustness report to: {out_file}")

if __name__ == "__main__":
    main()

