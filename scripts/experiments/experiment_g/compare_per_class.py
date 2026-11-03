import json

with open("models/experiments/experiment_g/experiment_g_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

classes = data["evaluations"]["Baseline (Production)"]["benchmark_50"]["labels"]

print("="*105)
print(f"{'Class':<22} | {'Baseline F1 (P/R)':<24} | {'Cand F2 F1 (P/R)':<24} | {'Cand G2 F1 (P/R)':<24}")
print("="*105)

for cls in classes:
    b_p = data["evaluations"]["Baseline (Production)"]["benchmark_50"]["per_class"].get(cls, {})
    f2_p = data["evaluations"]["Candidate F2 (Staged Ref)"]["benchmark_50"]["per_class"].get(cls, {})
    g2_p = data["evaluations"]["Candidate G2 (Aggressive Recall)"]["benchmark_50"]["per_class"].get(cls, {})
    
    b_str = f"{b_p.get('f1',0):.2f} ({b_p.get('precision',0):.2f}/{b_p.get('recall',0):.2f})"
    f2_str = f"{f2_p.get('f1',0):.2f} ({f2_p.get('precision',0):.2f}/{f2_p.get('recall',0):.2f})"
    g2_str = f"{g2_p.get('f1',0):.2f} ({g2_p.get('precision',0):.2f}/{g2_p.get('recall',0):.2f})"
    
    print(f"{cls:<22} | {b_str:<24} | {f2_str:<24} | {g2_str:<24}")

