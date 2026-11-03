import uuid
import hashlib
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

class TestCase(BaseModel):
    input: str
    expected: str
    test_type: str = "unit"

class CodeDebuggingExample(BaseModel):
    example_id: str = Field(default_factory=lambda: f"pp-dbg-{uuid.uuid4().hex[:12]}")
    language: str
    bug_category: str
    difficulty: str = "medium"  # easy, medium, hard
    original_code: str
    bug_description: str
    faulty_line_numbers: List[int] = Field(default_factory=list)
    corrected_code: Optional[str] = None
    patch: Optional[str] = None
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)
    verification_status: str = "unverified_static"  # verified_passing, unverified_static, syntax_verified, failed_test
    source_dataset: str
    source_record_id: str
    repository: Optional[str] = "patchproof/debugging-bench"
    commit_hash: Optional[str] = None
    license: str = "Apache-2.0"
    duplicate_group_id: str = ""
    template_family: Optional[str] = None
    split: str = "train"  # train, val, test

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v_clean = v.lower().strip()
        allowed = {"python", "c", "cpp", "c++", "javascript", "typescript", "java", "golang", "go"}
        if v_clean not in allowed:
            raise ValueError(f"Language '{v}' is not in allowed list: {allowed}")
        if v_clean in ("go", "golang"):
            return "go"
        if v_clean in ("cpp", "c++"):
            return "cpp"
        return v_clean

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        v_clean = v.lower().strip()
        if v_clean not in {"easy", "medium", "hard"}:
            raise ValueError(f"Difficulty must be easy, medium, or hard, got '{v}'")
        return v_clean

    @field_validator("split")
    @classmethod
    def validate_split(cls, v: str) -> str:
        v_clean = v.lower().strip()
        if v_clean not in {"train", "val", "test", "unassigned"}:
            raise ValueError(f"Split must be train, val, test, or unassigned, got '{v}'")
        return v_clean

    def compute_content_hash(self) -> str:
        """Computes a normalized SHA-256 hash for exact deduplication."""
        # Normalize whitespace
        norm_code = "".join(self.original_code.split())
        key = f"{self.language}:{norm_code}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def to_jsonl(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_jsonl(cls, json_str: str) -> "CodeDebuggingExample":
        data = json.loads(json_str)
        return cls(**data)

