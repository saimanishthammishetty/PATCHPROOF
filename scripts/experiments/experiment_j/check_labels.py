import json
from collections import Counter

val_labels = Counter()
with open('data/processed/val.jsonl', encoding='utf-8') as f:
    for line in f:
        val_labels[json.loads(line)['bug_category']] += 1

test_labels = Counter()
with open('data/processed/test.jsonl', encoding='utf-8') as f:
    for line in f:
        test_labels[json.loads(line)['bug_category']] += 1

print('=== VAL label distribution ===')
for k, v in sorted(val_labels.items()):
    print(f'  {k:30s}: {v}')

print()
print('=== TEST label distribution ===')
for k, v in sorted(test_labels.items()):
    print(f'  {k:30s}: {v}')

val_only = set(val_labels) - set(test_labels)
test_only = set(test_labels) - set(val_labels)
print()
print('Val-only labels:', val_only)
print('Test-only labels:', test_only)

