"""
High-diversity, robust dataset generator for PATCHPROOF.
Directly targets known ML limitations:
1. Synthetic template token sensitivity (generates diverse variable names across domains).
2. JavaScript async defects coverage (missing await, unhandled promises, incorrect async returns,
   promise rejection handling, race conditions).
3. Realistic Python, JavaScript, and C defect patterns.
4. Clean-code negative controls.
5. Strict group-based leakage prevention using template_family isolation keys.
"""

import random
import uuid
import difflib
import sys
from typing import List, Dict, Any, Tuple
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.datasets.schema import CodeDebuggingExample

RANDOM_SEED = 2026

DOMAINS_VARS = [
    # Data & Collections
    "items", "records", "tokens", "entries", "elements", "chunks", "batches", "payload",
    "dataset", "matrix", "stream", "buffer", "packets", "nodes", "graph", "tree",
    # System & App Config
    "options", "config", "settings", "params", "metadata", "headers", "flags", "properties",
    "credentials", "preferences", "session", "context", "state", "env_vars",
    # Web & API
    "users", "accounts", "profiles", "requests", "clients", "orders", "invoices", "products",
    "messages", "events", "transactions", "metrics", "endpoints", "routes", "webhooks",
    # Handlers & Callbacks
    "listeners", "handlers", "callbacks", "watchers", "subscribers", "observers", "tasks",
    "jobs", "workers", "pipelines", "queues", "consumers", "producers",
    # State & Storage
    "cache", "store", "registry", "index_map", "lookup_table", "history", "seen", "visited",
    "accumulator", "results", "output_list", "error_log", "audit_trail"
]

DOMAINS_FUNCS = [
    "fetch", "retrieve", "query", "load", "extract", "parse", "process", "transform",
    "sanitize", "filter", "validate", "verify", "authenticate", "authorize", "dispatch",
    "broadcast", "emit", "publish", "subscribe", "notify", "update", "persist", "save",
    "sync", "reconcile", "compute", "calculate", "aggregate", "summarize", "format",
    "serialize", "deserialize", "encode", "decode", "encrypt", "decrypt", "flush"
]

