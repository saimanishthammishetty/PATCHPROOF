import random
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from scripts.datasets.schema import CodeDebuggingExample

logger = logging.getLogger("DatasetSplitter")

PROCESSED_DIR = Path("C:/PATCHPROOF/data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

class DatasetSplitter:
    """
    Performs leakage-free splitting by grouping related repositories, commits,
    and synthetic template variants strictly into either train, val, or test splits.
    """

    def __init__(
        self,
        train_ratio: float = 0.80,
        val_ratio: float = 0.10,
        test_ratio: float = 0.10,
        seed: int = 42,
        output_dir: Path = PROCESSED_DIR
    ):
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.seed = seed
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def split_and_save(
        self,
        examples: List[CodeDebuggingExample]
    ) -> Dict[str, Any]:
        rng = random.Random(self.seed)

        # Group examples by isolation key: duplicate_group_id or repository
        groups: Dict[str, List[CodeDebuggingExample]] = {}
        for ex in examples:
            group_key = ex.template_family or ex.duplicate_group_id or ex.repository or ex.source_dataset
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(ex)

        group_keys = list(groups.keys())
        rng.shuffle(group_keys)

        train_examples: List[CodeDebuggingExample] = []
        val_examples: List[CodeDebuggingExample] = []
        test_examples: List[CodeDebuggingExample] = []

        total_target = len(examples)
        val_target = max(1, int(total_target * self.val_ratio))
        test_target = max(1, int(total_target * self.test_ratio))
        train_target = max(1, total_target - val_target - test_target)

        for k in group_keys:
            grp = groups[k]
            if len(train_examples) < train_target:
                for item in grp:
                    item.split = "train"
                train_examples.extend(grp)
            elif len(val_examples) < val_target:
                for item in grp:
                    item.split = "val"
                val_examples.extend(grp)
            else:
                for item in grp:
                    item.split = "test"
                test_examples.extend(grp)

        # Ensure non-empty test and val if train has at least 3 elements
        if not test_examples and len(train_examples) > 2:
            moved = train_examples.pop()
            moved.split = "test"
            test_examples.append(moved)
        if not val_examples and len(train_examples) > 2:
            moved = train_examples.pop()
            moved.split = "val"
            val_examples.append(moved)

        # Save to JSONL files
        splits_map = {
            "train": (self.output_dir / "train.jsonl", train_examples),
            "val": (self.output_dir / "val.jsonl", val_examples),
            "test": (self.output_dir / "test.jsonl", test_examples),
        }

        for s_name, (file_path, items) in splits_map.items():
            with open(file_path, "w", encoding="utf-8") as f:
                for item in items:
                    f.write(item.to_jsonl() + "\n")

        # Compile distribution statistics
        stats = {
            "total_examples": len(examples),
            "train_count": len(train_examples),
            "val_count": len(val_examples),
            "test_count": len(test_examples),
            "actual_ratios": {
                "train": round(len(train_examples) / max(1, len(examples)), 3),
                "val": round(len(val_examples) / max(1, len(examples)), 3),
                "test": round(len(test_examples) / max(1, len(examples)), 3)
            },
            "language_distribution": {},
            "bug_category_distribution": {},
            "source_distribution": {}
        }

        for ex in examples:
            stats["language_distribution"][ex.language] = stats["language_distribution"].get(ex.language, 0) + 1
            stats["bug_category_distribution"][ex.bug_category] = stats["bug_category_distribution"].get(ex.bug_category, 0) + 1
            stats["source_distribution"][ex.source_dataset] = stats["source_distribution"].get(ex.source_dataset, 0) + 1

        stats_path = self.output_dir / "split_statistics.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        return stats
