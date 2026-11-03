"""
Phase J5: Generalization Testing.
Tests Experiment J Hybrid against adversarial patterns:
  - Novel identifiers never seen in training
  - Different code formatting/indentation styles
  - Nested / complex expressions
  - Adversarial clean code resembling real bugs
Reports per-pattern accuracy and failure modes.
"""
import json
import sys
import os
import joblib
import numpy as np

sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_i"))
sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_f"))

from static_analyzer import StaticAnalyzer
from sklearn.metrics import accuracy_score, f1_score

try:
    from ast_normalizer import normalize_snippet
except ImportError:
    def normalize_snippet(code, lang): return code, {}

analyzer = StaticAnalyzer()
h1_model = joblib.load("models/experiments/experiment_h/candidate_h1_ast_only.joblib")
h1_classes = list(h1_model.classes_)

with open("models/experiments/experiment_j/optimal_config.json") as f:
    opt_cfg = json.load(f)
THRESHOLD = opt_cfg["optimal_ml_threshold"]

STATIC_CAT_MAP = {
    "api_misuse": "type_error", "exception_handling": "condition_error",
    "type_error": "type_error", "memory_safety": "memory_safety",
    "resource_leak": "resource_leak", "null_pointer": "null_pointer",
    "async_error": "async_error", "condition_error": "condition_error",
    "none_correct_code": "none_correct_code",
}
H1_CAT_MAP = {
    "api_misuse": "type_error", "exception_handling": "condition_error",
    "loop_error": "condition_error", "off_by_one": "condition_error",
    "state_management": "memory_safety", "undefined_behavior": "memory_safety",
    "async_error": "async_error", "condition_error": "condition_error",
    "memory_safety": "memory_safety", "none_correct_code": "none_correct_code",
    "null_pointer": "null_pointer", "resource_leak": "resource_leak",
    "type_error": "type_error",
}

def predict(code, lang):
    findings = analyzer.analyze(code, lang)
    if findings and findings[0].confidence >= 0.85:
        return STATIC_CAT_MAP.get(findings[0].category, findings[0].category)
    norm_code, _ = normalize_snippet(code, lang)
    probs = h1_model.predict_proba([norm_code])[0]
    top_idx = np.argmax(probs)
    top_cls = h1_classes[top_idx]
    top_prob = probs[top_idx]
    mapped = H1_CAT_MAP.get(top_cls, top_cls)
    if mapped != "none_correct_code" and top_prob >= THRESHOLD:
        return mapped
    return "none_correct_code"

