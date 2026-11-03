import sys
sys.path.insert(0, 'scripts/experiments/experiment_f')
from ast_normalizer import normalize_snippet
import joblib

code = '''void c_resolve_matrix_13(long count) {
    printf("Total items processed: %d\\n", count);
}'''

norm, success = normalize_snippet(code, 'c')
print("Success:", success)
print("Original code:\n", code)
print("Normalized code:\n", norm)

baseline = joblib.load('models/bug_detector.joblib')
h1 = joblib.load('models/experiments/experiment_h/candidate_h1_ast_only.joblib')

print("\n--- Predictions on Original ---")
print("Baseline prediction:", baseline.predict([code])[0])
b_probs = baseline.predict_proba([code])[0]
print("Baseline max prob:", round(max(b_probs), 4), "class:", baseline.classes_[b_probs.argmax()])

print("\n--- Predictions on Normalized ---")
print("H1 on norm prediction:", h1.predict([norm])[0])
h1_probs = h1.predict_proba([norm])[0]
print("H1 max prob:", round(max(h1_probs), 4), "class:", h1.classes_[h1_probs.argmax()])

print("\n--- H1 on RAW (un-normalized) ---")
print("H1 on raw prediction:", h1.predict([code])[0])
h1_raw_probs = h1.predict_proba([code])[0]
print("H1 max prob on raw:", round(max(h1_raw_probs), 4), "class:", h1.classes_[h1_raw_probs.argmax()])
