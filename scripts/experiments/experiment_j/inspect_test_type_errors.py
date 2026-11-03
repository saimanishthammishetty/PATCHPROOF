import json

with open("data/processed/test.jsonl", "r", encoding="utf-8") as f:
    count = 0
    for line in f:
        d = json.loads(line)
        if d["bug_category"] == "type_error":
            print(f"Sample #{count}: Lang: {d['language']}, Template: {d.get('template_family')}")
            print(f"Code:\n{d['original_code'][:200]}")
            print("-" * 60)
            count += 1
            if count >= 5:
                break