GENERALIZATION_TESTS = {
    "novel_identifiers": [
        # Novel function/variable names completely unseen in training
        {"code": "def zr9x_proc(wqlf=[]):\n    wqlf.append(42)\n    return wqlf", "lang": "python", "label": "memory_safety", "desc": "mutable default, random names"},
        {"code": "try:\n    bvntx_load()\nexcept:\n    pass", "lang": "python", "label": "condition_error", "desc": "bare except, random func name"},
        {"code": "async def qplmk():\n    asyncio.sleep(0.1)", "lang": "python", "label": "async_error", "desc": "missing await, random name"},
        {"code": "void flvrx_report(long n) { printf(\"%d\", n); }", "lang": "c", "label": "type_error", "desc": "format mismatch, random func"},
        {"code": "int *qxtbr = malloc(32);\nif (!qxtbr) return;\n// leaked", "lang": "c", "label": "memory_safety", "desc": "malloc leak, random var"},
        {"code": "def jkpvz(a, b):\n    return a + b", "lang": "python", "label": "none_correct_code", "desc": "clean add, random names"},
        {"code": "FILE *grvth = fopen(path, 'rb');\nif (grvth) { use(grvth); fclose(grvth); }", "lang": "c", "label": "none_correct_code", "desc": "clean fopen/fclose, random names"},
    ],
    "formatting_variants": [
        # Different indentation, no newlines, extra whitespace
        {"code": "def f(x=[]): x.append(1); return x", "lang": "python", "label": "memory_safety", "desc": "mutable default, one-liner"},
        {"code": "try:\n        open('f')\nexcept:\n        pass", "lang": "python", "label": "condition_error", "desc": "bare except, 8-space indent"},
        {"code": "int add(int a,int b){return a+b;}", "lang": "c", "label": "none_correct_code", "desc": "clean C, no spaces"},
        {"code": "void  f( long  n )  {  printf( \"%d\" , n ) ;  }", "lang": "c", "label": "type_error", "desc": "format mismatch, extra spaces"},
        {"code": "async function  fetchData ( )  {\n  return  fetch('/api') ;\n}", "lang": "javascript", "label": "async_error", "desc": "missing await, extra spaces"},
        {"code": "const   ok = async () => { const r = await fetch('/x'); return r.json(); };", "lang": "javascript", "label": "none_correct_code", "desc": "clean async, extra spaces"},
    ],
    "nested_expressions": [
        # Deeply nested / complex expressions
        {"code": "def f(x=None):\n    if x is None:\n        x = []\n    def inner(y=[]):\n        y.append(x)\n        return y\n    return inner", "lang": "python", "label": "memory_safety", "desc": "mutable default in nested function"},
        {"code": "try:\n    try:\n        risky()\n    except TypeError:\n        pass\nexcept:\n    pass", "lang": "python", "label": "condition_error", "desc": "nested try, outer bare except"},
        {"code": "int *p = (int*)malloc(sizeof(int)*n);\nif (p) {\n    for(int i=0;i<n;i++) p[i]=i;\n    // forgot free\n    return 0;\n}", "lang": "c", "label": "memory_safety", "desc": "malloc in block, no free"},
        {"code": "async function chain() {\n  return fetch('/a').then(r => fetch('/b/' + r.id));\n}", "lang": "javascript", "label": "async_error", "desc": "chained fetch, no await, no catch"},
        {"code": "def safe_nested():\n    try:\n        with open('f') as fp:\n            return fp.read()\n    except IOError as e:\n        return str(e)", "lang": "python", "label": "none_correct_code", "desc": "clean nested try+with"},
    ],
    "adversarial_clean": [
        # Clean code that structurally resembles bugs
        {"code": "def f(items=None):\n    if items is None:\n        items = []\n    items.append(1)\n    return items", "lang": "python", "label": "none_correct_code", "desc": "None-guarded mutable default (correct pattern)"},
        {"code": "try:\n    x = int(s)\nexcept (ValueError, TypeError) as e:\n    log(e)\n    x = 0", "lang": "python", "label": "none_correct_code", "desc": "specific exception caught and logged"},
        {"code": "int *p = malloc(n);\nif (!p) return -1;\nuse(p);\nfree(p);\nreturn 0;", "lang": "c", "label": "none_correct_code", "desc": "malloc with check, use and free"},
        {"code": "FILE *f = fopen(path,'r');\nif (!f) { perror(path); return -1; }\nread_file(f);\nfclose(f);\nreturn 0;", "lang": "c", "label": "none_correct_code", "desc": "fopen with error check and fclose"},
        {"code": "void log_count(int n) { printf(\"%d items\\n\", n); }", "lang": "c", "label": "none_correct_code", "desc": "printf %d with int (correct)"},
        {"code": "async function safe() {\n  try {\n    const r = await fetch('/api');\n    return await r.json();\n  } catch(e) { return null; }\n}", "lang": "javascript", "label": "none_correct_code", "desc": "await with try/catch"},
    ],
    "language_boundary": [
        # Edge cases at language boundaries
        {"code": "x: int = 'hello'", "lang": "python", "label": "type_error", "desc": "type annotation mismatch"},
        {"code": "def f() -> int:\n    return 'string'", "lang": "python", "label": "type_error", "desc": "return type mismatch"},
        {"code": "const x: number = 'hello';", "lang": "javascript", "label": "type_error", "desc": "TS type mismatch (JS tokenizer)"},
        {"code": "uint8_t buf[256];\nmemcpy(buf, src, 512);", "lang": "c", "label": "memory_safety", "desc": "memcpy overflow"},
        {"code": "char *s = NULL;\nstrlen(s);", "lang": "c", "label": "null_pointer", "desc": "null deref strlen"},
    ],
}

results_by_category = {}
all_preds = []
all_labels = []

for category, tests in GENERALIZATION_TESTS.items():
    print(f"\n{'='*60}")
    print(f"Category: {category.upper()} ({len(tests)} tests)")
    print(f"{'='*60}")
    cat_preds = []
    cat_labels = []
    for t in tests:
        pred = predict(t["code"], t["lang"])
        correct = "PASS" if pred == t["label"] else "FAIL"
        print(f"  {correct} [{t['lang']:12s}] {t['desc']}")
        print(f"    Expected: {t['label']:20s}  Got: {pred}")
        cat_preds.append(pred)
        cat_labels.append(t["label"])
        all_preds.append(pred)
        all_labels.append(t["label"])

    cat_acc = sum(1 for p, l in zip(cat_preds, cat_labels) if p == l) / len(cat_labels)
    results_by_category[category] = {
        "n": len(tests),
        "accuracy": round(cat_acc, 4),
        "correct": sum(1 for p, l in zip(cat_preds, cat_labels) if p == l),
    }
    print(f"\n  Category Accuracy: {cat_acc*100:.1f}% ({results_by_category[category]['correct']}/{len(tests)})")

overall_acc = sum(1 for p, l in zip(all_preds, all_labels) if p == l) / len(all_labels)
print(f"\n{'='*60}")
print(f"OVERALL GENERALIZATION ACCURACY: {overall_acc*100:.1f}% ({sum(1 for p,l in zip(all_preds,all_labels) if p==l)}/{len(all_labels)})")
print(f"{'='*60}")

# Save
os.makedirs("models/experiments/experiment_j", exist_ok=True)
gen_results = {
    "overall_accuracy": round(overall_acc, 6),
    "total_tests": len(all_labels),
    "by_category": results_by_category,
}
with open("models/experiments/experiment_j/phase_j5_generalization.json", "w") as f:
    json.dump(gen_results, f, indent=2)
print("\nSaved: models/experiments/experiment_j/phase_j5_generalization.json")
