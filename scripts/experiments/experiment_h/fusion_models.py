"""
Experiment H Fusion Model Classes.
Implements:
- EarlyFeatureConcatenator (H3)
- LateProbabilityFusion (H4)
- ClassSpecificChannelRouter (H5)
"""

import numpy as np
from scipy import sparse
from sklearn.base import BaseEstimator, ClassifierMixin

class EarlyFusionClassifier(BaseEstimator, ClassifierMixin):
    """H3: Early feature concatenation of AST TF-IDF and Lexical TF-IDF."""
    def __init__(self, vec_ast, vec_lex, clf):
        self.vec_ast = vec_ast
        self.vec_lex = vec_lex
        self.clf = clf
        self.classes_ = getattr(clf, "classes_", None)

    def fit(self, X_ast, X_lex, y):
        feat_ast = self.vec_ast.fit_transform(X_ast)
        feat_lex = self.vec_lex.fit_transform(X_lex)
        X_fused = sparse.hstack([feat_ast, feat_lex], format="csr")
        self.clf.fit(X_fused, y)
        self.classes_ = self.clf.classes_
        return self

    def transform(self, X_ast, X_lex):
        feat_ast = self.vec_ast.transform(X_ast)
        feat_lex = self.vec_lex.transform(X_lex)
        return sparse.hstack([feat_ast, feat_lex], format="csr")

    def predict(self, X_ast, X_lex):
        X_fused = self.transform(X_ast, X_lex)
        return self.clf.predict(X_fused)

    def predict_proba(self, X_ast, X_lex):
        X_fused = self.transform(X_ast, X_lex)
        return self.clf.predict_proba(X_fused)


class LateProbabilityFusion(BaseEstimator, ClassifierMixin):
    """H4: Late probability fusion combining AST and Lexical calibrated probabilities."""
    def __init__(self, model_ast, model_lex, alpha=0.5):
        self.model_ast = model_ast
        self.model_lex = model_lex
        self.alpha = alpha  # Weight for AST channel (1 - alpha for Lexical channel)
        self.classes_ = model_ast.named_steps["clf"].classes_

    def predict_proba(self, X_ast, X_lex):
        p_ast = self.model_ast.predict_proba(X_ast)
        p_lex = self.model_lex.predict_proba(X_lex)
        return self.alpha * p_ast + (1.0 - self.alpha) * p_lex

    def predict(self, X_ast, X_lex):
        probs = self.predict_proba(X_ast, X_lex)
        idx = np.argmax(probs, axis=1)
        return np.array([self.classes_[i] for i in idx])


class ClassSpecificChannelRouter(BaseEstimator, ClassifierMixin):
    """
    H5: Dynamic confidence and syntactic routing.
    Gives higher weight to Channel B (Lexical) for type errors and exception handling,
    and higher weight to Channel A (AST) for structural defects (async, memory safety, resource leaks).
    """
    def __init__(self, model_ast, model_lex, class_weights_map=None):
        self.model_ast = model_ast
        self.model_lex = model_lex
        self.classes_ = list(model_ast.named_steps["clf"].classes_)
        # Default channel weight map for Channel A (1 - weight for Channel B)
        # Structural defects -> trust AST channel more (e.g. 0.70)
        # Lexical/Type defects -> trust Lexical channel more (e.g. 0.30, giving Lexical 0.70)
        if class_weights_map is None:
            self.class_weights_map = {
                "async_error": 0.65,
                "resource_leak": 0.70,
                "condition_error": 0.60,
                "memory_safety": 0.60,
                "off_by_one": 0.55,
                "none_correct_code": 0.50,
                "api_misuse": 0.40,
                "exception_handling": 0.30,
                "type_error": 0.25,
                "loop_error": 0.50,
                "null_pointer": 0.50,
                "state_management": 0.50,
                "undefined_behavior": 0.50,
            }
        else:
            self.class_weights_map = class_weights_map

    def predict_proba(self, X_ast, X_lex):
        p_ast = self.model_ast.predict_proba(X_ast)
        p_lex = self.model_lex.predict_proba(X_lex)
        
        # Apply per-class weighting matrix
        weight_vec = np.array([self.class_weights_map.get(str(c), 0.5) for c in self.classes_])
        # fused = weight_vec * p_ast + (1 - weight_vec) * p_lex
        fused = p_ast * weight_vec + p_lex * (1.0 - weight_vec)
        # Re-normalize to sum to 1
        sums = fused.sum(axis=1, keepdims=True)
        sums[sums == 0] = 1.0
        return fused / sums

    def predict(self, X_ast, X_lex):
        probs = self.predict_proba(X_ast, X_lex)
        idx = np.argmax(probs, axis=1)
        return np.array([self.classes_[i] for i in idx])

