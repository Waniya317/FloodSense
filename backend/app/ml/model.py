"""
FloodSense AI - ML Training Pipeline
XGBoost + LightGBM with SHAP explainability and full evaluation suite
"""

import numpy as np
import pandas as pd
import joblib
import shap
import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, classification_report, confusion_matrix,
    average_precision_score,
)
from sklearn.model_selection import cross_val_score
import xgboost as xgb
import lightgbm as lgb

logger = logging.getLogger(__name__)

# ─── Risk Level Mapping ───────────────────────────────────────────────────────
RISK_THRESHOLDS = {
    "Low":      (0.00, 0.25),
    "Medium":   (0.25, 0.50),
    "High":     (0.50, 0.75),
    "Critical": (0.75, 1.00),
}

RISK_COLORS = {
    "Low":      "#22c55e",  # green
    "Medium":   "#f59e0b",  # amber
    "High":     "#ef4444",  # red
    "Critical": "#7c3aed",  # purple
}

RISK_URDU = {
    "Low":      "کم",
    "Medium":   "درمیانہ",
    "High":     "زیادہ",
    "Critical": "انتہائی خطرناک",
}


def probability_to_risk(prob: float) -> str:
    """Convert flood probability to risk level string."""
    for level, (lo, hi) in RISK_THRESHOLDS.items():
        if lo <= prob < hi:
            return level
    return "Critical"


# ─── XGBoost Model ────────────────────────────────────────────────────────────
def build_xgboost(
    scale_pos_weight: float = 3.0,
    n_estimators: int = 200,
    random_state: int = 42,
) -> xgb.XGBClassifier:
    return xgb.XGBClassifier(
        n_estimators=n_estimators,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="logloss",
        early_stopping_rounds=20,
        random_state=random_state,
        n_jobs=-1,
        verbosity=0,
    )


# ─── LightGBM Model ───────────────────────────────────────────────────────────
def build_lightgbm(
    scale_pos_weight: float = 3.0,
    n_estimators: int = 200,
    random_state: int = 42,
) -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(
        n_estimators=n_estimators,
        max_depth=5,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_samples=20,
        reg_alpha=0.1,
        reg_lambda=1.0,
        class_weight={0: 1.0, 1: scale_pos_weight},
        early_stopping_rounds=20,
        random_state=random_state,
        n_jobs=-1,
        verbose=-1,
    )


# ─── Ensemble Model ─────────────────────────────────────────────────────────
class EnsembleModel:
    def __init__(self, m1, m2):
        self.m1 = m1
        self.m2 = m2
        self.model_name = "XGBoost+LightGBM Ensemble"

    def predict_proba(self, X):
        p1 = self.m1.predict_proba(X)
        p2 = self.m2.predict_proba(X)
        return (p1 + p2) / 2

    def predict(self, X, threshold=0.5):
        proba = self.predict_proba(X)[:, 1]
        return (proba >= threshold).astype(int)


# ─── Training ─────────────────────────────────────────────────────────────────
def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    model_type: str = "xgboost",
    use_both_and_ensemble: bool = True,
) -> Tuple[Any, float]:
    """
    Train XGBoost and/or LightGBM.
    Returns best model and optimal decision threshold.
    """
    flood_ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    logger.info(f"Class ratio 0:1 = {flood_ratio:.1f}")

    models = {}

    if model_type in ("xgboost", "both"):
        logger.info("Training XGBoost...")
        xgb_model = build_xgboost(scale_pos_weight=min(flood_ratio, 10))
        xgb_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False,
        )
        models["xgboost"] = xgb_model

    if model_type in ("lightgbm", "both"):
        logger.info("Training LightGBM...")
        lgb_model = build_lightgbm(scale_pos_weight=min(flood_ratio, 10))
        lgb_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(-1)],
        )
        models["lightgbm"] = lgb_model

    # Ensemble: average probabilities
    if len(models) == 2:
        best_model = EnsembleModel(models["xgboost"], models["lightgbm"])
    else:
        best_model = list(models.values())[0]
        best_model.model_name = model_type

    # Tune threshold on validation set to maximize F1
    best_threshold = tune_threshold(best_model, X_val, y_val)
    logger.info(f"Optimal decision threshold: {best_threshold:.3f}")

    return best_model, best_threshold


