"""
PATCHPROOF Experiment L — Phase L1: Dual-Channel Tokenizer
Implements two independent, aligned feature representation channels:

Channel A: Structural Representation
- Scope-aware AST normalization (Python ast, C pycparser, JS TS-API/fallback).
- Normalizes user-defined local variables and parameters (p_1, v_1).
- Preserves control-flow structure, function signatures, and call hierarchies.
- Fallback preserves full raw code on parser failure.

Channel B: Lexical & Domain-Specific Semantic Token Representation
- Explicitly extracts and preserves format specifiers (%d, %ld, %s, %zu, %u, %x, %p).
- Detects format specifier and argument type pairs (e.g. FMT_PAIR_%d_long).
- Detects signed/unsigned mismatches (%u on signed, %d on unsigned).
- Detects wide/narrow mismatches (%ld on int, %d on 64-bit int).
- Detects pointer mismatches and incompatible pointer assignments.
- Preserves type keywords (long, int, size_t, uint8_t, char*, void, etc.).
- Preserves memory lifecycle tokens (malloc, free, sizeof, NULL, nullptr).
- Preserves concurrency & async tokens (async, await, Promise, fetch, .then, .catch).
- Preserves boundary and off-by-one indicators (range(len+1), <= len).
- Preserves exception constructs (bare except, swallowed pass).
- Preserves Python type-mismatch signatures (str + int, len(int)).

Supports C, C++, Python, and JavaScript with robust fallback.
"""

import ast
import re
import sys
import os
from typing import Tuple, Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath("scripts/experiments/experiment_f"))
try:
    from ast_normalizer import normalize_snippet, normalize_python, normalize_c
except ImportError:
    def normalize_snippet(code, lang): return code, False

# ---------------------------------------------------------------------------
# Channel B: Lexical & Semantic Token Extractor
# ---------------------------------------------------------------------------

FORMAT_SPEC_REGEX = re.compile(r"%(?:[-+0 #*]*\d*(?:\.\d+)?[hlLzjt]*[diuoxXfFeEgGaAcspn%])")
C_FN_REGEX = re.compile(r"\b(printf|sprintf|snprintf|fprintf|vprintf|vsnprintf|scanf|sscanf|fscanf)\s*\(")
QUOTE_REGEX = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')

C_TYPE_KEYWORDS = [
    "long long", "unsigned long", "unsigned int", "unsigned short", "unsigned char",
    "int64_t", "uint64_t", "int32_t", "uint32_t", "int16_t", "uint16_t", "int8_t", "uint8_t",
    "size_t", "ssize_t", "uintptr_t", "intptr_t", "off_t",
    "long", "int", "short", "char", "float", "double", "unsigned", "signed",
    "void", "bool"
]

MEMORY_OPS = {"malloc", "free", "calloc", "realloc", "sizeof", "memcpy", "memset", "memmove"}
ASYNC_OPS = {"async", "await", "Promise", "fetch", "then", "catch", "setTimeout", "asyncio"}

