import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.metrics import classification_report, f1_score, accuracy_score
from scripts.datasets.schema import CodeDebuggingExample

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrainModel")

MODELS_DIR = Path("C:/PATCHPROOF/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR = Path("C:/PATCHPROOF/data/processed")

class BaselineBugDetector:
    """
    Baseline heuristic bug detector using keyword and rule matching.
    Serves as the benchmark to prove machine learning model improvement.
    """
    def __init__(self):
        self.defect_keywords = {
            "memory_safety": ["free", "malloc", "sizeof", "dangling", "strcpy", "sprintf", "buffer"],
            "off_by_one": ["<=", "range(", "len(", "[len("],
            "type_error": ["%", "parseInt", "str(", "int(", "TypeError"],
            "async_error": ["async", "Promise", "fetch", "go func", "chan int"],
            "null_pointer": ["None", "null", "nil", "->", "NullPointerException"],
            "exception_handling": ["except", "catch", "try", "throw", "panic"],
            "resource_leak": ["close()", "fclose", "FileInputStream", "defer resp.Body.Close"]
        }

    def predict(self, code_samples: List[str]) -> List[str]:
        predictions = []
        for code in code_samples:
            assigned = "none_correct_code"
            for cat, kws in self.defect_keywords.items():
                if any(kw in code for kw in kws):
                    assigned = cat
                    break
            predictions.append(assigned)
        return predictions

class MLCodeBugModel:
    """
    Baseline Machine Learning Model for Code Defect Classification (Phase 2 model).
    Uses single-scale word n-grams and linear classification.
    """
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%]+",
            ngram_range=(1, 2),
            max_features=4000,
            sublinear_tf=True
        )
        self.classifier = LogisticRegression(
            C=1.0,
            max_iter=500,
            class_weight="balanced",
            random_state=42
        )
        self.pipeline = None

    def fit(self, X_train: List[str], y_train: List[str]):
        logger.info(f"Training baseline ML model on {len(X_train)} samples across {len(set(y_train))} classes...")
        self.pipeline = Pipeline([
            ("tfidf", self.vectorizer),
            ("clf", self.classifier)
        ])
        self.pipeline.fit(X_train, y_train)
        logger.info("Training complete.")

    def predict(self, X: List[str]) -> List[str]:
        return self.pipeline.predict(X).tolist()

    def predict_proba(self, X: List[str]) -> np.ndarray:
        return self.pipeline.predict_proba(X)

    def save(self, model_path: Path = MODELS_DIR / "bug_detector.joblib"):
        joblib.dump(self.pipeline, model_path)
        logger.info(f"Model artifact saved to {model_path}")

    @classmethod
    def load(cls, model_path: Path = MODELS_DIR / "bug_detector.joblib") -> Pipeline:
        return joblib.load(model_path)


class CandidateBugModel:
    """
    Candidate Machine Learning Model (Phase 3 expanded model).
    Uses multi-scale feature union combining:
    - Word n-grams (1, 2) for lexical identifiers and programming tokens.
    - Char-wb n-grams (3, 5) for sub-word syntax patterns and delimiters.
    - Balanced L2-regularized Logistic Regression (C=2.0).
    """
    def __init__(self, C: float = 2.0, max_iter: int = 600):
        self.word_vec = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b|[<>=!+\-*/&|~^%]+",
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True
        )
        self.char_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=5000,
            sublinear_tf=True
        )
        self.features = FeatureUnion([
            ("word", self.word_vec),
            ("char", self.char_vec)
        ])
        self.classifier = LogisticRegression(
            C=C,
            max_iter=max_iter,
            class_weight="balanced",
            random_state=42
        )
        self.pipeline = None

    def fit(self, X_train: List[str], y_train: List[str]):
        logger.info(f"[CANDIDATE] Fitting multi-scale feature union & classifier on {len(X_train)} samples across {len(set(y_train))} classes...")
        self.pipeline = Pipeline([
            ("features", self.features),
            ("clf", self.classifier)
        ])
        self.pipeline.fit(X_train, y_train)
        logger.info("[CANDIDATE] Fitting complete.")

    def predict(self, X: List[str]) -> List[str]:
        return self.pipeline.predict(X).tolist()

    def predict_proba(self, X: List[str]) -> np.ndarray:
        return self.pipeline.predict_proba(X)

    def save(self, model_path: Path = MODELS_DIR / "bug_detector_candidate.joblib"):
        joblib.dump(self.pipeline, model_path)
        logger.info(f"[CANDIDATE] Candidate artifact saved to {model_path}")

    @classmethod
    def load(cls, model_path: Path = MODELS_DIR / "bug_detector_candidate.joblib") -> Pipeline:
        return joblib.load(model_path)


def load_split(split_name: str) -> List[CodeDebuggingExample]:
    file_path = PROCESSED_DIR / f"{split_name}.jsonl"
    if not file_path.exists():
        raise FileNotFoundError(f"Split file {file_path} not found. Run pipeline first.")
    examples = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                examples.append(CodeDebuggingExample.from_jsonl(line))
    return examples

def run_training_candidate(C: float = 2.0) -> Dict[str, Any]:
    """
    Trains candidate model strictly on train split, tunes/evaluates on val split.
    Does NOT touch test split. Saves to bug_detector_candidate.joblib.
    """
    train_ex = load_split("train")
    val_ex = load_split("val")

    X_train = [ex.original_code for ex in train_ex]
    y_train = [ex.bug_category for ex in train_ex]

    X_val = [ex.original_code for ex in val_ex]
    y_val = [ex.bug_category for ex in val_ex]

    # Baseline on validation split
    baseline = BaselineBugDetector()
    base_preds = baseline.predict(X_val)
    base_acc = accuracy_score(y_val, base_preds)
    base_f1 = f1_score(y_val, base_preds, average="weighted", zero_division=0)

    # Train Candidate Model
    candidate = CandidateBugModel(C=C)
    candidate.fit(X_train, y_train)
    cand_preds = candidate.predict(X_val)
    cand_acc = accuracy_score(y_val, cand_preds)
    cand_f1 = f1_score(y_val, cand_preds, average="weighted", zero_division=0)

    # Save Candidate separately
    candidate.save(MODELS_DIR / "bug_detector_candidate.joblib")

    summary = {
        "model_type": "CandidateBugModel (Multi-scale TF-IDF Word+Char + Logistic Regression)",
        "hyperparameters": {
            "C": C,
            "max_features_word": 5000,
            "max_features_char": 5000,
            "class_weight": "balanced"
        },
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "classes": sorted(list(set(y_train))),
        "baseline_val": {
            "accuracy": round(float(base_acc), 4),
            "f1_weighted": round(float(base_f1), 4)
        },
        "candidate_val": {
            "accuracy": round(float(cand_acc), 4),
            "f1_weighted": round(float(cand_f1), 4)
        },
        "validation_gain": {
            "accuracy_delta": round(float(cand_acc - base_acc), 4),
            "f1_delta": round(float(cand_f1 - base_f1), 4)
        }
    }

    report_path = MODELS_DIR / "candidate_training_summary.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Candidate training summary:\n{json.dumps(summary, indent=2)}")
    return summary

# Backward-compatible alias
run_training = run_training_candidate

if __name__ == "__main__":
    run_training_candidate()
