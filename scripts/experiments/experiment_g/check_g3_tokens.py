import joblib

m = joblib.load('models/experiments/experiment_g/candidate_g3_clean_tokens.joblib')
vec = m.named_steps['tfidf']
clf = m.named_steps['clf']
classes = list(clf.classes_)

text = """def sanitize_handlers(p_1, p_2):
    return p_1 + '_' + p_2"""

toks = [t for t in vec.build_analyzer()(text) if t in vec.vocabulary_]
print("Active tokens in Candidate G3:")
for t in toks:
    idx = vec.vocabulary_[t]
    print(f"  {t:<20}: type_error={clf.coef_[classes.index('type_error')][idx]:.3f}, none_correct={clf.coef_[classes.index('none_correct_code')][idx]:.3f}")

probs = m.predict_proba([text])[0]
print("\nCandidate G3 prediction probabilities:")
for c, p in sorted(zip(classes, probs), key=lambda x: -x[1])[:5]:
    print(f"  {c:<20}: {p:.4f}")

