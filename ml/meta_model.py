import pandas as pd
import numpy as np
from loguru import logger
from pydantic import BaseModel
from typing import Dict
import xgboost as xgb
import os

class MLPrediction(BaseModel):
    probability_of_success: float
    risk_classification: str      # "LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"
    is_tradable: bool             # Boolean gate for downstream
    explanation: str

class MetaModel:
    def __init__(self, model_dir: str = "models", model_name: str = "xgboost_meta_v1.json"):
        self.model_path = os.path.join(model_dir, model_name)
        self.min_probability_threshold = 0.60 # Reject setups with <60% predicted win rate
        self.is_trained = False
        self.model = xgb.XGBClassifier()

        # Ensure model directory exists
        os.makedirs(model_dir, exist_ok=True)

        try:
            if os.path.exists(self.model_path):
                self.model.load_model(self.model_path)
                self.is_trained = True
                logger.info(f"Loaded XGBoost Meta Model from {self.model_path}")
            else:
                logger.warning("No pre-trained ML model found. Running in Heuristic Fallback mode until Phase 10 training.")
        except Exception as e:
            logger.error(f"Failed to load Meta Model: {e}")

    async def predict(self, features: Dict[str, float]) -> MLPrediction:
        try:
            if not self.is_trained:
                # HEURISTIC FALLBACK: Mathematically approximate probability 
                # based on confluence score strength and regime confidence.
                base_prob = 0.50
                score_impact = (abs(features.get("confluence_score", 0.0)) / 2.0) * 0.30 # Max 30% boost
                conf_impact = (features.get("confluence_confidence", 1.0) - 0.5) * 0.10 # +/- 5% based on confidence
                
                prob = base_prob + score_impact + conf_impact
                prob = min(max(prob, 0.0), 0.99)
                explanation = "Probability calculated via heuristic fallback (ML not trained)."
            else:
                # REAL ML INFERENCE
                # Convert dict to single-row DataFrame (XGBoost expects 2D array)
                df_features = pd.DataFrame([features])
                # predict_proba returns [[prob_loss, prob_win]]
                prob = float(self.model.predict_proba(df_features)[0][1])
                explanation = "Probability predicted via XGBoost Inference."

            # Risk Classification
            risk = "HIGH_RISK"
            if prob >= 0.75:
                risk = "LOW_RISK"
            elif prob >= 0.60:
                risk = "MEDIUM_RISK"

            is_tradable = prob >= self.min_probability_threshold

            return MLPrediction(
                probability_of_success=round(prob, 3),
                risk_classification=risk,
                is_tradable=is_tradable,
                explanation=explanation
            )

        except Exception as e:
            logger.error(f"Meta Model prediction failed: {e}")
            return MLPrediction(
                probability_of_success=0.0, risk_classification="HIGH_RISK", 
                is_tradable=False, explanation=f"Error: {e}"
            )
