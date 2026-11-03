import json

with open("models/experiments/experiment_g/experiment_g_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("="*90)
print(f"{'Model':<35} | {'Bench Acc':<10} | {'Macro F1':<10} | {'Clean FPR':<10} | {'Bug Recall':<10} | {'PyNovel':<10} | {'JSAsync':<10}")
print("="*90)

for name, eval_dict in data["evaluations"].items():
    b = eval_dict["benchmark_50"]
    sub = b["sub_categories"]
    print(f"{name:<35} | {b['accuracy']*100:8.1f}% | {b['macro_f1']:10.4f} | {b['clean_code_fpr']*100:8.1f}% | {b['bug_detection_recall']*100:8.1f}% | {sub['python_novel_identifiers (13)']*100:8.1f}% | {sub['js_async_coverage (10)']*100:8.1f}%")

print("\n" + "="*90)
print(f"{'Model':<35} | {'Untouched Acc':<14} | {'Untouched F1':<14} | {'Robust Held Acc':<16} | {'Robust Held F1':<14}")
print("="*90)

for name, eval_dict in data["evaluations"].items():
    u = eval_dict["untouched_test_8353"]
    r = eval_dict["robust_heldout_1226"]
    print(f"{name:<35} | {u['accuracy']*100:12.1f}% | {u['macro_f1']:14.4f} | {r['accuracy']*100:14.1f}% | {r['macro_f1']:14.4f}")

print("\n" + "="*90)
print("INTERCEPTS BY MODEL:")
print("="*90)
for name, inters in data["intercepts"].items():
    print(f"\n{name}:")
    for cls, val in sorted(inters.items()):
        print(f"  {cls:<22}: {val:6.3f}")