class DualChannelTokenizer:
    """Multi-channel representation generator for software defect analysis."""

    def __init__(self):
        pass

    # -----------------------------------------------------------------------
    # Channel A: Structural
    # -----------------------------------------------------------------------
    @classmethod
    def extract_structural_channel(cls, code: str, language: str) -> Tuple[str, bool]:
        """Generates AST scope-normalized code text and returns (code, parse_success)."""
        lang = language.lower().strip()
        norm_code, success = normalize_snippet(code, lang)
        return norm_code, success

    @classmethod
    def _parse_printf_calls(cls, code: str) -> List[Tuple[str, str, str]]:
        """Safely parses printf-family calls in linear O(N) time without regex backtracking."""
        matches = []
        for m in C_FN_REGEX.finditer(code):
            fn_name = m.group(1)
            start_idx = m.end()
            paren_depth = 1
            i = start_idx
            end_idx = -1
            in_quote = False
            while i < len(code) and i < start_idx + 2000:
                ch = code[i]
                if ch == '"' and (i == 0 or code[i-1] != '\\'):
                    in_quote = not in_quote
                elif not in_quote:
                    if ch == '(':
                        paren_depth += 1
                    elif ch == ')':
                        paren_depth -= 1
                        if paren_depth == 0:
                            end_idx = i
                            break
                    elif ch in (';', '}'):
                        break
                i += 1

            if end_idx != -1:
                args_str = code[start_idx:end_idx]
                quotes = QUOTE_REGEX.findall(args_str)
                fmt_str = ""
                trailing_args = ""
                for q in quotes:
                    if "%" in q:
                        fmt_str = q
                        q_literal = f'"{q}"'
                        if q_literal in args_str:
                            after_q = args_str.split(q_literal, 1)[1]
                            trailing_args = after_q.lstrip(",").strip()
                        break
                if fmt_str:
                    matches.append((fn_name, fmt_str, trailing_args))
        return matches

    # -----------------------------------------------------------------------
    # Channel B: Lexical & Domain Semantic
    # -----------------------------------------------------------------------
    @classmethod
    def extract_lexical_channel(cls, code: str, language: str) -> str:
        """
        Extracts specialized lexical features, explicit format specifiers,
        type-format relationships, memory operations, and async tokens.
        """
        lang = language.lower().strip()
        tokens: List[str] = []

        # 1. Format Specifiers & Type-Format Relations (C / C++)
        if lang in ("c", "cpp", "c++"):
            # Scan printf family calls safely in O(N) linear time
            for fn_name, fmt_str, args_str in cls._parse_printf_calls(code):

                tokens.append(f"CALL_{fn_name}")
                specs = FORMAT_SPEC_REGEX.findall(fmt_str)
                for s in specs:
                    clean_spec = s.replace("%", "").strip()
                    tokens.append(f"FMT_SPEC_%{clean_spec}")

                if args_str:
                    raw_args = [a.strip() for a in args_str.split(",") if a.strip()]
                    for i, arg in enumerate(raw_args):
                        spec_for_arg = specs[i] if i < len(specs) else "%EXTRA_ARG"
                        arg_clean = re.sub(r"[^a-zA-Z0-9_]", "", arg)
                        
                        # Find declared type of argument in the function scope
                        found_type = None
                        for kw in C_TYPE_KEYWORDS:
                            pattern = r"\b" + re.escape(kw) + r"\s+(?:\*+\s*)?" + re.escape(arg_clean) + r"\b"
                            if re.search(pattern, code):
                                found_type = kw
                                break

                        if found_type:
                            tokens.append(f"ARG_TYPE_{found_type.replace(' ', '_')}")
                            clean_s = spec_for_arg.replace("%", "")
                            tokens.append(f"FMT_PAIR_%{clean_s}_{found_type.replace(' ', '_')}")

                            # 1a. Format Mismatch: %d on 64-bit int / long / size_t
                            if clean_s in ("d", "i") and found_type in ("long", "long long", "size_t", "uint64_t", "int64_t"):
                                tokens.append("FMT_MISMATCH_%d_on_64bit")
                            # 1b. Format Mismatch: %ld on 32-bit int
                            elif clean_s in ("ld", "lu") and found_type in ("int", "short", "char", "int32_t", "uint32_t"):
                                tokens.append("FMT_MISMATCH_wide_on_narrow")
                            # 1c. Format Mismatch: %u on signed int
                            elif clean_s in ("u", "x", "X") and found_type in ("int", "short", "long", "int32_t", "signed"):
                                tokens.append("FMT_MISMATCH_unsigned_on_signed")
                            # 1d. Format Mismatch: %d on unsigned int
                            elif clean_s in ("d", "i") and "unsigned" in found_type:
                                tokens.append("FMT_MISMATCH_signed_on_unsigned")
                            # 1e. Format Mismatch: %zu on non-size_t
                            elif clean_s == "zu" and found_type not in ("size_t", "ssize_t"):
                                tokens.append("FMT_MISMATCH_zu_on_non_size_t")
                                if found_type in ("int", "short", "char", "int32_t", "uint32_t"):
                                    tokens.append("FMT_MISMATCH_wide_on_narrow")
                            # 1f. Format Mismatch: %s on non-string
                            elif clean_s == "s" and found_type not in ("char", "char*"):
                                tokens.append("FMT_MISMATCH_%s_on_nonstring")
                            # 1g. Format Mismatch: %p on non-pointer
                            elif clean_s == "p" and found_type not in ("uintptr_t", "intptr_t") and "*" not in code:
                                tokens.append("FMT_MISMATCH_%p_on_nonpointer")
                            # 1h. Verified Match (Control signal)
                            elif (clean_s in ("d", "i") and found_type == "int") or \
                                 (clean_s == "ld" and found_type == "long") or \
                                 (clean_s == "zu" and found_type == "size_t") or \
                                 (clean_s == "s" and found_type == "char"):
                                tokens.append(f"FMT_MATCH_%{clean_s}_{found_type.replace(' ', '_')}")

            # Standalone format specifier scan (for code blocks without full printf call)
            standalone_specs = FORMAT_SPEC_REGEX.findall(code)
            for s in standalone_specs:
                clean_s = s.replace("%", "").strip()
                tokens.append(f"RAW_FMT_%{clean_s}")

            # C Type keywords
            for kw in C_TYPE_KEYWORDS:
                if re.search(r"\b" + re.escape(kw) + r"\b", code):
                    tokens.append(f"C_TYPE_{kw.replace(' ', '_')}")

            # Pointer mismatch patterns
            if re.search(r"\b(?:int|char|void)\s*\*+\s*[a-zA-Z_]\w*\s*=\s*\d+\b", code):
                tokens.append("C_PTR_ASSIGN_INT_LITERAL")
            if re.search(r"\((?:float|double)\s*\*+\s*\)\s*[a-zA-Z_]\w*", code):
                tokens.append("C_PTR_INCOMPATIBLE_CAST")

            # Memory operations
            for m in MEMORY_OPS:
                if re.search(r"\b" + re.escape(m) + r"\b", code):
                    tokens.append(f"C_MEM_{m}")

            # Pointer operators
            if "->" in code: tokens.append("C_ARROW_DEREF")
            if "*=" in code or re.search(r"\*\s*[a-zA-Z_]\w*", code): tokens.append("C_PTR_DEREF")
            if "&" in code: tokens.append("C_ADDR_OF")
            if re.search(r"\b(NULL|nullptr)\b", code): tokens.append("C_NULL_LITERAL")

        # 2. Python Semantic Tokens
        elif lang == "python":
            # Mutable defaults
            if re.search(r"def\s+\w+\s*\([^)]*=\s*\[\s*\]", code):
                tokens.append("PY_MUTABLE_LIST_DEFAULT")
            if re.search(r"def\s+\w+\s*\([^)]*=\s*\{\s*\}", code):
                tokens.append("PY_MUTABLE_DICT_DEFAULT")
            # Bare except
            if re.search(r"except\s*:", code):
                tokens.append("PY_BARE_EXCEPT")
            # Swallowed pass
            if re.search(r"except[^:]*:\s*\n\s*pass\b", code):
                tokens.append("PY_SWALLOWED_PASS")
            # Type error: str + int concatenation
            if re.search(r"['\"][^'\"]*['\"]\s*\+\s*[a-zA-Z_]\w*", code) or \
               re.search(r"[a-zA-Z_]\w*\s*\+\s*['\"][^'\"]*['\"]", code):
                tokens.append("PY_STR_CONCAT_OP")
            # Type error: len() on integer
            if re.search(r"\blen\s*\(\s*\d+\s*\)", code):
                tokens.append("PY_LEN_ON_INT")
            # None dereference
            if re.search(r"\bNone\b", code):
                tokens.append("PY_NONE_LITERAL")
            # Async Python
            if re.search(r"\basync\s+def\b", code): tokens.append("PY_ASYNC_DEF")
            if re.search(r"\bawait\b", code): tokens.append("PY_AWAIT_KW")
            if re.search(r"\basyncio\.sleep\b", code): tokens.append("PY_ASYNCIO_SLEEP")

        # 3. JavaScript / TypeScript Semantic Tokens
        elif lang in ("javascript", "typescript", "js", "ts"):
            if re.search(r"\basync\b", code): tokens.append("JS_ASYNC")
            if re.search(r"\bawait\b", code): tokens.append("JS_AWAIT")
            if re.search(r"\bPromise\b", code): tokens.append("JS_PROMISE")
            if re.search(r"\bfetch\b", code): tokens.append("JS_FETCH")
            if ".then(" in code: tokens.append("JS_THEN")
            if ".catch(" in code: tokens.append("JS_CATCH")
            # Missing catch on promise chain
            if ".then(" in code and ".catch(" not in code:
                tokens.append("JS_PROMISE_MISSING_CATCH")
            # Missing await in async function
            if re.search(r"async\s+function", code) and "fetch(" in code and "await" not in code and "return" not in code:
                tokens.append("JS_MISSING_AWAIT")
            if "==" in code and "===" not in code: tokens.append("JS_LOOSE_EQ")
            if re.search(r"\b(null|undefined)\b", code): tokens.append("JS_NULLISH")

        # Common cross-language boundary tokens
        if re.search(r"<=\s*(?:len|length|size|count)\b", code):
            tokens.append("BND_LTE_LENGTH")
        if re.search(r"range\s*\(\s*len\s*\([^)]+\)\s*\+\s*1\s*\)", code):
            tokens.append("BND_RANGE_LEN_PLUS_ONE")

        # Raw lexical word extraction
        raw_words = re.findall(r"\b[a-zA-Z_]\w+\b", code)
        tokens.extend(raw_words[:40])

        return " ".join(tokens)

    # -----------------------------------------------------------------------
    # Dual-Channel Representation
    # -----------------------------------------------------------------------
    @classmethod
    def transform(cls, code: str, language: str) -> Dict[str, Any]:
        """Returns structural, lexical, and metadata for a snippet."""
        struct_ch, parse_success = cls.extract_structural_channel(code, language)
        lex_ch = cls.extract_lexical_channel(code, language)
        return {
            "channel_structural": struct_ch,
            "channel_lexical": lex_ch,
            "channel_combined": f"{struct_ch}\n__CHANNEL_SPLIT__\n{lex_ch}",
            "parse_success": parse_success
        }

if __name__ == "__main__":
    test_code = """void c_resolve_matrix_13(long count) {
    printf("Total items processed: %d\\n", count);
}"""
    res = DualChannelTokenizer.transform(test_code, "c")
    print("=== Channel A (Structural) ===")
    print(res["channel_structural"])
    print("\n=== Channel B (Lexical) ===")
    print(res["channel_lexical"])
    print("\nParse success:", res["parse_success"])
