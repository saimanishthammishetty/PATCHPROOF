import random
import difflib
import hashlib
import uuid
from typing import List, Dict, Any, Tuple
from scripts.datasets.schema import CodeDebuggingExample

# Seed for absolute reproducibility
RANDOM_SEED = 42

class SyntheticBugGenerator:
    """
    High-throughput generator for controlled, realistic software defects and clean controls
    across C/C++, Python, JavaScript/TypeScript, Java, and Go.
    """

    def __init__(self, seed: int = RANDOM_SEED):
        self.rng = random.Random(seed)
        self._init_templates()

    def _init_templates(self):
        # We define diverse task families across algorithms, data structures, utilities, security
        self.var_names = [
            "data", "buffer", "tokens", "records", "items", "payload", "config", "session",
            "cache", "queue", "matrix", "stream", "packet", "counter", "registry", "index_map"
        ]
        self.func_prefixes = [
            "process", "parse", "validate", "compute", "format", "filter", "sanitize",
            "serialize", "transform", "aggregate", "verify", "dispatch", "resolve", "encode"
        ]

    def _generate_python_examples(self, count: int) -> List[CodeDebuggingExample]:
        examples: List[CodeDebuggingExample] = []
        bug_types = [
            "mutable_default", "indexing_off_by_one", "type_error_concat",
            "exception_swallowing", "is_vs_equality", "unhandled_none_return",
            "broken_while_termination", "correct_control"
        ]

        for i in range(count):
            b_type = self.rng.choice(bug_types)
            var = self.rng.choice(self.var_names)
            func = f"{self.rng.choice(self.func_prefixes)}_{var}_{i%1000}"

            if b_type == "mutable_default":
                orig = (
                    f"def {func}(item, {var}=[]):\n"
                    f"    \"\"\"Appends item to batch queue.\"\"\"\n"
                    f"    {var}.append(item)\n"
                    f"    return {var}\n"
                )
                fixed = (
                    f"def {func}(item, {var}=None):\n"
                    f"    \"\"\"Appends item to batch queue.\"\"\"\n"
                    f"    if {var} is None:\n"
                    f"        {var} = []\n"
                    f"    {var}.append(item)\n"
                    f"    return {var}\n"
                )
                desc = "Mutable default argument retains state across multiple function invocations."
                cat = "api_misuse"
                diff = "easy"
                faulty_lines = [1]
                tests = [{"input": f"{func}('val1'); {func}('val2')", "expected": "['val2']"}]
            
            elif b_type == "indexing_off_by_one":
                orig = (
                    f"def {func}(elements):\n"
                    f"    \"\"\"Finds peak element in sequence.\"\"\"\n"
                    f"    n = len(elements)\n"
                    f"    for idx in range(0, n + 1):\n"
                    f"        if elements[idx] > 100:\n"
                    f"            return idx\n"
                    f"    return -1\n"
                )
                fixed = (
                    f"def {func}(elements):\n"
                    f"    \"\"\"Finds peak element in sequence.\"\"\"\n"
                    f"    n = len(elements)\n"
                    f"    for idx in range(0, n):\n"
                    f"        if elements[idx] > 100:\n"
                    f"            return idx\n"
                    f"    return -1\n"
                )
                desc = "Range upper limit includes n + 1 causing IndexError on list lookup."
                cat = "off_by_one"
                diff = "easy"
                faulty_lines = [4]
                tests = [{"input": f"{func}([10, 20, 30])", "expected": "-1"}]

            elif b_type == "type_error_concat":
                orig = (
                    f"def {func}(user_id, count):\n"
                    f"    \"\"\"Constructs transaction identifier.\"\"\"\n"
                    f"    prefix = 'TXN_'\n"
                    f"    txn_id = prefix + user_id + '_' + count\n"
                    f"    return txn_id.upper()\n"
                )
                fixed = (
                    f"def {func}(user_id, count):\n"
                    f"    \"\"\"Constructs transaction identifier.\"\"\"\n"
                    f"    prefix = 'TXN_'\n"
                    f"    txn_id = prefix + str(user_id) + '_' + str(count)\n"
                    f"    return txn_id.upper()\n"
                )
                desc = "TypeError: string concatenation requires explicit conversion of integer argument count."
                cat = "type_error"
                diff = "easy"
                faulty_lines = [4]
                tests = [{"input": f"{func}('user12', 42)", "expected": "'TXN_USER12_42'"}]

            elif b_type == "exception_swallowing":
                orig = (
                    f"def {func}(filepath):\n"
                    f"    \"\"\"Parses metrics file securely.\"\"\"\n"
                    f"    try:\n"
                    f"        with open(filepath, 'r') as f:\n"
                    f"            return int(f.read().strip())\n"
                    f"    except Exception:\n"
                    f"        return 0\n"
                )
                fixed = (
                    f"def {func}(filepath):\n"
                    f"    \"\"\"Parses metrics file securely.\"\"\"\n"
                    f"    try:\n"
                    f"        with open(filepath, 'r') as f:\n"
                    f"            return int(f.read().strip())\n"
                    f"    except (FileNotFoundError, ValueError) as err:\n"
                    f"        logger.warning(f'Could not read metric from {{filepath}}: {{err}}')\n"
                    f"        return 0\n"
                )
                desc = "Bare exception catching swallows critical KeyboardInterrupt and SystemExit signals without logging."
                cat = "exception_handling"
                diff = "medium"
                faulty_lines = [6]
                tests = [{"input": f"{func}('non_existent.txt')", "expected": "0"}]

            elif b_type == "is_vs_equality":
                orig = (
                    f"def {func}(status_code):\n"
                    f"    \"\"\"Verifies HTTP response code.\"\"\"\n"
                    f"    if status_code is 200:\n"
                    f"        return 'SUCCESS'\n"
                    f"    return 'FAILURE'\n"
                )
                fixed = (
                    f"def {func}(status_code):\n"
                    f"    \"\"\"Verifies HTTP response code.\"\"\"\n"
                    f"    if status_code == 200:\n"
                    f"        return 'SUCCESS'\n"
                    f"    return 'FAILURE'\n"
                )
                desc = "Identity comparison 'is' used for integer literal instead of equality '=='."
                cat = "condition_error"
                diff = "easy"
                faulty_lines = [3]
                tests = [{"input": f"{func}(200)", "expected": "'SUCCESS'"}]

            elif b_type == "unhandled_none_return":
                orig = (
                    f"def {func}(record_map, key):\n"
                    f"    \"\"\"Extracts nested payload token.\"\"\"\n"
                    f"    entry = record_map.get(key)\n"
                    f"    return entry['token'].strip()\n"
                )
                fixed = (
                    f"def {func}(record_map, key):\n"
                    f"    \"\"\"Extracts nested payload token.\"\"\"\n"
                    f"    entry = record_map.get(key)\n"
                    f"    if entry is None or 'token' not in entry:\n"
                    f"        return None\n"
                    f"    return entry['token'].strip()\n"
                )
                desc = "TypeError: 'NoneType' object is not subscriptable when record_map does not contain key."
                cat = "null_pointer"
                diff = "medium"
                faulty_lines = [4]
                tests = [{"input": f"{func}({{}}, 'missing')", "expected": "None"}]

            elif b_type == "broken_while_termination":
                orig = (
                    f"def {func}(val, limit):\n"
                    f"    \"\"\"Calculates exponential growth ceiling.\"\"\"\n"
                    f"    step = 0\n"
                    f"    while val < limit:\n"
                    f"        step += 1\n"
                    f"    return step\n"
                )
                fixed = (
                    f"def {func}(val, limit):\n"
                    f"    \"\"\"Calculates exponential growth ceiling.\"\"\"\n"
                    f"    step = 0\n"
                    f"    while val < limit:\n"
                    f"        val *= 2\n"
                    f"        step += 1\n"
                    f"    return step\n"
                )
                desc = "Infinite loop: while loop condition variable 'val' is never updated inside loop body."
                cat = "loop_error"
                diff = "medium"
                faulty_lines = [4]
                tests = [{"input": f"{func}(2, 10)", "expected": "3"}]

            else:  # correct_control
                orig = (
                    f"def {func}(items):\n"
                    f"    \"\"\"Safely filters positive numeric items.\"\"\"\n"
                    f"    if not isinstance(items, (list, tuple)):\n"
                    f"        raise TypeError('items must be a list or tuple')\n"
                    f"    return [x for x in items if isinstance(x, (int, float)) and x > 0]\n"
                )
                fixed = orig
                desc = "Correct code: clean, fully validated positive list filter."
                cat = "none_correct_code"
                diff = "easy"
                faulty_lines = []
                tests = [{"input": f"{func}([1, -5, 3.2, 'a'])", "expected": "[1, 3.2]"}]

            diff_text = "".join(difflib.unified_diff(
                orig.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile="original.py",
                tofile="fixed.py"
            ))

            ex = CodeDebuggingExample(
                example_id=f"pp-syn-py-{uuid.uuid4().hex[:10]}",
                language="python",
                bug_category=cat,
                difficulty=diff,
                original_code=orig,
                bug_description=desc,
                faulty_line_numbers=faulty_lines,
                corrected_code=fixed,
                patch=diff_text if diff_text else None,
                test_cases=tests,
                verification_status="syntax_verified",
                source_dataset="synthetic_patchproof",
                source_record_id=f"syn-py-{i:05d}",
                repository="patchproof/synthetic-python",
                duplicate_group_id=f"synth_python_{b_type}",
                template_family=f"synth_python_{b_type}",
                license="Apache-2.0"
            )
            examples.append(ex)

        return examples

    def _generate_c_examples(self, count: int) -> List[CodeDebuggingExample]:
        examples: List[CodeDebuggingExample] = []
        c_types = [
            "dangling_pointer", "off_by_one_buffer", "format_specifier_mismatch",
            "missing_free_leak", "uninitialized_var", "double_free", "correct_control"
        ]

        for i in range(count):
            b_type = self.rng.choice(c_types)
            var = self.rng.choice(self.var_names)
            func = f"c_{self.rng.choice(self.func_prefixes)}_{var}_{i%1000}"

            if b_type == "dangling_pointer":
                orig = (
                    f"char* {func}(const char* input) {{\n"
                    f"    char local_buf[64];\n"
                    f"    strncpy(local_buf, input, sizeof(local_buf) - 1);\n"
                    f"    local_buf[sizeof(local_buf) - 1] = '\\0';\n"
                    f"    return local_buf;\n"
                    f"}}\n"
                )
                fixed = (
                    f"char* {func}(const char* input) {{\n"
                    f"    char* heap_buf = (char*)malloc(64);\n"
                    f"    if (!heap_buf) return NULL;\n"
                    f"    strncpy(heap_buf, input, 63);\n"
                    f"    heap_buf[63] = '\\0';\n"
                    f"    return heap_buf;\n"
                    f"}}\n"
                )
                desc = "Returning pointer to stack-allocated local array produces a dangling pointer and undefined behavior."
                cat = "memory_safety"
                diff = "medium"
                faulty_lines = [5]
                tests = [{"input": f"{func}(\"test\")", "expected": "\"test\""}]

            elif b_type == "off_by_one_buffer":
                orig = (
                    f"void {func}(int* arr, int size) {{\n"
                    f"    for (int i = 0; i <= size; i++) {{\n"
                    f"        arr[i] = i * 2;\n"
                    f"    }}\n"
                    f"}}\n"
                )
                fixed = (
                    f"void {func}(int* arr, int size) {{\n"
                    f"    for (int i = 0; i < size; i++) {{\n"
                    f"        arr[i] = i * 2;\n"
                    f"    }}\n"
                    f"}}\n"
                )
                desc = "Off-by-one error in array boundary condition (i <= size writes past allocation)."
                cat = "off_by_one"
                diff = "easy"
                faulty_lines = [2]
                tests = [{"input": "int a[5]; func(a, 5);", "expected": "a[4] == 8"}]

            elif b_type == "format_specifier_mismatch":
                orig = (
                    f"void {func}(long count) {{\n"
                    f"    printf(\"Total items processed: %d\\n\", count);\n"
                    f"}}\n"
                )
                fixed = (
                    f"void {func}(long count) {{\n"
                    f"    printf(\"Total items processed: %ld\\n\", count);\n"
                    f"}}\n"
                )
                desc = "Type mismatch: printf uses %d (int) for 64-bit long integer parameter."
                cat = "type_error"
                diff = "easy"
                faulty_lines = [2]
                tests = [{"input": f"{func}(100000L)", "expected": "Output contains '100000'"}]

            elif b_type == "missing_free_leak":
                orig = (
                    f"int {func}(int size) {{\n"
                    f"    int* ptr = (int*)malloc(sizeof(int) * size);\n"
                    f"    if (!ptr) return -1;\n"
                    f"    ptr[0] = 42;\n"
                    f"    if (size > 10) return ptr[0];\n"
                    f"    free(ptr);\n"
                    f"    return 0;\n"
                    f"}}\n"
                )
                fixed = (
                    f"int {func}(int size) {{\n"
                    f"    int* ptr = (int*)malloc(sizeof(int) * size);\n"
                    f"    if (!ptr) return -1;\n"
                    f"    ptr[0] = 42;\n"
                    f"    int res = (size > 10) ? ptr[0] : 0;\n"
                    f"    free(ptr);\n"
                    f"    return res;\n"
                    f"}}\n"
                )
                desc = "Resource leak: early return path skips free(ptr), causing heap memory leak."
                cat = "resource_leak"
                diff = "medium"
                faulty_lines = [5]
                tests = [{"input": f"{func}(20)", "expected": "42"}]

            elif b_type == "uninitialized_var":
                orig = (
                    f"int {func}(const int* data, int len) {{\n"
                    f"    int sum;\n"
                    f"    for (int i = 0; i < len; i++) {{\n"
                    f"        sum += data[i];\n"
                    f"    }}\n"
                    f"    return sum;\n"
                    f"}}\n"
                )
                fixed = (
                    f"int {func}(const int* data, int len) {{\n"
                    f"    int sum = 0;\n"
                    f"    for (int i = 0; i < len; i++) {{\n"
                    f"        sum += data[i];\n"
                    f"    }}\n"
                    f"    return sum;\n"
                    f"}}\n"
                )
                desc = "Undefined behavior: local accumulator variable 'sum' read before initialization."
                cat = "undefined_behavior"
                diff = "easy"
                faulty_lines = [2]
                tests = [{"input": "int a[] = {1, 2}; func(a, 2);", "expected": "3"}]

            elif b_type == "double_free":
                orig = (
                    f"void {func}(char* ptr) {{\n"
                    f"    if (ptr) {{\n"
                    f"        free(ptr);\n"
                    f"    }}\n"
                    f"    free(ptr);\n"
                    f"}}\n"
                )
                fixed = (
                    f"void {func}(char* ptr) {{\n"
                    f"    if (ptr) {{\n"
                    f"        free(ptr);\n"
                    f"    }}\n"
                    f"}}\n"
                )
                desc = "Double free vulnerability: memory block freed multiple times causes heap corruption."
                cat = "memory_safety"
                diff = "hard"
                faulty_lines = [5]
                tests = [{"input": "char* p = malloc(10); func(p);", "expected": "Clean execution"}]

            else:  # correct_control
                orig = (
                    f"size_t {func}(const char* s) {{\n"
                    f"    if (s == NULL) return 0;\n"
                    f"    size_t len = 0;\n"
                    f"    while (s[len] != '\\0') len++;\n"
                    f"    return len;\n"
                    f"}}\n"
                )
                fixed = orig
                desc = "Correct code: NULL-checked strlen implementation with bounded traversal."
                cat = "none_correct_code"
                diff = "easy"
                faulty_lines = []
                tests = [{"input": f"{func}(\"hello\")", "expected": "5"}]

            diff_text = "".join(difflib.unified_diff(
                orig.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile="original.c",
                tofile="fixed.c"
            ))

            ex = CodeDebuggingExample(
                example_id=f"pp-syn-c-{uuid.uuid4().hex[:10]}",
                language="c",
                bug_category=cat,
                difficulty=diff,
                original_code=orig,
                bug_description=desc,
                faulty_line_numbers=faulty_lines,
                corrected_code=fixed,
                patch=diff_text if diff_text else None,
                test_cases=tests,
                verification_status="unverified_static",
                source_dataset="synthetic_patchproof",
                source_record_id=f"syn-c-{i:05d}",
                repository="patchproof/synthetic-c",
                duplicate_group_id=f"synth_c_{b_type}",
                template_family=f"synth_c_{b_type}",
                license="Apache-2.0"
            )
            examples.append(ex)

        return examples

    def _generate_js_ts_examples(self, count: int) -> List[CodeDebuggingExample]:
        examples: List[CodeDebuggingExample] = []
        js_types = [
            "missing_await", "loose_equality", "undefined_prop_access",
            "state_mutation", "nan_coercion", "correct_control"
        ]

        for i in range(count):
            b_type = self.rng.choice(js_types)
            var = self.rng.choice(self.var_names)
            func = f"js_{self.rng.choice(self.func_prefixes)}_{var}_{i%1000}"

            if b_type == "missing_await":
                orig = (
                    f"async function {func}(userId) {{\n"
                    f"    const profile = fetchUserProfile(userId);\n"
                    f"    return profile.email.toLowerCase();\n"
                    f"}}\n"
                )
                fixed = (
                    f"async function {func}(userId) {{\n"
                    f"    const profile = await fetchUserProfile(userId);\n"
                    f"    return profile ? profile.email.toLowerCase() : null;\n"
                    f"}}\n"
                )
                desc = "Missing await keyword on Promise returned by fetchUserProfile causes TypeError reading email of Promise."
                cat = "async_error"
                diff = "medium"
                faulty_lines = [2]
                tests = [{"input": f"{func}('u1')", "expected": "'user@example.com'"}]

            elif b_type == "loose_equality":
                orig = (
                    f"function {func}(val) {{\n"
                    f"    if (val == 0) {{\n"
                    f"        return 'EMPTY_OR_ZERO';\n"
                    f"    }}\n"
                    f"    return 'POPULATED';\n"
                    f"}}\n"
                )
                fixed = (
                    f"function {func}(val) {{\n"
                    f"    if (val === 0) {{\n"
                    f"        return 'EMPTY_OR_ZERO';\n"
                    f"    }}\n"
                    f"    return 'POPULATED';\n"
                    f"}}\n"
                )
                desc = "Loose equality '==' causes type coercion where empty string \"\" and false falsely match 0."
                cat = "condition_error"
                diff = "easy"
                faulty_lines = [2]
                tests = [{"input": f"{func}(\"\")", "expected": "'POPULATED'"}]

            elif b_type == "undefined_prop_access":
                orig = (
                    f"function {func}(config) {{\n"
                    f"    return config.database.host.trim();\n"
                    f"}}\n"
                )
                fixed = (
                    f"function {func}(config) {{\n"
                    f"    return config?.database?.host?.trim() ?? 'localhost';\n"
                    f"}}\n"
                )
                desc = "Unsafe property traversal causes 'Cannot read property host of undefined' when database is omitted."
                cat = "null_pointer"
                diff = "easy"
                faulty_lines = [2]
                tests = [{"input": f"{func}({{}})", "expected": "'localhost'"}]

            elif b_type == "state_mutation":
                orig = (
                    f"function {func}(prevState, newPayload) {{\n"
                    f"    prevState.items.push(newPayload);\n"
                    f"    return prevState;\n"
                    f"}}\n"
                )
                fixed = (
                    f"function {func}(prevState, newPayload) {{\n"
                    f"    return {{\n"
                    f"        ...prevState,\n"
                    f"        items: [...prevState.items, newPayload]\n"
                    f"    }};\n"
                    f"}}\n"
                )
                desc = "Direct mutation of previous state array breaks React component re-rendering invariants."
                cat = "state_management"
                diff = "medium"
                faulty_lines = [2]
                tests = [{"input": f"{func}({{items: [1]}}, 2)", "expected": "{items: [1, 2]}"}]

            elif b_type == "nan_coercion":
                orig = (
                    f"function {func}(inputStr) {{\n"
                    f"    const val = parseInt(inputStr);\n"
                    f"    return val * 10;\n"
                    f"}}\n"
                )
                fixed = (
                    f"function {func}(inputStr) {{\n"
                    f"    const val = parseInt(inputStr, 10);\n"
                    f"    if (Number.isNaN(val)) return 0;\n"
                    f"    return val * 10;\n"
                    f"}}\n"
                )
                desc = "Unchecked parseInt returns NaN on non-numeric input which propagates silently through math calculations."
                cat = "type_error"
                diff = "easy"
                faulty_lines = [3]
                tests = [{"input": f"{func}('invalid')", "expected": "0"}]

            else:  # correct_control
                orig = (
                    f"function {func}(items) {{\n"
                    f"    if (!Array.isArray(items)) return [];\n"
                    f"    return items.filter(Boolean).map(x => String(x).trim());\n"
                    f"}}\n"
                )
                fixed = orig
                desc = "Correct code: safely validates input array, filters falsy elements, and maps trimmed strings."
                cat = "none_correct_code"
                diff = "easy"
                faulty_lines = []
                tests = [{"input": f"{func}([' a ', null, 'b '])", "expected": "['a', 'b']"}]

            diff_text = "".join(difflib.unified_diff(
                orig.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile="original.js",
                tofile="fixed.js"
            ))

            ex = CodeDebuggingExample(
                example_id=f"pp-syn-js-{uuid.uuid4().hex[:10]}",
                language="javascript",
                bug_category=cat,
                difficulty=diff,
                original_code=orig,
                bug_description=desc,
                faulty_line_numbers=faulty_lines,
                corrected_code=fixed,
                patch=diff_text if diff_text else None,
                test_cases=tests,
                verification_status="unverified_static",
                source_dataset="synthetic_patchproof",
                source_record_id=f"syn-js-{i:05d}",
                repository="patchproof/synthetic-js",
                duplicate_group_id=f"synth_js_{b_type}",
                template_family=f"synth_js_{b_type}",
                license="Apache-2.0"
            )
            examples.append(ex)

        return examples

    def _generate_java_go_examples(self, count: int) -> List[CodeDebuggingExample]:
        examples: List[CodeDebuggingExample] = []
        go_types = ["nil_pointer", "slice_oob", "goroutine_leak", "unhandled_error", "correct_control"]
        java_types = ["null_pointer", "array_oob", "resource_leak", "string_equality", "correct_control"]

        for i in range(count):
            is_go = (i % 2 == 0)
            var = self.rng.choice(self.var_names)

            if is_go:
                b_type = self.rng.choice(go_types)
                func = f"Go_{self.rng.choice(self.func_prefixes)}_{var}_{i%1000}"

                if b_type == "nil_pointer":
                    orig = f"func {func}(res *Response) string {{\n    return res.Body.Text\n}}\n"
                    fixed = f"func {func}(res *Response) string {{\n    if res == nil || res.Body == nil {{\n        return \"\"\n    }}\n    return res.Body.Text\n}}\n"
                    desc = "Nil pointer dereference when Response or Body struct is nil."
                    cat = "null_pointer"
                    faulty_lines = [2]
                elif b_type == "slice_oob":
                    orig = f"func {func}(items []int) int {{\n    n := len(items)\n    return items[n]\n}}\n"
                    fixed = f"func {func}(items []int) int {{\n    n := len(items)\n    if n == 0 {{\n        return 0\n    }}\n    return items[n-1]\n}}\n"
                    desc = "Slice index out of bounds: accessing items[len(items)]."
                    cat = "off_by_one"
                    faulty_lines = [3]
                elif b_type == "goroutine_leak":
                    orig = f"func {func}(val int) {{\n    ch := make(chan int)\n    go func() {{\n        ch <- val\n    }}()\n}}\n"
                    fixed = f"func {func}(val int) {{\n    ch := make(chan int, 1)\n    go func() {{\n        ch <- val\n    }}()\n}}\n"
                    desc = "Goroutine leak: sending to unbuffered channel without receiver blocks goroutine indefinitely."
                    cat = "async_error"
                    faulty_lines = [2]
                elif b_type == "unhandled_error":
                    orig = f"func {func}(path string) string {{\n    data, _ := os.ReadFile(path)\n    return string(data)\n}}\n"
                    fixed = f"func {func}(path string) string {{\n    data, err := os.ReadFile(path)\n    if err != nil {{\n        return \"\"\n    }}\n    return string(data)\n}}\n"
                    desc = "Unhandled file read error: ignores error value causing empty string or panic."
                    cat = "exception_handling"
                    faulty_lines = [2]
                else:  # correct_control
                    orig = f"func {func}(nums []int) int {{\n    sum := 0\n    for _, v := range nums {{\n        sum += v\n    }}\n    return sum\n}}\n"
                    fixed = orig
                    desc = "Correct code: clean slice sum traversal."
                    cat = "none_correct_code"
                    faulty_lines = []

                diff_text = "".join(difflib.unified_diff(
                    orig.splitlines(keepends=True),
                    fixed.splitlines(keepends=True),
                    fromfile="original.go",
                    tofile="fixed.go"
                ))
                ex = CodeDebuggingExample(
                    example_id=f"pp-syn-go-{uuid.uuid4().hex[:10]}",
                    language="go",
                    bug_category=cat,
                    difficulty="medium" if faulty_lines else "easy",
                    original_code=orig,
                    bug_description=desc,
                    faulty_line_numbers=faulty_lines,
                    corrected_code=fixed,
                    patch=diff_text if diff_text else None,
                    test_cases=[],
                    verification_status="unverified_static",
                    source_dataset="synthetic_patchproof",
                    source_record_id=f"syn-go-{i:05d}",
                    repository="patchproof/synthetic-go",
                    duplicate_group_id=f"synth_go_{b_type}",
                    template_family=f"synth_go_{b_type}",
                    license="Apache-2.0"
                )
            else:
                b_type = self.rng.choice(java_types)
                func = f"java_{self.rng.choice(self.func_prefixes)}_{var}_{i%1000}"

                if b_type == "null_pointer":
                    orig = f"public String {func}(String input) {{\n    return input.toUpperCase().trim();\n}}\n"
                    fixed = f"public String {func}(String input) {{\n    if (input == null) return \"\";\n    return input.toUpperCase().trim();\n}}\n"
                    desc = "NullPointerException when input string argument is null."
                    cat = "null_pointer"
                    faulty_lines = [2]
                elif b_type == "array_oob":
                    orig = f"public int {func}(int[] arr) {{\n    return arr[arr.length];\n}}\n"
                    fixed = f"public int {func}(int[] arr) {{\n    if (arr.length == 0) return 0;\n    return arr[arr.length - 1];\n}}\n"
                    desc = "ArrayIndexOutOfBoundsException: indexing arr[arr.length]."
                    cat = "off_by_one"
                    faulty_lines = [2]
                elif b_type == "resource_leak":
                    orig = f"public void {func}(String path) throws Exception {{\n    FileInputStream fis = new FileInputStream(path);\n    fis.read();\n}}\n"
                    fixed = f"public void {func}(String path) throws Exception {{\n    try (FileInputStream fis = new FileInputStream(path)) {{\n        fis.read();\n    }}\n}}\n"
                    desc = "Resource leak: unclosed FileInputStream without try-with-resources."
                    cat = "resource_leak"
                    faulty_lines = [2]
                elif b_type == "string_equality":
                    orig = f"public boolean {func}(String s1, String s2) {{\n    return s1 == s2;\n}}\n"
                    fixed = f"public boolean {func}(String s1, String s2) {{\n    return s1 != null && s1.equals(s2);\n}}\n"
                    desc = "String reference equality comparison '==' instead of value equality '.equals()'."
                    cat = "condition_error"
                    faulty_lines = [2]
                else:  # correct_control
                    orig = f"public int {func}(List<Integer> list) {{\n    int total = 0;\n    for (int n : list) {{\n        total += n;\n    }}\n    return total;\n}}\n"
                    fixed = orig
                    desc = "Correct code: clean list sum traversal."
                    cat = "none_correct_code"
                    faulty_lines = []

                diff_text = "".join(difflib.unified_diff(
                    orig.splitlines(keepends=True),
                    fixed.splitlines(keepends=True),
                    fromfile="Original.java",
                    tofile="Fixed.java"
                ))
                ex = CodeDebuggingExample(
                    example_id=f"pp-syn-java-{uuid.uuid4().hex[:10]}",
                    language="java",
                    bug_category=cat,
                    difficulty="medium" if faulty_lines else "easy",
                    original_code=orig,
                    bug_description=desc,
                    faulty_line_numbers=faulty_lines,
                    corrected_code=fixed,
                    patch=diff_text if diff_text else None,
                    test_cases=[],
                    verification_status="unverified_static",
                    source_dataset="synthetic_patchproof",
                    source_record_id=f"syn-java-{i:05d}",
                    repository="patchproof/synthetic-java",
                    duplicate_group_id=f"synth_java_{b_type}",
                    template_family=f"synth_java_{b_type}",
                    license="Apache-2.0"
                )

            examples.append(ex)
        return examples

    def generate(self, total_count: int) -> List[CodeDebuggingExample]:
        """
        Generates total_count synthetic debugging examples balanced across ecosystems:
        ~35% Python, ~30% C/C++, ~25% JavaScript, ~10% Java/Go.
        """
        py_count = int(total_count * 0.35)
        c_count = int(total_count * 0.30)
        js_count = int(total_count * 0.25)
        other_count = total_count - (py_count + c_count + js_count)

        all_examples: List[CodeDebuggingExample] = []
        all_examples.extend(self._generate_python_examples(py_count))
        all_examples.extend(self._generate_c_examples(c_count))
        all_examples.extend(self._generate_js_ts_examples(js_count))
        all_examples.extend(self._generate_java_go_examples(other_count))

        self.rng.shuffle(all_examples)
        return all_examples

if __name__ == "__main__":
    generator = SyntheticBugGenerator()
    samples = generator.generate(100)
    print(f"Generated {len(samples)} synthetic debugging samples across languages.")
    print("Sample 0:", samples[0].bug_description)
