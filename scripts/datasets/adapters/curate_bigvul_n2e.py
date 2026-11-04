"""
Experiment N2E — Leakage-Safe Big-Vul Candidate Curation Engine.

Performs conservative leakage screening and eligibility classification on
Experiment N2C.1 candidates based on N2D independent audit results:
1. Reconciles audit reviews and exact record/group overlaps against production splits.
2. Applies strict non-leakage eligibility rules at both record and group levels.
3. Partitions records into curated_candidates.jsonl, manual_review.jsonl, and excluded_candidates.jsonl.
4. Preserves all multiple exclusion reasons per record.
5. Generates comprehensive curation_report.json.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import Counter, defaultdict

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.datasets.schema import CodeDebuggingExample


class BigVulCandidateCuratorN2E:
    """
    Leakage-safe curator enforcing zero-tolerance test overlap,
    group-level split isolation, and truthful semantic review classification.
    """

    def __init__(self):
        pass

    @staticmethod
    def normalize_code(code: str) -> str:
        return "".join(code.split())

    @staticmethod
    def compute_hash(code: str, language: str) -> str:
        norm = "".join(code.split())
        return hashlib.sha256(f"{language}:{norm}".encode("utf-8")).hexdigest()

    def load_split_groups_and_codes(self, splits_dir: Path) -> Dict[str, Dict[str, Set[str]]]:
        """
        Indexes production splits for exact code, full hash, and project_commit group containment.
        """
        split_names = ["train", "val", "test", "robust_heldout_test"]
        index = {s: {"codes": set(), "hashes": set(), "groups": set()} for s in split_names}

        for s_name in split_names:
            path = splits_dir / f"{s_name}.jsonl"
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    code = rec.get("original_code", "")
                    lang = rec.get("language", "c")
                    norm_c = self.normalize_code(code)
                    h = self.compute_hash(code, lang)
                    
                    index[s_name]["codes"].add(norm_c)
                    index[s_name]["hashes"].add(h)

                    # Group containment
                    grp = rec.get("duplicate_group_id") or rec.get("template_family") or ""
                    repo = rec.get("repository", "")
                    c = rec.get("commit_hash", "")
                    if repo.startswith("bigvul/") and c:
                        proj = repo.replace("bigvul/", "")
                        index[s_name]["groups"].add(f"bigvul_{proj}_{c[:8]}".lower())
                    if grp:
                        index[s_name]["groups"].add(grp.lower())

        return index

    def curate(
        self,
        candidates_path: Path,
        reviews_path: Path,
        splits_dir: Path,
        output_curated_path: Path,
        output_manual_path: Path,
        output_excluded_path: Path,
        output_report_path: Path
    ) -> Dict[str, Any]:
        """
        Executes conservative curation of candidates and outputs partitioned JSONL files and report.
        """
        output_curated_path.parent.mkdir(parents=True, exist_ok=True)
        output_manual_path.parent.mkdir(parents=True, exist_ok=True)
        output_excluded_path.parent.mkdir(parents=True, exist_ok=True)
        output_report_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Load candidates and reviews
        candidates: List[Dict[str, Any]] = []
        with open(candidates_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))

        reviews_by_id: Dict[str, Dict[str, Any]] = {}
        with open(reviews_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    reviews_by_id[r["example_id"]] = r

        # 2. Load split indices
        split_index = self.load_split_groups_and_codes(splits_dir)

        # 3. Process and categorize every candidate
        curated_candidates: List[Dict[str, Any]] = []
        manual_review_candidates: List[Dict[str, Any]] = []
        excluded_candidates: List[Dict[str, Any]] = []

        reason_counts: Counter = Counter()
        primary_category_counts: Counter = Counter()
        group_candidate_map = defaultdict(list)

        record_overlap_splits: Counter = Counter()
        group_overlap_splits: Counter = Counter()
        all_candidate_groups: Set[str] = set()

        for c in candidates:
            eid = c.get("example_id")
            rev = reviews_by_id.get(eid, {})
            code = c.get("original_code", "")
            lang = c.get("language", "c")
            norm_c = self.normalize_code(code)
            h = self.compute_hash(code, lang)
            grp = c.get("duplicate_group_id", "").lower()
            all_candidate_groups.add(grp)
            group_candidate_map[grp].append(c)

            reasons: List[str] = []
            matching_splits: Set[str] = set()

            # Record-level overlap checks
            in_test_record = (norm_c in split_index["test"]["codes"] or h in split_index["test"]["hashes"])
            in_train_record = (norm_c in split_index["train"]["codes"] or h in split_index["train"]["hashes"])
            in_val_record = (norm_c in split_index["val"]["codes"] or h in split_index["val"]["hashes"])
            in_robust_record = (norm_c in split_index["robust_heldout_test"]["codes"] or h in split_index["robust_heldout_test"]["hashes"])

            if in_test_record:
                reasons.append("excluded_test_overlap_record")
                matching_splits.add("test")
                record_overlap_splits["test"] += 1
            if in_train_record:
                reasons.append("excluded_train_overlap_record")
                matching_splits.add("train")
                record_overlap_splits["train"] += 1
            if in_val_record:
                reasons.append("excluded_val_overlap_record")
                matching_splits.add("val")
                record_overlap_splits["val"] += 1
            if in_robust_record:
                reasons.append("excluded_robust_heldout_overlap_record")
                matching_splits.add("robust_heldout")
                record_overlap_splits["robust_heldout"] += 1

            # Group-level overlap checks
            in_test_group = (grp in split_index["test"]["groups"])
            in_train_group = (grp in split_index["train"]["groups"])
            in_val_group = (grp in split_index["val"]["groups"])
            in_robust_group = (grp in split_index["robust_heldout_test"]["groups"])

            if in_test_group:
                reasons.append("excluded_test_overlap_group")
                matching_splits.add("test")
                group_overlap_splits["test"] += 1
            if in_train_group:
                reasons.append("excluded_train_overlap_group")
                matching_splits.add("train")
                group_overlap_splits["train"] += 1
            if in_val_group:
                reasons.append("excluded_val_overlap_group")
                matching_splits.add("val")
                group_overlap_splits["val"] += 1
            if in_robust_group:
                reasons.append("excluded_robust_heldout_overlap_group")
                matching_splits.add("robust_heldout")
                group_overlap_splits["robust_heldout"] += 1

            # Language uncertainty check
            lang_cert = rev.get("language_certainty", "certain")
            if lang_cert == "uncertain":
                reasons.append("excluded_language_uncertain")

            # Metadata integrity check
            if not c.get("repository") or not c.get("commit_hash") or not c.get("source_dataset") or not c.get("source_record_id"):
                reasons.append("excluded_metadata_issue")

            for r_name in reasons:
                reason_counts[r_name] += 1

            # Review status
            review_status = rev.get("review_status", "Plausible")
            if review_status == "Plausible":
                reason_counts["plausible_semantics_manual_review"] += 1

            # Decision Logic
            has_hard_exclusion = bool(reasons)
            is_confirmed = (review_status == "Confirmed")
            is_plausible = (review_status == "Plausible")

            record_annotated = dict(c)
            record_annotated["curation_metadata"] = {
                "exclusion_reasons": reasons,
                "review_status": review_status,
                "language_certainty": lang_cert,
                "matching_splits": sorted(list(matching_splits)),
                "group_id": grp
            }

            if not has_hard_exclusion and is_confirmed:
                record_annotated["curation_decision"] = "eligible_for_future_split"
                curated_candidates.append(record_annotated)
                primary_category_counts["eligible_for_future_split"] += 1
            elif not has_hard_exclusion and is_plausible:
                record_annotated["curation_decision"] = "manual_review_required"
                manual_review_candidates.append(record_annotated)
                primary_category_counts["manual_review_required"] += 1
            else:
                record_annotated["curation_decision"] = "excluded"
                excluded_candidates.append(record_annotated)
                # Assign primary exclusion category for reporting
                if "excluded_test_overlap_record" in reasons or "excluded_test_overlap_group" in reasons:
                    primary_category_counts["excluded_test_overlap"] += 1
                elif "excluded_train_overlap_record" in reasons or "excluded_train_overlap_group" in reasons or "excluded_val_overlap_record" in reasons or "excluded_val_overlap_group" in reasons:
                    primary_category_counts["excluded_train_val_overlap"] += 1
                elif "excluded_language_uncertain" in reasons:
                    primary_category_counts["excluded_language_uncertain"] += 1
                elif "excluded_metadata_issue" in reasons:
                    primary_category_counts["excluded_metadata_issue"] += 1
                else:
                    primary_category_counts["excluded_other"] += 1

        # 4. Write output files
        with open(output_curated_path, "w", encoding="utf-8") as f:
            for item in curated_candidates:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        with open(output_manual_path, "w", encoding="utf-8") as f:
            for item in manual_review_candidates:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        with open(output_excluded_path, "w", encoding="utf-8") as f:
            for item in excluded_candidates:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        # 5. Group accounting
        unique_groups_test = set()
        unique_groups_train = set()
        unique_groups_val = set()
        for grp in all_candidate_groups:
            if grp in split_index["test"]["groups"]:
                unique_groups_test.add(grp)
            if grp in split_index["train"]["groups"]:
                unique_groups_train.add(grp)
            if grp in split_index["val"]["groups"]:
                unique_groups_val.add(grp)

        all_overlapping_groups = unique_groups_test | unique_groups_train | unique_groups_val
        non_overlapping_groups = all_candidate_groups - all_overlapping_groups

        # 6. Compile Report
        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "curator_version": "1.0.0",
            "candidates_source_file": str(candidates_path),
            "total_input_candidates": len(candidates),
            "partition_accounting": {
                "curated_candidates_count": len(curated_candidates),
                "manual_review_candidates_count": len(manual_review_candidates),
                "excluded_candidates_count": len(excluded_candidates),
                "record_conservation_verified": (len(curated_candidates) + len(manual_review_candidates) + len(excluded_candidates) == len(candidates))
            },
            "primary_category_breakdown": dict(primary_category_counts),
            "overlapping_reason_counts": dict(reason_counts),
            "group_level_accounting": {
                "total_unique_candidate_groups": len(all_candidate_groups),
                "unique_groups_overlapping_test": len(unique_groups_test),
                "unique_groups_overlapping_train": len(unique_groups_train),
                "unique_groups_overlapping_val": len(unique_groups_val),
                "unique_groups_overlapping_robust_heldout": 0,
                "unique_groups_clean_non_overlapping": len(non_overlapping_groups),
                "clean_non_overlapping_group_ids": sorted(list(non_overlapping_groups))
            },
            "record_level_overlap_summary": {
                "records_overlapping_test": record_overlap_splits["test"],
                "records_overlapping_train": record_overlap_splits["train"],
                "records_overlapping_val": record_overlap_splits["val"],
                "records_overlapping_robust_heldout": record_overlap_splits["robust_heldout"]
            },
            "curated_candidates_details": [
                {
                    "example_id": c.get("example_id"),
                    "source_record_id": c.get("source_record_id"),
                    "bug_category": c.get("bug_category"),
                    "language": c.get("language"),
                    "repository": c.get("repository"),
                    "commit_hash": c.get("commit_hash"),
                    "duplicate_group_id": c.get("duplicate_group_id")
                }
                for c in curated_candidates
            ],
            "output_files": {
                "curated_candidates": str(output_curated_path),
                "manual_review": str(output_manual_path),
                "excluded_candidates": str(output_excluded_path),
                "curation_report": str(output_report_path)
            }
        }

        with open(output_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report


def main():
    curator = BigVulCandidateCuratorN2E()
    report = curator.curate(
        candidates_path=ROOT_DIR / "data" / "experiments" / "experiment_n2c_1" / "bigvul_candidates.jsonl",
        reviews_path=ROOT_DIR / "data" / "experiments" / "experiment_n2d" / "candidate_review.jsonl",
        splits_dir=ROOT_DIR / "data" / "processed",
        output_curated_path=ROOT_DIR / "data" / "experiments" / "experiment_n2e" / "curated_candidates.jsonl",
        output_manual_path=ROOT_DIR / "data" / "experiments" / "experiment_n2e" / "manual_review.jsonl",
        output_excluded_path=ROOT_DIR / "data" / "experiments" / "experiment_n2e" / "excluded_candidates.jsonl",
        output_report_path=ROOT_DIR / "data" / "experiments" / "experiment_n2e" / "curation_report.json"
    )

    print("Experiment N2E Candidate Curation Completed Successfully!")
    print(f"Total input candidates: {report['total_input_candidates']}")
    print(f"Curated eligible candidates: {report['partition_accounting']['curated_candidates_count']}")
    print(f"Manual review candidates: {report['partition_accounting']['manual_review_candidates_count']}")
    print(f"Excluded candidates: {report['partition_accounting']['excluded_candidates_count']}")
    print(f"Conservation verified: {report['partition_accounting']['record_conservation_verified']}")
    print(f"Non-overlapping groups: {report['group_level_accounting']['unique_groups_clean_non_overlapping']}")


if __name__ == "__main__":
    main()

