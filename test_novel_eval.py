import sys
sys.path.insert(0, 'backend')
from app.services.debug_service import DebugService
from app.models.schemas import CodeDebugRequest

novel_tests = [
    # 1. Unseen python mutable default with novel signature
    ('def collect_metrics(server_id, store={}):\n    store[server_id] = True\n    return store', 'python', 'api_misuse', 1),
    # 2. Unseen python identity comparison on int
    ('def is_admin(role_id):\n    return role_id is 99', 'python', 'condition_error', 2),
    # 3. Unseen python bare exception
    ('def load_data(path):\n    try:\n        return open(path).read()\n    except:\n        pass', 'python', 'exception_handling', 5),
    # 4. Unseen clean python function
    ('def add_numbers(a, b):\n    return a + b', 'python', 'none_correct_code', None),
    # 5. Unseen clean python list comprehension
    ('def uppercase_words(words):\n    return [w.upper() for w in words if isinstance(w, str)]', 'python', 'none_correct_code', None),
    # 6. Unseen JS loose equality
    ('function isZero(val) {\n    return val == 0;\n}', 'javascript', 'condition_error', 2),
    # 7. Unseen JS missing await
    ('async function getUser() {\n    const res = fetch("/api/user");\n    return res.json();\n}', 'javascript', 'async_error', 2),
    # 8. Unseen clean JS
    ('function multiply(x, y) {\n    return x * y;\n}', 'javascript', 'none_correct_code', None),
    # 9. Unseen clean C
    ('int square(int n) {\n    return n * n;\n}', 'c', 'none_correct_code', None),
    # 10. Unseen C format specifier
    ('void log_id(long id) {\n    printf("ID: %d\\n", id);\n}', 'c', 'type_error', 2)
]

correct_cat = 0
correct_loc = 0
loc_attempted = 0

print('--- NOVEL UNSEEN SNIPPETS EVALUATION ---')
for idx, (code, lang, expected_cat, expected_line) in enumerate(novel_tests, 1):
    resp = DebugService.analyze_code(CodeDebugRequest(code=code, language=lang))
    cat_match = (resp.predicted_category == expected_cat)
    if cat_match:
        correct_cat += 1
    if resp.faulty_line_number is not None:
        loc_attempted += 1
        if resp.faulty_line_number == expected_line:
            correct_loc += 1
    print(f'Test {idx:02d} ({lang:10s}): Expected={expected_cat:20s} Got={resp.predicted_category:20s} Conf={resp.confidence_score*100:5.1f}% Line={str(resp.faulty_line_number):5s} ExpectedLine={str(expected_line):5s} -> Status: {"PASS" if cat_match else "FAIL"}')

print(f'\nNovel Snippets Category Accuracy: {correct_cat}/{len(novel_tests)} ({correct_cat/len(novel_tests)*100:.1f}%)')
print(f'Novel Snippets Localization Accuracy: {correct_loc}/{loc_attempted} ({correct_loc/max(1, loc_attempted)*100:.1f}%)')
