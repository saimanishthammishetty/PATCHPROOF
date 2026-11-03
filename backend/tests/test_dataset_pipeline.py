import pytest
from scripts.datasets.schema import CodeDebuggingExample
from scripts.datasets.generate_synthetic import SyntheticBugGenerator
from scripts.datasets.deduplicate import DatasetDeduplicator
from scripts.datasets.validate import DatasetValidator
from scripts.datasets.split import DatasetSplitter
from scripts.training.train import MLCodeBugModel, BaselineBugDetector

def test_schema_serialization_and_validation():
    ex = CodeDebuggingExample(
        language="python",
        bug_category="off_by_one",
        difficulty="easy",
        original_code="for i in range(10): pass",
        bug_description="Loop off by one",
        faulty_line_numbers=[1],
        source_dataset="test",
        source_record_id="t-1"
    )
    json_str = ex.to_jsonl()
    restored = CodeDebuggingExample.from_jsonl(json_str)
    assert restored.example_id == ex.example_id
    assert restored.language == "python"
    assert restored.bug_category == "off_by_one"
    assert restored.faulty_line_numbers == [1]

def test_synthetic_bug_generation():
    generator = SyntheticBugGenerator(seed=42)
    samples = generator.generate(20)
    assert len(samples) == 20
    langs = {s.language for s in samples}
    assert "python" in langs
    assert "c" in langs
    assert "javascript" in langs

    # Verify each sample has required fields
    for s in samples:
        assert len(s.original_code) > 0
        assert len(s.bug_description) > 0
        assert s.difficulty in ("easy", "medium", "hard")

def test_deduplicator():
    ex1 = CodeDebuggingExample(
        language="python",
        bug_category="type_error",
        original_code="def foo():\n    return 1 + '2'",
        bug_description="TypeError test",
        source_dataset="test",
        source_record_id="d-1"
    )
    # Duplicate with whitespace variance
    ex2 = CodeDebuggingExample(
        language="python",
        bug_category="type_error",
        original_code="def foo():\n\n    return 1 + '2'\n",
        bug_description="TypeError duplicate",
        source_dataset="test",
        source_record_id="d-2"
    )
    ex3 = CodeDebuggingExample(
        language="python",
        bug_category="none_correct_code",
        original_code="def bar():\n    return 42",
        bug_description="Different code",
        source_dataset="test",
        source_record_id="d-3"
    )

    retained, exact_dupes, near_dupes = DatasetDeduplicator.deduplicate([ex1, ex2, ex3])
    assert len(retained) == 2
    assert exact_dupes == 1

def test_validator_and_rejection_tracking(tmp_path):
    validator = DatasetValidator(log_rejections=True)
    
    # Valid example
    valid_ex = CodeDebuggingExample(
        language="python",
        bug_category="api_misuse",
        original_code="def safe():\n    return True",
        bug_description="Safe function",
        faulty_line_numbers=[1],
        source_dataset="test",
        source_record_id="v-1"
    )
    
    # Invalid line number out of bounds
    invalid_ex = CodeDebuggingExample(
        language="python",
        bug_category="api_misuse",
        original_code="def short():\n    pass",
        bug_description="Bad line number",
        faulty_line_numbers=[99],  # Line 99 does not exist!
        source_dataset="test",
        source_record_id="v-2"
    )

    passed, report = validator.validate_batch([valid_ex, invalid_ex])
    assert len(passed) == 1
    assert report["rejected"] == 1
    assert "FAULTY_LINE_OUT_OF_BOUNDS" in list(report["rejections_by_reason"].keys())[0]

def test_leakage_free_splitter(tmp_path):
    generator = SyntheticBugGenerator(seed=123)
    examples = generator.generate(50)
    splitter = DatasetSplitter(train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42, output_dir=tmp_path)
    stats = splitter.split_and_save(examples)
    
    assert stats["train_count"] > 0
    assert stats["val_count"] > 0
    assert stats["test_count"] > 0
    assert stats["train_count"] + stats["val_count"] + stats["test_count"] == 50

def test_baseline_and_ml_classifier_training():
    generator = SyntheticBugGenerator(seed=999)
    samples = generator.generate(60)
    X = [s.original_code for s in samples]
    y = [s.bug_category for s in samples]

    baseline = BaselineBugDetector()
    base_preds = baseline.predict(X[:10])
    assert len(base_preds) == 10

    ml_model = MLCodeBugModel()
    ml_model.fit(X[:45], y[:45])
    ml_preds = ml_model.predict(X[45:])
    assert len(ml_preds) == 15

