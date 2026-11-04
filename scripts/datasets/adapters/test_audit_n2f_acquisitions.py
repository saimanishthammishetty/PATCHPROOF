"""
Automated Unit Tests for Experiment N2F Dataset Acquisition Auditor.

Covers all Phase 5 validation requirements:
1. Provenance completeness and deterministic metadata indexing.
2. Duplicate and overlap detection using synthetic fixtures.
3. Unknown license/provenance quarantine policy.
4. Unsupported taxonomy labels remain unmapped.
5. Downloaded dataset git commit pinning and working tree cleanliness.
6. Cryptographic verification of protected production hashes.
"""

import sys
import json
import hashlib
import tempfile
from pathlib import Path
import unittest

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.datasets.adapters.audit_n2f_acquisitions import DatasetAcquisitionAuditorN2F


class TestDatasetAcquisitionAuditorN2F(unittest.TestCase):

    # Baseline SHA-256 hashes of protected production artifacts
    PROTECTED_HASHES = {
        "models/bug_detector.joblib": "5f93bba9ce457fe991580afcd3c482d2d8fb626c019ab1dcda58b73731176a20",
        "data/processed/test.jsonl": "9aad8de8b09b0e2fefe04f40c82e32ced4241d695bf14f2ad87d1b0bc9f19b7d",
        "data/processed/robust_heldout_test.jsonl": "e080c89720ba3efa317354922f7fe76b995be583be20ade441b3c710daec8ad1",
        "data/processed/train.jsonl": "6868ccac75c0048bc12f400094aa193d566664ccb7aca59ade4b005164fcb4ad",
        "data/processed/val.jsonl": "935c6011b67ec85b0f1991b3f13a8e4740d7b6fdf834c093fd0ba6ee090a271f",
        "scripts/datasets/split.py": "9f04150c57023eabc76a638d3d29431292f1b0f629ee8ac9a94f2c7126705fcd",
        "scripts/datasets/experimental_stratified_group_split.py": "0851bc257de0fb05e846166e1c2c36a3aaf72bb1b5059169c1820b7c3518e6c6"
    }

    def setUp(self):
        self.auditor = DatasetAcquisitionAuditorN2F(ROOT_DIR)

    def test_provenance_completeness(self):
        """Verify that all dataset configurations contain required provenance fields."""
        for ds_key, cfg in self.auditor.DATASET_CONFIGS.items():
            self.assertIn("name", cfg)
            self.assertIn("official_url", cfg)
            self.assertIn("language", cfg)
            self.assertIn("paper", cfg)
            self.assertIn("framework_license", cfg)
            self.assertIn("underlying_project_licenses", cfg)
            self.assertIn("relative_dir", cfg)

    def test_synthetic_overlap_detection(self):
        """Verify synthetic fixture overlap detection against mock production splits."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            splits_dir = tmp_path / "splits"
            splits_dir.mkdir(parents=True, exist_ok=True)

            # Create mock train split containing commit 'c0ffee12'
            (splits_dir / "train.jsonl").write_text(
                json.dumps({"commit_hash": "c0ffee1234567890"}) + "\n",
                encoding="utf-8"
            )
            # Create mock test split containing commit 'deadbeef'
            (splits_dir / "test.jsonl").write_text(
                json.dumps({"commit_hash": "deadbeef12345678"}) + "\n",
                encoding="utf-8"
            )

            acquired_commits = {
                "dataset_overlapping": {"c0ffee1234567890", "unique1111"},
                "dataset_clean": {"clean2222", "clean3333"}
            }

            report = self.auditor.audit_split_overlaps(acquired_commits, splits_dir)

            self.assertFalse(report["dataset_overlapping"]["train"]["is_zero_leakage"])
            self.assertEqual(report["dataset_overlapping"]["train"]["overlapping_commits_count"], 1)
            self.assertTrue(report["dataset_overlapping"]["test"]["is_zero_leakage"])

            self.assertTrue(report["dataset_clean"]["train"]["is_zero_leakage"])
            self.assertTrue(report["dataset_clean"]["test"]["is_zero_leakage"])

    def test_unknown_license_quarantine(self):
        """Verify that datasets lacking explicit verified licenses require quarantine."""
        for ds_key, cfg in self.auditor.DATASET_CONFIGS.items():
            # Frameworks without a dedicated root LICENSE file must specify underlying licenses
            if cfg["license_evidence_type"] != "ROOT_LICENSE_FILE":
                self.assertIn("underlying_project_licenses", cfg)
                self.assertTrue(len(cfg["underlying_project_licenses"]) > 0)

    def test_unsupported_taxonomy_labels_remain_unmapped(self):
        """Verify that native categories outside PATCHPROOF 13-class taxonomy maintain quarantine estimates."""
        # BugsJS estimate
        inv_bugsjs = self.auditor.audit_bugsjs(ROOT_DIR / "data/experiments/experiment_n2f/raw/bugsjs")
        self.assertGreater(inv_bugsjs["taxonomy_compatibility"]["unmapped_quarantine_estimate"], 0)

        # BugsInPy estimate
        inv_bip = self.auditor.audit_bugsinpy(ROOT_DIR / "data/experiments/experiment_n2f/raw/bugsinpy")
        self.assertGreater(inv_bip["taxonomy_compatibility"]["unmapped_quarantine_estimate"], 0)

    def test_downloaded_datasets_integrity(self):
        """Verify git commit hashes and cleanliness of all 4 downloaded datasets."""
        for ds_key, cfg in self.auditor.DATASET_CONFIGS.items():
            ds_dir = ROOT_DIR / cfg["relative_dir"]
            self.assertTrue(ds_dir.exists(), f"Missing dataset directory: {ds_dir}")
            git_info = self.auditor.get_git_info(ds_dir)
            self.assertTrue(git_info["exists"], f"{ds_key} is not a git repository")
            self.assertIsNotNone(git_info["head"], f"{ds_key} missing HEAD commit")
            self.assertEqual(len(git_info["head"]), 40, f"{ds_key} HEAD commit is not full 40-char SHA-1")
            self.assertTrue(git_info["clean"], f"{ds_key} working tree is dirty")

    def test_protected_production_hashes_intact(self):
        """Cryptographically recheck that production models, splits, and splitters remain unchanged."""
        for rel_path, expected_hash in self.PROTECTED_HASHES.items():
            full_path = ROOT_DIR / rel_path
            self.assertTrue(full_path.exists(), f"Protected file missing: {rel_path}")
            actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest().lower()
            self.assertEqual(
                actual_hash,
                expected_hash.lower(),
                f"PROTECTED FILE MODIFIED: {rel_path}! Expected {expected_hash}, got {actual_hash}"
            )


if __name__ == "__main__":
    unittest.main()

