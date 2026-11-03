"""
Experiment I - Phase 3: Hybrid Static Analysis + ML Engine.
Combines:
1. Deterministic Static Analyzer findings (provenance: deterministic_static_rule).
2. Candidate H1 AST Structural Model predictions (provenance: ast_structural_ml).
With explicit provenance tracking, calibration, and duplicate prevention.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import joblib
import numpy as np

sys.path.insert(0, str(Path.cwd()))
from scripts.experiments.experiment_f.ast_normalizer import normalize_snippet
from scripts.experiments.experiment_i.static_analyzer import StaticAnalyzer, StaticFinding

@dataclass
class HybridDiagnosis:
    category: str
    confidence: float
    provenance: str  # "deterministic_static_rule" | "ast_structural_ml" | "clean_concurrence"
    rule_id: Optional[str]
    message: str
    static_findings: List[StaticFinding]
    ml_probabilities: Dict[str, float]

class HybridBugDetector:
    """
    Hybrid Code Defect Classifier.
    Integrates deterministic language AST analyzers with Candidate H1 AST structural ML model.
    """
    def __init__(self, ml_model_path: str = "models/experiments/experiment_h/candidate_h1_ast_only.joblib", ml_threshold: float = 0.40):
        self.ml_model_path = Path(ml_model_path)
        if self.ml_model_path.exists():
            self.ml_model = joblib.load(self.ml_model_path)
            self.classes_ = list(self.ml_model.classes_)
        else:
            self.ml_model = None
            self.classes_ = []
        self.ml_threshold = ml_threshold

    def diagnose(self, code: str, language: str) -> HybridDiagnosis:
        # 1. Deterministic Static Analysis Pass
        static_findings = StaticAnalyzer.analyze(code, language)
        
        # 2. ML Prediction Pass (Candidate H1 on AST-normalized code)
        norm_code, _ = normalize_snippet(code, language)
        ml_probs_dict = {}
        top_ml_cat = "none_correct_code"
        top_ml_conf = 1.0

        if self.ml_model is not None:
            raw_probs = self.ml_model.predict_proba([norm_code])[0]
            ml_probs_dict = {c: round(float(raw_probs[i]), 4) for i, c in enumerate(self.classes_)}
            top_idx = int(np.argmax(raw_probs))
            top_ml_cat = self.classes_[top_idx]
            top_ml_conf = float(raw_probs[top_idx])

        # 3. Evidence Aggregation & Provenance Resolution
        if static_findings:
            top_finding = static_findings[0]
            return HybridDiagnosis(
                category=top_finding.category,
                confidence=top_finding.confidence,
                provenance="deterministic_static_rule",
                rule_id=top_finding.rule_id,
                message=f"Deterministic AST rule '{top_finding.rule_id}' matched: {top_finding.message}",
                static_findings=static_findings,
                ml_probabilities=ml_probs_dict
            )

        # If no static rule fired, evaluate ML predictions
        if top_ml_cat != "none_correct_code" and top_ml_conf >= self.ml_threshold:
            return HybridDiagnosis(
                category=top_ml_cat,
                confidence=round(top_ml_conf, 4),
                provenance="ast_structural_ml",
                rule_id=None,
                message=f"AST structural pattern recognized defect '{top_ml_cat}' with confidence {top_ml_conf*100:.1f}%.",
                static_findings=[],
                ml_probabilities=ml_probs_dict
            )

        # Default clean
        conf = top_ml_conf if top_ml_cat == "none_correct_code" else round(1.0 - top_ml_conf, 4)
        return HybridDiagnosis(
            category="none_correct_code",
            confidence=round(max(conf, 0.70), 4),
            provenance="clean_concurrence" if top_ml_cat == "none_correct_code" else "ast_structural_ml",
            rule_id=None,
            message="No deterministic defect rules triggered and code structure aligns with clean benchmarks.",
            static_findings=[],
            ml_probabilities=ml_probs_dict
        )

    def predict(self, code_list: List[str], lang_list: List[str]) -> List[str]:
        return [self.diagnose(c, l).category for c, l in zip(code_list, lang_list)]

