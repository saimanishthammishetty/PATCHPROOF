"""
PATCHPROOF Experiment K — Phase 5: Candidate Model Training
Trains CandidateBugModel on the augmented corpus (train.jsonl + experiment_k_dataset.jsonl).
Strictly preserves models/bug_detector.joblib and live API routes.
Saves model artifact to models/experiments/experiment_k/bug_detector_candidate_k.joblib.
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
import joblib
import numpy as np

ROOT_DIR = Path("C:/PATCHPROOF")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.metrics import classification_report, f1_score, accuracy_score

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
EXP_K_DATA_DIR = ROOT_DIR / "data" / "experiments" / "experiment_k"
EXP_K_MODEL_DIR = ROOT_DIR / "models" / "experiments" / "experiment_k"
EXP_K_MODEL_DIR.mkdir(parents=True, exist_ok=True)

class CandidateBugModelK:
    """
    Experiment K Candidate Architecture:
    Multi-scale Feature Union:
    - Word n-grams (1, 2) with programming token regex patterns (5,000 features)
    - Sub-word Char-wb n-grams (3, 5) for syntactic delimiters and prefixes (5,000 features)
    - Regularized Logistic Regression with balanced class weighting (C=2.0, max_iter=600)
    """
    def __init__(self, C: float = 2.0, max_iter: int = 600, random_state: int = 42):
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state

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
            C=self.C,
            max_iter=self.max_iter,
            class_weight="balanced",
            random_state=self.random_state,
            n_jobs=-1
        )
        self.pipeline = Pipeline([
            ("features", self.features),
            ("clf", self.classifier)
        ])

    def fit(self, X_train: List[str], y_train: List[str]):
        self.pipeline.fit(X_train, y_train)

    def predict(self, X: List[str]) -> List[str]:
        return self.pipeline.predict(X).tolist()

    def predict_proba(self, X: List[str]) -> np.ndarray:
        return self.pipeline.predict_proba(X)

def load_training_data() -> Tuple[List[str], List[str]]:
    """Loads baseline train.jsonl + experiment_k_dataset.jsonl."""
    X: List[str] = []
    y: List[str] = []

    # 1. Baseline train.jsonl
    train_file = PROCESSED_DIR / "train.jsonl"
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                X.append(obj["original_code"])
                y.append(obj["bug_category"])

    base_count = len(X)

    # 2. Experiment K dataset
    expk_file = EXP_K_DATA_DIR / "experiment_k_dataset.jsonl"
    with open(expk_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                X.append(obj["original_code"])
                y.append(obj["bug_category"])

    print(f"[DATA] Loaded {base_count:,} baseline train samples + {len(X) - base_count:,} Exp-K samples = {len(X):,} total.")
    return X, y

def load_val_data() -> Tuple[List[str], List[str]]:
    """Loads validation split."""
    X: List[str] = []
    y: List[str] = []
    val_file = PROCESSED_DIR / "val.jsonl"
    with open(val_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                X.append(obj["original_code"])
                y.append(obj["bug_category"])
    return X, y

def train_and_save_candidate():
    print("="*80)
    print("PATCHPROOF EXPERIMENT K: PHASE 5 — CANDIDATE MODEL TRAINING")
    print("="*80)

    # Baseline model check
    baseline_path = ROOT_DIR / "models" / "bug_detector.joblib"
    assert baseline_path.exists(), "FATAL: Baseline model not found!"
    with open(baseline_path, "rb") as f:
        baseline_sha256 = hashlib.sha256(f.read()).hexdigest()
    print(f"[BASE] Verified untouched baseline model SHA-256: {baseline_sha256}")

    # Load training and validation data
    X_train, y_train = load_training_data()
    X_val, y_val = load_val_data()
    print(f"[VAL] Validation set contains {len(X_val):,} samples.")

    # Train candidate model
    start_train = time.time()
    candidate = CandidateBugModelK(C=2.0, max_iter=600, random_state=42)
    print("[TRAIN] Fitting multi-scale TF-IDF union and balanced classifier...")
    candidate.fit(X_train, y_train)
    train_duration = time.time() - start_train
    print(f"[TRAIN] Training completed in {train_duration:.2f} seconds.")

    # Validation evaluation
    start_infer = time.time()
    val_preds = candidate.predict(X_val)
    val_infer_time = time.time() - start_infer

    val_acc = accuracy_score(y_val, val_preds)
    val_f1_weighted = f1_score(y_val, val_preds, average="weighted", zero_division=0)
    val_f1_macro = f1_score(y_val, val_preds, average="macro", zero_division=0)

    print(f"[VAL EVAL] Validation Accuracy: {val_acc:.4f}")
    print(f"[VAL EVAL] Validation Macro F1: {val_f1_macro:.4f}")
    print(f"[VAL EVAL] Validation Weighted F1: {val_f1_weighted:.4f}")

    # Save candidate model strictly to models/experiments/experiment_k/
    candidate_model_path = EXP_K_MODEL_DIR / "bug_detector_candidate_k.joblib"
    joblib.dump(candidate.pipeline, candidate_model_path)

    with open(candidate_model_path, "rb") as f:
        candidate_sha256 = hashlib.sha256(f.read()).hexdigest()
    file_size_mb = os.path.getsize(candidate_model_path) / (1024 * 1024)
    print(f"[SAVE] Candidate model saved to {candidate_model_path}")
    print(f"[SAVE] Candidate SHA-256: {candidate_sha256} ({file_size_mb:.2f} MB)")

    # Verify baseline model remains untouched
    with open(baseline_path, "rb") as f:
        baseline_sha256_after = hashlib.sha256(f.read()).hexdigest()
    assert baseline_sha256 == baseline_sha256_after, "FATAL: Baseline model was corrupted or modified!"
    print(f"[VERIFY] Baseline model invariant preserved: {baseline_sha256_after}")

    # Record training metrics
    metrics = {
        "experiment": "Experiment K",
        "phase": "Phase 5 — Candidate Model Training",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_architecture": "CandidateBugModelK (Multi-scale TF-IDF Word+Char + Logistic Regression)",
        "hyperparameters": {
            "C": 2.0,
            "max_iter": 600,
            "random_state": 42,
            "max_features_word": 5000,
            "max_features_char": 5000,
            "class_weight": "balanced"
        },
        "training_samples": len(X_train),
        "validation_samples": len(X_val),
        "classes_trained": sorted(list(set(y_train))),
        "training_time_seconds": round(train_duration, 2),
        "val_inference_time_seconds": round(val_infer_time, 4),
        "validation_metrics": {
            "accuracy": round(float(val_acc), 4),
            "macro_f1": round(float(val_f1_macro), 4),
            "weighted_f1": round(float(val_f1_weighted), 4)
        },
        "artifact_path": str(candidate_model_path.as_posix()),
        "artifact_sha256": candidate_sha256,
        "artifact_size_bytes": os.path.getsize(candidate_model_path),
        "baseline_preservation_verified": True
    }

    metrics_path = EXP_K_MODEL_DIR / "training_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"[OK] Training metrics saved to {metrics_path}")

if __name__ == "__main__":
    train_and_save_candidate()
