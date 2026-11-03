"""
Pipeline script to:
1. Backup current train/val/test splits to data/processed_v2_backup/.
2. Generate 10,000 robust, diverse samples across:
   - JS Async (missing await, unhandled promise, incorrect return, rejection, race condition)
   - Python Diverse Identifiers (mutable default, identity comp, bare except, off-by-one, type error)
   - C Memory & Resource Leaks
   - Clean Code Controls (Hard Negatives)
3. Group-split the robust samples:
   - 8,000 to train
   - 1,000 to val
   - 1,000 to data/processed/robust_heldout_test.jsonl
   (Zero template leakage across splits; original test.jsonl remains strictly untouched).
4. Retrain CandidateBugModel with expanded vocabulary and sublinear TF-IDF.
5. Save candidate artifact to models/bug_detector_candidate.joblib.
6. Evaluate on BOTH:
   - Untouched held-out test.jsonl (8,353 records)
   - 50-snippet Generalization Benchmark (scripts/benchmark_novel_eval.py)
"""

import sys
import shutil
import json
import logging
from pathlib import Path
from collections import Counter
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.datasets.schema import CodeDebuggingExample
from scripts.datasets.generate_robust_samples import RobustSampleGenerator
from scripts.training.train import CandidateBugModel, MODELS_DIR, PROCESSED_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrainRobustCandidate")

BACKUP_DIR = Path("C:/PATCHPROOF/data/processed_v2_backup")

def backup_existing():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for fname in ["train.jsonl", "val.jsonl", "test.jsonl", "split_statistics.json"]:
        src = PROCESSED_DIR / fname
        dst = BACKUP_DIR / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            logger.info(f"Backed up {fname} to {BACKUP_DIR}")

