import json

with open("data/processed/robust_heldout_test.jsonl", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if idx in (0, 100, 500, 600, 700, 1000):
            d = json.loads(line)
            print(f"Sample {idx}:")
            print(f"  Lang: {d['language']}, Bug: {d['bug_category']}")
            print(f"  Template Family: {d.get('template_family')}")
            print(f"  Code:\n{d['original_code']}")
            print("-" * 60)

