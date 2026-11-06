"""
PATCHPROOF Phase L — Investigation A: Dataset Quality & Provenance Audit
Audits Experiment K dataset and baseline training dataset for source-label correlations,
C clean vs vulnerable distributions, synthetic vs real ratios, and train/test overlaps.
Outputs: models/experiments/experiment_l/phase_l_dataset_audit.json
"""

import os
import sys
import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_DIR = ROOT_DIR / "data" / "experiments" / "experiment_k"
EXP_L_DIR = ROOT_DIR / "models" / "experiments" / "experiment_l"
EXP_L_DIR.mkdir(parents=True, exist_ok=True)

def norm_hash(code: str, lang: str) -> str:
    clean = "".join(code.split())
    return hashlib.sha256(f"{lang}:{clean}".encode("utf-8")).hexdigest()[:16]

def audit_dataset_quality():
    print("=" * 80)
    print("PHASE L: INVESTIGATION A — DATASET QUALITY & PROVENANCE AUDIT")
    print("=" * 80)

    # 1. Load Experiment K dataset
    expk_path = EXP_K_DIR / "experiment_k_dataset.jsonl"
    expk_samples = []
    with open(expk_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                expk_samples.append(json.loads(line))
    print(f"[LOAD] Loaded {len(expk_samples):,} Experiment K samples from {expk_path}")

    # 2. Load Train split
    train_path = PROCESSED_DIR / "train.jsonl"
    train_samples = []
    with open(train_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                train_samples.append(json.loads(line))
    print(f"[LOAD] Loaded {len(train_samples):,} baseline train samples from {train_path}")

    # 3. Load Test split
    test_path = PROCESSED_DIR / "test.jsonl"
    test_samples = []
    with open(test_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_samples.append(json.loads(line))
    print(f"[LOAD] Loaded {len(test_samples):,} test samples from {test_path}")

    # Combine for training corpus audit
    combined_train = train_samples + expk_samples
    print(f"[CORPUS] Total training corpus: {len(combined_train):,} samples.")

    # A. Language distribution by class (in combined train)
    lang_by_class = defaultdict(Counter)
    for s in combined_train:
        lang_by_class[s["bug_category"]][s["language"]] += 1

    # B. Source dataset distribution by class
    source_by_class = defaultdict(Counter)
    for s in combined_train:
        src = s.get("source_dataset", "unknown")
        source_by_class[s["bug_category"]][src] += 1

    # C. Repository distribution by class (top repos)
    repo_by_class = defaultdict(Counter)
    for s in combined_train:
        repo = s.get("repository", "unknown")
        repo_by_class[s["bug_category"]][repo] += 1

    # D. Synthetic vs Real by class
    synth_real_by_class = defaultdict(lambda: {"synthetic": 0, "real": 0})
    for s in combined_train:
        cat = s["bug_category"]
        is_synth = s.get("is_synthetic", False)
        # Check source dataset if is_synthetic is not explicitly boolean
        if is_synth is True or "synthetic" in str(s.get("source_dataset", "")).lower():
            synth_real_by_class[cat]["synthetic"] += 1
        else:
            synth_real_by_class[cat]["real"] += 1

    # E. C-specific analysis: Clean vs Vulnerable across splits
    c_clean_train = sum(1 for s in combined_train if s["language"] == "c" and s["bug_category"] == "none_correct_code")
    c_vul_train = sum(1 for s in combined_train if s["language"] == "c" and s["bug_category"] != "none_correct_code")
    c_mem_train = sum(1 for s in combined_train if s["language"] == "c" and s["bug_category"] == "memory_safety")

    c_clean_test = sum(1 for s in test_samples if s["language"] == "c" and s["bug_category"] == "none_correct_code")
    c_vul_test = sum(1 for s in test_samples if s["language"] == "c" and s["bug_category"] != "none_correct_code")
    c_mem_test = sum(1 for s in test_samples if s["language"] == "c" and s["bug_category"] == "memory_safety")

    # Sources of C code in training
    c_sources = Counter()
    c_clean_sources = Counter()
    c_mem_sources = Counter()
    for s in combined_train:
        if s["language"] == "c":
            src = s.get("source_dataset", "unknown")
            c_sources[src] += 1
            if s["bug_category"] == "none_correct_code":
                c_clean_sources[src] += 1
            elif s["bug_category"] == "memory_safety":
                c_mem_sources[src] += 1

    # Sources of C code in test
    c_test_sources = Counter()
    c_test_clean_sources = Counter()
    c_test_mem_sources = Counter()
    for s in test_samples:
        if s["language"] == "c":
            src = s.get("source_dataset", "unknown")
            c_test_sources[src] += 1
            if s["bug_category"] == "none_correct_code":
                c_test_clean_sources[src] += 1
            elif s["bug_category"] == "memory_safety":
                c_test_mem_sources[src] += 1

    # Overlap between Train and Test sources
    train_repos = set(s.get("repository", "") for s in combined_train if s.get("repository"))
    test_repos = set(s.get("repository", "") for s in test_samples if s.get("repository"))
    repo_overlap = train_repos & test_repos

    # Exact near-duplicate check on C samples
    c_train_hashes = set(norm_hash(s["original_code"], "c") for s in combined_train if s["language"] == "c")
    c_test_hashes = set(norm_hash(s["original_code"], "c") for s in test_samples if s["language"] == "c")
    c_leakage = len(c_train_hashes & c_test_hashes)

    audit_results = {
        "experiment": "Phase L — Investigation A",
        "description": "Dataset Quality and Provenance Audit for C Language & Taxonomy",
        "corpus_summary": {
            "baseline_train_count": len(train_samples),
            "expk_acquired_count": len(expk_samples),
            "combined_train_count": len(combined_train),
            "test_sample_count": len(test_samples)
        },
        "c_language_breakdown": {
            "training": {
                "total_c_samples": c_clean_train + c_vul_train,
                "clean_c_count": c_clean_train,
                "vulnerable_c_count": c_vul_train,
                "memory_safety_c_count": c_mem_train,
                "c_clean_to_vul_ratio": round(c_clean_train / c_vul_train, 4) if c_vul_train > 0 else 0,
                "c_clean_to_mem_ratio": round(c_clean_train / c_mem_train, 4) if c_mem_train > 0 else 0,
                "c_sources_all": dict(c_sources.most_common(10)),
                "c_clean_sources": dict(c_clean_sources.most_common(10)),
                "c_memory_safety_sources": dict(c_mem_sources.most_common(10))
            },
            "testing": {
                "total_c_samples": c_clean_test + c_vul_test,
                "clean_c_count": c_clean_test,
                "vulnerable_c_count": c_vul_test,
                "memory_safety_c_count": c_mem_test,
                "c_clean_to_vul_ratio": round(c_clean_test / c_vul_test, 4) if c_vul_test > 0 else 0,
                "c_clean_to_mem_ratio": round(c_clean_test / c_mem_test, 4) if c_mem_test > 0 else 0,
                "c_sources_all": dict(c_test_sources.most_common(10)),
                "c_clean_sources": dict(c_test_clean_sources.most_common(10)),
                "c_memory_safety_sources": dict(c_test_mem_sources.most_common(10))
            },
            "leakage_test_vs_train_c_hashes": c_leakage
        },
        "synthetic_vs_real_by_class": {k: dict(v) for k, v in synth_real_by_class.items()},
        "language_by_class": {k: dict(v) for k, v in lang_by_class.items()},
        "source_by_class": {k: dict(v.most_common(5)) for k, v in source_by_class.items()},
        "repository_overlap": {
            "train_unique_repos": len(train_repos),
            "test_unique_repos": len(test_repos),
            "overlapping_repos_count": len(repo_overlap),
            "overlapping_repos": sorted(list(repo_overlap))[:20]
        }
    }

    out_file = EXP_L_DIR / "phase_l_dataset_audit.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"\n[OK] Phase L Dataset Audit written to {out_file}")

    print("\n--- Key Audit Findings ---")
    print(f"C Training Samples: Clean = {c_clean_train:,} | Vulnerable = {c_vul_train:,} (Memory Safety = {c_mem_train:,})")
    print(f"C Testing Samples : Clean = {c_clean_test:,} | Vulnerable = {c_vul_test:,} (Memory Safety = {c_mem_test:,})")
    print(f"Clean C Sources in Train: {dict(c_clean_sources.most_common(5))}")
    print(f"Memory Safety Sources in Train: {dict(c_mem_sources.most_common(5))}")
    print(f"Clean C Sources in Test : {dict(c_test_clean_sources.most_common(5))}")
    print(f"Memory Safety Sources in Test: {dict(c_test_mem_sources.most_common(5))}")
    print(f"C-Hash Leakage (must be 0): {c_leakage}")

if __name__ == "__main__":
    audit_dataset_quality()
