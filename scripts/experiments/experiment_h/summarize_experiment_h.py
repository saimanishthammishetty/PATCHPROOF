import json

with open("models/experiments/experiment_h/experiment_h_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

models = list(data["evaluations"].keys())
classes = data["evaluations"]["Baseline (Production)"]["benchmark_50"]["labels"]

print("="*120)
print(f"{'Class':<22} | {'Baseline':<12} | {'F2':<12} | {'H1 (AST)':<12} | {'H2 (Lex)':<12} | {'H3 (Early)':<12} | {'H4 (Late)':<12} | {'H5 (Route)':<12}")
print("="*120)

for cls in classes:
    row = [f"{cls:<22}"]
    for m in ["Baseline (Production)", "Candidate F2 (Staged Ref)", "Candidate H1 (AST-Only)", "Candidate H2 (Lexical-Only)", "Candidate H3 (Early Fusion)", "Candidate H4 (Late Fusion)", "Candidate H5 (Routed Fusion)"]:
        p = data["evaluations"][m]["benchmark_50"]["per_class"].get(cls, {})
        f1_val = p.get("f1", 0.0)
        row.append(f"{f1_val:10.2f}  ")
    print(" | ".join(row))

print("\n" + "="*120)
print(f"{'Model':<30} | {'Brier':<8} | {'ECE':<8} | {'Clean FPR':<10} | {'Bug Recall':<10} | {'Python Acc':<12} | {'JS Acc':<10} | {'C Acc':<8}")
print("="*120)
for m in models:
    b = data["evaluations"][m]["benchmark_50"]
    lg = b["language_accuracy"]
    print(f"{m:<30} | {b['brier_score']:6.4f} | {b['ece']:6.4f} | {b['clean_code_fpr']*100:8.1f}% | {b['bug_detection_recall']*100:8.1f}% | {lg.get('python',0)*100:10.1f}% | {lg.get('javascript',0)*100:8.1f}% | {lg.get('c',0)*100:6.1f}%")

