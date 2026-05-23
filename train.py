import os
import pandas as pd
import numpy as np
import xgboost as xgb
from loguru import logger
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, classification_report

# Ensure models directory exists
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_meta_v1.json")
os.makedirs(MODEL_DIR, exist_ok=True)

class ModelTrainer:
    def __init__(self):
        # Strict hyperparameters to prevent overfitting on financial data
        self.params = {
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'max_depth': 4,              # Keep shallow to prevent memorizing noise
            'learning_rate': 0.05,       # Slow learning rate
            'subsample': 0.8,            # Use 80% of data per tree
            'colsample_bytree': 0.8,     # Use 80% of features per tree
            'n_estimators': 150,
            'random_state': 42
        }
        self.model = xgb.XGBClassifier(**self.params)

    def fetch_training_data(self) -> pd.DataFrame:
        """
        In production, this connects to PostgreSQL:
        `SELECT features_json, is_win FROM trade_history WHERE is_completed = true`
        
        For V1 initialization, we generate a synthetic institutional dataset 
        to bootstrap the model weights.
        """
        logger.info("Generating bootstrap dataset for initial XGBoost training...")
        np.random.seed(42)
        n_samples = 2000

        # Simulate the features our FeaturePipeline (Phase 5) generates
        data = {
            "confluence_score": np.random.uniform(-2.0, 2.0, n_samples),
            "confluence_confidence": np.random.uniform(0.3, 1.0, n_samples),
            "regime_encoded": np.random.choice([2, 1, 0, -1, -2, -3], n_samples),
            "regime_confidence": np.random.uniform(0.4, 0.99, n_samples),
            "atr_ratio": np.random.uniform(0.01, 0.06, n_samples),
            "adx_14": np.random.uniform(10, 60, n_samples),
            "active_strategy_count": np.random.choice([1, 2, 3], n_samples),
            "funding_rate": np.random.uniform(-0.02, 0.02, n_samples),
            "oi_delta": np.random.uniform(-0.05, 0.05, n_samples)
        }
        
        df = pd.DataFrame(data)

        # Simulate the Target Variable (1 = Hit TP, 0 = Hit SL)
        # We artificially embed logic so the ML learns that high confluence + trend = Win
        target_prob = 0.40 # Base win rate
        
        # Boost probability if confluence is high and regime is a strong trend
        trend_match = ((df['confluence_score'] > 1.0) & (df['regime_encoded'] >= 1)) | \
                      ((df['confluence_score'] < -1.0) & (df['regime_encoded'] <= -1))
        
        # Penalize probability if volatility is extreme or funding is squeezed
        high_risk = (df['atr_ratio'] > 0.04) | (abs(df['funding_rate']) > 0.015)

        target_prob += np.where(trend_match, 0.25, 0.0)
        target_prob -= np.where(high_risk, 0.20, 0.0)
        
        # Add some noise
        target_prob += np.random.normal(0, 0.05, n_samples)
        
        df['target'] = (target_prob > 0.5).astype(int)
        
        logger.info(f"Generated {n_samples} samples. Class distribution: {df['target'].value_counts().to_dict()}")
        return df

    def train_and_save(self):
        df = self.fetch_training_data()
        
        # Split features (X) and target (y)
        X = df.drop(columns=['target'])
        y = df['target']
        
        # Walk-forward split (simulate time-series by not shuffling)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

        logger.info("Training XGBoost Meta Model...")
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_test, y_test)],
            verbose=False
        )

        # Evaluate strictly
        y_pred = self.model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)

        logger.info(f"Model Evaluation Metrics on Test Set:")
        logger.info(f"Accuracy:  {acc*100:.2f}%")
        logger.info(f"Precision: {prec*100:.2f}% (Critical for minimizing false signals)")
        
        # Save the model
        self.model.save_model(MODEL_PATH)
        logger.success(f"Model successfully saved to {MODEL_PATH}")
        logger.info("The engine will automatically detect this file and switch off Heuristic Fallback mode on its next cycle.")

if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.train_and_save()
