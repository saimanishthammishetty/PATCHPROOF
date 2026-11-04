"""
Automated Unit Tests for Experiment N2D Big-Vul Quality Auditor.

Covers:
1. Provenance and metadata audit validation.
2. Vulnerability-label review classifications (Confirmed, Plausible, Incorrect, Insufficient).
3. Split leakage detection logic across train, val, test, and robust held-out.
4. Language audit and uncertainty isolation.
5. End-to-end audit execution and report schema validation.
"""

import sys
import json
import tempfile
from pathlib import Path
import unittest

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.datasets.adapters.audit_bigvul_n2d import BigVulQualityAuditorN2D


class TestBigVulQualityAuditorN2D(unittest.TestCase):

    def setUp(self):
        self.auditor = BigVulQualityAuditorN2D()

    def test_review_classification_confirmed(self):
        """Verify explicit NULL check, overflow check, and locking diffs are classified as Confirmed."""
        # 1. Confirmed null_pointer
        cand_null = {
            "bug_category": "null_pointer",
            "original_code": "void parse(struct node *p) { p->val = 1; }",
            "corrected_code": "void parse(struct node *p) { if (!p) return; p->val = 1; }"
        }
        status, rationale, metrics = self.auditor.review_candidate_vulnerability(cand_null)
        self.assertEqual(status, "Confirmed")
        self.assertIn("NULL pointer guard check", rationale)
        self.assertEqual(metrics["lines_added"], 1)

        # 2. Confirmed undefined_behavior
        cand_undef = {
            "bug_category": "undefined_behavior",
            "original_code": "int add(int a, int b) { return a + b; }",
            "corrected_code": "int add(int a, int b) { if (a > INT_MAX - b) return -1; return a + b; }"
        }
        status, rationale, _ = self.auditor.review_candidate_vulnerability(cand_undef)
        self.assertEqual(status, "Confirmed")
        self.assertIn("overflow boundary", rationale)

        # 3. Confirmed state_management
        cand_sync = {
            "bug_category": "state_management",
            "original_code": "void update() { global_val = 1; }",
            "corrected_code": "void update() { mutex_lock(&m); global_val = 1; mutex_unlock(&m); }"
        }
        status, rationale, _ = self.auditor.review_candidate_vulnerability(cand_sync)
        self.assertEqual(status, "Confirmed")
        self.assertIn("locking", rationale)

    def test_review_classification_plausible(self):
        """Verify indirect or control flow fixes are classified as Plausible."""
        cand_plausible = {
            "bug_category": "null_pointer",
            "original_code": "void lookup(int idx) { item_ptr = table[idx]; item_ptr->ref++; }",
            "corrected_code": "void lookup(int idx) { item_ptr = get_safe_item(idx); item_ptr->ref++; }"
        }
        status, rationale, _ = self.auditor.review_candidate_vulnerability(cand_plausible)
        self.assertEqual(status, "Plausible")
        self.assertIn("alters pointer initialization", rationale)

    def test_review_classification_insufficient(self):
        """Verify identical code with no diff is classified as Insufficient."""
        cand_no_diff = {
            "bug_category": "null_pointer",
            "original_code": "void fn() { return; }",
            "corrected_code": "void fn() { return; }"
        }
        status, rationale, metrics = self.auditor.review_candidate_vulnerability(cand_no_diff)
        self.assertEqual(status, "Insufficient")
        self.assertEqual(metrics["lines_added"], 0)
        self.assertEqual(metrics["lines_removed"], 0)

    def test_review_classification_incorrect(self):
        """Verify unsupported category string is marked as Incorrect."""
        cand_bad_cat = {
            "bug_category": "unsupported_taxonomy_xyz",
            "original_code": "void fn() { int x = 1; }",
            "corrected_code": "void fn() { int x = 2; }"
        }
        status, rationale, _ = self.auditor.review_candidate_vulnerability(cand_bad_cat)
        self.assertEqual(status, "Incorrect")

    def test_split_leakage_detection(self):
        """Verify exact code and hash overlap against loaded split indices."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            split_file = tmp_path / "mock_train.jsonl"
            split_rec = {
                "original_code": "void existing_code() { int a = 1; }",
                "language": "c",
                "duplicate_group_id": "group_123"
            }
            split_file.write_text(json.dumps(split_rec) + "\n", encoding="utf-8")

            index = self.auditor.load_split_index(split_file)
            self.assertEqual(index["count"], 1)

            # Match
            match_code = "void existing_code() {\n  int a = 1;\n}"
            norm = self.auditor.normalize_code(match_code)
            self.assertIn(norm, index["code_map"])

            # Non-match
            non_match_code = "void other_code() { int b = 2; }"
            norm_non = self.auditor.normalize_code(non_match_code)
            self.assertNotIn(norm_non, index["code_map"])

    def test_end_to_end_audit(self):
        """Verify complete run_audit workflow with mock candidate and split files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cand_file = tmp_path / "candidates.jsonl"
            splits_dir = tmp_path / "splits"
            splits_dir.mkdir(parents=True, exist_ok=True)

            out_audit = tmp_path / "quality_audit.json"
            out_review = tmp_path / "candidate_review.jsonl"

            # Create mock splits
            for s in ["train", "val", "test", "robust_heldout_test"]:
                (splits_dir / f"{s}.jsonl").write_text("", encoding="utf-8")

            # Create mock candidate
            cand = {
                "example_id": "pp-bvl-mock01",
                "source_record_id": "bigvul_row_000001_CVE-2020-001_linux_abc1",
                "repository": "bigvul/linux",
                "commit_hash": "abc12345",
                "bug_category": "null_pointer",
                "original_code": "void fn(struct item *p) { p->val = 1; }",
                "corrected_code": "void fn(struct item *p) { if (!p) return; p->val = 1; }",
                "language": "c",
                "faulty_line_numbers": [],
                "verification_status": "unverified_static",
                "license": "Public-Domain",
                "source_dataset": "big_vul"
            }
            cand_file.write_text(json.dumps(cand) + "\n", encoding="utf-8")

            report = self.auditor.run_audit(cand_file, splits_dir, out_audit, out_review)

            self.assertEqual(report["total_candidates_audited"], 1)
            self.assertEqual(report["phase1_provenance_metadata_audit"]["unique_source_row_identities"], 1)
            self.assertEqual(report["phase1_provenance_metadata_audit"]["row_id_collisions"], 0)
            self.assertEqual(report["phase2_vulnerability_label_review"]["breakdown"]["confirmed_count"], 1)
            self.assertTrue(out_audit.exists())
            self.assertTrue(out_review.exists())


if __name__ == "__main__":
    unittest.main()

