import joblib
import pandas as pd
import json
from feature_engineering import FeatureEngineer

# Load model & metadata
model = joblib.load("health_monitor_model.pkl")
features_order = joblib.load("features.pkl")

with open("label_mapping.json") as f:
    LABEL_MAP = json.load(f)

engineer = FeatureEngineer()

def process_new_reading(hr, spo2, temp, stress):
    feats = engineer.add_reading(hr, spo2, temp, stress)

    if feats is None:
        return {"status": "waiting_for_more_data"}

    X = pd.DataFrame([feats])[features_order]

    pred = model.predict(X)[0]
    prob = model.predict_proba(X).max()

    return {
        "emergency_status": LABEL_MAP[str(pred)],
        "confidence": round(float(prob), 3)
    }