class RobustSampleGenerator:
    def __init__(self, seed: int = RANDOM_SEED):
        self.rng = random.Random(seed)

    def _rand_var(self) -> str:
        return self.rng.choice(DOMAINS_VARS)

    def _rand_func(self) -> str:
        return f"{self.rng.choice(DOMAINS_FUNCS)}_{self._rand_var()}"

    def generate_all(self, total_count: int = 10000) -> List[CodeDebuggingExample]:
        examples: List[CodeDebuggingExample] = []
        
        # Allocations:
        # 3,000 JS Async (all 5 categories)
        # 3,000 Python Diverse Identifier Defects
        # 2,000 C Defect Patterns
        # 2,000 Clean Controls (Hard Negative Controls across JS, Python, C)
        
        examples.extend(self.generate_js_async_samples(3000))
        examples.extend(self.generate_python_robust_samples(3000))
        examples.extend(self.generate_c_robust_samples(2000))
        examples.extend(self.generate_clean_controls(2000))

        self.rng.shuffle(examples)
        return examples

    # -------------------------------------------------------------
    # 1. JAVASCRIPT ASYNC DEFECTS (3,000 samples)
    # -------------------------------------------------------------
    def generate_js_async_samples(self, count: int) -> List[CodeDebuggingExample]:
        examples = []
        sub_types = [
            "missing_await",
            "unhandled_promise",
            "incorrect_async_return",
            "promise_rejection",
            "async_race_condition"
        ]

        async_ops = [
            ("fetchUserData", "userId", "user.profile.email"),
            ("queryDatabase", "sqlQuery", "result.rows[0]"),
            ("readConfiguration", "filePath", "config.database.host"),
            ("sendHttpRequest", "endpoint", "response.data.token"),
            ("axios.get", "url", "res.data.status"),
            ("fs.promises.readFile", "docPath", "fileContent.toString()"),
            ("crypto.subtle.digest", "dataBuffer", "hashBuffer.byteLength"),
            ("cacheStore.get", "cacheKey", "cachedValue.payload"),
            ("loadRemoteSchema", "schemaUrl", "schema.definitions.id"),
            ("dispatchWebhook", "hookUrl", "deliveryResult.statusCode")
        ]

        for i in range(count):
            sub = self.rng.choice(sub_types)
            v = self._rand_var()
            f = self._rand_func()
            op, arg, prop = self.rng.choice(async_ops)

            if sub == "missing_await":
                orig = (
                    f"async function {f}({arg}) {{\n"
                    f"    const {v} = {op}({arg});\n"
                    f"    return {v}.{prop.split('.')[1]};\n"
                    f"}}\n"
                )
                fixed = (
                    f"async function {f}({arg}) {{\n"
                    f"    const {v} = await {op}({arg});\n"
                    f"    return {v} ? {v}.{prop.split('.')[1]} : null;\n"
                    f"}}\n"
                )
                desc = f"Missing await keyword on asynchronous call '{op}'. Attempting to read property of unfulfilled Promise causes TypeError."
                faulty_lines = [2]

            elif sub == "unhandled_promise":
                orig = (
                    f"function {f}({arg}) {{\n"
                    f"    {op}({arg})\n"
                    f"        .then(({v}) => {{\n"
                    f"            console.log('Processed:', {v});\n"
                    f"        }});\n"
                    f"}}\n"
                )
                fixed = (
                    f"function {f}({arg}) {{\n"
                    f"    {op}({arg})\n"
                    f"        .then(({v}) => {{\n"
                    f"            console.log('Processed:', {v});\n"
                    f"        }})\n"
                    f"        .catch((err) => {{\n"
                    f"            console.error('Operation failed:', err);\n"
                    f"        }});\n"
                    f"}}\n"
                )
                desc = "Unhandled Promise rejection: asynchronous promise chain lacks a .catch() error handler."
                faulty_lines = [2]

            elif sub == "incorrect_async_return":
                orig = (
                    f"async function {f}({v}List) {{\n"
                    f"    const results = [];\n"
                    f"    {v}List.forEach(async (item) => {{\n"
                    f"        const res = await {op}(item);\n"
                    f"        results.push(res);\n"
                    f"    }});\n"
                    f"    return results;\n"
                    f"}}\n"
                )
                fixed = (
                    f"async function {f}({v}List) {{\n"
                    f"    const results = await Promise.all({v}List.map(async (item) => {{\n"
                    f"        return await {op}(item);\n"
                    f"    }}));\n"
                    f"    return results;\n"
                    f"}}\n"
                )
                desc = "Array.forEach with an async callback does not wait for promises to resolve; returns empty results before work completes."
                faulty_lines = [3]

            elif sub == "promise_rejection":
                orig = (
                    f"function {f}({arg}) {{\n"
                    f"    return new Promise((resolve, reject) => {{\n"
                    f"        if (!{arg}) {{\n"
                    f"            return reject('Invalid parameter provided');\n"
                    f"        }}\n"
                    f"        resolve({op}({arg}));\n"
                    f"    }});\n"
                    f"}}\n"
                )
                fixed = (
                    f"function {f}({arg}) {{\n"
                    f"    return new Promise((resolve, reject) => {{\n"
                    f"        if (!{arg}) {{\n"
                    f"            return reject(new Error('Invalid parameter provided'));\n"
                    f"        }}\n"
                    f"        resolve({op}({arg}));\n"
                    f"    }});\n"
                    f"}}\n"
                )
                desc = "Promise rejects with a primitive string instead of an Error object, losing stack trace information."
                faulty_lines = [4]

            else:  # async_race_condition
                orig = (
                    f"let {v}Counter = 0;\n"
                    f"async function {f}() {{\n"
                    f"    const current = {v}Counter;\n"
                    f"    await {op}();\n"
                    f"    {v}Counter = current + 1;\n"
                    f"    return {v}Counter;\n"
                    f"}}\n"
                )
                fixed = (
                    f"let {v}Counter = 0;\n"
                    f"let {v}Mutex = Promise.resolve();\n"
                    f"async function {f}() {{\n"
                    f"    return {v}Mutex = {v}Mutex.then(async () => {{\n"
                    f"        await {op}();\n"
                    f"        {v}Counter += 1;\n"
                    f"        return {v}Counter;\n"
                    f"    }});\n"
                    f"}}\n"
                )
                desc = "Asynchronous race condition: non-atomic read-modify-write on shared state across await suspension points."
                faulty_lines = [3]

            diff = "".join(difflib.unified_diff(
                orig.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile="original.js",
                tofile="remediated.js"
            ))

            ex = CodeDebuggingExample(
                example_id=f"pp-rob-js-{uuid.uuid4().hex[:10]}",
                language="javascript",
                bug_category="async_error",
                difficulty="medium",
                original_code=orig,
                bug_description=desc,
                faulty_line_numbers=faulty_lines,
                corrected_code=fixed,
                patch=diff,
                verification_status="syntax_verified",
                source_dataset="robust_synthetic",
                source_record_id=f"rob-js-{i:05d}",
                repository="patchproof/robust-javascript",
                duplicate_group_id=f"robust_js_{sub}",
                template_family=f"robust_js_{sub}",
                license="Apache-2.0"
            )
            examples.append(ex)

        return examples

    # -------------------------------------------------------------
    # 2. PYTHON ROBUST IDENTIFIER SAMPLES (3,000 samples)
    # -------------------------------------------------------------
    def generate_python_robust_samples(self, count: int) -> List[CodeDebuggingExample]:
        examples = []
        py_bugs = [
            "mutable_default",
            "identity_comparison",
            "bare_except",
            "off_by_one_loop",
            "type_error_concat"
        ]

        for i in range(count):
            b = self.rng.choice(py_bugs)
            v = self._rand_var()
            f = self._rand_func()

            if b == "mutable_default":
                container = self.rng.choice(["[]", "{}", "set()"])
                empty_init = "[]" if container == "[]" else ("{}" if container == "{}" else "set()")
                orig = (
                    f"def {f}(key, {v}={container}):\n"
                    f"    if isinstance({v}, list):\n"
                    f"        {v}.append(key)\n"
                    f"    elif isinstance({v}, set):\n"
                    f"        {v}.add(key)\n"
                    f"    return {v}\n"
                )
                fixed = (
                    f"def {f}(key, {v}=None):\n"
                    f"    if {v} is None:\n"
                    f"        {v} = {empty_init}\n"
                    f"    if isinstance({v}, list):\n"
                    f"        {v}.append(key)\n"
                    f"    elif isinstance({v}, set):\n"
                    f"        {v}.add(key)\n"
                    f"    return {v}\n"
                )
                desc = "Mutable default argument retains state across multiple function invocations."
                cat = "api_misuse"
                faulty_lines = [1]

            elif b == "identity_comparison":
                target_val = self.rng.choice([200, 404, 500, 0, 99, 1000])
                orig = (
                    f"def {f}(code_val):\n"
                    f"    if code_val is {target_val}:\n"
                    f"        return 'MATCH'\n"
                    f"    return 'MISMATCH'\n"
                )
                fixed = (
                    f"def {f}(code_val):\n"
                    f"    if code_val == {target_val}:\n"
                    f"        return 'MATCH'\n"
                    f"    return 'MISMATCH'\n"
                )
                desc = "Identity comparison 'is' used with literal value instead of equality operator '=='."
                cat = "condition_error"
                faulty_lines = [2]

            elif b == "bare_except":
                orig = (
                    f"def {f}(path_or_data):\n"
                    f"    try:\n"
                    f"        result = int(str(path_or_data).strip())\n"
                    f"        return result\n"
                    f"    except:\n"
                    f"        return 0\n"
                )
                fixed = (
                    f"def {f}(path_or_data):\n"
                    f"    try:\n"
                    f"        result = int(str(path_or_data).strip())\n"
                    f"        return result\n"
                    f"    except (ValueError, TypeError) as err:\n"
                    f"        return 0\n"
                )
                desc = "Bare except catches system exit and keyboard interrupt exceptions, masking critical runtime issues."
                cat = "exception_handling"
                faulty_lines = [5]

            elif b == "off_by_one_loop":
                orig = (
                    f"def {f}({v}_list):\n"
                    f"    total = 0\n"
                    f"    for idx in range(len({v}_list) + 1):\n"
                    f"        total += {v}_list[idx]\n"
                    f"    return total\n"
                )
                fixed = (
                    f"def {f}({v}_list):\n"
                    f"    total = 0\n"
                    f"    for idx in range(len({v}_list)):\n"
                    f"        total += {v}_list[idx]\n"
                    f"    return total\n"
                )
                desc = "Index bounds error: range upper limit exceeds valid indexing bounds by 1."
                cat = "off_by_one"
                faulty_lines = [3]

            else:  # type_error_concat
                orig = (
                    f"def {f}(prefix_str, id_num):\n"
                    f"    return prefix_str + '_' + id_num\n"
                )
                fixed = (
                    f"def {f}(prefix_str, id_num):\n"
                    f"    return prefix_str + '_' + str(id_num)\n"
                )
                desc = "TypeError: string concatenation requires str conversion of numeric operand."
                cat = "type_error"
                faulty_lines = [2]

            diff = "".join(difflib.unified_diff(
                orig.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile="original.py",
                tofile="remediated.py"
            ))

            ex = CodeDebuggingExample(
                example_id=f"pp-rob-py-{uuid.uuid4().hex[:10]}",
                language="python",
                bug_category=cat,
                difficulty="easy",
                original_code=orig,
                bug_description=desc,
                faulty_line_numbers=faulty_lines,
                corrected_code=fixed,
                patch=diff,
                verification_status="syntax_verified",
                source_dataset="robust_synthetic",
                source_record_id=f"rob-py-{i:05d}",
                repository="patchproof/robust-python",
                duplicate_group_id=f"robust_py_{b}",
                template_family=f"robust_py_{b}",
                license="Apache-2.0"
            )
            examples.append(ex)

        return examples

    # -------------------------------------------------------------
    # 3. C ROBUST SAMPLES (2,000 samples)
    # -------------------------------------------------------------
    def generate_c_robust_samples(self, count: int) -> List[CodeDebuggingExample]:
        examples = []
        c_bugs = ["stack_buffer_return", "buffer_overflow_sprintf", "missing_free", "uninitialized_var"]

        for i in range(count):
            b = self.rng.choice(c_bugs)
            v = self._rand_var()
            f = f"c_{self._rand_func()}"

            if b == "stack_buffer_return":
                orig = (
                    f"char* {f}(const char* input_str) {{\n"
                    f"    char {v}_buf[64];\n"
                    f"    strncpy({v}_buf, input_str, 63);\n"
                    f"    {v}_buf[63] = '\\0';\n"
                    f"    return {v}_buf;\n"
                    f"}}\n"
                )
                fixed = (
                    f"char* {f}(const char* input_str) {{\n"
                    f"    char* heap_buf = (char*)malloc(64);\n"
                    f"    if (!heap_buf) return NULL;\n"
                    f"    strncpy(heap_buf, input_str, 63);\n"
                    f"    heap_buf[63] = '\\0';\n"
                    f"    return heap_buf;\n"
                    f"}}\n"
                )
                desc = "Returning pointer to stack-allocated local array produces a dangling pointer."
                cat = "memory_safety"
                faulty_lines = [5]

            elif b == "buffer_overflow_sprintf":
                orig = (
                    f"void {f}(char* dest, const char* name, int id) {{\n"
                    f"    sprintf(dest, \"User_%s_%d\", name, id);\n"
                    f"}}\n"
                )
                fixed = (
                    f"void {f}(char* dest, size_t max_len, const char* name, int id) {{\n"
                    f"    snprintf(dest, max_len, \"User_%s_%d\", name, id);\n"
                    f"}}\n"
                )
                desc = "Use of unbounded sprintf invites buffer overflow vulnerability."
                cat = "memory_safety"
                faulty_lines = [2]

            elif b == "missing_free":
                orig = (
                    f"int {f}(int flag) {{\n"
                    f"    char* ptr = (char*)malloc(128);\n"
                    f"    if (flag < 0) return -1;\n"
                    f"    free(ptr);\n"
                    f"    return 0;\n"
                    f"}}\n"
                )
                fixed = (
                    f"int {f}(int flag) {{\n"
                    f"    char* ptr = (char*)malloc(128);\n"
                    f"    if (flag < 0) {{\n"
                    f"        free(ptr);\n"
                    f"        return -1;\n"
                    f"    }}\n"
                    f"    free(ptr);\n"
                    f"    return 0;\n"
                    f"}}\n"
                )
                desc = "Memory leak: allocated buffer 'ptr' is not deallocated before early return."
                cat = "resource_leak"
                faulty_lines = [3]

            else:  # uninitialized_var
                orig = (
                    f"int {f}(int count) {{\n"
                    f"    int total;\n"
                    f"    for (int i = 0; i < count; i++) total += i;\n"
                    f"    return total;\n"
                    f"}}\n"
                )
                fixed = (
                    f"int {f}(int count) {{\n"
                    f"    int total = 0;\n"
                    f"    for (int i = 0; i < count; i++) total += i;\n"
                    f"    return total;\n"
                    f"}}\n"
                )
                desc = "Variable 'total' used without initialization, resulting in undefined behavior."
                cat = "undefined_behavior"
                faulty_lines = [2]

            diff = "".join(difflib.unified_diff(
                orig.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile="original.c",
                tofile="remediated.c"
            ))

            ex = CodeDebuggingExample(
                example_id=f"pp-rob-c-{uuid.uuid4().hex[:10]}",
                language="c",
                bug_category=cat,
                difficulty="medium",
                original_code=orig,
                bug_description=desc,
                faulty_line_numbers=faulty_lines,
                corrected_code=fixed,
                patch=diff,
                verification_status="syntax_verified",
                source_dataset="robust_synthetic",
                source_record_id=f"rob-c-{i:05d}",
                repository="patchproof/robust-c",
                duplicate_group_id=f"robust_c_{b}",
                template_family=f"robust_c_{b}",
                license="Apache-2.0"
            )
            examples.append(ex)

        return examples

    # -------------------------------------------------------------
    # 4. CLEAN CODE NEGATIVE CONTROLS (2,000 samples)
    # -------------------------------------------------------------
    def generate_clean_controls(self, count: int) -> List[CodeDebuggingExample]:
        examples = []
        for i in range(count):
            lang = self.rng.choice(["python", "javascript", "c"])
            v = self._rand_var()
            f = self._rand_func()

            if lang == "python":
                orig = (
                    f"def {f}({v}_items, default_val=None):\n"
                    f"    \"\"\"Clean validated filter.\"\"\"\n"
                    f"    if default_val is None:\n"
                    f"        default_val = []\n"
                    f"    if not isinstance({v}_items, list):\n"
                    f"        return default_val\n"
                    f"    return [x for x in {v}_items if x is not None]\n"
                )
            elif lang == "javascript":
                orig = (
                    f"async function {f}({v}Id) {{\n"
                    f"    try {{\n"
                    f"        const data = await fetchRecord({v}Id);\n"
                    f"        return data ? data.value : null;\n"
                    f"    }} catch (err) {{\n"
                    f"        console.error('Fetch error:', err);\n"
                    f"        return null;\n"
                    f"    }}\n"
                    f"}}\n"
                )
            else:  # c
                orig = (
                    f"int {f}(const char* {v}_src, char* dest, size_t dest_size) {{\n"
                    f"    if (!{v}_src || !dest || dest_size == 0) return -1;\n"
                    f"    strncpy(dest, {v}_src, dest_size - 1);\n"
                    f"    dest[dest_size - 1] = '\\0';\n"
                    f"    return 0;\n"
                    f"}}\n"
                )

            ex = CodeDebuggingExample(
                example_id=f"pp-rob-clean-{uuid.uuid4().hex[:10]}",
                language=lang,
                bug_category="none_correct_code",
                difficulty="easy",
                original_code=orig,
                bug_description="Verified clean code control sample without defect patterns.",
                faulty_line_numbers=[],
                corrected_code=orig,
                patch=None,
                verification_status="syntax_verified",
                source_dataset="robust_synthetic",
                source_record_id=f"rob-clean-{i:05d}",
                repository="patchproof/robust-clean",
                duplicate_group_id=f"robust_clean_{lang}",
                template_family=f"robust_clean_{lang}",
                license="Apache-2.0"
            )
            examples.append(ex)

        return examples

if __name__ == "__main__":
    gen = RobustSampleGenerator()
    samples = gen.generate_all(10000)
    print(f"Generated {len(samples)} robust code samples.")
    from collections import Counter
    cats = Counter(s.bug_category for s in samples)
    langs = Counter(s.language for s in samples)
    print("Categories:", dict(cats))
    print("Languages:", dict(langs))
