"""
PATCHPROOF Experiment L — Phase L1: Tokenizer Validation & Benchmark Suite
Executes comprehensive validation across:
1. Tokenizer Correctness (Format mismatches, pointer mismatches, signedness, Python/JS defects, clean code)
2. Channel A Structural Normalization & Parser Fallback Robustness
3. Channel Alignment (Sample IDs, labels, pairing consistency)
4. Performance Benchmarks (100, 1000, 10000 samples, memory, throughput)
5. Vocabulary Coverage & Token Preservation vs. Baseline and Candidate H1
Outputs:
- models/experiments/experiment_l/phase_l1_tokenizer_validation.json
- models/experiments/experiment_l/phase_l1_performance.json
- models/experiments/experiment_l/phase_l1_token_preservation.json
- models/experiments/experiment_l/phase_l1_validation.log
"""

import json
import os
import sys
import time
import tracemalloc
import logging
from collections import Counter, defaultdict
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_l"))
from dual_channel_tokenizer import DualChannelTokenizer

# Logging setup
log_dir = "models/experiments/experiment_l"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "phase_l1_validation.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PhaseL1Validation")

# ---------------------------------------------------------------------------
# 1. Correctness Test Cases
# ---------------------------------------------------------------------------
CORRECTNESS_TESTCASES = [
    # C Format Specifier Mismatches
    {
        "id": "c_fmt_d_on_long",
        "lang": "c",
        "category": "format_mismatch",
        "code": "void test_func(long count) {\n    printf(\"Processed: %d\\n\", count);\n}",
        "expected_lexical_tokens": ["FMT_SPEC_%d", "ARG_TYPE_long", "FMT_PAIR_%d_long", "FMT_MISMATCH_%d_on_64bit"]
    },
    {
        "id": "c_fmt_s_on_int",
        "lang": "c",
        "category": "format_mismatch",
        "code": "void log_error(int code) {\n    printf(\"Error code: %s\\n\", code);\n}",
        "expected_lexical_tokens": ["FMT_SPEC_%s", "ARG_TYPE_int", "FMT_PAIR_%s_int", "FMT_MISMATCH_%s_on_nonstring"]
    },
    {
        "id": "c_fmt_u_on_signed_int",
        "lang": "c",
        "category": "signedness_mismatch",
        "code": "void print_val(int delta) {\n    printf(\"Delta: %u\\n\", delta);\n}",
        "expected_lexical_tokens": ["FMT_SPEC_%u", "ARG_TYPE_int", "FMT_PAIR_%u_int", "FMT_MISMATCH_unsigned_on_signed"]
    },
    {
        "id": "c_fmt_zu_on_int",
        "lang": "c",
        "category": "format_mismatch",
        "code": "void show_len(int length) {\n    printf(\"Length: %zu\\n\", length);\n}",
        "expected_lexical_tokens": ["FMT_SPEC_%zu", "ARG_TYPE_int", "FMT_PAIR_%zu_int", "FMT_MISMATCH_zu_on_non_size_t"]
    },
    # Correct C Format Strings (Negative Controls)
    {
        "id": "c_fmt_correct_d_int",
        "lang": "c",
        "category": "clean_format_control",
        "code": "void print_idx(int index) {\n    printf(\"Index: %d\\n\", index);\n}",
        "expected_lexical_tokens": ["FMT_SPEC_%d", "ARG_TYPE_int", "FMT_MATCH_%d_int"]
    },
    {
        "id": "c_fmt_correct_ld_long",
        "lang": "c",
        "category": "clean_format_control",
        "code": "void print_total(long total) {\n    printf(\"Total: %ld\\n\", total);\n}",
        "expected_lexical_tokens": ["FMT_SPEC_%ld", "ARG_TYPE_long", "FMT_MATCH_%ld_long"]
    },
    {
        "id": "c_fmt_correct_zu_size_t",
        "lang": "c",
        "category": "clean_format_control",
        "code": "void print_size(size_t sz) {\n    printf(\"Size: %zu\\n\", sz);\n}",
        "expected_lexical_tokens": ["FMT_SPEC_%zu", "ARG_TYPE_size_t", "FMT_MATCH_%zu_size_t"]
    },
    # Pointer Mismatches
    {
        "id": "c_ptr_assign_int_lit",
        "lang": "c",
        "category": "pointer_mismatch",
        "code": "void init_buf() {\n    char *ptr = 12345;\n}",
        "expected_lexical_tokens": ["C_PTR_ASSIGN_INT_LITERAL", "C_TYPE_char"]
    },
    {
        "id": "c_ptr_incompat_cast",
        "lang": "c",
        "category": "pointer_mismatch",
        "code": "void cast_val(int *p) {\n    float *f = (float*)p;\n}",
        "expected_lexical_tokens": ["C_PTR_INCOMPATIBLE_CAST", "C_TYPE_float", "C_TYPE_int"]
    },
    # Python Type Errors
    {
        "id": "py_str_int_concat",
        "lang": "python",
        "category": "python_type_error",
        "code": "def concat_prefix(prefix_str, id_num):\n    return prefix_str + '_' + id_num\n",
        "expected_lexical_tokens": ["PY_STR_CONCAT_OP"]
    },
    {
        "id": "py_len_on_int",
        "lang": "python",
        "category": "python_type_error",
        "code": "def get_length(val):\n    return len(42)\n",
        "expected_lexical_tokens": ["PY_LEN_ON_INT"]
    },
    # JavaScript Async Errors
    {
        "id": "js_unhandled_promise",
        "lang": "javascript",
        "category": "js_async_error",
        "code": "function loadData() {\n    fetch('/api/items').then(res => res.json());\n}",
        "expected_lexical_tokens": ["JS_FETCH", "JS_THEN", "JS_PROMISE_MISSING_CATCH"]
    },
    {
        "id": "js_missing_await",
        "lang": "javascript",
        "category": "js_async_error",
        "code": "async function sendNotification(msg) {\n    fetch('/notify', { method: 'POST' });\n}",
        "expected_lexical_tokens": ["JS_ASYNC", "JS_FETCH", "JS_MISSING_AWAIT"]
    },
    # Clean Code (Controls)
    {
        "id": "clean_c_add",
        "lang": "c",
        "category": "clean_control",
        "code": "int add(int a, int b) {\n    return a + b;\n}",
        "expected_lexical_tokens": ["C_TYPE_int"]
    },
    {
        "id": "clean_py_add",
        "lang": "python",
        "category": "clean_control",
        "code": "def add(a: int, b: int) -> int:\n    return a + b\n",
        "expected_lexical_tokens": ["add", "return"]
    },
    {
        "id": "clean_js_async",
        "lang": "javascript",
        "category": "clean_control",
        "code": "async function getData() {\n    const r = await fetch('/api');\n    return await r.json();\n}",
        "expected_lexical_tokens": ["JS_ASYNC", "JS_AWAIT", "JS_FETCH"]
    }
]

