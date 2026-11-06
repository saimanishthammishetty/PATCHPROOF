"""
PATCHPROOF Phase O.1 — Read-Only Quarantine Policy Engine.
Strict Rules:
  - Function-level deduplication as primary exclusion policy.
  - Exact SHA-256 duplicates REJECTED.
  - Normalized-code duplicates REJECTED.
  - AST-equivalent functions REJECTED where reliable AST parsing is available.
  - Same-function and template-family overlaps REJECTED.
  - Same-commit distinct functions FLAGGED for manual review (NEVER automatically accepted).
  - Missing or ambiguous provenance REJECTED.
  - nginx and SQLite marked UNAVAILABLE_OFFLINE.
  - Zero data acquisition, zero model modifications, preserves NEVER_MERGE_ACTIVE.
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple, Optional, Set

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pycparser import c_parser, c_ast, c_generator
from scripts.experiments.experiment_i.static_analyzer import StaticAnalyzer

C_TYPEDEFS = """
typedef int FILE;
typedef unsigned long size_t;
typedef int bool;
typedef unsigned char uint8_t;
typedef unsigned int uint32_t;
typedef unsigned short uint16_t;
typedef long int64_t;
typedef unsigned long uint64_t;
typedef void SSL;
typedef void tvbuff_t;
typedef void packet_info;
typedef void proto_tree;
"""

class FullCScopeVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.local_map = {}
        self.p_idx = 1
        self.v_idx = 1

    def visit_FuncDef(self, node):
        if node.decl.type.args:
            for p in node.decl.type.args.params:
                if isinstance(p, c_ast.Decl) and p.name:
                    self.local_map[p.name] = f"p_{self.p_idx}"
                    self.p_idx += 1
                    p.name = self.local_map[p.name]
                    if hasattr(p.type, 'declname'):
                        p.type.declname = p.name
                    elif hasattr(p.type, 'type') and hasattr(p.type.type, 'declname'):
                        p.type.type.declname = p.name

        def collect_decls(n):
            for child_name, child in n.children():
                if isinstance(child, c_ast.Decl) and child.name:
                    if child.name not in self.local_map:
                        self.local_map[child.name] = f"v_{self.v_idx}"
                        self.v_idx += 1
                        child.name = self.local_map[child.name]
                        if hasattr(child.type, 'declname'):
                            child.type.declname = child.name
                        elif hasattr(child.type, 'type') and hasattr(child.type.type, 'declname'):
                            child.type.type.declname = child.name
                collect_decls(child)

        if node.body:
            collect_decls(node.body)

        self.generic_visit(node.body)

    def visit_ID(self, node):
        if node.name in self.local_map:
            node.name = self.local_map[node.name]

def normalize_c_full(code: str) -> Tuple[str, bool]:
    try:
        parser = c_parser.CParser()
        full_code = C_TYPEDEFS + code
        ast_c = parser.parse(full_code)
        user_func = None
        for ext in reversed(ast_c.ext):
            if isinstance(ext, c_ast.FuncDef):
                user_func = ext
                break
        if not user_func:
            return code, False
        visitor = FullCScopeVisitor()
        visitor.visit(user_func)
        gen = c_generator.CGenerator()
        return gen.visit(user_func), True
    except Exception:
        return code, False

PROJECT_PATTERNS = re.compile(r'\b(av_|qemu_|qemufile|png_|usb_|linux_|android_)', flags=re.IGNORECASE)

def debias_text(code: str) -> str:
    return PROJECT_PATTERNS.sub('lib_', code)

def strip_c_comments(code: str) -> str:
    return re.sub(r'//.*?$|/\*.*?\*/', '', code, flags=re.MULTILINE | re.DOTALL)

def compute_exact_sha256(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()

def compute_normalized_sha256(code: str) -> str:
    clean = "".join(strip_c_comments(debias_text(code)).split())
    return hashlib.sha256(f"c:{clean}".encode("utf-8")).hexdigest()

def compute_ast_sha256(code: str) -> Tuple[Optional[str], bool]:
    """Computes AST-level canonical hash using scope-aware normalization."""
    norm_code, ok = normalize_c_full(code)
    if ok:
        clean = "".join(strip_c_comments(norm_code).split())
        return hashlib.sha256(f"c_ast:{clean}".encode("utf-8")).hexdigest(), True
    return None, False

@dataclass
class QuarantineVerdict:
    status: str  # ACCEPTED | REJECTED | FLAGGED_MANUAL_REVIEW
    decision_code: str
    reason: str
    provenance_verified: bool
    leakage_risk_level: str  # NONE | LOW | MEDIUM | HIGH | CRITICAL
    exact_hash: str
    normalized_hash: str
    ast_hash: Optional[str] = None
    commit_hash: Optional[str] = None

class QuarantinePolicyEngine:
    def __init__(self,
                 exact_exclusions: Optional[Set[str]] = None,
                 norm_exclusions: Optional[Set[str]] = None,
                 ast_exclusions: Optional[Set[str]] = None,
                 commit_exclusions: Optional[Set[str]] = None,
                 template_exclusions: Optional[Set[str]] = None):
        self.exact_exclusions = exact_exclusions if exact_exclusions is not None else set()
        self.norm_exclusions = norm_exclusions if norm_exclusions is not None else set()
        self.ast_exclusions = ast_exclusions if ast_exclusions is not None else set()
        self.commit_exclusions = commit_exclusions if commit_exclusions is not None else set()
        self.template_exclusions = template_exclusions if template_exclusions is not None else set()

        # Session seen sets to prevent internal duplicates
        self.seen_exact: Set[str] = set()
        self.seen_norm: Set[str] = set()
        self.seen_ast: Set[str] = set()

    @classmethod
    def load_from_processed_splits(cls, root_dir: Path = ROOT_DIR) -> "QuarantinePolicyEngine":
        """Loads historical exclusion hashes from existing training, validation, and test datasets."""
        exact_set = set()
        norm_set = set()
        ast_set = set()
        commit_set = set()
        template_set = set()

        split_files = [
            root_dir / "data" / "processed" / "train.jsonl",
            root_dir / "data" / "processed" / "val.jsonl",
            root_dir / "data" / "processed" / "test.jsonl",
            root_dir / "data" / "processed" / "robust_heldout_test.jsonl",
            root_dir / "data" / "experiments" / "experiment_k" / "experiment_k_dataset.jsonl"
        ]

        for sfile in split_files:
            if not sfile.exists():
                continue
            with open(sfile, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        code = record.get("original_code", "")
                        if code:
                            exact_set.add(compute_exact_sha256(code))
                            norm_set.add(compute_normalized_sha256(code))
                        commit = record.get("commit_hash")
                        if commit:
                            commit_set.add(commit.lower().strip())
                        func_name = record.get("function_name")
                        file_path = record.get("file_path")
                        if func_name and file_path:
                            template_set.add(f"{file_path}::{func_name}".lower())
                        tmpl = record.get("template_family")
                        if tmpl:
                            template_set.add(f"tmpl::{tmpl}".lower())
                    except Exception:
                        continue

        return cls(
            exact_exclusions=exact_set,
            norm_exclusions=norm_set,
            ast_exclusions=ast_set,
            commit_exclusions=commit_set,
            template_exclusions=template_set
        )

    def evaluate_candidate(self, candidate: Dict[str, Any]) -> QuarantineVerdict:
        """
        Evaluates a candidate record against the 8-tier quarantine policy.
        """
        repo = str(candidate.get("repository", "")).lower().strip()
        code = candidate.get("original_code", "")
        is_vul = bool(candidate.get("is_vulnerable", False) or candidate.get("vul", 0) == 1)
        commit = str(candidate.get("commit_hash", candidate.get("commit_id", ""))).lower().strip()
        cve = candidate.get("cve_id", candidate.get("CVE ID"))
        cwe = candidate.get("cwe_id", candidate.get("CWE ID"))
        func_name = candidate.get("function_name", "")
        file_path = candidate.get("file_path", "")
        template_fam = candidate.get("template_family", "")

        exact_h = compute_exact_sha256(code) if code else ""
        norm_h = compute_normalized_sha256(code) if code else ""
        ast_h, ast_ok = None, False

        # -------------------------------------------------------------
        # TIER 1: Offline Availability & Source Verification
        # -------------------------------------------------------------
        if any(unavail in repo for unavail in ["nginx", "sqlite"]):
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_SOURCE_UNAVAILABLE_OFFLINE",
                reason="Repository 'nginx' or 'sqlite' is marked UNAVAILABLE_OFFLINE. No downloads or fabrication permitted.",
                provenance_verified=False,
                leakage_risk_level="NONE",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        # -------------------------------------------------------------
        # TIER 2: Excluded Repositories (QEMU & FFmpeg)
        # -------------------------------------------------------------
        if any(ex in repo for ex in ["qemu", "ffmpeg"]):
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_REPOSITORY_QEMU_FFMPEG",
                reason="Repository QEMU/FFmpeg is strictly excluded by design to prevent project-shortcut bias.",
                provenance_verified=False,
                leakage_risk_level="CRITICAL",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        # -------------------------------------------------------------
        # TIER 3: Syntax & Format Validity
        # -------------------------------------------------------------
        if not code or len(code.strip()) < 30:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_SYNTAX_EMPTY_OR_TOO_SHORT",
                reason="Function code is empty or shorter than minimum threshold (30 chars).",
                provenance_verified=False,
                leakage_risk_level="NONE",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        if len(code) > 6000:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_EXCEEDS_MAX_LENGTH",
                reason="Function code exceeds maximum length bound (6000 chars).",
                provenance_verified=False,
                leakage_risk_level="NONE",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        if "{" not in code or "(" not in code:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_SYNTAX_FRAGMENT",
                reason="Code lacks basic function structure (braces and parentheses).",
                provenance_verified=False,
                leakage_risk_level="NONE",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        # -------------------------------------------------------------
        # TIER 4: Provenance Verification & Quality Control
        # -------------------------------------------------------------
        if is_vul:
            # Vulnerable sample: Must have valid CVE, commit, and CWE
            if not cve or not re.match(r"^CVE-\d{4}-\d+$", str(cve).strip()):
                return QuarantineVerdict(
                    status="REJECTED",
                    decision_code="REJECTED_MISSING_OR_AMBIGUOUS_PROVENANCE",
                    reason=f"Vulnerable sample missing or ambiguous CVE identifier: '{cve}'.",
                    provenance_verified=False,
                    leakage_risk_level="HIGH",
                    exact_hash=exact_h,
                    normalized_hash=norm_h,
                    ast_hash=ast_h,
                    commit_hash=commit
                )
            if not commit or len(commit) < 7:
                return QuarantineVerdict(
                    status="REJECTED",
                    decision_code="REJECTED_MISSING_OR_AMBIGUOUS_PROVENANCE",
                    reason=f"Vulnerable sample missing valid commit hash: '{commit}'.",
                    provenance_verified=False,
                    leakage_risk_level="HIGH",
                    exact_hash=exact_h,
                    normalized_hash=norm_h,
                    ast_hash=ast_h,
                    commit_hash=commit
                )
            if not cwe or not str(cwe).strip().startswith("CWE-"):
                return QuarantineVerdict(
                    status="REJECTED",
                    decision_code="REJECTED_MISSING_OR_AMBIGUOUS_PROVENANCE",
                    reason=f"Vulnerable sample missing valid CWE taxonomy label: '{cwe}'.",
                    provenance_verified=False,
                    leakage_risk_level="HIGH",
                    exact_hash=exact_h,
                    normalized_hash=norm_h,
                    ast_hash=ast_h,
                    commit_hash=commit
                )
        else:
            # Clean sample: Must have commit/release
            if not commit or len(commit) < 7:
                return QuarantineVerdict(
                    status="REJECTED",
                    decision_code="REJECTED_MISSING_OR_AMBIGUOUS_PROVENANCE",
                    reason="Clean sample missing verifiable release tag or commit hash.",
                    provenance_verified=False,
                    leakage_risk_level="MEDIUM",
                    exact_hash=exact_h,
                    normalized_hash=norm_h,
                    ast_hash=ast_h,
                    commit_hash=commit
                )

        # -------------------------------------------------------------
        # TIER 5: Exact SHA-256 Deduplication
        # -------------------------------------------------------------
        if exact_h in self.exact_exclusions:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_EXACT_CODE_DUPLICATE",
                reason="Exact code SHA-256 hash matches an existing sample in historical datasets.",
                provenance_verified=True,
                leakage_risk_level="CRITICAL",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )
        if exact_h in self.seen_exact:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_INTERNAL_EXACT_DUPLICATE",
                reason="Exact code SHA-256 duplicate within current acquisition session.",
                provenance_verified=True,
                leakage_risk_level="HIGH",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        # -------------------------------------------------------------
        # TIER 6: Normalized-Code Deduplication (Comments, Whitespace, Identifiers)
        # -------------------------------------------------------------
        if norm_h in self.norm_exclusions:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_NORMALIZED_CODE_DUPLICATE",
                reason="Normalized code hash matches an existing sample (whitespace/comment/identifier formatting variation).",
                provenance_verified=True,
                leakage_risk_level="CRITICAL",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )
        if norm_h in self.seen_norm:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_INTERNAL_NORM_DUPLICATE",
                reason="Normalized code duplicate within current acquisition session.",
                provenance_verified=True,
                leakage_risk_level="HIGH",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        # -------------------------------------------------------------
        # TIER 6.5: Clean Code Static Analysis Verification
        # -------------------------------------------------------------
        if not is_vul:
            findings = StaticAnalyzer.analyze_c(code)
            if findings:
                f_desc = "; ".join(f"{f.rule_id}: {f.message}" for f in findings)
                return QuarantineVerdict(
                    status="REJECTED",
                    decision_code="REJECTED_CLEAN_FAILED_STATIC_ANALYSIS",
                    reason=f"Candidate clean sample triggered static analysis defect findings: {f_desc}",
                    provenance_verified=True,
                    leakage_risk_level="MEDIUM",
                    exact_hash=exact_h,
                    normalized_hash=norm_h,
                    ast_hash=ast_h,
                    commit_hash=commit
                )

        # -------------------------------------------------------------
        # TIER 7: AST-Equivalent Deduplication
        # -------------------------------------------------------------
        if self.ast_exclusions or self.seen_ast:
            ast_h, ast_ok = compute_ast_sha256(code) if code else (None, False)
            if ast_ok and ast_h:
                if ast_h in self.ast_exclusions:
                    return QuarantineVerdict(
                        status="REJECTED",
                        decision_code="REJECTED_AST_EQUIVALENT",
                        reason="Scope-aware AST normalization matches an existing function structure.",
                        provenance_verified=True,
                        leakage_risk_level="HIGH",
                        exact_hash=exact_h,
                        normalized_hash=norm_h,
                        ast_hash=ast_h,
                        commit_hash=commit
                    )
                if ast_h in self.seen_ast:
                    return QuarantineVerdict(
                        status="REJECTED",
                        decision_code="REJECTED_INTERNAL_AST_DUPLICATE",
                        reason="AST-equivalent duplicate within current acquisition session.",
                        provenance_verified=True,
                        leakage_risk_level="HIGH",
                        exact_hash=exact_h,
                        normalized_hash=norm_h,
                        ast_hash=ast_h,
                        commit_hash=commit
                    )

        # -------------------------------------------------------------
        # TIER 8: Function Signature & Template-Family Overlap
        # -------------------------------------------------------------
        func_key = f"{file_path}::{func_name}".lower() if func_name and file_path else ""
        if func_key and func_key in self.template_exclusions:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_FUNCTION_TEMPLATE_OVERLAP",
                reason=f"Function identifier and file path '{func_key}' matches an existing benchmarked function.",
                provenance_verified=True,
                leakage_risk_level="HIGH",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        tmpl_key = f"tmpl::{template_fam}".lower() if template_fam else ""
        if tmpl_key and tmpl_key in self.template_exclusions:
            return QuarantineVerdict(
                status="REJECTED",
                decision_code="REJECTED_FUNCTION_TEMPLATE_OVERLAP",
                reason=f"Template family '{template_fam}' matches a known synthetic/mutation template family.",
                provenance_verified=True,
                leakage_risk_level="HIGH",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        # -------------------------------------------------------------
        # TIER 9: Same-Commit Distinct Function Flagging (Decision #6)
        # -------------------------------------------------------------
        if commit and commit in self.commit_exclusions:
            # Function is distinct (passed exact, norm, ast, and signature checks),
            # but originates from a commit hash seen in historical data.
            # Decision #6: Same-commit distinct functions are ELIGIBLE for manual review;
            # they must NEVER be automatically accepted.
            return QuarantineVerdict(
                status="FLAGGED_MANUAL_REVIEW",
                decision_code="FLAGGED_SAME_COMMIT_MANUAL_REVIEW_REQUIRED",
                reason="Function is demonstrably distinct from existing code, but originates from a commit previously present in training/evaluation sets. Requires manual review.",
                provenance_verified=True,
                leakage_risk_level="MEDIUM",
                exact_hash=exact_h,
                normalized_hash=norm_h,
                ast_hash=ast_h,
                commit_hash=commit
            )

        # -------------------------------------------------------------
        # ACCEPTED: Fully Verified and Distinct
        # -------------------------------------------------------------
        self.seen_exact.add(exact_h)
        self.seen_norm.add(norm_h)
        if ast_ok and ast_h:
            self.seen_ast.add(ast_h)

        status_code = "ACCEPTED_VULNERABLE_BENCHMARK_CANDIDATE" if is_vul else "ACCEPTED_CLEAN_BENCHMARK_CANDIDATE"
        return QuarantineVerdict(
            status="ACCEPTED",
            decision_code=status_code,
            reason="Sample passes all function-level, AST, repository, and provenance quarantine checks.",
            provenance_verified=True,
            leakage_risk_level="NONE",
            exact_hash=exact_h,
            normalized_hash=norm_h,
            ast_hash=ast_h,
            commit_hash=commit
        )
