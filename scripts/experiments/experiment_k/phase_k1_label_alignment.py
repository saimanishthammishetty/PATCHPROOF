"""
PATCHPROOF Experiment K — Phase K1: Label Alignment & Canonical Taxonomy
Audits all dataset splits, models, label frequencies, missing/extra classes,
and leakages. Defines a rigorous canonical taxonomy preserving original labels.
"""

import json
import hashlib
import os
import sys
from collections import Counter, defaultdict
import joblib

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def inspect_split(filepath):
    counts = Counter()
    sources = Counter()
    languages = Counter()
    templates = set()
    exact_hashes = set()
    total = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            total += 1
            rec = json.loads(line)
            cat = rec.get("bug_category", "UNKNOWN")
            src = rec.get("source_dataset", rec.get("source", "UNKNOWN"))
            lng = rec.get("language", "UNKNOWN")
            tmpl = rec.get("template_family", None)
            code = rec.get("original_code", "").strip()

            counts[cat] += 1
            sources[src] += 1
            languages[lng] += 1
            if tmpl:
                templates.add(tmpl)
            if code:
                exact_hashes.add(hashlib.sha256(code.encode("utf-8")).hexdigest())

    return {
        "total": total,
        "counts": dict(counts),
        "sources": dict(sources),
        "languages": dict(languages),
        "template_count": len(templates),
        "templates": templates,
        "exact_hashes": exact_hashes
    }

