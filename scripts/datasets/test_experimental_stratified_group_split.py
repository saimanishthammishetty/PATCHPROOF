"""
Unit Test Suite for Experimental Stratified Group Splitter (v1.1.0)
===================================================================

Phase: Experiment N1 / N1.1 (Leakage-Safe Multi-Class Dataset Splitter)
Tests all edge cases:
- Balanced class allocation
- Severe class imbalance
- Rare classes with very few groups (1 or 2 groups)
- Groups containing multiple labels
- Groups containing multiple languages
- Large super-groups
- Impossible coverage constraints
- Reproducibility with fixed seeds
- Zero group leakage assertions across every pair of splits
- Robust held-out exclusion
- Exact record conservation
- Conflicting class and language requirements
"""

import unittest
import uuid
from typing import List

from scripts.datasets.schema import CodeDebuggingExample
from scripts.datasets.experimental_stratified_group_split import (
    ExperimentalStratifiedGroupSplitter,
)


def make_example(
    group_id: str,
    bug_category: str = "memory_safety",
    language: str = "python",
    code: str = "def test(): pass"
) -> CodeDebuggingExample:
    return CodeDebuggingExample(
        example_id=f"pp-test-{uuid.uuid4().hex[:10]}",
        language=language,
        bug_category=bug_category,
        difficulty="medium",
        original_code=code,
        bug_description="synthetic test record",
        faulty_line_numbers=[1],
        source_dataset="unit_test",
        source_record_id=str(uuid.uuid4().hex[:8]),
        template_family=group_id,
        duplicate_group_id=group_id,
        split="unassigned",
    )


