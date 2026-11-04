"""
Automated Unit Tests for Targeted Big-Vul Adapter v2 (Experiment N2C.1).

Covers all 13 audit and preservation requirements:
1. Multiple source rows sharing one CVE.
2. Multiple functions sharing one project/commit.
3. Commit identifiers containing suffixes such as ?w=1.
4. Missing license metadata handling (marks as 'unknown').
5. Preservation of source-provided license values (e.g. 'Public-Domain').
6. No fabricated faulty line (verifies empty list []).
7. No false syntax-verified status (verifies 'unverified_static').
8. C/C++ classification and hash consistency.
9. Full 64-char SHA-256 hash output.
10. Duplicate normalized code detection.
11. Weak CWE-401, CWE-362, and CWE-190 evidence rejection.
12. Deterministic output across runs.
13. Original N2C outputs remaining 100% unchanged.
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

from scripts.datasets.adapters.bigvul_targeted_adapter_v2 import BigVulTargetedAdapterV2
from scripts.datasets.schema import CodeDebuggingExample


class TestBigVulTargetedAdapterV2(unittest.TestCase):

    # Pre-recorded SHA-256 hashes of original N2C experiment outputs
    ORIGINAL_N2C_HASHES = {
        "bigvul_candidates.jsonl": "32d370f3fd3108923398ad3eabd75c4348dcba230126257d5b64a0cff8a1f8ae",
        "unmapped_candidates.jsonl": "81b2022adb3742c5b5683a215c6969ef6db3b0cd5fcc9a250cee2ca267e24dde",
        "extraction_report.json": "39a6b3d30a307e8c8cef5274dc7244855584588d530c6ad6004fdc89cbca856f"
    }

    def setUp(self):
        self.adapter = BigVulTargetedAdapterV2(min_code_len=15)

    def test_multiple_source_rows_sharing_one_cve(self):
        """Verify multiple functions in different rows sharing a CVE get unique source_record_id."""
        rec1 = {
            "cve_id": "CVE-2019-15923",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void parse_node_a(struct node *p) { if (p->val == NULL) return; }",
            "is_vul": True,
            "license": "Public-Domain"
        }
        rec2 = {
            "cve_id": "CVE-2019-15923",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void parse_node_b(struct node *q) { if (q->next == NULL) return; }",
            "is_vul": True,
            "license": "Public-Domain"
        }
        ex1, rej1, _ = self.adapter.process_record(rec1, row_number=101)
        ex2, rej2, _ = self.adapter.process_record(rec2, row_number=102)

        self.assertIsNotNone(ex1)
        self.assertIsNotNone(ex2)
        self.assertIsNone(rej1)
        self.assertIsNone(rej2)
        # Distinct unique source-row identities
        self.assertEqual(ex1.source_record_id, "bigvul_row_000101_CVE-2019-15923_linux_78c9c4df")
        self.assertEqual(ex2.source_record_id, "bigvul_row_000102_CVE-2019-15923_linux_78c9c4df")
        self.assertNotEqual(ex1.source_record_id, ex2.source_record_id)
        self.assertNotEqual(ex1.example_id, ex2.example_id)

    def test_multiple_functions_sharing_one_project_commit(self):
        """Verify distinct functions in the same project/commit keep identical group provenance but distinct IDs."""
        rec1 = {
            "cve_id": "CVE-2018-6158",
            "cwe_id": "CWE-362",
            "project": "Chrome",
            "commit_id": "20b65d00ca3d8696430e22efad7485366f8c3a21",
            "code": "void update_gc_a(int idx) { current_idx = idx; MutexLocker locker(table_mutex_); }",
            "is_vul": True
        }
        rec2 = {
            "cve_id": "CVE-2018-6158",
            "cwe_id": "CWE-362",
            "project": "Chrome",
            "commit_id": "20b65d00ca3d8696430e22efad7485366f8c3a21",
            "code": "void update_gc_b(int idx) { table_index = idx; MutexLocker locker(table_mutex_); }",
            "is_vul": True
        }
        ex1, _, _ = self.adapter.process_record(rec1, row_number=201)
        ex2, _, _ = self.adapter.process_record(rec2, row_number=202)

        self.assertIsNotNone(ex1)
        self.assertIsNotNone(ex2)
        # Shared group provenance
        self.assertEqual(ex1.duplicate_group_id, "bigvul_Chrome_20b65d00")
        self.assertEqual(ex2.duplicate_group_id, "bigvul_Chrome_20b65d00")
        self.assertEqual(ex1.template_family, ex2.template_family)
        # Distinct row identities
        self.assertNotEqual(ex1.source_record_id, ex2.source_record_id)

    def test_commit_identifiers_containing_suffixes(self):
        """Verify commit identifiers containing query parameters like ?w=1 are normalized while raw is preserved."""
        rec = {
            "cve_id": "CVE-2018-12896",
            "cwe_id": "CWE-190",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76?w=1",
            "code": "void rearm(int a, int b) { if (a > INT_MAX - b) return; }",
            "is_vul": True
        }
        ex, rej, _ = self.adapter.process_record(rec, row_number=301)
        self.assertIsNotNone(ex)
        self.assertEqual(ex.commit_hash, "78c9c4dfbf8c04883941445a195276bb4bb92c76")
        self.assertIn("raw_commit=78c9c4dfbf8c04883941445a195276bb4bb92c76?w=1", ex.bug_description)
        self.assertEqual(ex.duplicate_group_id, "bigvul_linux_78c9c4df")

    def test_missing_license_metadata(self):
        """Verify missing or null license metadata is truthfully represented as 'unknown'."""
        rec = {
            "cve_id": "CVE-2019-15923",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void check_ptr(struct node *p) { if (p->val == NULL) return; }",
            "is_vul": True,
            "license": None
        }
        ex, _, _ = self.adapter.process_record(rec, row_number=401)
        self.assertIsNotNone(ex)
        self.assertEqual(ex.license, "unknown")

    def test_preservation_of_source_provided_license(self):
        """Verify source-provided license strings are preserved verbatim without invented claims."""
        rec = {
            "cve_id": "CVE-2019-15923",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void check_ptr(struct node *p) { if (p->val == NULL) return; }",
            "is_vul": True,
            "license": "Public-Domain"
        }
        ex, _, _ = self.adapter.process_record(rec, row_number=402)
        self.assertIsNotNone(ex)
        self.assertEqual(ex.license, "Public-Domain")

    def test_no_fabricated_faulty_line(self):
        """Verify faulty_line_numbers is an empty list rather than hardcoded [1]."""
        rec = {
            "cve_id": "CVE-2019-15923",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void check_ptr(struct node *p) { if (p->val == NULL) return; }",
            "is_vul": True
        }
        ex, _, _ = self.adapter.process_record(rec, row_number=501)
        self.assertIsNotNone(ex)
        self.assertEqual(ex.faulty_line_numbers, [])

    def test_no_false_syntax_verified_status(self):
        """Verify verification_status is truthfully 'unverified_static'."""
        rec = {
            "cve_id": "CVE-2019-15923",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void check_ptr(struct node *p) { if (p->val == NULL) return; }",
            "is_vul": True
        }
        ex, _, _ = self.adapter.process_record(rec, row_number=601)
        self.assertIsNotNone(ex)
        self.assertEqual(ex.verification_status, "unverified_static")

    def test_c_cpp_classification_and_hash_consistency(self):
        """Verify C vs C++ detection is code-driven and reflected in the full content hash."""
        cpp_code = "class BufferManager { public: void clean(int *p) { if (p == nullptr) return; } };"
        c_code = "void clean(struct item *p) { if (p->val == NULL) return; }"

        lang_cpp, certain_cpp = self.adapter.detect_language(cpp_code, None)
        lang_c, certain_c = self.adapter.detect_language(c_code, None)

        self.assertEqual(lang_cpp, "cpp")
        self.assertTrue(certain_cpp)
        self.assertEqual(lang_c, "c")
        self.assertTrue(certain_c)

        # Hash must differ by language even if code were identical
        hash_c = self.adapter.compute_normalized_code_hash("void test() {}", "c")
        hash_cpp = self.adapter.compute_normalized_code_hash("void test() {}", "cpp")
        self.assertNotEqual(hash_c, hash_cpp)

    def test_full_sha256_output(self):
        """Verify normalized code hashes are full 64-character SHA-256 strings."""
        code = "void compute() { int x = 42; }"
        h = self.adapter.compute_normalized_code_hash(code, "c")
        self.assertEqual(len(h), 64)
        self.assertEqual(h, hashlib.sha256(b"c:voidcompute(){intx=42;}").hexdigest())

    def test_duplicate_normalized_code_detection(self):
        """Verify deduplication detects identical normalized code across rows."""
        rec1 = {
            "cve_id": "CVE-2019-1001",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "aaaabbbbccccdddd",
            "code": "void parse(struct node *p) { if (p->val == NULL) return; }",
            "is_vul": True
        }
        rec2 = {
            "cve_id": "CVE-2019-1002",
            "cwe_id": "CWE-476",
            "project": "linux",
            "commit_id": "eeeeffffaaaabbbb",
            "code": "void parse( struct  node *p ) {\n  if ( p->val == NULL ) return;\n}",
            "is_vul": True
        }
        ex1, rej1, _ = self.adapter.process_record(rec1, row_number=701)
        ex2, rej2, _ = self.adapter.process_record(rec2, row_number=702)

        self.assertIsNotNone(ex1)
        self.assertIsNone(ex2)
        self.assertIsNotNone(rej2)
        self.assertIn("DUPLICATE_CODE_HASH", rej2["rejection_reason"])

    def test_weak_cwe401_and_cwe362_evidence_rejection(self):
        """Verify weak, generic, or ambiguous evidence is quarantined with precise reasons."""
        # 1. Weak CWE-401 (contains 'cleanup' but no malloc/allocation)
        rec_weak_401 = {
            "cve_id": "CVE-2020-4010",
            "cwe_id": "CWE-401",
            "project": "linux",
            "commit_id": "1111222233334444",
            "code": "void cleanup_task(int code) { log_cleanup(); return; }",
            "is_vul": True
        }
        ex_401, rej_401, _ = self.adapter.process_record(rec_weak_401, row_number=801)
        self.assertIsNone(ex_401)
        self.assertIn("CWE-401 lacks concrete resource/memory allocation", rej_401["rejection_reason"])

        # 2. Weak CWE-362 (contains 'thread' variable but no synchronization primitive)
        rec_weak_362 = {
            "cve_id": "CVE-2020-3620",
            "cwe_id": "CWE-362",
            "project": "Chrome",
            "commit_id": "5555666677778888",
            "code": "void process_thread_id(int thread_id) { int active = thread_id; }",
            "is_vul": True
        }
        ex_362, rej_362, _ = self.adapter.process_record(rec_weak_362, row_number=802)
        self.assertIsNone(ex_362)
        self.assertIn("CWE-362 lacks synchronization or atomic concurrency primitives", rej_362["rejection_reason"])

        # 3. Weak CWE-190 (simple loop increment with no overflow evidence)
        rec_weak_190 = {
            "cve_id": "CVE-2020-1900",
            "cwe_id": "CWE-190",
            "project": "linux",
            "commit_id": "9999000011112222",
            "code": "int increment_val(int i) { int res = i + 1; return res; }",
            "is_vul": True
        }
        ex_190, rej_190, _ = self.adapter.process_record(rec_weak_190, row_number=803)
        self.assertIsNone(ex_190)
        self.assertIn("CWE-190 lacks concrete integer overflow or boundary evidence", rej_190["rejection_reason"])

    def test_deterministic_output(self):
        """Verify deterministic output across multiple adapter runs."""
        rec = {
            "cve_id": "CVE-2018-12896",
            "cwe_id": "CWE-190",
            "project": "linux",
            "commit_id": "78c9c4dfbf8c04883941445a195276bb4bb92c76",
            "code": "void check(int a, int b) { if (a > INT_MAX - b) return; }",
            "is_vul": True,
            "license": "Public-Domain"
        }
        adapter1 = BigVulTargetedAdapterV2()
        adapter2 = BigVulTargetedAdapterV2()

        ex1, _, _ = adapter1.process_record(rec, row_number=901)
        ex2, _, _ = adapter2.process_record(rec, row_number=901)

        self.assertIsNotNone(ex1)
        self.assertIsNotNone(ex2)
        self.assertEqual(ex1.example_id, ex2.example_id)
        self.assertEqual(ex1.source_record_id, ex2.source_record_id)
        self.assertEqual(ex1.to_jsonl(), ex2.to_jsonl())

    def test_original_n2c_outputs_unchanged(self):
        """Verify original Experiment N2C output artifacts remain byte-for-byte unchanged."""
        n2c_dir = ROOT_DIR / "data" / "experiments" / "experiment_n2c"
        for filename, expected_hash in self.ORIGINAL_N2C_HASHES.items():
            filepath = n2c_dir / filename
            self.assertTrue(filepath.exists(), f"Missing N2C file: {filepath}")
            actual_hash = hashlib.sha256(filepath.read_bytes()).hexdigest().lower()
            self.assertEqual(
                actual_hash,
                expected_hash.lower(),
                f"N2C file {filename} hash mismatch! Expected {expected_hash}, got {actual_hash}"
            )


if __name__ == "__main__":
    unittest.main()

