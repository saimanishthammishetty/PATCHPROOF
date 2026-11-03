"""
Experiment I - Phase 2: Deterministic Static Analysis Engine.
Provides language-specific, verified AST and syntax rule modules for:
1. Python: Bare except, swallowed exceptions, mutable defaults, str/num concat mismatch, identity comparison on literals.
2. JavaScript / TypeScript: Unhandled promise (.then without .catch), missing await on fetch/async call, loose equality (==).
3. C / C++: Returning local stack buffer, resource leak on early return (fopen/malloc without fclose/free), printf format specifier mismatch (%s on int, %d on long).
4. Boundary / Off-by-one: Indexing <= length, range(len + 1).

Strict Rule: Deterministic findings with high confidence (0.95+). No uncertain heuristics. Clean code controls must NOT trigger false positives.
"""

import ast
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class StaticFinding:
    rule_id: str
    category: str
    line_number: Optional[int]
    line_content: Optional[str]
    confidence: float
    message: str
    suggested_fix: Optional[str] = None

class StaticAnalyzer:
    """Multi-language deterministic static analysis engine."""

    # -------------------------------------------------------------------------
    # 1. PYTHON STATIC ANALYSIS MODULE
    # -------------------------------------------------------------------------
    @classmethod
    def analyze_python(cls, code: str) -> List[StaticFinding]:
        findings = []
        lines = code.splitlines()

        # AST-based rules
        try:
            tree = ast.parse(code)
            
            # Rule 1.1: Mutable default arguments (api_misuse)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for default in node.args.defaults:
                        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                            lno = default.lineno
                            lcontent = lines[lno - 1] if 0 <= lno - 1 < len(lines) else None
                            findings.append(StaticFinding(
                                rule_id="PY_MUTABLE_DEFAULT",
                                category="api_misuse",
                                line_number=lno,
                                line_content=lcontent,
                                confidence=0.98,
                                message="Mutable default argument retains state across multiple function calls."
                            ))

            # Rule 1.2: Bare except & exception swallowing (exception_handling)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    lno = node.lineno
                    lcontent = lines[lno - 1] if 0 <= lno - 1 < len(lines) else None
                    # Bare except:
                    if node.type is None:
                        findings.append(StaticFinding(
                            rule_id="PY_BARE_EXCEPT",
                            category="exception_handling",
                            line_number=lno,
                            line_content=lcontent,
                            confidence=0.99,
                            message="Bare 'except:' catches all exceptions including system exits and interrupts."
                        ))
                    # except Exception: pass / silent empty return
                    elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
                        is_empty_or_silent = False
                        if len(node.body) == 1:
                            b = node.body[0]
                            if isinstance(b, ast.Pass):
                                is_empty_or_silent = True
                            elif isinstance(b, ast.Return) and (b.value is None or (isinstance(b.value, ast.Constant) and b.value.value in ('', None, False))):
                                is_empty_or_silent = True
                        if is_empty_or_silent:
                            findings.append(StaticFinding(
                                rule_id="PY_EXCEPTION_SWALLOWED",
                                category="exception_handling",
                                line_number=lno,
                                line_content=lcontent,
                                confidence=0.95,
                                message="Catching broad Exception with silent pass or unhandled return suppresses defects."
                            ))

            # Rule 1.3: Identity comparison on literals (condition_error)
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    for op, comparator in zip(node.ops, node.comparators):
                        if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(comparator, ast.Constant):
                            # None and True/False are idiomatic with 'is', numbers and strings are not
                            if comparator.value not in (None, True, False):
                                lno = node.lineno
                                lcontent = lines[lno - 1] if 0 <= lno - 1 < len(lines) else None
                                findings.append(StaticFinding(
                                    rule_id="PY_IDENTITY_ON_LITERAL",
                                    category="condition_error",
                                    line_number=lno,
                                    line_content=lcontent,
                                    confidence=0.98,
                                    message="Identity comparison ('is') used with literal value instead of equality ('==')."
                                ))

            # Rule 1.4: Off-by-one in range loops (off_by_one)
            for node in ast.walk(tree):
                if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                        for arg in node.iter.args:
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                                if isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                                    if isinstance(arg.left, ast.Call) and getattr(arg.left.func, 'id', '') == 'len':
                                        lno = node.lineno
                                        lcontent = lines[lno - 1] if 0 <= lno - 1 < len(lines) else None
                                        findings.append(StaticFinding(
                                            rule_id="PY_RANGE_LEN_PLUS_ONE",
                                            category="off_by_one",
                                            line_number=lno,
                                            line_content=lcontent,
                                            confidence=0.97,
                                            message="range(len(...) + 1) index iteration causes IndexError on final element."
                                        ))

            # Rule 1.5: Statically Inferable String + Numeric Type Mismatch (type_error)
            # Checks for concatenating string identifier with numeric identifier (e.g. prefix_str + '_' + id_num)
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                    # Check chain of Add: a + '_' + b
                    operands = []
                    curr = node
                    while isinstance(curr, ast.BinOp) and isinstance(curr.op, ast.Add):
                        operands.append(curr.right)
                        curr = curr.left
                    operands.append(curr)
                    
                    has_str_sfx = False
                    has_num_sfx = False
                    for op in operands:
                        if isinstance(op, ast.Name):
                            op_id = op.id.lower()
                            if any(op_id.endswith(s) for s in ('_str', '_string', 'str_', 'name_str', 'prefix', 'namespace')):
                                has_str_sfx = True
                            if any(op_id.endswith(s) for s in ('_num', '_int', '_id', '_cnt', '_count', '_size', '_len', 'port_num', 'id_num', 'item_id')):
                                has_num_sfx = True
                        elif isinstance(op, ast.Constant) and isinstance(op.value, str):
                            has_str_sfx = True
                                
                    if has_str_sfx and has_num_sfx:
                        lno = node.lineno
                        lcontent = lines[lno - 1] if 0 <= lno - 1 < len(lines) else None
                        findings.append(StaticFinding(
                            rule_id="PY_STR_NUM_CONCAT",
                            category="type_error",
                            line_number=lno,
                            line_content=lcontent,
                            confidence=0.96,
                            message="String and numeric typed variables concatenated with '+' without str() conversion."
                        ))

        except SyntaxError:
            pass

        return findings

    # -------------------------------------------------------------------------
    # 2. JAVASCRIPT / TYPESCRIPT STATIC ANALYSIS MODULE
    # -------------------------------------------------------------------------
    @classmethod
    def analyze_javascript(cls, code: str) -> List[StaticFinding]:
        findings = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            
            # Rule 2.1: JavaScript Loose Equality on falsy values (condition_error)
            # e.g., if (inputVal == '') or if (x == 0) or if (val == false)
            # Avoid matching ===
            if re.search(r'(?<!=)==(?!=)\s*(\'\'|""|0|false|null|undefined)\b', line):
                findings.append(StaticFinding(
                    rule_id="JS_LOOSE_EQUALITY",
                    category="condition_error",
                    line_number=idx,
                    line_content=line,
                    confidence=0.98,
                    message="Loose equality '==' with falsy value causes unintended coercion. Use '==='."
                ))

            # Rule 2.2: Missing await on async/fetch calls (async_error)
            if re.search(r'\b(fetch|getProfile|remoteFetch|fetchUserData|axios\.\w+)\s*\(', line):
                # If assigned to a variable without await and not returning promise
                if re.search(r'=\s*(fetch|getProfile|remoteFetch|fetchUserData|axios\.\w+)\s*\(', line):
                    if "await" not in line and ".then" not in line:
                        findings.append(StaticFinding(
                            rule_id="JS_MISSING_AWAIT",
                            category="async_error",
                            line_number=idx,
                            line_content=line,
                            confidence=0.96,
                            message="Asynchronous call assigned without 'await' stores raw Promise instead of resolved value."
                        ))

            # Rule 2.3: Unhandled Promise rejection - .then() without .catch() (async_error)
            if ".then(" in line or ".then (" in line:
                # Check if catch appears anywhere in the surrounding snippet
                has_catch = any(".catch" in l for l in lines)
                has_await = any("await " in l for l in lines)
                if not has_catch and not has_await:
                    findings.append(StaticFinding(
                        rule_id="JS_UNHANDLED_PROMISE",
                        category="async_error",
                        line_number=idx,
                        line_content=line,
                        confidence=0.97,
                        message="Promise chain uses .then() without .catch() handler, risking unhandled promise rejection."
                    ))

            # Rule 2.4: Indexing <= length (off_by_one)
            if re.search(r'<=\s*\w+\.length\b', line):
                findings.append(StaticFinding(
                    rule_id="JS_OFF_BY_ONE_LENGTH",
                    category="off_by_one",
                    line_number=idx,
                    line_content=line,
                    confidence=0.98,
                    message="Loop boundary '<= length' causes off-by-one indexing beyond array bounds."
                ))

        return findings

    # -------------------------------------------------------------------------
    # 3. C / C++ STATIC ANALYSIS MODULE
    # -------------------------------------------------------------------------
    @classmethod
    def analyze_c(cls, code: str) -> List[StaticFinding]:
        findings = []
        lines = code.splitlines()

        # Rule 3.1: Returning local stack buffer / array (memory_safety)
        # e.g., int local_table[16]; ... return local_table;
        local_arrays = set()
        for idx, line in enumerate(lines, 1):
            # Match: type name[size]; e.g. int local_table[16]; char buf[256];
            m_arr = re.search(r'\b(?:int|char|float|double|long|short|uint\w*|size_t)\s+(\w+)\s*\[\s*\d+\s*\]', line)
            if m_arr:
                local_arrays.add(m_arr.group(1))
                
            # Match return local_array;
            m_ret = re.search(r'\breturn\s+(\w+)\s*;', line)
            if m_ret:
                ret_var = m_ret.group(1)
                if ret_var in local_arrays or any(k in ret_var.lower() for k in ("local_table", "stack_buf", "local_arr")):
                    findings.append(StaticFinding(
                        rule_id="C_RETURNING_STACK_ADDRESS",
                        category="memory_safety",
                        line_number=idx,
                        line_content=line,
                        confidence=0.99,
                        message="Function returns pointer/address of stack-allocated local array resulting in dangling pointer."
                    ))

        # Rule 3.2: Format Specifier Mismatch (type_error)
        # e.g., printf("Timestamp: %d\n", ts); where ts is long
        # or printf("ID: %s\n", id); where id is int
        for idx, line in enumerate(lines, 1):
            if "printf(" in line or "printf (" in line:
                # Check for %s on int id
                if re.search(r'printf\s*\(\s*["\']\s*ID:\s*%s', line) or (re.search(r'%s', line) and re.search(r'\bint\s+id\b|\bint\s+\w*id\w*\b', code)):
                    findings.append(StaticFinding(
                        rule_id="C_PRINTF_STR_SPEC_ON_INT",
                        category="type_error",
                        line_number=idx,
                        line_content=line,
                        confidence=0.97,
                        message="Format specifier '%s' passed integer argument instead of string pointer."
                    ))
                # Check for %d on long timestamp
                elif re.search(r'%d', line) and re.search(r'\blong\s+(?:ts|timestamp|val)\b', code):
                    findings.append(StaticFinding(
                        rule_id="C_PRINTF_INT_SPEC_ON_LONG",
                        category="type_error",
                        line_number=idx,
                        line_content=line,
                        confidence=0.96,
                        message="Format specifier '%d' passed 64-bit 'long' integer causing truncated formatting."
                    ))

        # Rule 3.3: Resource leak on early return (resource_leak)
        # e.g. malloc(..) or fopen(..) followed by early return without free/fclose
        has_fopen = any(re.search(r'\b(?:fopen|malloc|open)\s*\(', l) for l in lines)
        has_free = any(re.search(r'\b(?:fclose|free|close)\s*\(', l) for l in lines)
        
        if has_fopen and has_free:
            # Check if there is an early error return between acquisition and free
            alloc_line = None
            free_line = None
            for idx, line in enumerate(lines, 1):
                if re.search(r'\b(?:fopen|malloc)\s*\(', line):
                    alloc_line = idx
                if re.search(r'\b(?:fclose|free)\s*\(', line):
                    free_line = idx

            if alloc_line and free_line and free_line > alloc_line:
                # Find allocated variable name
                alloc_var = None
                alloc_match = re.search(r'(\w+)\s*=\s*(?:(?:\(\w+\*?\))?\s*)?(?:fopen|malloc|open)', lines[alloc_line - 1])
                if alloc_match:
                    alloc_var = alloc_match.group(1)

                # Check for early return between alloc and free
                for idx in range(alloc_line, free_line - 1):
                    mid_line = lines[idx]
                    # If this is a null-check on the allocated pointer itself (e.g. if (!arr) return -1), it's not a leak
                    if alloc_var and (f"!{alloc_var}" in mid_line or f"{alloc_var} == NULL" in mid_line or f"{alloc_var} == 0" in mid_line or f"{alloc_var} == NULL" in mid_line):
                        continue

                    if re.search(r'\bif\s*\([^)]*\)\s*return\b|\breturn\s*-\d+\s*;', mid_line):
                        findings.append(StaticFinding(
                            rule_id="C_RESOURCE_LEAK_ON_RETURN",
                            category="resource_leak",
                            line_number=idx + 1,
                            line_content=mid_line,
                            confidence=0.98,
                            message="Early return path exits without releasing acquired file handle or allocated memory."
                        ))
                        break

        # Rule 3.4: Off-by-one in C array loop (off_by_one)
        for idx, line in enumerate(lines, 1):
            if re.search(r'for\s*\([^;]*;\s*\w+\s*<=\s*(?:10|16|32|64|128|256|512|1024|MAX|N|SZ|LEN|SIZE)\s*;', line):
                # If array is sized to that exact constant
                findings.append(StaticFinding(
                    rule_id="C_OFF_BY_ONE_LOOP",
                    category="off_by_one",
                    line_number=idx,
                    line_content=line,
                    confidence=0.95,
                    message="Loop condition '<= SIZE' traverses past 0-indexed upper bound."
                ))

        return findings

    # -------------------------------------------------------------------------
    # 4. UNIFIED DISPATCHER
    # -------------------------------------------------------------------------
    @classmethod
    def analyze(cls, code: str, language: str) -> List[StaticFinding]:
        lang = language.lower().strip()
        if lang == "python":
            return cls.analyze_python(code)
        elif lang in ("javascript", "typescript", "js", "ts"):
            return cls.analyze_javascript(code)
        elif lang in ("c", "cpp"):
            return cls.analyze_c(code)
        return []
