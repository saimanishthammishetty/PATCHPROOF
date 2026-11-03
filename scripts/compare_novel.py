import joblib

novel_tests = [
    ('def collect_metrics(server_id, store={}):\n    store[server_id] = True\n    return store', 'python', 'api_misuse', 1),
    ('def is_admin(role_id):\n    return role_id is 99', 'python', 'condition_error', 2),
    ('def load_data(path):\n    try:\n        return open(path).read()\n    except:\n        pass', 'python', 'exception_handling', 5),
    ('def add_numbers(a, b):\n    return a + b', 'python', 'none_correct_code', None),
    ('def uppercase_words(words):\n    return [w.upper() for w in words if isinstance(w, str)]', 'python', 'none_correct_code', None),
    ('function isZero(val) {\n    return val == 0;\n}', 'javascript', 'condition_error', 2),
    ('async function getUser() {\n    const res = fetch("/api/user");\n    return res.json();\n}', 'javascript', 'async_error', 2),
    ('function multiply(x, y) {\n    return x * y;\n}', 'javascript', 'none_correct_code', None),
    ('int square(int n) {\n    return n * n;\n}', 'c', 'none_correct_code', None),
    ('void log_id(long id) {\n    printf("ID: %d\\n", id);\n}', 'c', 'type_error', 2)
]

base_model = joblib.load('C:/PATCHPROOF/models/bug_detector_v1_baseline.joblib')
cand_model = joblib.load('C:/PATCHPROOF/models/bug_detector_candidate.joblib')

base_correct = 0
cand_correct = 0

print(f"{'#':2} | {'Lang':10} | {'Expected':18} | {'Baseline Pred':18} | {'Candidate Pred':18} | Match")
print('-'*80)
for i, (code, lang, expected, _) in enumerate(novel_tests, 1):
    base_pred = str(base_model.predict([code])[0])
    cand_pred = str(cand_model.predict([code])[0])
    if base_pred == expected: base_correct += 1
    if cand_pred == expected: cand_correct += 1
    match_str = f"Base:{'PASS' if base_pred==expected else 'FAIL'} Cand:{'PASS' if cand_pred==expected else 'FAIL'}"
    print(f"{i:2} | {lang:10} | {expected:18} | {base_pred:18} | {cand_pred:18} | {match_str}")

print('-'*80)
print(f"Baseline Novel Accuracy:  {base_correct}/10 ({base_correct*10}%)")
print(f"Candidate Novel Accuracy: {cand_correct}/10 ({cand_correct*10}%)")
