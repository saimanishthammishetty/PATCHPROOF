import ast
import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
from scripts.datasets.schema import CodeDebuggingExample

logger = logging.getLogger("DatasetValidator")

REPORTS_DIR = Path("C:/PATCHPROOF/data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class DatasetValidator:
    """
    Validates examples against schema invariants, Python AST syntactic parsing,
    faulty line boundaries, and records all rejections with diagnostic rationale.
    """

    def __init__(self, log_rejections: bool = True):
        self.log_rejections = log_rejections
        self.rejection_file = REPORTS_DIR / "rejections.jsonl"
        if self.rejection_file.exists():
            self.rejection_file.unlink()

    def _record_rejection(self, ex_id: str, source: str, reason: str, details: str):
        if not self.log_rejections:
            return
        entry = {
            "example_id": ex_id,
            "source_dataset": source,
            "rejection_reason": reason,
            "details": details
        }
        with open(self.rejection_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def validate_example(self, ex: CodeDebuggingExample) -> Tuple[bool, str]:
        # 1. Required text content
        if not ex.original_code or not ex.original_code.strip():
            return False, "EMPTY_ORIGINAL_CODE"
        if not ex.bug_description or not ex.bug_description.strip():
            return False, "EMPTY_DESCRIPTION"

        # 2. Line number bounds
        line_count = len(ex.original_code.splitlines())
        for lno in ex.faulty_line_numbers:
            if lno < 1 or lno > line_count:
                return False, f"FAULTY_LINE_OUT_OF_BOUNDS: line {lno} for code with {line_count} lines"

        # 3. Python AST parsing check
        if ex.language == "python":
            try:
                ast.parse(ex.original_code)
            except SyntaxError as e:
                # If it's a bug that's specifically a syntax error it might fail AST,
                # but for general debugging examples we require valid AST structure
                if ex.bug_category != "syntax_error":
                    return False, f"PYTHON_SYNTAX_ERROR: {str(e)}"

            if ex.corrected_code:
                try:
                    ast.parse(ex.corrected_code)
                except SyntaxError as e:
                    return False, f"FIXED_PYTHON_SYNTAX_ERROR: {str(e)}"

        # 4. Patch sanity check
        if ex.patch and not any(line.startswith("@@") or line.startswith("---") for line in ex.patch.splitlines()):
            return False, "MALFORMED_UNIFIED_DIFF_PATCH"

        return True, "VALID"

    def validate_batch(
        self,
        examples: List[CodeDebuggingExample]
    ) -> Tuple[List[CodeDebuggingExample], Dict[str, Any]]:
        passed: List[CodeDebuggingExample] = []
        rejection_counts: Dict[str, int] = {}
        verification_status_counts: Dict[str, int] = {}

        for ex in examples:
            valid, reason = self.validate_example(ex)
            if valid:
                passed.append(ex)
                v_stat = ex.verification_status
                verification_status_counts[v_stat] = verification_status_counts.get(v_stat, 0) + 1
            else:
                rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
                self._record_rejection(ex.example_id, ex.source_dataset, reason, ex.bug_description)

        quality_report = {
            "total_evaluated": len(examples),
            "passed": len(passed),
            "rejected": len(examples) - len(passed),
            "pass_rate_percent": round(len(passed) / max(1, len(examples)) * 100, 2),
            "rejections_by_reason": rejection_counts,
            "verification_status_coverage": verification_status_counts
        }

        # Save quality report
        report_path = REPORTS_DIR / "validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(quality_report, f, indent=2)

        return passed, quality_report

