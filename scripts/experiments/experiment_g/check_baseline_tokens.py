import joblib

m = joblib.load('models/bug_detector.joblib')
vec = m.named_steps['tfidf']
clf = m.named_steps['clf']
classes = list(clf.classes_)

text = """def sanitize_handlers(prefix_str, id_num):
    return prefix_str + '_' + id_num"""

toks = [t for t in vec.build_analyzer()(text) if t in vec.vocabulary_]
print("Active tokens in Baseline:")
for t in toks:
    idx = vec.vocabulary_[t]
    print(f"  {t:<20}: type_error={clf.coef_[classes.index('type_error')][idx]:.3f}, none_correct={clf.coef_[classes.index('none_correct_code')][idx]:.3f}")

probs = m.predict_proba([text])[0]
print("\nBaseline prediction probabilities:")
for c, p in sorted(zip(classes, probs), key=lambda x: -x[1])[:5]:
    print(f"  {c:<20}: {p:.4f}")

