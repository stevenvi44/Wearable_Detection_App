"""
ML Model Service for Health Monitoring Predictions
Manages ML model inference and per-user feature engineering state
"""
import os
import sys
import joblib
import pandas as pd
import json
from typing import Optional, Dict
from pathlib import Path

# Add ML_model directory to path
ML_MODEL_DIR = Path(__file__).parent / "ML_model"
sys.path.insert(0, str(ML_MODEL_DIR))

from ML_model.feature_engineering import FeatureEngineer

# Load model and metadata (lazy loading)
_model = None
_features_order = None
_label_map = None
_feature_engineers = {}  # user_id -> FeatureEngineer instance


def _load_model():
    """Lazy load the ML model and metadata"""
    global _model, _features_order, _label_map
    
    if _model is None:
        model_path = ML_MODEL_DIR / "health_monitor_model.pkl"
        features_path = ML_MODEL_DIR / "features.pkl"
        label_map_path = ML_MODEL_DIR / "label_mapping.json"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not features_path.exists():
            raise FileNotFoundError(f"Features file not found: {features_path}")
        if not label_map_path.exists():
            raise FileNotFoundError(f"Label mapping file not found: {label_map_path}")
        
        _model = joblib.load(model_path)
        _features_order = joblib.load(features_path)
        
        with open(label_map_path) as f:
            _label_map = json.load(f)
    
    return _model, _features_order, _label_map


def get_feature_engineer(user_id: int) -> FeatureEngineer:
    """Get or create a FeatureEngineer instance for a user"""
    if user_id not in _feature_engineers:
        _feature_engineers[user_id] = FeatureEngineer()
    return _feature_engineers[user_id]


def predict_emergency_status(
    user_id: int,
    hr: Optional[int],
    spo2: Optional[int],
    temp: Optional[float],
    stress: Optional[str]
) -> Dict:
    """
    Process a new vital reading and return emergency status prediction.
    
    Args:
        user_id: User ID to maintain separate feature engineering state
        hr: Heart rate
        spo2: Oxygen saturation
        temp: Temperature
        stress: Stress level ("low", "normal", "high")
    
    Returns:
        Dict with either:
        - {"status": "waiting_for_more_data"} if not enough readings yet
        - {"emergency_status": "safe_now"|"warning_soon"|"critical", "confidence": float}
    """
    # Validate inputs
    if hr is None or spo2 is None or temp is None or stress is None:
        return {"status": "insufficient_data", "message": "Missing required vital signs"}
    
    # Validate stress value
    valid_stress = ["low", "normal", "high"]
    if stress not in valid_stress:
        return {"status": "invalid_data", "message": f"Stress must be one of: {valid_stress}"}
    
    try:
        # Load model if not already loaded
        model, features_order, label_map = _load_model()
        
        # Get feature engineer for this user
        engineer = get_feature_engineer(user_id)
        
        # Add reading and get features
        feats = engineer.add_reading(hr, spo2, temp, stress)
        
        # Not enough data yet (need 5 readings)
        if feats is None:
            return {"status": "waiting_for_more_data"}
        
        # Prepare features in correct order
        X = pd.DataFrame([feats])[features_order]
        
        # Make prediction
        pred = model.predict(X)[0]
        prob = model.predict_proba(X).max()
        
        return {
            "emergency_status": label_map[str(pred)],
            "confidence": round(float(prob), 3)
        }
    
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"ML prediction error: {e}")
        return {"status": "error", "message": str(e)}


def reset_user_state(user_id: int):
    """Reset feature engineering state for a user (useful for testing)"""
    if user_id in _feature_engineers:
        del _feature_engineers[user_id]