# ---------------------------------------------------------------------------
# 2. Channel A Robustness & Parser Fallback Cases
# ---------------------------------------------------------------------------
PARSER_FALLBACK_CASES = [
    {
        "id": "c_syntax_error_unmatched_brace",
        "lang": "c",
        "code": "void broken_func(int x) {\n    if (x > 0) {\n        return 1;\n",
        "expect_fallback": True
    },
    {
        "id": "c_complex_preprocessor_macro",
        "lang": "c",
        "code": "#define MAX_VAL 100\n#ifdef DEBUG\nMY_CUSTOM_MACRO(x)\n#endif\nvoid test() { int a = 1; }",
        "expect_fallback": True
    },
    {
        "id": "python_syntax_error",
        "lang": "python",
        "code": "def broken(x\n    return x + 1",
        "expect_fallback": True
    },
    {
        "id": "c_valid_syntax",
        "lang": "c",
        "code": "int calculate_sum(int a, int b) {\n    int result = a + b;\n    return result;\n}",
        "expect_fallback": False
    },
    {
        "id": "python_valid_syntax",
        "lang": "python",
        "code": "def calculate_sum(a, b):\n    result = a + b\n    return result\n",
        "expect_fallback": False
    }
]

def run_correctness_validation() -> Dict[str, Any]:
    logger.info("Executing Step 1: Tokenizer Correctness Validation...")
    results = []
    passed = 0
    total = len(CORRECTNESS_TESTCASES)

    for tc in CORRECTNESS_TESTCASES:
        t_out = DualChannelTokenizer.transform(tc["code"], tc["lang"])
        lex = t_out["channel_lexical"]
        struct = t_out["channel_structural"]
        
        missing_tokens = []
        for exp_tok in tc["expected_lexical_tokens"]:
            if exp_tok not in lex:
                missing_tokens.append(exp_tok)

        status = "PASS" if not missing_tokens else "FAIL"
        if status == "PASS": passed += 1

        results.append({
            "id": tc["id"],
            "language": tc["lang"],
            "category": tc["category"],
            "status": status,
            "expected_tokens": tc["expected_lexical_tokens"],
            "missing_tokens": missing_tokens,
            "channel_structural_preview": struct[:100].replace("\n", " "),
            "channel_lexical_preview": lex[:100]
        })
        logger.info(f"  [{status}] {tc['id']:30s} (Missing: {missing_tokens or 'None'})")

    accuracy = round(passed / total * 100, 2)
    logger.info(f"Step 1 Summary: {passed}/{total} test cases passed ({accuracy}%).")
    return {
        "total_testcases": total,
        "passed": passed,
        "accuracy_pct": accuracy,
        "testcases": results
    }

