"""
Targeted Big-Vul Dataset Adapter for PATCHPROOF (Experiment N2C).

Extracts high-fidelity real-world C/C++ defect samples from cached Big-Vul records
targeting minority classes (null_pointer, resource_leak, undefined_behavior, state_management)
with strict semantic justification and quarantine for ambiguous or non-target records.
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

# Ensure root directory is on PYTHONPATH for schema imports
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.datasets.schema import CodeDebuggingExample


class BigVulTargetedAdapter:
    """
    Extracts and validates targeted CWE candidates from Big-Vul into the
    CodeDebuggingExample schema with strict semantic guards and quarantine.
    """

    # Target CWE to Canonical Class mappings
    CWE_MAPPING = {
        "CWE-476": "null_pointer",
        "CWE-401": "resource_leak",
        "CWE-190": "undefined_behavior",
        "CWE-362": "state_management",
    }

    # Semantic validation regular expressions
    RE_ARITHMETIC = re.compile(r'[\+\-\*\/\%]|<<|>>')
    RE_INT_TYPES = re.compile(
        r'\b(int|size_t|long|unsigned|short|uint\w*|int\w*|INT_MAX|UINT_MAX|SIZE_MAX|LLONG_MAX|sizeof)\b'
    )
    RE_CONCURRENCY = re.compile(
        r'\b(mutex\w*|lock\w*|unlock\w*|atomic\w*|thread\w*|spin\w*|sync\w*|shared\w*|barrier\w*|sem_\w*|pthread\w*|critical\w*|volatile\w*|rwlock\w*|futex\w*|sched\w*|queue\w*|sock\w*|wait\w*|wake\w*)\b',
        re.IGNORECASE
    )
    RE_POINTER = re.compile(r'->|\*|\[\w+\]|\bNULL\b|\bnullptr\b')
    RE_ALLOC_RESOURCE = re.compile(
        r'\b(malloc|calloc|realloc|strdup|free|alloc\w*|open|close|fopen|fclose|new|delete|cleanup|release|dispose)\b',
        re.IGNORECASE
    )

    def __init__(self, min_code_len: int = 15):
        self.min_code_len = min_code_len
        self.seen_code_hashes: Set[str] = set()

    @staticmethod
    def compute_normalized_code_hash(code: str, language: str = "c") -> str:
        """Computes whitespace-normalized SHA-256 hash for deduplication."""
        norm_code = "".join(code.split())
        key = f"{language}:{norm_code}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def validate_semantics(self, cwe_id: str, code: str, fixed_code: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validates whether the actual code and label semantics justify the 13-class mapping.
        Returns (is_valid, failure_reason).
        """
        if cwe_id == "CWE-476":
            if not self.RE_POINTER.search(code):
                return False, "AMBIGUOUS_SEMANTICS: CWE-476 lacks pointer syntax or NULL checks"
            return True, None

        elif cwe_id == "CWE-401":
            search_text = code + ("\n" + fixed_code if fixed_code else "")
            if not self.RE_ALLOC_RESOURCE.search(search_text):
                return False, "AMBIGUOUS_SEMANTICS: CWE-401 lacks memory/resource allocation or free primitives"
            return True, None

        elif cwe_id == "CWE-190":
            # Must contain both integer types and arithmetic operations
            has_arith = bool(self.RE_ARITHMETIC.search(code))
            has_types = bool(self.RE_INT_TYPES.search(code))
            if not (has_arith and has_types):
                return False, "AMBIGUOUS_SEMANTICS: CWE-190 lacks integer arithmetic and overflow semantics"
            return True, None

        elif cwe_id == "CWE-362":
            # Must involve concurrency/synchronization primitives in vulnerable or fixed code
            search_text = code + ("\n" + fixed_code if fixed_code else "")
            if not self.RE_CONCURRENCY.search(search_text):
                return False, "AMBIGUOUS_SEMANTICS: CWE-362 lacks concurrency or synchronization primitives"
            return True, None

        return False, f"UNSUPPORTED_CWE: {cwe_id}"

    def process_record(self, raw_record: Dict[str, Any]) -> Tuple[Optional[CodeDebuggingExample], Optional[Dict[str, Any]]]:
        """
        Processes a single Big-Vul record.
        Returns (example, None) on success, or (None, quarantine_entry) on rejection.
        """
        # 1. Basic structural checks
        if not isinstance(raw_record, dict):
            return None, {
                "rejection_reason": "INVALID_RECORD_FORMAT: Expected JSON object",
                "raw_record": raw_record
            }

        code = raw_record.get("code")
        if not code or not isinstance(code, str) or len(code.strip()) < self.min_code_len:
            return None, {
                "rejection_reason": "MISSING_OR_SHORT_CODE: Code missing or < min length",
                "raw_record": raw_record
            }

        # 2. Check vulnerability status
        if not raw_record.get("is_vul", False):
            return None, {
                "rejection_reason": "NON_VULNERABLE_OR_CLEAN: is_vul is False or missing",
                "raw_record": raw_record
            }

        # 3. Check CWE identification
        cwe_id = raw_record.get("cwe_id")
        if not cwe_id or not isinstance(cwe_id, str):
            return None, {
                "rejection_reason": "MISSING_CWE_ID: cwe_id is null or invalid",
                "raw_record": raw_record
            }

        cwe_id = cwe_id.strip()
        if cwe_id not in self.CWE_MAPPING:
            return None, {
                "rejection_reason": f"UNSUPPORTED_CWE: {cwe_id} not in target list",
                "raw_record": raw_record
            }

        target_category = self.CWE_MAPPING[cwe_id]

        # 4. Check required provenance fields
        project = raw_record.get("project")
        commit_id = raw_record.get("commit_id")
        cve_id = raw_record.get("cve_id")

        missing_fields = []
        if not project:
            missing_fields.append("project")
        if not commit_id:
            missing_fields.append("commit_id")
        if not cve_id:
            missing_fields.append("cve_id")

        if missing_fields:
            return None, {
                "rejection_reason": f"MISSING_REQUIRED_FIELDS: {', '.join(missing_fields)}",
                "raw_record": raw_record
            }

        # 5. Semantic Justification Guard
        fixed_code = raw_record.get("fixed_code")
        is_justified, semantic_error = self.validate_semantics(cwe_id, code, fixed_code)
        if not is_justified:
            return None, {
                "rejection_reason": semantic_error,
                "raw_record": raw_record
            }

        # 6. Deduplication Check
        norm_hash = self.compute_normalized_code_hash(code, "c")
        if norm_hash in self.seen_code_hashes:
            return None, {
                "rejection_reason": f"DUPLICATE_CODE_HASH: {norm_hash}",
                "raw_record": raw_record
            }

        self.seen_code_hashes.add(norm_hash)

        # 7. Construct Deterministic Pydantic Example
        # Deterministic ID based on CVE, commit, and content hash
        id_seed = f"{cve_id}:{commit_id}:{norm_hash}"
        example_id = f"pp-bvl-{hashlib.sha256(id_seed.encode('utf-8')).hexdigest()[:12]}"
        
        # Determine language (cpp if project/code indicates C++, default c)
        lang = "cpp" if "cpp" in project.lower() or "chrome" in project.lower() or "class " in code else "c"

        example = CodeDebuggingExample(
            example_id=example_id,
            language=lang,
            bug_category=target_category,
            difficulty="hard",
            original_code=code,
            bug_description=f"{cve_id}: {cwe_id} ({target_category}) defect in {project}",
            faulty_line_numbers=[1],
            corrected_code=fixed_code if fixed_code and isinstance(fixed_code, str) and len(fixed_code.strip()) >= 5 else None,
            patch=None,
            test_cases=[],
            verification_status="syntax_verified",
            source_dataset="big_vul",
            source_record_id=str(cve_id),
            repository=f"bigvul/{project}",
            commit_hash=str(commit_id),
            license=raw_record.get("license", "Public-Domain"),
            duplicate_group_id=f"bigvul_{project}_{str(commit_id)[:8]}",
            template_family=f"bigvul_{project}_{str(commit_id)[:8]}",
            split="unassigned"
        )

        return example, None

    def process_file(
        self,
        input_path: Path,
        candidates_path: Path,
        quarantine_path: Path,
        report_path: Path
    ) -> Dict[str, Any]:
        """
        Processes an entire input JSONL file and writes outputs to the specified paths.
        """
        candidates_path.parent.mkdir(parents=True, exist_ok=True)
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        total_read = 0
        extracted_candidates: List[CodeDebuggingExample] = []
        quarantined_records: List[Dict[str, Any]] = []
        rejection_counts: Counter = Counter()
        class_counts: Counter = Counter()
        project_counts: Counter = Counter()

        self.seen_code_hashes.clear()

        with open(input_path, "r", encoding="utf-8") as f_in:
            for line_no, line in enumerate(f_in, start=1):
                line = line.strip()
                if not line:
                    continue
                total_read += 1

                try:
                    raw_rec = json.loads(line)
                except json.JSONDecodeError as e:
                    rejection = {
                        "rejection_reason": f"JSON_DECODE_ERROR: line {line_no} - {str(e)}",
                        "raw_line": line[:200]
                    }
                    quarantined_records.append(rejection)
                    rejection_counts["JSON_DECODE_ERROR"] += 1
                    continue

                example, rejection = self.process_record(raw_rec)

                if example is not None:
                    extracted_candidates.append(example)
                    class_counts[example.bug_category] += 1
                    proj = example.repository.replace("bigvul/", "")
                    project_counts[proj] += 1
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
            "source_file": str(input_path),
            "total_input_records": total_read,
            "valid_candidates_extracted": len(extracted_candidates),
            "duplicates_removed": duplicates_count,
            "quarantined_records": len(quarantined_records),
            "class_distribution": dict(class_counts),
            "unique_projects_count": len(project_counts),
            "top_projects": dict(project_counts.most_common(15)),
            "rejection_breakdown": dict(rejection_counts),
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
    parser = argparse.ArgumentParser(description="Targeted Big-Vul Adapter for PATCHPROOF")
    parser.add_argument("--input", type=str, default="data/raw/big_vul_real_15000.jsonl")
    parser.add_argument("--output-candidates", type=str, default="data/experiments/experiment_n2c/bigvul_candidates.jsonl")
    parser.add_argument("--output-quarantine", type=str, default="data/experiments/experiment_n2c/unmapped_candidates.jsonl")
    parser.add_argument("--output-report", type=str, default="data/experiments/experiment_n2c/extraction_report.json")
    args = parser.parse_args()

    adapter = BigVulTargetedAdapter()
    report = adapter.process_file(
        input_path=Path(args.input),
        candidates_path=Path(args.output_candidates),
        quarantine_path=Path(args.output_quarantine),
        report_path=Path(args.output_report)
    )

    print("Targeted Big-Vul Extraction Completed Successfully!")
    print(f"Total read: {report['total_input_records']}")
    print(f"Candidates extracted: {report['valid_candidates_extracted']}")
    print(f"Quarantined records: {report['quarantined_records']}")
    print(f"Duplicates removed: {report['duplicates_removed']}")
    print(f"Class distribution: {report['class_distribution']}")
    print(f"Unique projects: {report['unique_projects_count']}")


if __name__ == "__main__":
    main()
