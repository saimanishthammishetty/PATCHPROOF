
import json
import hashlib
from collections import Counter

def load_dataset(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records

def exact_hash(code):
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()

def normalized_code(code):
    return " ".join(code.split())

robust = load_dataset("data/processed/robust_heldout_test.jsonl")

robust_exact = set()
robust_normalized = set()

for record in robust:
    code = record.get("original_code", "")
    if code.strip():
        robust_exact.add(exact_hash(code))
        robust_normalized.add(normalized_code(code))

print("=" * 70)
print("PATCHPROOF - EXPERIMENT K ROBUST DATASET LEAKAGE AUDIT")
print("=" * 70)

print("\nROBUST DATASET")
print("Total records:", len(robust))
print("Unique exact code:", len(robust_exact))
print("Unique normalized code:", len(robust_normalized))

print("\nLANGUAGE DISTRIBUTION:")
print(Counter(r.get("language", "UNKNOWN") for r in robust))

print("\nCLASS DISTRIBUTION:")
print(Counter(r.get("bug_category", "UNKNOWN") for r in robust))

datasets = [
    "data/processed/train.jsonl",
    "data/processed/val.jsonl",
    "data/processed/test.jsonl",
    "data/experiments/experiment_k/experiment_k_dataset.jsonl"
]

print("\n" + "=" * 70)
print("CROSS-DATASET OVERLAP")
print("=" * 70)

for path in datasets:
    records = load_dataset(path)

    exact_matches = 0
    normalized_matches = 0

    for record in records:
        code = record.get("original_code", "")

        if not code.strip():
            continue

        if exact_hash(code) in robust_exact:
            exact_matches += 1

        if normalized_code(code) in robust_normalized:
            normalized_matches += 1

    print("\nDataset:", path)
    print("Total records:", len(records))
    print("Exact overlap:", exact_matches)
    print("Normalized overlap:", normalized_matches)

print("\n" + "=" * 70)
print("AUDIT COMPLETED")
print("=" * 70)