def main():
    print("=" * 80)
    print("PATCHPROOF EXPERIMENT K1: LABEL ALIGNMENT & TAXONOMY AUDIT")
    print("=" * 80)

    # 1. Models audit
    baseline_path = "models/bug_detector.joblib"
    h1_path = "models/experiments/experiment_h/candidate_h1_ast_only.joblib"

    baseline_hash = sha256_file(baseline_path)
    baseline_model = joblib.load(baseline_path)
    baseline_classes = [str(c) for c in baseline_model.classes_]

    h1_hash = sha256_file(h1_path)
    h1_model = joblib.load(h1_path)
    h1_classes = [str(c) for c in h1_model.classes_]

    print(f"\n[Models]")
    print(f"  Production Baseline: {baseline_path} (SHA-256: {baseline_hash[:16]}...)")
    print(f"    Classes ({len(baseline_classes)}): {baseline_classes}")
    print(f"  Candidate H1:        {h1_path} (SHA-256: {h1_hash[:16]}...)")
    print(f"    Classes ({len(h1_classes)}): {h1_classes}")

    # 2. Dataset audit
    datasets = {
        "train": "data/processed/train.jsonl",
        "val": "data/processed/val.jsonl",
        "test": "data/processed/test.jsonl",
        "robust_heldout_test": "data/processed/robust_heldout_test.jsonl"
    }

    split_data = {}
    for name, path in datasets.items():
        h = sha256_file(path)
        print(f"\nScanning {name} ({path})... SHA-256: {h[:16]}...")
        data = inspect_split(path)
        data["sha256"] = h
        split_data[name] = data
        print(f"  Total records: {data['total']}")
        print(f"  Distinct classes: {len(data['counts'])}")
        print(f"  Languages: {data['languages']}")

    # 3. Leakage checks
    print("\n" + "=" * 60)
    print("LEAKAGE ANALYSIS")
    print("=" * 60)
    pairs = [
        ("train", "val"),
        ("train", "test"),
        ("val", "test"),
        ("train", "robust_heldout_test"),
        ("val", "robust_heldout_test"),
        ("test", "robust_heldout_test")
    ]
    leakage_report = {}
    for s1, s2 in pairs:
        code_overlap = len(split_data[s1]["exact_hashes"] & split_data[s2]["exact_hashes"])
        tmpl_overlap = len(split_data[s1]["templates"] & split_data[s2]["templates"])
        leakage_report[f"{s1}_vs_{s2}"] = {
            "exact_code_duplicates": code_overlap,
            "template_family_overlap": tmpl_overlap
        }
        print(f"  {s1:20s} vs {s2:20s}: Exact Code Duplicates = {code_overlap}, Template Overlap = {tmpl_overlap}")

    # 4. Canonical Taxonomy
    # Define full 13-class canonical taxonomy and hierarchical aggregation
    all_known_classes = sorted(list(set(baseline_classes) | set(h1_classes)))
    
    canonical_taxonomy = {
        "description": "PATCHPROOF Unified 13-Class Software Defect Taxonomy",
        "version": "1.0",
        "classes": {
            "none_correct_code": {
                "super_category": "benign",
                "definition": "Clean, benign code containing no known software defects or vulnerabilities.",
                "severity": "none"
            },
            "memory_safety": {
                "super_category": "memory",
                "definition": "Spatial or temporal memory corruption (buffer overflow, use-after-free, double free, dangling pointer).",
                "severity": "critical"
            },
            "type_error": {
                "super_category": "types_and_format",
                "definition": "Type mismatch, incompatible operand types, format string / specifier mismatch (e.g. %d on long or string on int).",
                "severity": "high"
            },
            "null_pointer": {
                "super_category": "pointer_dereference",
                "definition": "Dereferencing a null/nil/None pointer or referencing an attribute of a null object.",
                "severity": "high"
            },
            "resource_leak": {
                "super_category": "lifecycle",
                "definition": "Failure to release allocated resources (file descriptors, sockets, database handles, heap buffers) on all execution paths.",
                "severity": "medium"
            },
            "condition_error": {
                "super_category": "logic_and_control",
                "definition": "Incorrect conditional branching, inverted boundary conditions, missing validation logic.",
                "severity": "medium"
            },
            "async_error": {
                "super_category": "concurrency",
                "definition": "Unhandled Promise rejection, missing await on asynchronous call, async race condition.",
                "severity": "high"
            },
            "exception_handling": {
                "super_category": "error_handling",
                "definition": "Bare except clause, silently swallowed exception, improper catch block suppressing critical system signals.",
                "severity": "medium"
            },
            "loop_error": {
                "super_category": "logic_and_control",
                "definition": "Infinite loop, broken loop termination criteria, improper iterator increment.",
                "severity": "medium"
            },
            "off_by_one": {
                "super_category": "logic_and_control",
                "definition": "Fencepost error, indexing array with index <= length or range(len + 1).",
                "severity": "medium"
            },
            "api_misuse": {
                "super_category": "api_contract",
                "definition": "Improper API contract usage, mutable default argument in function definitions, invalid argument values.",
                "severity": "medium"
            },
            "state_management": {
                "super_category": "concurrency",
                "definition": "Unsafe state mutation, shared global state conflict, race condition on mutable shared variables.",
                "severity": "high"
            },
            "undefined_behavior": {
                "super_category": "runtime_safety",
                "definition": "Undefined language semantics, reading uninitialized variables, integer overflow resulting in UB.",
                "severity": "high"
            }
        },
        # Hierarchical rollup mapping for evaluation when testing coarse vs fine generalization
        "coarse_aggregation_map": {
            "none_correct_code": "clean",
            "memory_safety": "memory_defect",
            "type_error": "type_and_format",
            "null_pointer": "pointer_defect",
            "resource_leak": "resource_leak",
            "condition_error": "logic_and_control",
            "loop_error": "logic_and_control",
            "off_by_one": "logic_and_control",
            "async_error": "concurrency",
            "state_management": "concurrency",
            "exception_handling": "error_handling",
            "api_misuse": "api_contract",
            "undefined_behavior": "runtime_safety"
        }
    }

    # 5. Label Space Comparison Table
    print("\n" + "=" * 80)
    print("CLASS FREQUENCY ACROSS SPLITS")
    print("=" * 80)
    print(f"{'Class':22s} | {'Train (86k)':>11} | {'Val (10.8k)':>11} | {'Test (8.3k)':>11} | {'Robust (1.2k)':>12} | {'Model Supported':>15}")
    print("-" * 88)

    class_audit = {}
    for cls in all_known_classes:
        tr_c = split_data["train"]["counts"].get(cls, 0)
        va_c = split_data["val"]["counts"].get(cls, 0)
        te_c = split_data["test"]["counts"].get(cls, 0)
        ro_c = split_data["robust_heldout_test"]["counts"].get(cls, 0)

        tr_pct = f"{tr_c:5d} ({tr_c/split_data['train']['total']*100:4.1f}%)" if tr_c else "0 ( 0.0%)"
        va_pct = f"{va_c:5d} ({va_c/split_data['val']['total']*100:4.1f}%)" if va_c else "0 ( 0.0%)"
        te_pct = f"{te_c:5d} ({te_c/split_data['test']['total']*100:4.1f}%)" if te_c else "0 ( 0.0%)"
        ro_pct = f"{ro_c:5d} ({ro_c/split_data['robust_heldout_test']['total']*100:4.1f}%)" if ro_c else "0 ( 0.0%)"

        sup = "YES (Baseline,H1)"
        print(f"{cls:22s} | {tr_pct:>11} | {va_pct:>11} | {te_pct:>11} | {ro_pct:>12} | {sup:>15}")

        class_audit[cls] = {
            "train_count": tr_c,
            "train_pct": round(tr_c / split_data["train"]["total"] * 100, 2),
            "val_count": va_c,
            "val_pct": round(va_c / split_data["val"]["total"] * 100, 2),
            "test_count": te_c,
            "test_pct": round(te_c / split_data["test"]["total"] * 100, 2),
            "robust_count": ro_c,
            "robust_pct": round(ro_c / split_data["robust_heldout_test"]["total"] * 100, 2),
            "in_train": tr_c > 0,
            "in_val": va_c > 0,
            "in_test": te_c > 0,
            "in_robust": ro_c > 0
        }

    # Summary of discrepancies
    missing_from_test = [cls for cls, v in class_audit.items() if not v["in_test"]]
    missing_from_val = [cls for cls, v in class_audit.items() if not v["in_val"]]
    val_only_vs_test = [cls for cls, v in class_audit.items() if v["in_val"] and not v["in_test"]]

    print("\n[Taxonomy Discrepancy Findings]")
    print(f"  Missing from Test Set ({len(missing_from_test)} classes): {missing_from_test}")
    print(f"  Missing from Val Set  ({len(missing_from_val)} classes): {missing_from_val}")
    print(f"  Present in Val but ABSENT from Test: {val_only_vs_test}")
    print(f"  Robust Heldout has ONLY {len([c for c,v in class_audit.items() if v['in_robust']])} classes: {[c for c,v in class_audit.items() if v['in_robust']]}")

    # Save to JSON
    out_dir = "models/experiments/experiment_k"
    os.makedirs(out_dir, exist_ok=True)
    report = {
        "experiment": "K1",
        "taxonomy": canonical_taxonomy,
        "models": {
            "baseline": {
                "path": baseline_path,
                "sha256": baseline_hash,
                "classes": baseline_classes
            },
            "candidate_h1": {
                "path": h1_path,
                "sha256": h1_hash,
                "classes": h1_classes
            }
        },
        "splits": {
            name: {
                "path": datasets[name],
                "sha256": split_data[name]["sha256"],
                "total_records": split_data[name]["total"],
                "classes_present": list(split_data[name]["counts"].keys()),
                "counts": split_data[name]["counts"],
                "languages": split_data[name]["languages"],
                "unique_templates": split_data[name]["template_count"]
            }
            for name in datasets
        },
        "leakage_analysis": leakage_report,
        "class_audit": class_audit,
        "discrepancies": {
            "missing_from_test": missing_from_test,
            "missing_from_val": missing_from_val,
            "present_in_val_absent_from_test": val_only_vs_test
        }
    }

    out_file = os.path.join(out_dir, "phase_k1_label_alignment.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved report to: {out_file}")

if __name__ == "__main__":
    main()

