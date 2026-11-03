import joblib

b_vec = joblib.load('models/bug_detector.joblib').named_steps['tfidf']
h1_vec = joblib.load('models/experiments/experiment_h/candidate_h1_ast_only.joblib').named_steps['tfidf']

b_vocab = b_vec.vocabulary_
h1_vocab = h1_vec.vocabulary_

test_tokens = [
    'printf', 'long', 'count', 'total', 'items', 'processed',
    '%d', 'format', 'specifier', 'd', 'ld', 'p_1', 'uint8_t', 'size_t',
    'char', 'int', 'void', 'long count', 'long p_1', 'printf total',
    'items processed'
]

print(f"{'Token':20s} | {'Baseline Vocab':25s} | {'H1 Vocab':25s}")
print("-" * 75)
for t in test_tokens:
    in_b = f"YES (idx {b_vocab[t]})" if t in b_vocab else "NO"
    in_h1 = f"YES (idx {h1_vocab[t]})" if t in h1_vocab else "NO"
    print(f"{t:20s} | {in_b:25s} | {in_h1:25s}")

# Check what classes have highest weights for 'long count' or 'printf' in Baseline vs H1
b_clf = joblib.load('models/bug_detector.joblib').named_steps['clf']
h1_clf = joblib.load('models/experiments/experiment_h/candidate_h1_ast_only.joblib').named_steps['clf']

print("\n--- Baseline Coefficients for 'printf' ---")
if 'printf' in b_vocab:
    idx = b_vocab['printf']
    for cls_name, coef in zip(b_clf.classes_, b_clf.coef_[:, idx]):
        print(f"  {cls_name:20s}: {coef:+.4f}")

print("\n--- H1 Coefficients for 'printf' ---")
if 'printf' in h1_vocab:
    idx = h1_vocab['printf']
    for cls_name, coef in zip(h1_clf.classes_, h1_clf.coef_[:, idx]):
        print(f"  {cls_name:20s}: {coef:+.4f}")
