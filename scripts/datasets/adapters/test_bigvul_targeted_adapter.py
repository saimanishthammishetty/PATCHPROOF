"""
Automated Unit and Integration Tests for Targeted Big-Vul Adapter (Experiment N2C).

Covers:
1. Correct CWE mapping for all 4 target defect classes.
2. Ambiguous label rejection (semantic justification guards).
3. Duplicate removal using normalized content hashing.
4. Missing required fields and invalid records.
5. Empty input handling.
6. Deterministic output and ID generation.
7. Original provenance and group preservation.
8. End-to-end file processing and JSON output validation.
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

from scripts.datasets.adapters.bigvul_targeted_adapter import BigVulTargetedAdapter
from scripts.datasets.schema import CodeDebuggingExample


class TestBigVulTargetedAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = BigVulTargetedAdapter(min_code_len=15)

    def test_correct_cwe_mapping(self):
        """Verify that valid records for all 4 CWEs map to their canonical 13-class defect types."""
        # 1. CWE-476 -> null_pointer
        rec_476 = {
            "cve_id": "CVE-2019-15923",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void check_ptr(struct node *p) { if (p->val == NULL) return; }",
            "fixed_code": "void check_ptr(struct node *p) { if (!p || p->val == NULL) return; }",
            "is_vul": True,
            "license": "GPL-2.0"
        }
        ex_476, rej_476 = self.adapter.process_record(rec_476)
        self.assertIsNotNone(ex_476)
        self.assertIsNone(rej_476)
        self.assertEqual(ex_476.bug_category, "null_pointer")

        # 2. CWE-401 -> resource_leak
        rec_401 = {
            "cve_id": "CVE-2017-10001",
            "cwe_id": "CWE-401",
            "project": "curl",
            "commit_id": "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e",
            "code": "char *alloc_buffer(size_t len) { char *b = malloc(len); return b; }",
            "fixed_code": "char *alloc_buffer(size_t len) { char *b = malloc(len); free(b); return NULL; }",
            "is_vul": True,
            "license": "MIT"
        }
        ex_401, rej_401 = self.adapter.process_record(rec_401)
        self.assertIsNotNone(ex_401)
        self.assertIsNone(rej_401)
        self.assertEqual(ex_401.bug_category, "resource_leak")

        # 3. CWE-190 -> undefined_behavior (justified)
        rec_190 = {
            "cve_id": "CVE-2018-12896",
            "cwe_id": "CWE-190",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void add_overflow(int a, int b) { int c = a + b; if (c > INT_MAX) return; }",
            "fixed_code": "void add_overflow(int a, int b) { if (a > INT_MAX - b) return; }",
            "is_vul": True,
            "license": "GPL-2.0"
        }
        ex_190, rej_190 = self.adapter.process_record(rec_190)
        self.assertIsNotNone(ex_190)
        self.assertIsNone(rej_190)
        self.assertEqual(ex_190.bug_category, "undefined_behavior")

        # 4. CWE-362 -> state_management (justified)
        rec_362 = {
            "cve_id": "CVE-2018-6158",
            "cwe_id": "CWE-362",
            "project": "Chrome",
            "commit_id": "20b65d00ca3d8696430e22efad7485366f8c3a21",
            "code": "void update_gc_index(int idx) { current_index = idx; table[idx] = gc_info; }",
            "fixed_code": "void update_gc_index(int idx) { MutexLocker locker(table_mutex_); current_index = idx; }",
            "is_vul": True,
            "license": "BSD-3-Clause"
        }
        ex_362, rej_362 = self.adapter.process_record(rec_362)
        self.assertIsNotNone(ex_362)
        self.assertIsNone(rej_362)
        self.assertEqual(ex_362.bug_category, "state_management")

    def test_ambiguous_label_rejection(self):
        """Verify semantic justification guards reject ambiguous records into quarantine."""
        # CWE-190 without arithmetic or integer types (e.g. stub returning boolean)
        rec_190_ambiguous = {
            "cve_id": "CVE-2016-5770",
            "cwe_id": "CWE-190",
            "project": "php-src",
            "commit_id": "c0ffee1234567890abcdef1234567890abcdef12",
            "code": "bool is_available(void) { return false; }",
            "fixed_code": "bool is_available(void) { return true; }",
            "is_vul": True,
            "license": "PHP-3.01"
        }
        ex, rej = self.adapter.process_record(rec_190_ambiguous)
        self.assertIsNone(ex)
        self.assertIsNotNone(rej)
        self.assertIn("AMBIGUOUS_SEMANTICS: CWE-190", rej["rejection_reason"])

        # CWE-362 without concurrency/sync primitives
        rec_362_ambiguous = {
            "cve_id": "CVE-2013-2906",
            "cwe_id": "CWE-362",
            "project": "Chrome",
            "commit_id": "603af455b5641671b18d7d7d166630341d71b63f",
            "code": "bool get_user_prefs(void) { return prefs_loaded; }",
            "fixed_code": "bool get_user_prefs(void) { return true; }",
            "is_vul": True,
            "license": "BSD-3-Clause"
        }
        ex, rej = self.adapter.process_record(rec_362_ambiguous)
        self.assertIsNone(ex)
        self.assertIsNotNone(rej)
        self.assertIn("AMBIGUOUS_SEMANTICS: CWE-362", rej["rejection_reason"])

        # CWE-476 without pointers or NULL
        rec_476_ambiguous = {
            "cve_id": "CVE-2019-9999",
            "cwe_id": "CWE-476",
            "project": "test-repo",
            "commit_id": "feedface1234567890abcdef1234567890abcdef",
            "code": "int compute_sum(int a, int b) { return a + b; }",
            "is_vul": True
        }
        ex, rej = self.adapter.process_record(rec_476_ambiguous)
        self.assertIsNone(ex)
        self.assertIn("AMBIGUOUS_SEMANTICS: CWE-476", rej["rejection_reason"])

        # Unsupported CWE (e.g. CWE-119 memory buffer overflow)
        rec_119 = {
            "cve_id": "CVE-2017-1234",
            "cwe_id": "CWE-119",
            "project": "linux",
            "commit_id": "abcd1234abcd1234abcd1234abcd1234abcd1234",
            "code": "void copy_buf(char *dst, char *src) { strcpy(dst, src); }",
            "is_vul": True
        }
        ex, rej = self.adapter.process_record(rec_119)
        self.assertIsNone(ex)
        self.assertIn("UNSUPPORTED_CWE: CWE-119", rej["rejection_reason"])

        # Clean/non-vulnerable control (is_vul == False)
        rec_clean = {
            "cve_id": "CVE-2018-0001",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "1234abcd1234abcd1234abcd1234abcd1234abcd",
            "code": "void clean_func(char *p) { if (p) *p = 0; }",
            "is_vul": False
        }
        ex, rej = self.adapter.process_record(rec_clean)
        self.assertIsNone(ex)
        self.assertIn("NON_VULNERABLE_OR_CLEAN", rej["rejection_reason"])

    def test_duplicate_removal(self):
        """Verify that identical code snippets are deduplicated via normalized content hashes."""
        rec1 = {
            "cve_id": "CVE-2019-1111",
            "cwe_id": "CWE-476",
            "project": "libtest",
            "commit_id": "1111222233334444555566667777888899990000",
            "code": "void process_node(struct item *it) { it->count = 0; }",
            "is_vul": True,
            "license": "MIT"
        }
        # rec2 has identical normalized code (varying only in extra whitespace)
        rec2 = {
            "cve_id": "CVE-2019-2222",
            "cwe_id": "CWE-476",
            "project": "libtest",
            "commit_id": "9999888877776666555544443333222211110000",
            "code": "void   process_node( struct item *it ) {\n  it->count = 0;\n}",
            "is_vul": True,
            "license": "MIT"
        }
        ex1, rej1 = self.adapter.process_record(rec1)
        self.assertIsNotNone(ex1)
        self.assertIsNone(rej1)

        ex2, rej2 = self.adapter.process_record(rec2)
        self.assertIsNone(ex2)
        self.assertIsNotNone(rej2)
        self.assertIn("DUPLICATE_CODE_HASH", rej2["rejection_reason"])

    def test_missing_fields(self):
        """Verify that records with missing required fields are safely quarantined."""
        # Missing code
        ex, rej = self.adapter.process_record({"cve_id": "CVE-1", "cwe_id": "CWE-476", "is_vul": True})
        self.assertIsNone(ex)
        self.assertIn("MISSING_OR_SHORT_CODE", rej["rejection_reason"])

        # Code too short (< 15 characters)
        ex, rej = self.adapter.process_record({"code": "int x = 1;", "cve_id": "CVE-1", "cwe_id": "CWE-476", "is_vul": True})
        self.assertIsNone(ex)
        self.assertIn("MISSING_OR_SHORT_CODE", rej["rejection_reason"])

        # Missing commit_id and project
        ex, rej = self.adapter.process_record({
            "code": "void ptr_func(int *p) { *p = 10; }",
            "cve_id": "CVE-2020-0001",
            "cwe_id": "CWE-476",
            "is_vul": True
        })
        self.assertIsNone(ex)
        self.assertIn("MISSING_REQUIRED_FIELDS", rej["rejection_reason"])
        self.assertIn("project", rej["rejection_reason"])
        self.assertIn("commit_id", rej["rejection_reason"])

    def test_empty_input(self):
        """Verify handling of completely empty input files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            in_file = tmp_path / "empty.jsonl"
            cand_file = tmp_path / "candidates.jsonl"
            quar_file = tmp_path / "quarantine.jsonl"
            rep_file = tmp_path / "report.json"

            in_file.write_text("", encoding="utf-8")

            report = self.adapter.process_file(in_file, cand_file, quar_file, rep_file)
            self.assertEqual(report["total_input_records"], 0)
            self.assertEqual(report["valid_candidates_extracted"], 0)
            self.assertEqual(report["quarantined_records"], 0)
            self.assertTrue(cand_file.exists())
            self.assertTrue(rep_file.exists())

    def test_deterministic_output(self):
        """Verify that identical input produces identical example_id and normalized representation."""
        rec = {
            "cve_id": "CVE-2018-12896",
            "cwe_id": "CWE-190",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void add_val(int a, int b) { int sum = a + b; if (sum > INT_MAX) return; }",
            "is_vul": True,
            "license": "GPL-2.0"
        }
        adapter1 = BigVulTargetedAdapter()
        adapter2 = BigVulTargetedAdapter()

        ex1, _ = adapter1.process_record(rec)
        ex2, _ = adapter2.process_record(rec)

        self.assertIsNotNone(ex1)
        self.assertIsNotNone(ex2)
        self.assertEqual(ex1.example_id, ex2.example_id)
        self.assertEqual(ex1.bug_category, ex2.bug_category)
        self.assertEqual(ex1.compute_content_hash(), ex2.compute_content_hash())
        self.assertEqual(ex1.to_jsonl(), ex2.to_jsonl())

    def test_original_provenance_preservation(self):
        """Verify all original provenance metadata, licenses, and group keys are preserved."""
        rec = {
            "cve_id": "CVE-2018-6158",
            "cwe_id": "CWE-362",
            "project": "Chrome",
            "commit_id": "20b65d00ca3d8696430e22efad7485366f8c3a21",
            "code": "void update_gc(int idx) { current_idx = idx; MutexLocker lock(m); }",
            "fixed_code": "void update_gc(int idx) { MutexLocker lock(m); current_idx = idx; }",
            "is_vul": True,
            "license": "BSD-3-Clause"
        }
        ex, _ = self.adapter.process_record(rec)
        self.assertIsNotNone(ex)
        self.assertEqual(ex.source_dataset, "big_vul")
        self.assertEqual(ex.source_record_id, "CVE-2018-6158")
        self.assertEqual(ex.repository, "bigvul/Chrome")
        self.assertEqual(ex.commit_hash, "20b65d00ca3d8696430e22efad7485366f8c3a21")
        self.assertEqual(ex.license, "BSD-3-Clause")
        self.assertEqual(ex.duplicate_group_id, "bigvul_Chrome_20b65d00")
        self.assertEqual(ex.template_family, "bigvul_Chrome_20b65d00")
        self.assertIn("CVE-2018-6158: CWE-362", ex.bug_description)

    def test_process_file_end_to_end(self):
        """Verify end-to-end file processing, output file creation, and report structure."""
        records = [
            # Valid 476
            {"cve_id": "CVE-2020-001", "cwe_id": "CWE-476", "project": "linux", "commit_id": "abc1", "code": "void fn(int *p) { if (!p) return; *p = 1; }", "is_vul": True},
            # Valid 190
            {"cve_id": "CVE-2020-002", "cwe_id": "CWE-190", "project": "linux", "commit_id": "abc2", "code": "int add(int a, int b) { int c = a + b; return c; }", "is_vul": True},
            # Duplicate of Valid 190
            {"cve_id": "CVE-2020-003", "cwe_id": "CWE-190", "project": "linux", "commit_id": "abc3", "code": "int add(int a, int b) { int c = a + b; return c; }", "is_vul": True},
            # Unsupported CWE-119
            {"cve_id": "CVE-2020-004", "cwe_id": "CWE-119", "project": "linux", "commit_id": "abc4", "code": "void cpy(char *d, char *s) { strcpy(d, s); }", "is_vul": True},
            # Ambiguous 362 (no sync)
            {"cve_id": "CVE-2020-005", "cwe_id": "CWE-362", "project": "linux", "commit_id": "abc5", "code": "int get_val(void) { return static_val; }", "is_vul": True},
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            in_file = tmp_path / "input.jsonl"
            cand_file = tmp_path / "candidates.jsonl"
            quar_file = tmp_path / "quarantine.jsonl"
            rep_file = tmp_path / "report.json"

            with open(in_file, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r) + "\n")

            report = self.adapter.process_file(in_file, cand_file, quar_file, rep_file)
            self.assertEqual(report["total_input_records"], 5)
            self.assertEqual(report["valid_candidates_extracted"], 2)
            self.assertEqual(report["duplicates_removed"], 1)
            self.assertEqual(report["quarantined_records"], 3)
            self.assertEqual(report["class_distribution"]["null_pointer"], 1)
            self.assertEqual(report["class_distribution"]["undefined_behavior"], 1)
            self.assertEqual(report["unique_projects_count"], 1)

            # Verify candidate file content
            cand_lines = [json.loads(line) for line in cand_file.read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(len(cand_lines), 2)
            self.assertIn(cand_lines[0]["bug_category"], ["null_pointer", "undefined_behavior"])

            # Verify quarantine file content
            quar_lines = [json.loads(line) for line in quar_file.read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(len(quar_lines), 3)


if __name__ == "__main__":
    unittest.main()
