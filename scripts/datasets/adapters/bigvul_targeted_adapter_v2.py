"""
Targeted Big-Vul Dataset Adapter v2 for PATCHPROOF (Experiment N2C.1).

Improved version with:
1. Deterministic source-row identities preserving row numbers and provenance.
2. Full 64-char SHA-256 normalized content hashing.
3. Pre-hashing C vs C++ detection with uncertainty tracking (no project-name assumption).
4. Strict semantic justification guards (rejecting weak CWE-401, CWE-362, CWE-190 evidence).
5. Truthful verification status ('unverified_static') and non-fabricated empty faulty lines ([]).
6. Conservative license handling (preserves raw value, marks missing as 'unknown').
7. Full commit ID preservation (raw and normalized).
"""

import os
import sys
import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import Counter

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.datasets.schema import CodeDebuggingExample


class BigVulTargetedAdapterV2:
    """
    High-fidelity adapter for Big-Vul dataset extraction adhering to
    strict provenance, semantic verification, and non-fabrication rules.
    """

    CWE_MAPPING = {
        "CWE-476": "null_pointer",
        "CWE-401": "resource_leak",
        "CWE-190": "undefined_behavior",
        "CWE-362": "state_management",
    }

    # C++ detection regular expressions (keywords, syntax, casts, templates)
    RE_CPP_SYNTAX = re.compile(
        r'\b(class\s+\w+|namespace\s+\w+|template\s*<|std::|nullptr|public:|private:|protected:|'
        r'virtual\s+|override|noexcept|constexpr\b|static_cast<|reinterpret_cast<|dynamic_cast<|'
        r'const_cast<|new\s+\w+|delete\s+\w+|delete\[\]|throw\s+|catch\s*\()\b'
    )
    RE_C_SYNTAX = re.compile(
        r'\b(struct\s+\w+|typedef\s+|char\*|int\b|void\b|return\b|static\b|goto\b|sizeof\s*\()\b'
    )

    # Semantic Guard: CWE-476 (NULL pointer dereference)
    RE_PTR_DEREF = re.compile(r'->|\*\w+|\[\w+\]')
    RE_PTR_NULL_CONTEXT = re.compile(
        r'(\bNULL\b|\bnullptr\b|!\s*\w+|\b\w+\s*==\s*NULL|\b\w+\s*==\s*nullptr|\b\w+\s*!=\s*NULL|\b\w+\s*!=\s*nullptr|'
        r'\b(?:find|get|alloc|malloc|calloc|realloc|lookup|search|create)\w*\s*\()',
        re.IGNORECASE
    )

    # Semantic Guard: CWE-401 (Resource Leak) - Requires explicit allocation and lifecycle
    RE_RESOURCE_ALLOC = re.compile(
        r'\b(malloc|calloc|realloc|strdup|kcalloc|kmalloc|kzalloc|vmalloc|g_malloc|g_strdup|'
        r'new\s+\w+|fopen|open|socket|asprintf)\s*\(',
        re.IGNORECASE
    )
    RE_RESOURCE_FREE = re.compile(
        r'\b(free|kfree|vfree|g_free|delete\s+\w+|delete\[\]|close|fclose|release|put_\w+|destroy|dispose)\s*\(',
        re.IGNORECASE
    )

    # Semantic Guard: CWE-362 (Race Condition / Concurrency)
    RE_CONCURRENCY_PRIMITIVES = re.compile(
        r'\b(mutex\w*|spin_lock\w*|spin_unlock\w*|pthread_mutex\w*|MutexLocker|AutoLock|'
        r'atomic_\w+|std::atomic|rwlock\w*|read_lock\w*|write_lock\w*|down_read\w*|up_read\w*|'
        r'down_write\w*|up_write\w*|rcu_read_lock|rcu_read_unlock|smp_mb|barrier\w*|sem_wait|sem_post)\b',
        re.IGNORECASE
    )
    RE_SHARED_STATE_HINT = re.compile(
        r'\b(shared\w*|global\w*|g_\w+|table_\w+|queue_\w+|thread_\w+|session_\w+|task_struct|ipc_\w+|client_\w+)\b',
        re.IGNORECASE
    )

    # Semantic Guard: CWE-190 (Integer Overflow / Undefined Behavior)
    RE_INT_ARITHMETIC = re.compile(r'[\+\-\*\/\%]|<<|>>')
    RE_INT_TYPES = re.compile(
        r'\b(int|size_t|long|unsigned|short|uint\w*|int\w*|u8|u16|u32|u64|s8|s16|s32|s64|INT_MAX|UINT_MAX|SIZE_MAX|LLONG_MAX)\b'
    )
    RE_OVERFLOW_EVIDENCE = re.compile(
        r'(INT_MAX|UINT_MAX|SIZE_MAX|LLONG_MAX|overflow|__builtin_\w+_overflow|check_\w+|safe_\w+|0x[0-9a-fA-F]{4,}|'
        r'(?:\b(?:len|size|count|width|height|stride|num|total|n)\s*[\*\+]\s*(?:len|size|count|width|height|stride|num|total|n|sizeof|\d+))|'
        r'(?:\b(?:malloc|calloc|realloc|kmalloc|kzalloc|kcalloc|vmalloc|alloc)\s*\([^\)]*[\*\+][^\)]*\)))',
        re.IGNORECASE
    )

    def __init__(self, min_code_len: int = 15):
        self.min_code_len = min_code_len
        self.seen_code_hashes: Set[str] = set()

    @classmethod
    def detect_language(cls, code: str, fixed_code: Optional[str]) -> Tuple[str, bool]:
        """
        Conservative C vs C++ detection based strictly on code syntax.
        Returns: (detected_language, is_certain)
        """
        combined = code + ("\n" + fixed_code if fixed_code else "")
        if cls.RE_CPP_SYNTAX.search(combined):
            return "cpp", True
        elif cls.RE_C_SYNTAX.search(combined):
            return "c", True
        else:
            # Uncertain / generic snippet - defaults to C with uncertain flag
            return "c", False

    @staticmethod
    def compute_normalized_code_hash(code: str, language: str) -> str:
        """Computes a full 64-character SHA-256 hash of whitespace-normalized code."""
        norm_code = "".join(code.split())
        key = f"{language}:{norm_code}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_commit_id(raw_commit: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Preserves original commit ID while extracting a clean hex commit hash.
        Returns (raw_commit, normalized_commit).
        """
        if not raw_commit or not isinstance(raw_commit, str):
            return None, None
        raw_clean = raw_commit.strip()
        # Strip query parameters such as ?w=1 or url anchors
        norm_commit = raw_clean.split('?')[0].split('#')[0].strip()
        return raw_clean, norm_commit

    def validate_semantics(
        self,
        cwe_id: str,
        code: str,
        fixed_code: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Strict semantic validation preventing weak or ambiguous mappings.
        Returns (is_valid, failure_reason).
        """
        combined = code + ("\n" + fixed_code if fixed_code else "")

        if cwe_id == "CWE-476":
            has_deref = bool(self.RE_PTR_DEREF.search(code))
            has_null_ctx = bool(self.RE_PTR_NULL_CONTEXT.search(combined))
            if not has_deref:
                return False, "AMBIGUOUS_SEMANTICS: CWE-476 lacks pointer dereference syntax in code"
            if not has_null_ctx:
                return False, "AMBIGUOUS_SEMANTICS: CWE-476 lacks NULL comparison, nullptr or pointer source context"
            return True, None

        elif cwe_id == "CWE-401":
            has_alloc = bool(self.RE_RESOURCE_ALLOC.search(code))
            has_free = bool(self.RE_RESOURCE_FREE.search(combined))
            if not has_alloc:
                return False, "AMBIGUOUS_SEMANTICS: CWE-401 lacks concrete resource/memory allocation call"
            if not has_free:
                return False, "AMBIGUOUS_SEMANTICS: CWE-401 lacks deallocation or free lifecycle evidence"
            return True, None

        elif cwe_id == "CWE-190":
            has_arith = bool(self.RE_INT_ARITHMETIC.search(code))
            has_types = bool(self.RE_INT_TYPES.search(code))
            has_overflow = bool(self.RE_OVERFLOW_EVIDENCE.search(combined))
            if not (has_arith and has_types):
                return False, "AMBIGUOUS_SEMANTICS: CWE-190 lacks integer arithmetic and numeric type manipulation"
            if not has_overflow:
                return False, "AMBIGUOUS_SEMANTICS: CWE-190 lacks concrete integer overflow or boundary evidence"
            return True, None

        elif cwe_id == "CWE-362":
            has_sync = bool(self.RE_CONCURRENCY_PRIMITIVES.search(combined))
            has_shared = bool(self.RE_SHARED_STATE_HINT.search(combined))
            if not has_sync:
                return False, "AMBIGUOUS_SEMANTICS: CWE-362 lacks synchronization or atomic concurrency primitives"
            if not has_shared:
                return False, "AMBIGUOUS_SEMANTICS: CWE-362 lacks shared resource or state access context"
            return True, None

        return False, f"UNSUPPORTED_CWE: {cwe_id}"

    def process_record(
        self,
        raw_record: Dict[str, Any],
        row_number: int,
        source_name: str = "big_vul_real_15000.jsonl"
    ) -> Tuple[Optional[CodeDebuggingExample], Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Processes a single record with provenance, language classification,
        and strict semantic guards.
        Returns: (example_or_none, quarantine_or_none, metadata)
        """
        meta = {
            "row_number": row_number,
            "detected_language": "c",
            "language_certain": False,
            "full_code_hash": ""
        }

        # 1. Structural Validation
        if not isinstance(raw_record, dict):
            return None, {
                "row_number": row_number,
                "rejection_reason": "INVALID_RECORD_FORMAT: Expected JSON object",
                "raw_record": raw_record
            }, meta

        code = raw_record.get("code")
        if not code or not isinstance(code, str) or len(code.strip()) < self.min_code_len:
            return None, {
                "row_number": row_number,
                "rejection_reason": "MISSING_OR_SHORT_CODE: Code missing or below minimum length",
                "raw_record": raw_record
            }, meta

        # 2. Vulnerability Status
        if not raw_record.get("is_vul", False):
            return None, {
                "row_number": row_number,
                "rejection_reason": "NON_VULNERABLE_OR_CLEAN: is_vul is False or missing",
                "raw_record": raw_record
            }, meta

        # 3. CWE Target Validation
        cwe_id = raw_record.get("cwe_id")
        if not cwe_id or not isinstance(cwe_id, str):
            return None, {
                "row_number": row_number,
                "rejection_reason": "MISSING_CWE_ID: cwe_id is null or missing",
                "raw_record": raw_record
            }, meta

        cwe_id = cwe_id.strip()
        if cwe_id not in self.CWE_MAPPING:
            return None, {
                "row_number": row_number,
                "rejection_reason": f"UNSUPPORTED_CWE: {cwe_id} not in target list",
                "raw_record": raw_record
            }, meta

        target_category = self.CWE_MAPPING[cwe_id]

        # 4. Provenance Validation & Non-Sanitized Commit Preservation
        project = raw_record.get("project")
        raw_commit = raw_record.get("commit_id")
        cve_id = raw_record.get("cve_id")

        missing_fields = []
        if not project:
            missing_fields.append("project")
        if not raw_commit:
            missing_fields.append("commit_id")
        if not cve_id:
            missing_fields.append("cve_id")

        if missing_fields:
            return None, {
                "row_number": row_number,
                "rejection_reason": f"MISSING_REQUIRED_FIELDS: {', '.join(missing_fields)}",
                "raw_record": raw_record
            }, meta

        raw_commit_id, norm_commit_id = self.normalize_commit_id(raw_commit)

        # 5. Language Detection BEFORE Content Hashing
        fixed_code = raw_record.get("fixed_code")
        lang, lang_certain = self.detect_language(code, fixed_code)
        meta["detected_language"] = lang
        meta["language_certain"] = lang_certain

        # 6. Full SHA-256 Code Hashing
        full_code_hash = self.compute_normalized_code_hash(code, lang)
        meta["full_code_hash"] = full_code_hash

        # 7. Semantic Justification Guard
        is_justified, semantic_error = self.validate_semantics(cwe_id, code, fixed_code)
        if not is_justified:
            return None, {
                "row_number": row_number,
                "cve_id": cve_id,
                "project": project,
                "raw_commit": raw_commit_id,
                "rejection_reason": semantic_error,
                "raw_record": raw_record
            }, meta

        # 8. Deduplication Guard
        if full_code_hash in self.seen_code_hashes:
            return None, {
                "row_number": row_number,
                "cve_id": cve_id,
                "project": project,
                "rejection_reason": f"DUPLICATE_CODE_HASH: {full_code_hash}",
                "raw_record": raw_record
            }, meta

        self.seen_code_hashes.add(full_code_hash)

        # 9. Conservative License Handling
        # Preserve raw license if provided; never infer or invent
        raw_license = raw_record.get("license")
        record_license = raw_license if (raw_license and isinstance(raw_license, str) and raw_license.strip()) else "unknown"

        # 10. Construct Deterministic Source Row Identity
        # Distinct per row even when CVE and commit are shared
        source_record_id = f"bigvul_row_{row_number:06d}_{cve_id}_{project}_{norm_commit_id[:8]}"
        example_id_seed = f"v2:{row_number}:{source_name}:{cve_id}:{raw_commit_id}:{full_code_hash}"
        example_id = f"pp-bvl-{hashlib.sha256(example_id_seed.encode('utf-8')).hexdigest()[:12]}"

        # Construct CodeDebuggingExample
        example = CodeDebuggingExample(
            example_id=example_id,
            language=lang,
            bug_category=target_category,
            difficulty="hard",
            original_code=code,
            bug_description=f"{cve_id}: {cwe_id} ({target_category}) in {project} (commit {norm_commit_id[:8]}, raw_commit={raw_commit_id})",
            faulty_line_numbers=[],  # Truthful: No fabricated faulty line without AST localization
            corrected_code=fixed_code if fixed_code and isinstance(fixed_code, str) and len(fixed_code.strip()) >= 5 else None,
            patch=None,
            test_cases=[],
            verification_status="unverified_static",  # Truthful: Static unverified without compiler execution
            source_dataset="big_vul",
            source_record_id=source_record_id,
            repository=f"bigvul/{project}",
            commit_hash=norm_commit_id,
            license=record_license,
            duplicate_group_id=f"bigvul_{project}_{norm_commit_id[:8]}",
            template_family=f"bigvul_{project}_{norm_commit_id[:8]}",
            split="unassigned"
        )

        return example, None, meta

    def process_file(
        self,
        input_path: Path,
        candidates_path: Path,
        quarantine_path: Path,
        report_path: Path
    ) -> Dict[str, Any]:
        """
        Processes entire input JSONL file and outputs candidates, quarantine, and report.
        """
        candidates_path.parent.mkdir(parents=True, exist_ok=True)
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        total_read = 0
        extracted_candidates: List[CodeDebuggingExample] = []
        quarantined_records: List[Dict[str, Any]] = []
        rejection_counts: Counter = Counter()
        class_counts: Counter = Counter()
        lang_counts: Counter = Counter()
        uncertain_lang_count = 0
        project_counts: Counter = Counter()
        unique_cves: Set[str] = set()
        unique_groups: Set[str] = set()
        missing_license_count = 0
        source_provided_license_count = 0

        self.seen_code_hashes.clear()
        source_name = input_path.name

        with open(input_path, "r", encoding="utf-8") as f_in:
            for row_no, line in enumerate(f_in, start=1):
                line = line.strip()
                if not line:
                    continue
                total_read += 1

                try:
                    raw_rec = json.loads(line)
                except json.JSONDecodeError as e:
                    quarantined_records.append({
                        "row_number": row_no,
                        "rejection_reason": f"JSON_DECODE_ERROR: line {row_no} - {str(e)}",
                        "raw_line": line[:200]
                    })
                    rejection_counts["JSON_DECODE_ERROR"] += 1
                    continue

                # Track license presence in raw input
                if not raw_rec.get("license"):
                    missing_license_count += 1
                else:
                    source_provided_license_count += 1

                example, rejection, meta = self.process_record(raw_rec, row_number=row_no, source_name=source_name)

                if example is not None:
                    extracted_candidates.append(example)
                    class_counts[example.bug_category] += 1
                    lang_counts[example.language] += 1
                    if not meta["language_certain"]:
                        uncertain_lang_count += 1
                    proj = example.repository.replace("bigvul/", "")
                    project_counts[proj] += 1
                    unique_groups.add(example.duplicate_group_id)
                    cve_part = example.bug_description.split(":")[0]
                    unique_cves.add(cve_part)
                else:
                    quarantined_records.append(rejection)
                    reason_key = rejection.get("rejection_reason", "UNKNOWN").split(":")[0]
                    rejection_counts[reason_key] += 1

        # Write candidates
        with open(candidates_path, "w", encoding="utf-8") as f_cand:
            for ex in extracted_candidates:
                f_cand.write(ex.to_jsonl() + "\n")

        # Write quarantine
        with open(quarantine_path, "w", encoding="utf-8") as f_quar:
            for q in quarantined_records:
                f_quar.write(json.dumps(q, ensure_ascii=False) + "\n")

        # Compile report
        duplicates_count = rejection_counts.get("DUPLICATE_CODE_HASH", 0)
        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "adapter_version": "2.0.0",
            "source_file": str(input_path),
            "total_input_records": total_read,
            "valid_candidates_extracted": len(extracted_candidates),
            "duplicates_removed": duplicates_count,
            "quarantined_records": len(quarantined_records),
            "class_distribution": dict(class_counts),
            "language_distribution": dict(lang_counts),
            "uncertain_language_classifications": uncertain_lang_count,
            "unique_source_row_identities": len(extracted_candidates),
            "unique_projects_count": len(project_counts),
            "unique_cves_count": len(unique_cves),
            "unique_isolation_groups_count": len(unique_groups),
            "top_projects": dict(project_counts.most_common(15)),
            "license_accounting": {
                "source_provided_license_count": source_provided_license_count,
                "missing_license_count": missing_license_count,
                "license_description": "Source-provided unverified metadata preserved directly from raw dataset"
            },
            "rejection_breakdown": dict(rejection_counts),
            "provenance_spec": {
                "source_dataset": "big_vul",
                "fault_localization_policy": "empty_list_unlocalized",
                "verification_status": "unverified_static",
                "hash_algorithm": "full_sha256"
            },
            "output_files": {
                "candidates": str(candidates_path),
                "quarantine": str(quarantine_path),
                "report": str(report_path)
            }
        }

        with open(report_path, "w", encoding="utf-8") as f_rep:
            json.dump(report, f_rep, indent=2)

        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Targeted Big-Vul Adapter v2 for PATCHPROOF (Experiment N2C.1)")
    parser.add_argument("--input", type=str, default="data/raw/big_vul_real_15000.jsonl")
    parser.add_argument("--output-candidates", type=str, default="data/experiments/experiment_n2c_1/bigvul_candidates.jsonl")
    parser.add_argument("--output-quarantine", type=str, default="data/experiments/experiment_n2c_1/unmapped_candidates.jsonl")
    parser.add_argument("--output-report", type=str, default="data/experiments/experiment_n2c_1/extraction_report.json")
    args = parser.parse_args()

    adapter = BigVulTargetedAdapterV2()
    report = adapter.process_file(
        input_path=Path(args.input),
        candidates_path=Path(args.output_candidates),
        quarantine_path=Path(args.output_quarantine),
        report_path=Path(args.output_report)
    )

    print("Experiment N2C.1 Big-Vul Targeted Extraction v2 Complete!")
    print(f"Total read: {report['total_input_records']}")
    print(f"Candidates extracted: {report['valid_candidates_extracted']}")
    print(f"Quarantined records: {report['quarantined_records']}")
    print(f"Class distribution: {report['class_distribution']}")
    print(f"Language distribution: {report['language_distribution']}")
    print(f"Unique source rows: {report['unique_source_row_identities']}")
    print(f"Unique isolation groups: {report['unique_isolation_groups_count']}")


if __name__ == "__main__":
    main()

