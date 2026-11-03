import argparse
import sys
import time
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path("C:/PATCHPROOF")))

from scripts.datasets.download_sources import DatasetDownloader
from scripts.datasets.generate_synthetic import SyntheticBugGenerator
from scripts.datasets.normalize import DatasetNormalizer
from scripts.datasets.deduplicate import DatasetDeduplicator
from scripts.datasets.validate import DatasetValidator
from scripts.datasets.split import DatasetSplitter
from scripts.training.train import run_training
from scripts.training.evaluate import run_evaluation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PipelineOrchestrator")

def execute_pipeline(
    target_count: int = 100000,
    smoke_test: bool = False,
    skip_training: bool = True
):
    start_time = time.time()
    logger.info("=================================================================")
    logger.info("PATCHPROOF ML DATASET & TRAINING PIPELINE INITIALIZED (PHASE 3)")
    logger.info("=================================================================")

    if smoke_test:
        target_count = 500
        logger.info(f"SMOKE TEST MODE ENABLED: Target count scaled to {target_count}")

    # 1. Download / Sync Public Sources
    logger.info("[PHASE 1/6] Synchronizing legitimate public benchmarks...")
    downloader = DatasetDownloader()
    swe_raw = downloader.fetch_swe_bench()
    bs_raw = downloader.fetch_bugswarm()
    bv_seeds = downloader.fetch_big_vul_seeds()
    csn_seeds = downloader.fetch_codesearchnet_seeds()
    devign_raw = downloader.fetch_devign()
    big_vul_raw = downloader.fetch_big_vul_real(max_samples=15000)
    csn_raw = downloader.fetch_codesearchnet_real()
    pybugs_raw = downloader.fetch_python_bugs_real()

    # 2. Normalize Public Records
    logger.info("[PHASE 2/6] Normalizing public records to common JSONL schema...")
    normalized_public = []
    normalized_public.extend(DatasetNormalizer.normalize_swe_bench(swe_raw))
    normalized_public.extend(DatasetNormalizer.normalize_bugswarm(bs_raw))
    normalized_public.extend(DatasetNormalizer.normalize_big_vul_seeds(bv_seeds))
    normalized_public.extend(DatasetNormalizer.normalize_codesearchnet_seeds(csn_seeds))
    normalized_public.extend(DatasetNormalizer.normalize_devign_real(devign_raw))
    normalized_public.extend(DatasetNormalizer.normalize_big_vul_real(big_vul_raw))
    normalized_public.extend(DatasetNormalizer.normalize_codesearchnet_real(csn_raw))
    normalized_public.extend(DatasetNormalizer.normalize_python_bugs_real(pybugs_raw))
    logger.info(f"Normalized {len(normalized_public)} public benchmark examples.")

    # 3. Generate Diverse Synthetic Examples
    synthetic_needed = max(0, target_count - len(normalized_public))
    logger.info(f"[PHASE 3/6] Generating {synthetic_needed} diverse synthetic examples with clean template families...")
    generator = SyntheticBugGenerator(seed=42)
    synthetic_examples = generator.generate(synthetic_needed)
    logger.info(f"Generated {len(synthetic_examples)} synthetic examples across C/C++, Python, JS/TS, Java, and Go.")

    combined = normalized_public + synthetic_examples
    logger.info(f"Total raw examples gathered: {len(combined)}")

    # 4. Deduplicate
    logger.info("[PHASE 4/6] Deduplicating exact and near-duplicate instances...")
    retained, exact_dupes, near_dupes = DatasetDeduplicator.deduplicate(combined)
    logger.info(f"Deduplication complete: {len(retained)} retained ({exact_dupes} exact, {near_dupes} near-dupes removed).")

    # 5. Validate & Quality Control
    logger.info("[PHASE 5/6] Validating schema integrity and syntactic structure...")
    validator = DatasetValidator(log_rejections=True)
    valid_examples, quality_report = validator.validate_batch(retained)
    logger.info(f"Validation complete: {len(valid_examples)} passed, {quality_report['rejected']} rejected ({quality_report['pass_rate_percent']}% pass rate).")

    # 6. Leakage-Free Split
    logger.info("[PHASE 6/6] Executing repository-grouped leakage-free 80/10/10 split...")
    splitter = DatasetSplitter(train_ratio=0.80, val_ratio=0.10, test_ratio=0.10, seed=42)
    split_stats = splitter.split_and_save(valid_examples)
    logger.info(f"Splits generated: Train={split_stats['train_count']}, Val={split_stats['val_count']}, Test={split_stats['test_count']}")

    # 7. Model Training & Evaluation
    if not skip_training:
        logger.info("[MODEL TRAINING] Training Baseline vs Interpretable ML Classifier...")
        train_results = run_training()
        logger.info("[MODEL EVALUATION] Evaluating on independent test split...")
        eval_results = run_evaluation()
    else:
        logger.info("[MODEL TRAINING] Skipped as requested by flag.")
        train_results, eval_results = {}, {}

    elapsed = round(time.time() - start_time, 2)
    logger.info("=================================================================")
    logger.info(f"PIPELINE EXECUTION COMPLETE in {elapsed}s")
    logger.info(f"Final Retained Dataset Size: {len(valid_examples)} examples")
    logger.info("=================================================================")

    return {
        "elapsed_seconds": elapsed,
        "target_count": target_count,
        "total_gathered": len(combined),
        "retained_after_dedup": len(retained),
        "valid_examples": len(valid_examples),
        "quality_report": quality_report,
        "split_stats": split_stats,
        "train_results": train_results,
        "eval_results": eval_results
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PATCHPROOF ML Dataset & Training Pipeline")
    parser.add_argument("--target-count", type=int, default=100000, help="Target example count (default: 100,000)")
    parser.add_argument("--smoke-test", action="store_true", help="Quick smoke test with 500 examples")
    parser.add_argument("--skip-training", action="store_true", help="Skip model training and evaluation")
    args = parser.parse_args()

    execute_pipeline(
        target_count=args.target_count,
        smoke_test=args.smoke_test,
        skip_training=args.skip_training
    )

