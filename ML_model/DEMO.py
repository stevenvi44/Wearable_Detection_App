import time
import joblib
import json
import pandas as pd
from feature_engineering import FeatureEngineer

# ===============================
# Load model & metadata
# ===============================
model = joblib.load("health_monitor_model.pkl")
features_order = joblib.load("features.pkl")

with open("label_mapping.json") as f:
    LABEL_MAP = json.load(f)

engineer = FeatureEngineer()

# ===============================
# Simulated incoming sensor data
# ===============================
readings_stream = [
    # ---- SAFE ----
    {"hr": 78, "spo2": 98, "temperture": 27.5, "stress": "low"},
    {"hr": 80, "spo2": 98, "temperture": 27.6, "stress": "low"},
    {"hr": 82, "spo2": 97, "temperture": 27.6, "stress": "normal"},
    {"hr": 85, "spo2": 97, "temperture": 27.7, "stress": "normal"},
    {"hr": 86, "spo2": 97, "temperture": 27.8, "stress": "normal"},  # 👈 decision

    # ---- WARNING ----
    {"hr": 95, "spo2": 94, "temperture": 27.2, "stress": "low"},
    {"hr": 95, "spo2": 94, "temperture": 27.4, "stress": "normal"},
    {"hr": 95, "spo2": 95, "temperture": 27.6, "stress": "normal"},
    {"hr": 95, "spo2": 95, "temperture": 27.8, "stress": "normal"},
    {"hr": 96, "spo2": 99, "temperture": 27.0, "stress": "normal"},  # 👈 decision

    # ---- CRITICAL ----
    {"hr": 120, "spo2": 88, "temperture": 38.5, "stress": "high"},
    {"hr": 125, "spo2": 86, "temperture": 38.8, "stress": "high"},
    {"hr": 130, "spo2": 84, "temperture": 39.1, "stress": "high"},
    {"hr": 135, "spo2": 82, "temperture": 39.4, "stress": "high"},
    {"hr": 140, "spo2": 80, "temperture": 39.8, "stress": "high"},  # 👈 decision
]

# ===============================
# Run simulation
# ===============================
print("\n===== START STREAM =====\n")

for i, r in enumerate(readings_stream, start=1):
    print(f"📥 Reading {i}: {r}")

    feats = engineer.add_reading(
        hr=r["hr"],
        spo2=r["spo2"],
        temperature=r["temperture"],
        stress=r["stress"]
    )

    if feats is None:
        print("⏳ Status: waiting_for_more_data\n")
        continue

    X = pd.DataFrame([feats])[features_order]
    pred = model.predict(X)[0]
    prob = model.predict_proba(X).max()

    print("🚨 DECISION ISSUED")
    print("Emergency Status:", LABEL_MAP[str(pred)])
    print("Confidence:", round(float(prob), 3))
    print("-" * 40)

    time.sleep(1)

print("\n✅ DEMO FINISHED SUCCESSFULLY")