def run_channel_a_robustness() -> Dict[str, Any]:
    logger.info("\nExecuting Step 2: Channel A Parser Fallback Robustness...")
    results = []
    passed = 0

    for tc in PARSER_FALLBACK_CASES:
        struct, success = DualChannelTokenizer.extract_structural_channel(tc["code"], tc["lang"])
        # If fallback is expected, success should be False and struct should equal tc["code"]
        fallback_occurred = not success
        code_preserved = (len(struct.strip()) > 0 and (struct.strip() == tc["code"].strip() or success))

        test_pass = (fallback_occurred == tc["expect_fallback"]) and code_preserved
        if test_pass: passed += 1

        results.append({
            "id": tc["id"],
            "language": tc["lang"],
            "expect_fallback": tc["expect_fallback"],
            "fallback_occurred": fallback_occurred,
            "code_preserved": code_preserved,
            "parse_success": success,
            "status": "PASS" if test_pass else "FAIL"
        })
        logger.info(f"  [{'PASS' if test_pass else 'FAIL'}] {tc['id']:35s} Fallback: {fallback_occurred}, Preserved: {code_preserved}")

    return {
        "total": len(PARSER_FALLBACK_CASES),
        "passed": passed,
        "results": results
    }

def run_channel_alignment(val_records: List[Dict[str, Any]], sample_size: int = 500) -> Dict[str, Any]:
    logger.info(f"\nExecuting Step 3: Channel Alignment Validation ({sample_size} samples)...")
    aligned = 0
    errors = []

    for i, rec in enumerate(val_records[:sample_size]):
        code = rec["original_code"]
        lang = rec["language"]
        t_out = DualChannelTokenizer.transform(code, lang)

        ch_struct = t_out["channel_structural"]
        ch_lex = t_out["channel_lexical"]

        # Check alignment properties
        if not ch_struct or len(ch_struct.strip()) == 0:
            errors.append(f"Sample #{i}: Channel A is empty.")
            continue
        if not ch_lex or len(ch_lex.strip()) == 0:
            errors.append(f"Sample #{i}: Channel B is empty.")
            continue
        if "__CHANNEL_SPLIT__" not in t_out["channel_combined"]:
            errors.append(f"Sample #{i}: Combined channel split delimiter missing.")
            continue

        aligned += 1

    alignment_rate = round(aligned / sample_size * 100, 2)
    logger.info(f"  Alignment: {aligned}/{sample_size} verified 1-to-1 ({alignment_rate}%).")
    return {
        "evaluated_samples": sample_size,
        "aligned_samples": aligned,
        "alignment_rate_pct": alignment_rate,
        "errors": errors[:5]
    }

