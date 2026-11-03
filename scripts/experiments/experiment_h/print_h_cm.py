import json
import numpy as np

with open("models/experiments/experiment_h/experiment_h_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

models = ["Baseline (Production)", "Candidate F2 (Staged Ref)", "Candidate H1 (AST-Only)", "Candidate H3 (Early Fusion)", "Candidate H5 (Routed Fusion)"]

for m in models:
    b = data["evaluations"][m]["benchmark_50"]
    labels = b["labels"]
    cm = np.array(b["confusion_matrix"])
    print(f"\n{'='*75}\nCONFUSION MATRIX: {m}\n{'='*75}")
    print(f"{'True \\ Pred':<20} | " + " | ".join([f"{l[:5]:>5}" for l in labels]))
    print("-" * 75)
    for idx, l in enumerate(labels):
        row_str = " | ".join([f"{cm[idx, j]:5d}" for j in range(len(labels))])
        print(f"{l:<20} | {row_str}")

