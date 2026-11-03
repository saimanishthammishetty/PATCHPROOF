import json

with open("models/experiments/experiment_i/experiment_i_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("="*110)
print(f"{'System':<30} | {'Bench Acc':<10} | {'Macro F1':<10} | {'Clean FPR':<10} | {'Bug Recall':<10} | {'PyNovel':<10} | {'JSAsync':<10}")
print("="*110)

for sys_name, res in data["benchmark_50"].items():
    sub = res["sub_categories"]
    print(f"{sys_name:<30} | {res['accuracy']*100:8.1f}% | {res['macro_f1']:10.4f} | {res['clean_code_fpr']*100:8.1f}% | {res['bug_detection_recall']*100:8.1f}% | {sub['python_novel_identifiers (13)']*100:8.1f}% | {sub['js_async_coverage (10)']*100:8.1f}%")

print("\n" + "="*110)
print(f"{'System':<30} | {'RobHeld Acc':<12} | {'RobHeld F1':<12} | {'Untouched Acc':<14} | {'Untouched F1':<12}")
print("="*110)

for sys_name in data["benchmark_50"].keys():
    rob = data["robust_heldout_1226"][sys_name]
    unt = data["untouched_test_8353"][sys_name]
    print(f"{sys_name:<30} | {rob['accuracy']*100:10.2f}% | {rob['macro_f1']:12.4f} | {unt['accuracy']*100:12.2f}% | {unt['macro_f1']:12.4f}")

print("\n" + "="*110)
print("PER-CLASS COMPARISON ON NOVEL 50-SNIPPET BENCHMARK:")
print("="*110)
classes = data["benchmark_50"]["Baseline (Production)"]["labels"]
print(f"{'Class':<22} | {'Baseline':<12} | {'H1 (ML-Only)':<12} | {'Static-Only':<12} | {'Hybrid (Exp I)':<12}")
print("-" * 75)
for cls in classes:
    b_f1 = data["benchmark_50"]["Baseline (Production)"]["per_class"].get(cls, {}).get("f1", 0.0)
    h1_f1 = data["benchmark_50"]["Candidate H1 (ML-Only)"]["per_class"].get(cls, {}).get("f1", 0.0)
    st_f1 = data["benchmark_50"]["Static-Only Engine"]["per_class"].get(cls, {}).get("f1", 0.0)
    hy_f1 = data["benchmark_50"]["Hybrid Engine (Experiment I)"]["per_class"].get(cls, {}).get("f1", 0.0)
    print(f"{cls:<22} | {b_f1:10.2f}   | {h1_f1:10.2f}   | {st_f1:10.2f}   | {hy_f1:10.2f}  ")