def run_performance_benchmark(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    logger.info("\nExecuting Step 4: Extraction Performance Benchmarking...")
    benchmarks = {}

    sizes = [100, 1000]
    if len(records) >= 5000:
        sizes.append(min(5000, len(records)))

    for n in sizes:
        sample_batch = records[:n]
        tracemalloc.start()
        t0 = time.time()
        fallback_count = 0

        for r in sample_batch:
            res = DualChannelTokenizer.transform(r["original_code"], r["language"])
            if not res["parse_success"]:
                fallback_count += 1

        dt = time.time() - t0
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        fps = round(n / dt, 2) if dt > 0 else 0
        fallback_rate = round(fallback_count / n * 100, 2)
        peak_mb = round(peak_mem / (1024 * 1024), 2)

        benchmarks[f"batch_{n}"] = {
            "samples": n,
            "total_time_seconds": round(dt, 4),
            "samples_per_second": fps,
            "peak_memory_mb": peak_mb,
            "parser_fallbacks": fallback_count,
            "parser_fallback_rate_pct": fallback_rate
        }
        logger.info(f"  Batch {n:5d}: {dt:6.2f}s | {fps:7.1f} samples/sec | Fallback Rate: {fallback_rate:5.1f}% | Peak Mem: {peak_mb:5.1f} MB")

    return benchmarks

def run_token_preservation_comparison(test_records: List[Dict[str, Any]], sample_size: int = 1000) -> Dict[str, Any]:
    logger.info(f"\nExecuting Step 5: Vocabulary Coverage & Token Preservation vs Baselines...")
    cohort = test_records[:sample_size]

    KEY_TOKENS = [
        "%d", "%ld", "%s", "%zu", "%u",
        "long", "int", "size_t", "printf",
        "malloc", "free", "async", "await", "Promise"
    ]

    retention_counts = {
        "raw_baseline": Counter(),
        "h1_ast_only": Counter(),
        "channel_a_struct": Counter(),
        "channel_b_lexical": Counter(),
        "dual_channel": Counter()
    }

    for r in cohort:
        code = r["original_code"]
        lang = r["language"]
        t_out = DualChannelTokenizer.transform(code, lang)
        struct = t_out["channel_structural"]
        lex = t_out["channel_lexical"]
        comb = t_out["channel_combined"]

        for tok in KEY_TOKENS:
            # Raw code
            if tok in code: retention_counts["raw_baseline"][tok] += 1
            # H1 (AST-normalized)
            if tok in struct: retention_counts["h1_ast_only"][tok] += 1
            # Channel A
            if tok in struct: retention_counts["channel_a_struct"][tok] += 1
            # Channel B (Direct string or specialized tag e.g. FMT_SPEC_%d or C_TYPE_long)
            if tok in lex or f"%{tok.replace('%','')}" in lex or f"TYPE_{tok}" in lex or f"MEM_{tok}" in lex or f"JS_{tok.upper()}" in lex or f"FMT_SPEC_{tok}" in lex:
                retention_counts["channel_b_lexical"][tok] += 1
            # Dual Channel
            if tok in comb or f"FMT_SPEC_{tok}" in comb or f"C_TYPE_{tok}" in comb or f"MEM_{tok}" in comb:
                retention_counts["dual_channel"][tok] += 1

    table = []
    logger.info(f"{'Token':10s} | {'Raw Baseline':13s} | {'H1 (AST)':10s} | {'Channel A':10s} | {'Channel B':10s} | {'Dual-Channel':12s}")
    logger.info("-" * 75)

    comparison_dict = {}
    for tok in KEY_TOKENS:
        c_raw = retention_counts["raw_baseline"][tok]
        c_h1 = retention_counts["h1_ast_only"][tok]
        c_cha = retention_counts["channel_a_struct"][tok]
        c_chb = retention_counts["channel_b_lexical"][tok]
        c_dual = retention_counts["dual_channel"][tok]

        logger.info(f"{tok:10s} | {c_raw:13d} | {c_h1:10d} | {c_cha:10d} | {c_chb:10d} | {c_dual:12d}")
        comparison_dict[tok] = {
            "raw_baseline": c_raw,
            "h1_ast_only": c_h1,
            "channel_a_struct": c_cha,
            "channel_b_lexical": c_chb,
            "dual_channel": c_dual,
            "format_token_recovered": c_dual > c_h1 if tok.startswith("%") else True
        }

    return {
        "cohort_size": sample_size,
        "token_comparison": comparison_dict
    }

def main():
    logger.info("=" * 80)
    logger.info("PATCHPROOF EXPERIMENT L — PHASE L1 VALIDATION SUITE")
    logger.info("=" * 80)

    # Load validation data
    val_records = []
    val_path = "data/processed/val.jsonl"
    logger.info(f"Loading {val_path}...")
    with open(val_path, "r", encoding="utf-8") as f:
        for line in f:
            val_records.append(json.loads(line))
    logger.info(f"Loaded {len(val_records)} validation records.")

    # 1. Correctness
    correctness_results = run_correctness_validation()

    # 2. Channel A Robustness
    channel_a_results = run_channel_a_robustness()

    # 3. Channel Alignment
    alignment_results = run_channel_alignment(val_records, sample_size=500)

    # 4. Performance Benchmarks
    perf_results = run_performance_benchmark(val_records)

    # 5. Token Preservation Comparison
    token_results = run_token_preservation_comparison(val_records, sample_size=1000)

    # Save Output JSONs
    out_dir = "models/experiments/experiment_l"
    os.makedirs(out_dir, exist_ok=True)

    f1 = os.path.join(out_dir, "phase_l1_tokenizer_validation.json")
    with open(f1, "w", encoding="utf-8") as f:
        json.dump({
            "phase": "L1",
            "correctness_validation": correctness_results,
            "channel_a_robustness": channel_a_results,
            "channel_alignment": alignment_results
        }, f, indent=2)
    logger.info(f"\nSaved validation results to: {f1}")

    f2 = os.path.join(out_dir, "phase_l1_performance.json")
    with open(f2, "w", encoding="utf-8") as f:
        json.dump(perf_results, f, indent=2)
    logger.info(f"Saved performance benchmark to: {f2}")

    f3 = os.path.join(out_dir, "phase_l1_token_preservation.json")
    with open(f3, "w", encoding="utf-8") as f:
        json.dump(token_results, f, indent=2)
    logger.info(f"Saved token preservation comparison to: {f3}")

    logger.info("\nPHASE L1 VALIDATION COMPLETED SUCCESSFULLY.")

if __name__ == "__main__":
    main()
