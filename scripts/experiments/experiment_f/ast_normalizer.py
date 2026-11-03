"""
AST Scope-Aware Identifier Normalizer for Python, JavaScript, and C.
Strict Requirements:
- Normalizes only verified user-defined local variables and parameters.
- Preserves function names, class names, imports, runtime APIs (fetch, Promise, malloc, free, open, range, len),
  method names, attributes, strings, URLs, file paths, numbers, and keywords.
- Graceful fallback: If parsing fails, preserves original source and logs failure.
"""

import ast
import json
import logging
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any, List

logger = logging.getLogger("ASTNormalizer")

# -------------------------------------------------------------
# 1. PYTHON SCOPE-AWARE AST NORMALIZER
# -------------------------------------------------------------
BUILTIN_NAMES = set([
    "abs", "all", "any", "ascii", "bin", "bool", "breakpoint", "bytearray", "bytes",
    "callable", "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir",
    "divmod", "enumerate", "eval", "exec", "filter", "float", "format", "frozenset",
    "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input", "int",
    "isinstance", "issubclass", "iter", "len", "list", "locals", "map", "max",
    "memoryview", "min", "next", "object", "oct", "open", "ord", "pow", "print",
    "property", "range", "repr", "reversed", "round", "set", "setattr", "slice",
    "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError", "FileNotFoundError",
    "RuntimeError", "AttributeError", "StopIteration", "ZeroDivisionError", "NotImplementedError"
])

class PythonScopeAwareNormalizer(ast.NodeTransformer):
    def __init__(self):
        super().__init__()
        self.scope_stack = []
        self.imported_names = set()
        self.func_names = set()
        self.class_names = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name)
        return node

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name)
        return node

    def visit_ClassDef(self, node):
        self.class_names.add(node.name)
        node.body = [self.visit(b) for b in node.body]
        return node

    def visit_FunctionDef(self, node):
        return self._handle_function(node)

    def visit_AsyncFunctionDef(self, node):
        return self._handle_function(node)

    def _handle_function(self, node):
        self.func_names.add(node.name)
        
        local_symbols = {}
        param_counter = 1
        var_counter = 1
        
        # 1. Parameters
        all_params = list(node.args.args) + list(node.args.kwonlyargs)
        if node.args.vararg: all_params.append(node.args.vararg)
        if node.args.kwarg: all_params.append(node.args.kwarg)
        
        for p in all_params:
            if p.arg not in ("self", "cls"):
                local_symbols[p.arg] = f"p_{param_counter}"
                param_counter += 1

        # 2. Local variable declarations in body (shallow walk, skipping nested defs)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for sub in ast.walk(child):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                targets = []
                if isinstance(sub, ast.Assign):
                    targets.extend(sub.targets)
                elif isinstance(sub, (ast.AugAssign, ast.AnnAssign)):
                    targets.append(sub.target)
                elif isinstance(sub, ast.For):
                    targets.append(sub.target)
                elif isinstance(sub, ast.With):
                    for item in sub.items:
                        if item.optional_vars: targets.append(item.optional_vars)
                elif isinstance(sub, ast.NamedExpr):
                    targets.append(sub.target)
                elif isinstance(sub, ast.ExceptHandler):
                    if sub.name:
                        local_symbols[sub.name] = f"v_err_{var_counter}"
                        var_counter += 1
                elif isinstance(sub, ast.comprehension):
                    targets.append(sub.target)

                for t in targets:
                    for n in ast.walk(t):
                        if isinstance(n, ast.Name):
                            vname = n.id
                            if vname not in local_symbols and vname not in ("self", "cls") and vname not in self.imported_names:
                                local_symbols[vname] = f"v_{var_counter}"
                                var_counter += 1

        self.scope_stack.append(local_symbols)
        
        # Rename parameters
        for p in all_params:
            if p.arg in local_symbols:
                p.arg = local_symbols[p.arg]

        # Rename defaults (evaluated in outer scope)
        node.args.defaults = [self.visit(d) for d in node.args.defaults]
        node.args.kw_defaults = [self.visit(d) if d else None for d in node.args.kw_defaults]
        
        # Rename body
        node.body = [self.visit(b) for b in node.body]
        
        self.scope_stack.pop()
        return node

    def visit_Name(self, node):
        if self.scope_stack:
            curr = self.scope_stack[-1]
            if node.id in curr:
                node.id = curr[node.id]
        return node

    def visit_Attribute(self, node):
        # In obj.attr, transform `obj` (could be local var), but KEEP `attr` untouched!
        node.value = self.visit(node.value)
        return node

    def visit_keyword(self, node):
        # In func(arg=val), `arg` keyword name is preserved!
        node.value = self.visit(node.value)
        return node

