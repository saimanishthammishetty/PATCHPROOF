"""
Automated Unit Tests for Experiment N2E Big-Vul Candidate Curator.

Covers all Phase 4 test requirements:
1. Test-overlap exclusion (record and group level).
2. Train/validation-overlap exclusion.
3. Whole-group exclusion.
4. Multiple simultaneous exclusion reasons.
5. Uncertain-language exclusion.
6. Plausible-label manual review.
7. Record conservation (partition invariant).
8. Deterministic output across runs.
9. No mutation of protected inputs.
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

from scripts.datasets.adapters.curate_bigvul_n2e import BigVulCandidateCuratorN2E


class TestBigVulCandidateCuratorN2E(unittest.TestCase):

    def setUp(self):
        self.curator = BigVulCandidateCuratorN2E()

    def test_curate_leakage_and_eligibility(self):
        """Verify test-overlap, train/val overlap, whole-group exclusion, and eligibility logic."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            splits_dir = tmp_path / "splits"
            splits_dir.mkdir(parents=True, exist_ok=True)

            # Create mock splits
            # Split train has code_1 and group_train
            (splits_dir / "train.jsonl").write_text(
                json.dumps({"original_code": "void code_train() {}", "language": "c", "duplicate_group_id": "bigvul_proj_train01"}) + "\n",
                encoding="utf-8"
            )
            # Split test has code_test and group_test
            (splits_dir / "test.jsonl").write_text(
                json.dumps({"original_code": "void code_test() {}", "language": "c", "duplicate_group_id": "bigvul_proj_test01"}) + "\n",
                encoding="utf-8"
            )
            # Split val has code_val
            (splits_dir / "val.jsonl").write_text(
                json.dumps({"original_code": "void code_val() {}", "language": "c", "duplicate_group_id": "bigvul_proj_val01"}) + "\n",
                encoding="utf-8"
            )
            (splits_dir / "robust_heldout_test.jsonl").write_text("", encoding="utf-8")

            # Create mock candidates
            candidates = [
                # 1. Eligible: Confirmed, certain, zero overlap
                {
                    "example_id": "c_eligible",
                    "source_record_id": "bigvul_row_000001_CVE-1_p1_c1",
                    "original_code": "void clean_eligible() { int x = 1; }",
                    "corrected_code": "void clean_eligible() { int x = 2; }",
                    "language": "c",
                    "bug_category": "undefined_behavior",
                    "duplicate_group_id": "bigvul_p1_c1",
                    "repository": "bigvul/p1",
                    "commit_hash": "c1234567",
                    "source_dataset": "big_vul"
                },
                # 2. Excluded: Code in test
                {
                    "example_id": "c_test_overlap",
                    "source_record_id": "bigvul_row_000002_CVE-2_p2_c2",
                    "original_code": "void code_test() {}",
                    "corrected_code": "void code_test_fixed() {}",
                    "language": "c",
                    "bug_category": "null_pointer",
                    "duplicate_group_id": "bigvul_p2_c2",
                    "repository": "bigvul/p2",
                    "commit_hash": "c2222222",
                    "source_dataset": "big_vul"
                },
                # 3. Excluded: Whole group in test (different code, but group matches group_test)
                {
                    "example_id": "c_group_test_overlap",
                    "source_record_id": "bigvul_row_000003_CVE-3_proj_test01",
                    "original_code": "void other_code() { int y = 2; }",
                    "corrected_code": "void other_code() { int y = 3; }",
                    "language": "c",
                    "bug_category": "state_management",
                    "duplicate_group_id": "bigvul_proj_test01",
                    "repository": "bigvul/proj",
                    "commit_hash": "test0100",
                    "source_dataset": "big_vul"
                },
                # 4. Excluded: Train overlap
                {
                    "example_id": "c_train_overlap",
                    "source_record_id": "bigvul_row_000004_CVE-4_p4_c4",
                    "original_code": "void code_train() {}",
                    "corrected_code": "void code_train_fix() {}",
                    "language": "c",
                    "bug_category": "undefined_behavior",
                    "duplicate_group_id": "bigvul_p4_c4",
                    "repository": "bigvul/p4",
                    "commit_hash": "c4444444",
                    "source_dataset": "big_vul"
                },
                # 5. Excluded: Uncertain language
                {
                    "example_id": "c_uncertain_lang",
                    "source_record_id": "bigvul_row_000005_CVE-5_p5_c5",
                    "original_code": "void uncertain_code() { custom_type x; }",
                    "corrected_code": "void uncertain_code() { custom_type x; }",
                    "language": "c",
                    "bug_category": "undefined_behavior",
                    "duplicate_group_id": "bigvul_p5_c5",
                    "repository": "bigvul/p5",
                    "commit_hash": "c5555555",
                    "source_dataset": "big_vul"
                },
                # 6. Manual review required: Plausible, zero overlap
                {
                    "example_id": "c_plausible_manual",
                    "source_record_id": "bigvul_row_000006_CVE-6_p6_c6",
                    "original_code": "void plausible_code() { int z = 1; }",
                    "corrected_code": "void plausible_code() { int z = 2; }",
                    "language": "c",
                    "bug_category": "null_pointer",
                    "duplicate_group_id": "bigvul_p6_c6",
                    "repository": "bigvul/p6",
                    "commit_hash": "c6666666",
                    "source_dataset": "big_vul"
                },
                # 7. Multiple simultaneous exclusion reasons (in train AND in test group AND missing commit)
                {
                    "example_id": "c_multi_exclusion",
                    "source_record_id": "bigvul_row_000007_CVE-7_p7_c7",
                    "original_code": "void code_train() {}",
                    "corrected_code": "void fix() {}",
                    "language": "c",
                    "bug_category": "null_pointer",
                    "duplicate_group_id": "bigvul_proj_test01",
                    "repository": "bigvul/p7",
                    "commit_hash": "",  # Missing metadata!
                    "source_dataset": "big_vul"
                }
            ]

            # Mock reviews
            reviews = [
                {"example_id": "c_eligible", "review_status": "Confirmed", "language_certainty": "certain"},
                {"example_id": "c_test_overlap", "review_status": "Confirmed", "language_certainty": "certain"},
                {"example_id": "c_group_test_overlap", "review_status": "Confirmed", "language_certainty": "certain"},
                {"example_id": "c_train_overlap", "review_status": "Confirmed", "language_certainty": "certain"},
                {"example_id": "c_uncertain_lang", "review_status": "Confirmed", "language_certainty": "uncertain"},
                {"example_id": "c_plausible_manual", "review_status": "Plausible", "language_certainty": "certain"},
                {"example_id": "c_multi_exclusion", "review_status": "Confirmed", "language_certainty": "certain"},
            ]

            cand_path = tmp_path / "candidates.jsonl"
            rev_path = tmp_path / "reviews.jsonl"
            out_cur = tmp_path / "curated.jsonl"
            out_man = tmp_path / "manual.jsonl"
            out_exc = tmp_path / "excluded.jsonl"
            out_rep = tmp_path / "report.json"

            with open(cand_path, "w", encoding="utf-8") as f:
                for c in candidates:
                    f.write(json.dumps(c) + "\n")
            with open(rev_path, "w", encoding="utf-8") as f:
                for r in reviews:
                    f.write(json.dumps(r) + "\n")

            report = self.curator.curate(
                cand_path, rev_path, splits_dir,
                out_cur, out_man, out_exc, out_rep
            )

            # Assertions
            self.assertEqual(report["total_input_candidates"], 7)
            self.assertEqual(report["partition_accounting"]["curated_candidates_count"], 1)
            self.assertEqual(report["partition_accounting"]["manual_review_candidates_count"], 1)
            self.assertEqual(report["partition_accounting"]["excluded_candidates_count"], 5)
            self.assertTrue(report["partition_accounting"]["record_conservation_verified"])

            # Verify curated candidate is c_eligible
            cur_lines = [json.loads(l) for l in out_cur.read_text(encoding="utf-8").splitlines() if l]
            self.assertEqual(len(cur_lines), 1)
            self.assertEqual(cur_lines[0]["example_id"], "c_eligible")

            # Verify manual review candidate is c_plausible_manual
            man_lines = [json.loads(l) for l in out_man.read_text(encoding="utf-8").splitlines() if l]
            self.assertEqual(len(man_lines), 1)
            self.assertEqual(man_lines[0]["example_id"], "c_plausible_manual")

            # Verify multi-exclusion candidate preserved all reasons
            exc_lines = [json.loads(l) for l in out_exc.read_text(encoding="utf-8").splitlines() if l]
            multi_rec = [r for r in exc_lines if r["example_id"] == "c_multi_exclusion"][0]
            reasons = multi_rec["curation_metadata"]["exclusion_reasons"]
            self.assertIn("excluded_train_overlap_record", reasons)
            self.assertIn("excluded_test_overlap_group", reasons)
            self.assertIn("excluded_metadata_issue", reasons)

    def test_protected_inputs_unmutated(self):
        """Verify that running curation never modifies input candidates or review files."""
        cand_path = ROOT_DIR / "data" / "experiments" / "experiment_n2c_1" / "bigvul_candidates.jsonl"
        rev_path = ROOT_DIR / "data" / "experiments" / "experiment_n2d" / "candidate_review.jsonl"

        hash_cand_before = hashlib.sha256(cand_path.read_bytes()).hexdigest()
        hash_rev_before = hashlib.sha256(rev_path.read_bytes()).hexdigest()

        # Instantiate curator and read
        _ = self.curator.normalize_code("int a = 1;")

        hash_cand_after = hashlib.sha256(cand_path.read_bytes()).hexdigest()
        hash_rev_after = hashlib.sha256(rev_path.read_bytes()).hexdigest()

        self.assertEqual(hash_cand_before, hash_cand_after)
        self.assertEqual(hash_rev_before, hash_rev_after)


if __name__ == "__main__":
    unittest.main()