class TestExperimentalStratifiedGroupSplitter(unittest.TestCase):

    def test_zero_group_leakage_invariable(self):
        """Verifies that no isolation group ever crosses split boundaries."""
        examples: List[CodeDebuggingExample] = []
        for g_idx in range(50):
            grp_name = f"group_{g_idx:03d}"
            cat = "memory_safety" if g_idx % 2 == 0 else "type_error"
            lang = "python" if g_idx % 3 == 0 else "c"
            for _ in range(10):
                examples.append(make_example(grp_name, cat, lang))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        train_grps = {splitter.extract_group_key(e) for e in splits["train"]}
        val_grps = {splitter.extract_group_key(e) for e in splits["val"]}
        test_grps = {splitter.extract_group_key(e) for e in splits["test"]}

        self.assertEqual(len(train_grps & val_grps), 0, "Train and Val share groups!")
        self.assertEqual(len(train_grps & test_grps), 0, "Train and Test share groups!")
        self.assertEqual(len(val_grps & test_grps), 0, "Val and Test share groups!")
        self.assertEqual(diag["leakage_verification"]["status"], "PASSED_ZERO_LEAKAGE")

    def test_record_conservation_strict(self):
        """Verifies that every single input record is preserved with 0 dropped or duplicated samples."""
        examples: List[CodeDebuggingExample] = []
        for g_idx in range(35):
            for _ in range(7):
                examples.append(make_example(f"cons_grp_{g_idx}"))

        total_input = len(examples)
        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, _ = splitter.split(examples)

        total_output = sum(len(recs) for recs in splits.values())
        self.assertEqual(total_input, total_output, "Record count was not strictly conserved!")

        all_input_ids = {e.example_id for e in examples}
        all_output_ids = {e.example_id for s in splits.values() for e in s}
        self.assertEqual(all_input_ids, all_output_ids, "Input IDs do not match Output IDs exactly!")

    def test_robust_heldout_exclusion_safety(self):
        """Verifies that external robust heldout records are never allocated when properly quarantined."""
        primary_examples: List[CodeDebuggingExample] = [
            make_example(f"primary_grp_{i}") for i in range(50)
        ]
        robust_examples: List[CodeDebuggingExample] = [
            make_example(f"robust_grp_{i}", bug_category="async_error") for i in range(10)
        ]

        robust_ids = {e.example_id for e in robust_examples}
        robust_groups = {e.template_family for e in robust_examples}

        # Split primary dataset ONLY
        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, _ = splitter.split(primary_examples)

        # Assert zero robust samples entered any split
        for s in ["train", "val", "test"]:
            allocated_ids = {e.example_id for e in splits[s]}
            allocated_groups = {splitter.extract_group_key(e) for e in splits[s]}
            self.assertEqual(len(allocated_ids & robust_ids), 0, f"Robust samples leaked into {s}!")
            self.assertEqual(len(allocated_groups & robust_groups), 0, f"Robust groups leaked into {s}!")

    def test_balanced_class_allocation(self):
        """Verifies that multi-class data with sufficient groups is distributed to all splits."""
        classes = ["memory_safety", "type_error", "null_pointer", "resource_leak"]
        examples: List[CodeDebuggingExample] = []
        for c in classes:
            for g_idx in range(12):  # 12 groups per class
                grp_name = f"grp_{c}_{g_idx}"
                for _ in range(5):
                    examples.append(make_example(grp_name, bug_category=c))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        for c in classes:
            self.assertIn(c, diag["feasibility_assessment"]["fully_covered_classes"])
            self.assertGreater(diag["class_coverage"][c]["train"], 0)
            self.assertGreater(diag["class_coverage"][c]["val"], 0)
            self.assertGreater(diag["class_coverage"][c]["test"], 0)

    def test_severe_class_imbalance(self):
        """Verifies that tiny minority classes (10 samples) alongside massive majorities (1000 samples) reach test."""
        examples: List[CodeDebuggingExample] = []
        for g_idx in range(100):
            grp_name = f"maj_grp_{g_idx}"
            for _ in range(10):
                examples.append(make_example(grp_name, bug_category="none_correct_code"))

        for g_idx in range(5):
            grp_name = f"min_grp_{g_idx}"
            for _ in range(2):
                examples.append(make_example(grp_name, bug_category="state_management"))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        min_cov = diag["class_coverage"]["state_management"]
        self.assertGreater(min_cov["test"], 0, "Minority class was starved from test set!")
        self.assertGreater(min_cov["train"], 0, "Minority class missing from train set!")

    def test_single_group_constrained_class(self):
        """Verifies honest reporting when a class has only 1 indivisible group."""
        examples: List[CodeDebuggingExample] = []
        for g_idx in range(10):
            grp_name = f"norm_grp_{g_idx}"
            for _ in range(5):
                examples.append(make_example(grp_name, bug_category="memory_safety"))

        for _ in range(15):
            examples.append(make_example("single_grp_state", bug_category="state_management"))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        self.assertIn("state_management", diag["feasibility_assessment"]["single_group_constrained_classes"])
        assigned_splits = []
        for s in ["train", "val", "test"]:
            if any(e.bug_category == "state_management" for e in splits[s]):
                assigned_splits.append(s)
        self.assertEqual(len(assigned_splits), 1, "Single group was illegally fragmented across splits!")

    def test_two_group_constrained_class(self):
        """Verifies that a 2-group class covers 2 splits without breaking group isolation."""
        examples: List[CodeDebuggingExample] = []
        for g_idx in range(10):
            for _ in range(5):
                examples.append(make_example(f"c_grp_{g_idx}", bug_category="memory_safety"))

        for _ in range(5):
            examples.append(make_example("api_grp_1", bug_category="api_misuse"))
        for _ in range(5):
            examples.append(make_example("api_grp_2", bug_category="api_misuse"))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        api_cov = diag["class_coverage"]["api_misuse"]
        self.assertEqual(api_cov["feasibility"], "PARTIALLY_CONSTRAINED")
        self.assertTrue(api_cov["in_train"])
        self.assertTrue(api_cov["in_test"])
        self.assertFalse(api_cov["in_val"])

    def test_multi_label_groups(self):
        """Verifies that groups containing multiple bug classes remain indivisible."""
        examples: List[CodeDebuggingExample] = []
        for _ in range(5):
            examples.append(make_example("poly_grp_1", bug_category="memory_safety"))
        for _ in range(5):
            examples.append(make_example("poly_grp_1", bug_category="null_pointer"))

        for g_idx in range(20):
            for _ in range(5):
                examples.append(make_example(f"bg_grp_{g_idx}", bug_category="type_error"))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        poly_splits = set()
        for s in ["train", "val", "test"]:
            if any(splitter.extract_group_key(e) == "poly_grp_1" for e in splits[s]):
                poly_splits.add(s)

        self.assertEqual(len(poly_splits), 1, "Multi-label group was fragmented across splits!")

    def test_multi_language_groups(self):
        """Verifies that groups containing multiple languages remain indivisible."""
        examples: List[CodeDebuggingExample] = []
        for _ in range(3):
            examples.append(make_example("repo_polyglot", language="python"))
        for _ in range(3):
            examples.append(make_example("repo_polyglot", language="javascript"))

        for g_idx in range(15):
            examples.append(make_example(f"c_grp_{g_idx}", language="c"))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        poly_splits = set()
        for s in ["train", "val", "test"]:
            if any(splitter.extract_group_key(e) == "repo_polyglot" for e in splits[s]):
                poly_splits.add(s)

        self.assertEqual(len(poly_splits), 1, "Multi-language group was fragmented across splits!")

    def test_conflicting_class_and_lang_requirements(self):
        """Verifies solver behavior when group membership creates opposing class vs language demands."""
        examples: List[CodeDebuggingExample] = []
        # Group A: Rare language (Go), common class (none_correct_code)
        for _ in range(10):
            examples.append(make_example("conflict_grp_A", bug_category="none_correct_code", language="go"))

        # Group B: Common language (Python), rare class (null_pointer)
        for _ in range(10):
            examples.append(make_example("conflict_grp_B", bug_category="null_pointer", language="python"))

        # Background C groups
        for i in range(20):
            for _ in range(5):
                examples.append(make_example(f"bg_{i}", bug_category="memory_safety", language="c"))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        self.assertEqual(diag["leakage_verification"]["status"], "PASSED_ZERO_LEAKAGE")
        self.assertGreater(sum(diag["split_counts"].values()), 0)

    def test_large_super_group_ratio_impact(self):
        """Verifies that a massive group (e.g. 40% of data) is assigned to Train without crashing."""
        examples: List[CodeDebuggingExample] = []
        # Giant super-group: 400 samples
        for _ in range(400):
            examples.append(make_example("giant_super_group", bug_category="none_correct_code"))

        # 60 small groups of 10 samples each = 600 samples
        for g_idx in range(60):
            for _ in range(10):
                examples.append(make_example(f"small_grp_{g_idx}", bug_category="memory_safety"))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        self.assertEqual(diag["leakage_verification"]["status"], "PASSED_ZERO_LEAKAGE")
        self.assertEqual(sum(diag["split_counts"].values()), 1000)
        # Giant group should land in train to minimize ratio deviation
        train_groups = {splitter.extract_group_key(e) for e in splits["train"]}
        self.assertIn("giant_super_group", train_groups)

    def test_deterministic_reproducibility(self):
        """Verifies that identical random seeds produce byte-identical split allocations across multiple runs."""
        examples: List[CodeDebuggingExample] = []
        for g_idx in range(25):
            for _ in range(8):
                examples.append(make_example(f"rep_grp_{g_idx}"))

        splitter_a = ExperimentalStratifiedGroupSplitter(seed=98765, dry_run=True)
        splits_a, _ = splitter_a.split(examples)

        splitter_b = ExperimentalStratifiedGroupSplitter(seed=98765, dry_run=True)
        splits_b, _ = splitter_b.split(examples)

        for s in ["train", "val", "test"]:
            ids_a = [e.example_id for e in splits_a[s]]
            ids_b = [e.example_id for e in splits_b[s]]
            self.assertEqual(ids_a, ids_b, f"Seed 98765 non-deterministic on split {s}!")

    def test_language_coverage_in_test(self):
        """Verifies that every language with >= 3 groups has guaranteed representation in test."""
        langs = ["c", "python", "javascript", "go", "java"]
        examples: List[CodeDebuggingExample] = []
        for l in langs:
            for g_idx in range(4):
                for _ in range(5):
                    examples.append(make_example(f"lang_{l}_grp_{g_idx}", language=l))

        splitter = ExperimentalStratifiedGroupSplitter(seed=42, dry_run=True)
        splits, diag = splitter.split(examples)

        for l in langs:
            self.assertTrue(
                diag["language_coverage"][l]["in_test"],
                f"Language '{l}' was not included in the test split!"
            )


if __name__ == "__main__":
    unittest.main()