def augment_splits():
    logger.info("Generating 10,000 robust diverse samples...")
    gen = RobustSampleGenerator(seed=2026)
    samples = gen.generate_all(10000)

    # Group by template_family to guarantee zero split leakage
    groups = {}
    for s in samples:
        fam = s.template_family
        if fam not in groups:
            groups[fam] = []
        groups[fam].append(s)

    logger.info(f"Generated samples across {len(groups)} distinct isolation template families.")

    import random
    rng = random.Random(42)
    group_keys = list(groups.keys())
    rng.shuffle(group_keys)

    train_aug = []
    val_aug = []
    test_aug = []

    target_val = 1000
    target_test = 1000

    for k in group_keys:
        grp = groups[k]
        if len(val_aug) < target_val:
            for item in grp:
                item.split = "val"
            val_aug.extend(grp)
        elif len(test_aug) < target_test:
            for item in grp:
                item.split = "test"
            test_aug.extend(grp)
        else:
            for item in grp:
                item.split = "train"
            train_aug.extend(grp)

    logger.info(f"Robust allocation: Train={len(train_aug)}, Val={len(val_aug)}, RobustTest={len(test_aug)}")

    # Save robust heldout test separately
    robust_test_file = PROCESSED_DIR / "robust_heldout_test.jsonl"
    with open(robust_test_file, "w", encoding="utf-8") as f:
        for item in test_aug:
            f.write(item.to_jsonl() + "\n")
    logger.info(f"Saved {len(test_aug)} robust test records to {robust_test_file}")

    # Append to train and val (retaining all original records + adding robust samples)
    # Read existing base train
    orig_train_file = BACKUP_DIR / "train.jsonl"
    orig_val_file = BACKUP_DIR / "val.jsonl"

    all_train = []
    with open(orig_train_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_train.append(line.strip())

    all_val = []
    with open(orig_val_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_val.append(line.strip())

    # Add new samples
    for item in train_aug:
        all_train.append(item.to_jsonl())
    for item in val_aug:
        all_val.append(item.to_jsonl())

    # Write updated train.jsonl and val.jsonl
    with open(PROCESSED_DIR / "train.jsonl", "w", encoding="utf-8") as f:
        for l in all_train:
            f.write(l + "\n")

    with open(PROCESSED_DIR / "val.jsonl", "w", encoding="utf-8") as f:
        for l in all_val:
            f.write(l + "\n")

    logger.info(f"Updated train.jsonl: {len(all_train)} records (+{len(train_aug)})")
    logger.info(f"Updated val.jsonl: {len(all_val)} records (+{len(val_aug)})")

    # test.jsonl remains strictly untouched!
    orig_test_file = BACKUP_DIR / "test.jsonl"
    assert orig_test_file.stat().st_size == (PROCESSED_DIR / "test.jsonl").stat().st_size, "CRITICAL: test.jsonl was modified!"

def train_and_evaluate():
    logger.info("Loading training data...")
    X_train = []
    y_train = []
    with open(PROCESSED_DIR / "train.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ex = CodeDebuggingExample.from_jsonl(line)
                X_train.append(ex.original_code)
                y_train.append(ex.bug_category)

    logger.info(f"Loaded {len(X_train)} training samples across {len(set(y_train))} classes.")

    # Multi-scale TF-IDF with enhanced capacity (word 10,000 + char 10,000)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    word_vec = TfidfVectorizer(
        analyzer="word",
        token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%:,.;(){}\[\]]+",
        ngram_range=(1, 2),
        max_features=10000,
        sublinear_tf=True
    )
    char_vec = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=10000,
        sublinear_tf=True
    )
    features = FeatureUnion([
        ("word", word_vec),
        ("char", char_vec)
    ])
    classifier = LogisticRegression(
        C=2.5,
        max_iter=600,
        class_weight="balanced",
        random_state=42
    )

    pipeline = Pipeline([
        ("features", features),
        ("clf", classifier)
    ])

    logger.info(f"Fitting candidate model on {len(X_train)} samples...")
    pipeline.fit(X_train, y_train)
    logger.info("Fitting complete.")

    # Save Candidate artifact
    import joblib
    cand_path = MODELS_DIR / "bug_detector_candidate.joblib"
    joblib.dump(pipeline, cand_path)
    logger.info(f"Candidate model artifact saved to {cand_path} ({cand_path.stat().st_size:,} bytes)")

    # 1. Evaluate on untouched held-out test.jsonl (8,353 records)
    logger.info("Evaluating Candidate on untouched held-out test.jsonl...")
    X_test = []
    y_test = []
    with open(PROCESSED_DIR / "test.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ex = CodeDebuggingExample.from_jsonl(line)
                X_test.append(ex.original_code)
                y_test.append(ex.bug_category)

    cand_preds = pipeline.predict(X_test)
    test_acc = accuracy_score(y_test, cand_preds)
    p_w, r_w, f1_w, _ = precision_recall_fscore_support(y_test, cand_preds, average="weighted", zero_division=0)
    p_m, r_m, f1_m, _ = precision_recall_fscore_support(y_test, cand_preds, average="macro", zero_division=0)

    # Clean FPR
    clean_idx = [i for i, y in enumerate(y_test) if y == "none_correct_code"]
    clean_err = sum(1 for i in clean_idx if cand_preds[i] != "none_correct_code")
    test_fpr = round(clean_err / len(clean_idx), 4)

    logger.info(f"Held-out Test (8,353 samples): Acc={test_acc*100:.2f}%, Weighted F1={f1_w:.4f}, Macro F1={f1_m:.4f}, Clean FPR={test_fpr*100:.2f}%")

    # 2. Evaluate on 50-snippet Generalization Benchmark
    logger.info("Evaluating Candidate on 50-snippet Generalization Benchmark...")
    from scripts.benchmark_novel_eval import run_benchmark_on_model
    bench_results = run_benchmark_on_model(cand_path, "Retrained Robust Candidate")

    return {
        "held_out_test_accuracy": round(float(test_acc), 4),
        "held_out_test_weighted_f1": round(float(f1_w), 4),
        "held_out_test_clean_fpr": test_fpr,
        "benchmark_accuracy": bench_results["overall_accuracy"],
        "benchmark_weighted_f1": bench_results["weighted_f1"],
        "benchmark_clean_fpr": bench_results["clean_code_fpr"],
        "sub_category_accuracy": bench_results["sub_category_accuracy"]
    }

if __name__ == "__main__":
    backup_existing()
    augment_splits()
    results = train_and_evaluate()
    print("\nFINAL RESULTS SUMMARY:")
    print(json.dumps(results, indent=2))