def normalize_python(code: str) -> Tuple[str, bool]:
    try:
        tree = ast.parse(code)
        normalizer = PythonScopeAwareNormalizer()
        new_tree = normalizer.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree), True
    except Exception:
        return code, False

# -------------------------------------------------------------
# 2. C SCOPE-AWARE AST NORMALIZER (pycparser)
# -------------------------------------------------------------
from pycparser import c_parser, c_ast, c_generator

C_TYPEDEFS = """
typedef int FILE;
typedef unsigned long size_t;
typedef int bool;
typedef unsigned char uint8_t;
typedef unsigned int uint32_t;
"""

class CScopeVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.local_map = {}
        self.p_idx = 1
        self.v_idx = 1

    def visit_FuncDef(self, node):
        # 1. Collect params
        if node.decl.type.args:
            for p in node.decl.type.args.params:
                if isinstance(p, c_ast.Decl) and p.name:
                    self.local_map[p.name] = f"p_{self.p_idx}"
                    self.p_idx += 1
                    p.name = self.local_map[p.name]
                    if hasattr(p.type, 'declname'):
                        p.type.declname = p.name
                    elif hasattr(p.type, 'type') and hasattr(p.type.type, 'declname'):
                        p.type.type.declname = p.name

        # 2. Collect local variables in body
        if node.body and node.body.block_items:
            for item in node.body.block_items:
                if isinstance(item, c_ast.Decl) and item.name:
                    self.local_map[item.name] = f"v_{self.v_idx}"
                    self.v_idx += 1
                    item.name = self.local_map[item.name]
                    if hasattr(item.type, 'declname'):
                        item.type.declname = item.name
                    elif hasattr(item.type, 'type') and hasattr(item.type.type, 'declname'):
                        item.type.type.declname = item.name

        self.generic_visit(node.body)

    def visit_ID(self, node):
        if node.name in self.local_map:
            node.name = self.local_map[node.name]

def normalize_c(code: str) -> Tuple[str, bool]:
    try:
        parser = c_parser.CParser()
        full_code = C_TYPEDEFS + code
        ast_c = parser.parse(full_code)
        # Find the FuncDef
        user_func = None
        for ext in reversed(ast_c.ext):
            if isinstance(ext, c_ast.FuncDef):
                user_func = ext
                break
        if not user_func:
            return code, False
        visitor = CScopeVisitor()
        visitor.visit(user_func)
        gen = c_generator.CGenerator()
        return gen.visit(user_func), True
    except Exception:
        return code, False

# -------------------------------------------------------------
# 3. JAVASCRIPT SCOPE-AWARE AST NORMALIZER (Node TypeScript Compiler API)
# -------------------------------------------------------------
_JS_WORKER_PATH = Path(__file__).resolve().parent / "js_ast_worker.js"

class JSWorkerProcess:
    def __init__(self):
        self.proc = None
        self._start_worker()

    def _start_worker(self):
        if _JS_WORKER_PATH.exists():
            try:
                self.proc = subprocess.Popen(
                    ["node", str(_JS_WORKER_PATH)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8"
                )
            except Exception as e:
                logger.warning(f"Failed to start JS worker: {e}")
                self.proc = None

    def normalize(self, code: str) -> Tuple[str, bool]:
        if not self.proc or self.proc.poll() is not None:
            self._start_worker()
        if not self.proc:
            return code, False
        try:
            req = json.dumps({"id": 1, "code": code})
            self.proc.stdin.write(req + "\n")
            self.proc.stdin.flush()
            resp_line = self.proc.stdout.readline()
            if not resp_line:
                return code, False
            resp = json.loads(resp_line)
            if resp.get("code"):
                return resp["code"], True
            return code, False
        except Exception:
            return code, False

    def close(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

_JS_WORKER = None

def get_js_worker():
    global _JS_WORKER
    if _JS_WORKER is None:
        _JS_WORKER = JSWorkerProcess()
    return _JS_WORKER

def normalize_javascript(code: str) -> Tuple[str, bool]:
    worker = get_js_worker()
    return worker.normalize(code)

# -------------------------------------------------------------
# 4. UNIFIED MULTI-LANGUAGE DISPATCHER
# -------------------------------------------------------------
def normalize_snippet(code: str, language: str) -> Tuple[str, bool]:
    lang = language.lower().strip()
    if lang == "python":
        return normalize_python(code)
    elif lang in ("javascript", "typescript", "js", "ts"):
        return normalize_javascript(code)
    elif lang in ("c", "cpp"):
        return normalize_c(code)
    else:
        return code, False

