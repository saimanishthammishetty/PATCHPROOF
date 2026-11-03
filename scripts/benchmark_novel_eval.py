"""
Comprehensive Generalization Evaluation Benchmark (50 Diverse Unseen Snippets)
Tests model robustness against:
- Unseen variable names and domain identifiers.
- Structurally equivalent bugs.
- Comprehensive JavaScript async defects (missing await, unhandled promises,
  incorrect async returns, promise rejection, race conditions).
- Clean-code hard negative controls.
- Computes Precision, Recall, F1, Confusion Matrix, and AST Localization Accuracy.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter
import numpy as np
from sklearn.metrics import precision_recall_fscore_support, accuracy_score, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.services.debug_service import DebugService, CATEGORY_LABELS
from app.models.schemas import CodeDebugRequest

# 50 Novel, Hand-Crafted, Unseen Snippets across 3 Languages
BENCHMARK_SUITE = [
    # -------------------------------------------------------------
    # A. JavaScript Async Defects (10 test cases)
    # -------------------------------------------------------------
    {
        "id": "JS-ASYNC-01",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 2,
        "description": "Missing await on fetch call",
        "code": "async function getUserAccount(accountId) {\n    const response = fetch('/api/v2/accounts/' + accountId);\n    return response.json();\n}"
    },
    {
        "id": "JS-ASYNC-02",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 2,
        "description": "Missing await on database query",
        "code": "async function findOrder(orderRef) {\n    const order = db.collection('orders').findOne({ ref: orderRef });\n    return order.totalPrice;\n}"
    },
    {
        "id": "JS-ASYNC-03",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 2,
        "description": "Unhandled promise without catch handler",
        "code": "function syncInventory(batchId) {\n    apiClient.post('/inventory/sync', { batchId })\n        .then(result => {\n            console.log('Synced:', result.status);\n        });\n}"
    },
    {
        "id": "JS-ASYNC-04",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 2,
        "description": "Unhandled promise chain missing error callback",
        "code": "function broadcastNotification(msg) {\n    pushService.send(msg).then(() => updateMetrics(1));\n}"
    },
    {
        "id": "JS-ASYNC-05",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 3,
        "description": "Incorrect async return in forEach loop",
        "code": "async function processBatchOrders(orders) {\n    const output = [];\n    orders.forEach(async (order) => {\n        const saved = await saveOrder(order);\n        output.push(saved);\n    });\n    return output;\n}"
    },
    {
        "id": "JS-ASYNC-06",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 2,
        "description": "Map returning array of promises without Promise.all",
        "code": "async function fetchAllUsers(userIds) {\n    const promises = userIds.map(async (id) => fetchUser(id));\n    return promises;\n}"
    },
    {
        "id": "JS-ASYNC-07",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 4,
        "description": "Promise rejection with primitive string instead of Error",
        "code": "function validateToken(token) {\n    return new Promise((resolve, reject) => {\n        if (!token) {\n            return reject('Missing auth token');\n        }\n        resolve(jwt.verify(token));\n    });\n}"
    },
    {
        "id": "JS-ASYNC-08",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 4,
        "description": "Promise rejection throwing string literal",
        "code": "function loadCertificate(certId) {\n    return new Promise((resolve, reject) => {\n        if (!certId) {\n            reject('Invalid cert identifier');\n        }\n        resolve(readCert(certId));\n    });\n}"
    },
    {
        "id": "JS-ASYNC-09",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 3,
        "description": "Async race condition on shared state counter",
        "code": "let globalTxnCount = 0;\nasync function incrementTxn() {\n    const current = globalTxnCount;\n    await delay(10);\n    globalTxnCount = current + 1;\n    return globalTxnCount;\n}"
    },
    {
        "id": "JS-ASYNC-10",
        "lang": "javascript",
        "expected_cat": "async_error",
        "expected_line": 3,
        "description": "Cache check race condition across await point",
        "code": "let cachedProfile = null;\nasync function getProfile() {\n    if (!cachedProfile) {\n        const data = await remoteFetch();\n        cachedProfile = data;\n    }\n    return cachedProfile;\n}"
    },

    # -------------------------------------------------------------
    # B. Python Defect Patterns with Unseen Identifiers (15 test cases)
    # -------------------------------------------------------------
    {
        "id": "PY-MUT-01",
        "lang": "python",
        "expected_cat": "api_misuse",
        "expected_line": 1,
        "description": "Mutable default list parameter 'options'",
        "code": "def configure_pipeline(stage_name, options=[]):\n    options.append(stage_name)\n    return options"
    },
    {
        "id": "PY-MUT-02",
        "lang": "python",
        "expected_cat": "api_misuse",
        "expected_line": 1,
        "description": "Mutable default dict parameter 'metadata'",
        "code": "def record_telemetry(metric_key, metadata={}):\n    metadata[metric_key] = True\n    return metadata"
    },
    {
        "id": "PY-MUT-03",
        "lang": "python",
        "expected_cat": "api_misuse",
        "expected_line": 1,
        "description": "Mutable default parameter 'handlers'",
        "code": "def register_listener(event_type, handlers=[]):\n    handlers.append(event_type)\n    return len(handlers)"
    },
    {
        "id": "PY-COND-01",
        "lang": "python",
        "expected_cat": "condition_error",
        "expected_line": 2,
        "description": "Identity comparison 'is 200' on HTTP status code",
        "code": "def is_success(response_code):\n    if response_code is 200:\n        return True\n    return False"
    },
    {
        "id": "PY-COND-02",
        "lang": "python",
        "expected_cat": "condition_error",
        "expected_line": 2,
        "description": "Identity comparison 'is 404' on error code",
        "code": "def handle_error(status):\n    if status is 404:\n        return 'NOT_FOUND'\n    return 'SERVER_ERROR'"
    },
    {
        "id": "PY-COND-03",
        "lang": "python",
        "expected_cat": "condition_error",
        "expected_line": 2,
        "description": "Identity comparison 'is 99' on role ID",
        "code": "def check_admin_privileges(role_id):\n    return role_id is 99"
    },
    {
        "id": "PY-EXC-01",
        "lang": "python",
        "expected_cat": "exception_handling",
        "expected_line": 4,
        "description": "Bare except clause in file reader",
        "code": "def read_audit_log(filepath):\n    try:\n        return open(filepath).read()\n    except:\n        return ''"
    },
    {
        "id": "PY-EXC-02",
        "lang": "python",
        "expected_cat": "exception_handling",
        "expected_line": 4,
        "description": "Bare except clause in JSON parser",
        "code": "def parse_payload(raw_json):\n    try:\n        return json.loads(raw_json)\n    except:\n        return None"
    },
    {
        "id": "PY-EXC-03",
        "lang": "python",
        "expected_cat": "exception_handling",
        "expected_line": 4,
        "description": "Exception swallowing returning 0",
        "code": "def extract_numeric_id(token_str):\n    try:\n        return int(token_str)\n    except Exception:\n        pass"
    },
    {
        "id": "PY-OFF-01",
        "lang": "python",
        "expected_cat": "off_by_one",
        "expected_line": 2,
        "description": "Range upper limit off by one with + 1",
        "code": "def sum_all_elements(data_series):\n    for i in range(len(data_series) + 1):\n        process(data_series[i])"
    },
    {
        "id": "PY-OFF-02",
        "lang": "python",
        "expected_cat": "off_by_one",
        "expected_line": 2,
        "description": "Index traversal range off by one",
        "code": "def find_max_token(tokens):\n    for idx in range(0, len(tokens) + 1):\n        if tokens[idx] == 'END': return idx\n    return -1"
    },
    {
        "id": "PY-TYPE-01",
        "lang": "python",
        "expected_cat": "type_error",
        "expected_line": 2,
        "description": "String concatenation with integer without conversion",
        "code": "def make_cache_key(namespace, item_id):\n    return namespace + '_' + item_id"
    },
    {
        "id": "PY-TYPE-02",
        "lang": "python",
        "expected_cat": "type_error",
        "expected_line": 2,
        "description": "Type mismatch in hash key builder",
        "code": "def generate_session_hash(user_str, port_num):\n    return user_str + ':' + port_num"
    },
    {
        "id": "JS-EQ-01",
        "lang": "javascript",
        "expected_cat": "condition_error",
        "expected_line": 2,
        "description": "Loose equality with 0 in authentication check",
        "code": "function checkAccessTier(tier) {\n    if (tier == 0) {\n        return 'GUEST';\n    }\n    return 'MEMBER';\n}"
    },
    {
        "id": "JS-EQ-02",
        "lang": "javascript",
        "expected_cat": "condition_error",
        "expected_line": 2,
        "description": "Loose equality with empty string in form validator",
        "code": "function isFieldEmpty(inputVal) {\n    if (inputVal == '') {\n        return true;\n    }\n    return false;\n}"
    },

    # -------------------------------------------------------------
    # C. C Defect Patterns (10 test cases)
    # -------------------------------------------------------------
    {
        "id": "C-MEM-01",
        "lang": "c",
        "expected_cat": "memory_safety",
        "expected_line": 3,
        "description": "Returning address of stack buffer",
        "code": "char* create_temp_path() {\n    char temp_buf[32];\n    return temp_buf;\n}"
    },
    {
        "id": "C-MEM-02",
        "lang": "c",
        "expected_cat": "memory_safety",
        "expected_line": 4,
        "description": "Returning local array pointer",
        "code": "int* get_lookup_table() {\n    int local_table[16];\n    local_table[0] = 1;\n    return local_table;\n}"
    },
    {
        "id": "C-MEM-03",
        "lang": "c",
        "expected_cat": "memory_safety",
        "expected_line": 2,
        "description": "Unbounded sprintf buffer overflow risk",
        "code": "void format_message(char* dest, const char* msg) {\n    sprintf(dest, 'Notice: %s', msg);\n}"
    },
    {
        "id": "C-MEM-04",
        "lang": "c",
        "expected_cat": "memory_safety",
        "expected_line": 2,
        "description": "Unchecked strcpy buffer overflow risk",
        "code": "void copy_hostname(char* dest, const char* src) {\n    strcpy(dest, src);\n}"
    },
    {
        "id": "C-LEAK-01",
        "lang": "c",
        "expected_cat": "resource_leak",
        "expected_line": 3,
        "description": "Missing free before early return",
        "code": "int process_packet(int err) {\n    char* pkt = malloc(256);\n    if (err) return -1;\n    free(pkt);\n    return 0;\n}"
    },
    {
        "id": "C-LEAK-02",
        "lang": "c",
        "expected_cat": "resource_leak",
        "expected_line": 3,
        "description": "Unclosed file pointer before early error return",
        "code": "int read_header(const char* fn) {\n    FILE* fp = fopen(fn, 'r');\n    if (!fp) return -1;\n    if (check_error()) return -2;\n    fclose(fp);\n    return 0;\n}"
    },
    {
        "id": "C-TYPE-01",
        "lang": "c",
        "expected_cat": "type_error",
        "expected_line": 2,
        "description": "Format specifier mismatch (%d on 64-bit long)",
        "code": "void print_timestamp(long ts) {\n    printf('Timestamp: %d\\n', ts);\n}"
    },
    {
        "id": "C-TYPE-02",
        "lang": "c",
        "expected_cat": "type_error",
        "expected_line": 2,
        "description": "Format specifier mismatch (%s on int id)",
        "code": "void log_entity_id(int id) {\n    printf('ID: %s\\n', id);\n}"
    },
    {
        "id": "C-UNDEF-01",
        "lang": "c",
        "expected_cat": "undefined_behavior",
        "expected_line": 2,
        "description": "Accumulator variable used without initialization",
        "code": "int sum_range(int n) {\n    int sum;\n    for (int i = 0; i < n; i++) sum += i;\n    return sum;\n}"
    },
    {
        "id": "C-UNDEF-02",
        "lang": "c",
        "expected_cat": "undefined_behavior",
        "expected_line": 2,
        "description": "Pointer dereference without initialization",
        "code": "int get_value() {\n    int* ptr;\n    return *ptr;\n}"
    },

    # -------------------------------------------------------------
    # D. Clean-Code Negative Controls (15 test cases)
    # -------------------------------------------------------------
    {
        "id": "CLEAN-PY-01",
        "lang": "python",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean Python math addition",
        "code": "def add_numbers(a, b):\n    return a + b"
    },
    {
        "id": "CLEAN-PY-02",
        "lang": "python",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean Python list comprehension with isinstance",
        "code": "def filter_strings(items):\n    return [w.upper() for w in items if isinstance(w, str)]"
    },
    {
        "id": "CLEAN-PY-03",
        "lang": "python",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean Python default None pattern",
        "code": "def append_safely(item, store=None):\n    if store is None:\n        store = []\n    store.append(item)\n    return store"
    },
    {
        "id": "CLEAN-PY-04",
        "lang": "python",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean Python context manager file read",
        "code": "def read_file_safely(path):\n    with open(path, 'r', encoding='utf-8') as f:\n        return f.read()"
    },
    {
        "id": "CLEAN-PY-05",
        "lang": "python",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean Python dictionary get with fallback",
        "code": "def get_user_role(users_dict, uid):\n    return users_dict.get(uid, 'standard_user')"
    },
    {
        "id": "CLEAN-JS-01",
        "lang": "javascript",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean JS arithmetic multiply",
        "code": "function multiplyValues(x, y) {\n    return x * y;\n}"
    },
    {
        "id": "CLEAN-JS-02",
        "lang": "javascript",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean JS strict equality comparison",
        "code": "function isAuthorized(level) {\n    if (level === 1) return true;\n    return false;\n}"
    },
    {
        "id": "CLEAN-JS-03",
        "lang": "javascript",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean JS async/await with try-catch",
        "code": "async function fetchUserSafe(id) {\n    try {\n        const res = await fetch('/api/user/' + id);\n        return await res.json();\n    } catch (err) {\n        console.error(err);\n        return null;\n    }\n}"
    },
    {
        "id": "CLEAN-JS-04",
        "lang": "javascript",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean JS Promise.all with array map",
        "code": "async function loadAllRecords(ids) {\n    return await Promise.all(ids.map(id => fetchRecord(id)));\n}"
    },
    {
        "id": "CLEAN-JS-05",
        "lang": "javascript",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean JS new Promise with Error rejection",
        "code": "function parseAsync(data) {\n    return new Promise((resolve, reject) => {\n        if (!data) return reject(new Error('Data required'));\n        resolve(JSON.parse(data));\n    });\n}"
    },
    {
        "id": "CLEAN-C-01",
        "lang": "c",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean C square calculation",
        "code": "int square(int n) {\n    return n * n;\n}"
    },
    {
        "id": "CLEAN-C-02",
        "lang": "c",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean C string length with NULL check",
        "code": "size_t safe_strlen(const char* s) {\n    if (s == NULL) return 0;\n    size_t len = 0;\n    while (s[len] != '\\0') len++;\n    return len;\n}"
    },
    {
        "id": "CLEAN-C-03",
        "lang": "c",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean C bounded snprintf buffer format",
        "code": "int format_id(char* buf, size_t sz, int id) {\n    if (!buf || sz == 0) return -1;\n    return snprintf(buf, sz, 'ID: %d', id);\n}"
    },
    {
        "id": "CLEAN-C-04",
        "lang": "c",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean C dynamic allocation with proper free",
        "code": "int process_data(int count) {\n    int* arr = (int*)malloc(count * sizeof(int));\n    if (!arr) return -1;\n    arr[0] = 42;\n    free(arr);\n    return 0;\n}"
    },
    {
        "id": "CLEAN-C-05",
        "lang": "c",
        "expected_cat": "none_correct_code",
        "expected_line": None,
        "description": "Clean C initialized accumulator loop",
        "code": "int sum_array(const int* arr, int size) {\n    if (!arr) return 0;\n    int total = 0;\n    for (int i = 0; i < size; i++) total += arr[i];\n    return total;\n}"
    }
]

def run_benchmark_on_model(model_path: Path, model_name: str) -> Dict[str, Any]:
    print(f"\n==================================================")
    print(f"BENCHMARK EVALUATION: {model_name}")
    print(f"Model Path: {model_path} ({model_path.stat().st_size:,} bytes)")
    print(f"==================================================")

    import joblib
    pipeline = joblib.load(model_path)

    y_true = []
    y_pred = []
    results_list = []
    correct_cat = 0
    correct_loc = 0
    loc_attempted = 0
    clean_total = 0
    clean_correct = 0

    for idx, tc in enumerate(BENCHMARK_SUITE, 1):
        code = tc["code"]
        lang = tc["lang"]
        exp_cat = tc["expected_cat"]
        exp_line = tc["expected_line"]

        # Run model inference directly
        probs = pipeline.predict_proba([code])[0]
        classes = pipeline.classes_
        pred_idx = probs.argmax()
        pred_cat = classes[pred_idx]
        conf = round(float(probs[pred_idx]), 4)

        # Check localization if issue detected
        # For evaluation, we test how the model's raw category maps
        y_true.append(exp_cat)
        y_pred.append(pred_cat)

        matched = (pred_cat == exp_cat)
        if matched:
            correct_cat += 1

        if exp_cat == "none_correct_code":
            clean_total += 1
            if pred_cat == "none_correct_code":
                clean_correct += 1

        # Localize if bug expected
        loc_match = False
        pred_line = None
        if pred_cat != "none_correct_code":
            if lang == "python":
                pred_line, _, _ = DebugService._localize_python_defect(code, pred_cat)
            elif lang in ("javascript", "typescript", "c"):
                pred_line, _, _ = DebugService._localize_js_c_defect(code, lang, pred_cat)
            
            if pred_line is not None:
                loc_attempted += 1
                if pred_line == exp_line:
                    loc_match = True
                    correct_loc += 1

        results_list.append({
            "id": tc["id"],
            "desc": tc["description"],
            "lang": lang,
            "expected_cat": exp_cat,
            "pred_cat": pred_cat,
            "conf": conf,
            "expected_line": exp_line,
            "pred_line": pred_line,
            "cat_match": matched,
            "loc_match": loc_match
        })

        status = "PASS" if matched else "FAIL"
        print(f"[{idx:02d}] {tc['id']:12s} ({lang:10s}): Expected={exp_cat:18s} Pred={pred_cat:18s} Conf={conf*100:5.1f}% -> {status}")

    acc = round(correct_cat / len(BENCHMARK_SUITE), 4)
    loc_acc = round(correct_loc / max(1, loc_attempted), 4)
    clean_fpr = round((clean_total - clean_correct) / max(1, clean_total), 4)

    all_labels = sorted(list(set(y_true + y_pred)))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    p_weight, r_weight, f1_weight, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)

    cm = confusion_matrix(y_true, y_pred, labels=all_labels)

    # Sub-breakdown by focus area
    js_async_cases = [r for r in results_list if r["id"].startswith("JS-ASYNC")]
    js_async_acc = round(sum(1 for r in js_async_cases if r["cat_match"]) / max(1, len(js_async_cases)), 4)

    py_mut_cases = [r for r in results_list if r["id"].startswith("PY")]
    py_acc = round(sum(1 for r in py_mut_cases if r["cat_match"]) / max(1, len(py_mut_cases)), 4)

    c_cases = [r for r in results_list if r["id"].startswith("C-")]
    c_acc = round(sum(1 for r in c_cases if r["cat_match"]) / max(1, len(c_cases)), 4)

    clean_cases = [r for r in results_list if r["id"].startswith("CLEAN")]
    clean_acc = round(sum(1 for r in clean_cases if r["cat_match"]) / max(1, len(clean_cases)), 4)

    summary = {
        "model_name": model_name,
        "total_test_cases": len(BENCHMARK_SUITE),
        "overall_accuracy": acc,
        "macro_f1": round(float(f1_macro), 4),
        "weighted_f1": round(float(f1_weight), 4),
        "clean_code_fpr": clean_fpr,
        "localization_accuracy": loc_acc,
        "localization_attempted": loc_attempted,
        "localization_correct": correct_loc,
        "sub_category_accuracy": {
            "js_async_coverage (10 cases)": js_async_acc,
            "python_unseen_identifiers (13 cases)": py_acc,
            "c_defect_patterns (10 cases)": c_acc,
            "clean_code_negative_controls (15 cases)": clean_acc
        },
        "labels": all_labels,
        "confusion_matrix": cm.tolist()
    }

    print(f"\n--- {model_name} Summary ---")
    print(f"Overall Accuracy: {acc*100:.1f}% ({correct_cat}/{len(BENCHMARK_SUITE)})")
    print(f"Weighted F1: {f1_weight:.4f} | Macro F1: {f1_macro:.4f}")
    print(f"Clean-Code False Positive Rate: {clean_fpr*100:.1f}% ({clean_total - clean_correct}/{clean_total} false alarms)")
    print(f"JS Async Accuracy: {js_async_acc*100:.1f}%")
    print(f"Python Unseen Identifiers Accuracy: {py_acc*100:.1f}%")
    print(f"C Defect Patterns Accuracy: {c_acc*100:.1f}%")
    print(f"Localization Accuracy: {loc_acc*100:.1f}% ({correct_loc}/{loc_attempted})")

    return summary

if __name__ == "__main__":
    baseline_path = Path("C:/PATCHPROOF/models/bug_detector.joblib")
    candidate_path = Path("C:/PATCHPROOF/models/bug_detector_candidate.joblib")

    print("Running 50-snippet Generalization Benchmark on Baseline...")
    base_results = run_benchmark_on_model(baseline_path, "Phase 2 Baseline (Active Production)")

    if candidate_path.exists():
        print("\nRunning 50-snippet Generalization Benchmark on Candidate...")
        cand_results = run_benchmark_on_model(candidate_path, "Phase 3 Candidate")