def tune_threshold(model, X_val: np.ndarray, y_val: np.ndarray) -> float:
    """Find decision threshold that maximizes F1 on validation set."""
    proba = model.predict_proba(X_val)[:, 1]
    best_f1 = 0
    best_thresh = 0.5
    for t in np.arange(0.2, 0.8, 0.02):
        preds = (proba >= t).astype(int)
        f1 = f1_score(y_val, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t
    return float(best_thresh)


# ─── Evaluation ───────────────────────────────────────────────────────────────
def evaluate_model(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    threshold: float = 0.5,
    feature_names: Optional[list] = None,
) -> Dict[str, Any]:
    """Comprehensive evaluation suite."""
    proba = model.predict_proba(X_test)[:, 1]
    preds = (proba >= threshold).astype(int)

    metrics = {
        "accuracy":         float(accuracy_score(y_test, preds)),
        "f1":               float(f1_score(y_test, preds, zero_division=0)),
        "precision":        float(precision_score(y_test, preds, zero_division=0)),
        "recall":           float(recall_score(y_test, preds, zero_division=0)),
        "roc_auc":          float(roc_auc_score(y_test, proba)),
        "avg_precision":    float(average_precision_score(y_test, proba)),
        "threshold":        threshold,
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
        "classification_report": classification_report(
            y_test, preds, target_names=["No Flood", "Flood"], output_dict=True
        ),
    }

    logger.info("=" * 50)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 50)
    for k, v in metrics.items():
        if k not in ("confusion_matrix", "classification_report"):
            logger.info(f"  {k:20s}: {v:.4f}")
    logger.info(f"  {'accuracy':20s}: {metrics['accuracy']:.4f}  (target >0.70 ✓)" if metrics["accuracy"] > 0.70 else f"  accuracy: {metrics['accuracy']:.4f} (target >0.70 ✗)")
    logger.info("=" * 50)

    return metrics


# ─── SHAP Explainability ──────────────────────────────────────────────────────
def build_explainer(model, X_train: np.ndarray, feature_names: list):
    """Build SHAP TreeExplainer for post-hoc explanations."""
    try:
        # Use underlying model for ensemble
        base = getattr(model, "m1", model)
        explainer = shap.TreeExplainer(base)
        logger.info("SHAP TreeExplainer built successfully")
        return explainer
    except Exception as e:
        logger.warning(f"TreeExplainer failed: {e}. Using KernelExplainer.")
        bg = shap.sample(X_train, 100)
        explainer = shap.KernelExplainer(model.predict_proba, bg)
        return explainer


def explain_prediction(
    explainer,
    input_vec: np.ndarray,
    feature_names: list,
    top_n: int = 6,
) -> list:
    """
    Return top-N SHAP-based reasons for a prediction.
    Returns list of dicts: {feature, value, impact, direction}
    """
    try:
        shap_vals = explainer.shap_values(input_vec)
        # For binary classification, shap_values is list[2] or array
        if isinstance(shap_vals, list):
            vals = shap_vals[1][0]  # class=1 (flood) explanations
        else:
            vals = shap_vals[0]

        idx_sorted = np.argsort(np.abs(vals))[::-1][:top_n]
        reasons = []
        for i in idx_sorted:
            fname = feature_names[i] if i < len(feature_names) else f"feature_{i}"
            fval = float(input_vec[0][i]) if input_vec.shape[1] > i else 0.0
            impact = float(vals[i])
            reasons.append({
                "feature": fname,
                "value": round(fval, 3),
                "impact": round(impact, 4),
                "direction": "increases flood risk" if impact > 0 else "decreases flood risk",
            })
        return reasons
    except Exception as e:
        logger.warning(f"SHAP explanation failed: {e}")
        return [{"feature": "model", "value": 0, "impact": 0, "direction": "explanation unavailable"}]


# ─── Save / Load ──────────────────────────────────────────────────────────────
def save_artifacts(
    model,
    scaler,
    feature_names: list,
    threshold: float,
    metrics: dict,
    output_dir: str = "backend/models",
):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(model, f"{output_dir}/model.joblib")
    joblib.dump(scaler, f"{output_dir}/scaler.joblib")
    with open(f"{output_dir}/feature_names.json", "w") as f:
        json.dump(feature_names, f)
    with open(f"{output_dir}/metadata.json", "w") as f:
        json.dump({
            "threshold": threshold,
            "metrics": {k: v for k, v in metrics.items() if isinstance(v, float)},
            "n_features": len(feature_names),
        }, f, indent=2)
    logger.info(f"Artifacts saved to {output_dir}/")


def load_artifacts(model_dir: str = "backend/models") -> dict:
    model = joblib.load(f"{model_dir}/model.joblib")
    scaler = joblib.load(f"{model_dir}/scaler.joblib")
    with open(f"{model_dir}/feature_names.json") as f:
        feature_names = json.load(f)
    with open(f"{model_dir}/metadata.json") as f:
        metadata = json.load(f)
    return {
        "model": model,
        "scaler": scaler,
        "feature_names": feature_names,
        "threshold": metadata["threshold"],
        "metrics": metadata.get("metrics", {}),
    }