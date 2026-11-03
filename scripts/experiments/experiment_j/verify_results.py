import json
with open('models/experiments/experiment_j/experiment_j_results.json') as f:
    r = json.load(f)
print('Experiment:', r['experiment'])
print('Optimal threshold:', r['optimal_threshold'])
print()
print('=== BENCHMARK ===')
for sys_name, v in r['benchmark'].items():
    print(f"  {sys_name}: acc={v['accuracy']*100:.2f}% f1={v['macro_f1']:.4f} bugrecall={v['bug_recall']*100:.2f}%")
print()
print('=== TEST SET ===')
for sys_name, v in r['test'].items():
    print(f"  {sys_name}: acc={v['accuracy']*100:.2f}% f1={v['macro_f1']:.4f} bugrecall={v['bug_recall']*100:.2f}%")
print()
print('=== ROBUST HELDOUT ===')
for sys_name, v in r['robust_heldout'].items():
    print(f"  {sys_name}: acc={v['accuracy']*100:.2f}% f1={v['macro_f1']:.4f}")

