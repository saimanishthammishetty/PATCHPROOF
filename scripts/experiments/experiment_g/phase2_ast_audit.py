import sys
import json
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from scripts.datasets.schema import CodeDebuggingExample
from scripts.experiments.experiment_f.ast_normalizer import (
    normalize_python, normalize_javascript, normalize_c
)

print("="*80)
print("PHASE 2: AST NORMALIZATION AUDIT ACROSS SPLITS")
print("="*80)

def audit_split(split_name):
    print(f"\n--- Auditing {split_name}.jsonl ---")
    path = Path(f"data/processed/{split_name}.jsonl")
    
    total_by_lang = Counter()
    success_by_lang = Counter()
    fail_by_lang = Counter()
    reasons_by_lang = {
        "python": Counter(),
        "javascript": Counter(),
        "c": Counter()
    }
    
    sample_failures = {
        "python": [],
        "javascript": [],
        "c": []
    }
    
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip(): continue
            ex = CodeDebuggingExample.from_jsonl(line)
            lang = ex.language.lower().strip()
            code = ex.original_code
            total_by_lang[lang] += 1
            
            ok = False
            err_reason = "unknown"
            
            if lang == "python":
                try:
                    norm, ok = normalize_python(code)
                    if not ok or norm == code:
                        err_reason = "unmodified_or_no_function_def"
                    else:
                        ok = True
                except Exception as e:
                    err_reason = type(e).__name__
                    ok = False
                    
            elif lang in ("javascript", "typescript", "js", "ts"):
                try:
                    norm, ok = normalize_javascript(code)
                    if not ok or norm == code:
                        err_reason = "unmodified_or_no_function_def"
                    else:
                        ok = True
                except Exception as e:
                    err_reason = type(e).__name__
                    ok = False
                    
            elif lang in ("c", "cpp"):
                try:
                    norm, ok = normalize_c(code)
                    if not ok or norm == code:
                        err_reason = "pycparser_parse_error_or_fragment"
                    else:
                        ok = True
                except Exception as e:
                    err_reason = type(e).__name__
                    ok = False
            else:
                err_reason = "unsupported_language"
                ok = False
                
            if ok:
                success_by_lang[lang] += 1
            else:
                fail_by_lang[lang] += 1
                reasons_by_lang.setdefault(lang, Counter())[err_reason] += 1
                if len(sample_failures.setdefault(lang, [])) < 3:
                    sample_failures[lang].append((ex.bug_category, code.strip()[:150]))
                    
    print(f"Total Records: {sum(total_by_lang.values())}")
    for lang in sorted(total_by_lang.keys()):
        tot = total_by_lang[lang]
        succ = success_by_lang[lang]
        rate = (succ / tot * 100) if tot > 0 else 0
        print(f"  {lang:<15}: {succ:6d} / {tot:6d} ({rate:5.1f}% normalized)")
        if reasons_by_lang.get(lang):
            print(f"    Failure reasons: {dict(reasons_by_lang[lang].most_common(3))}")
            
    return sample_failures

train_fails = audit_split("train")
print("\nSample Failure Snippets from Train:")
for lang, samples in train_fails.items():
    print(f"\n--- {lang.upper()} Sample Fallbacks ---")
    for cat, snip in samples:
        print(f"  [{cat}] {repr(snip)}")

test_fails = audit_split("test")

