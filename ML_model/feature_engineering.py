import pandas as pd
import numpy as np

WINDOW = 5

STRESS_MAP = {
    "low": 0,
    "normal": 1,
    "high": 2
}

class FeatureEngineer:
    def __init__(self):
        self.buffer = []
        self.readings_count = 0
    def add_reading(self, hr, spo2, temperature, stress):
        # Encode stress
        stress = STRESS_MAP[stress]
        self.readings_count += 1
        # Add new reading
        self.buffer.append({
            "HR": hr,
            "SPO2": spo2,
            "Temperature": temperature,
            "Stress": stress
        })

        # Wait until buffer is full
        if len(self.buffer) < WINDOW:
            return None  # not enough data yet

        # Keep fixed window size
        if len(self.buffer) > WINDOW:
            self.buffer.pop(0)

        if self.readings_count % WINDOW != 0 :
            return None
        
        df = pd.DataFrame(self.buffer)

        # =========================
        # Feature Engineering
        # =========================
        features = {
            # ---------- HR ----------
            "HR_avg_5": df["HR"].mean(),
            "HR_std_5": df["HR"].std(),
            "HR_trend": df["HR"].iloc[-1] - df["HR"].iloc[0],

            # ---------- SPO2 ----------
            "SPO2_avg_5": df["SPO2"].mean(),
            "SPO2_drop": df["SPO2"].iloc[0] - df["SPO2"].iloc[-1],

            # ---------- Temperature ----------
            "Temp_avg_5": df["Temperature"].mean(),
            "Temp_trend": df["Temperature"].iloc[-1] - df["Temperature"].iloc[0],

            # ---------- Stress ----------
            "Stress_load": df["Stress"].sum(),
            "Stress_high_ratio": (df["Stress"] == 2).sum() / WINDOW,

            # ---------- Golden Features ----------
            # SAME AS TRAINING (mean of per-sample ratios)
            "O2_Efficiency": (df["SPO2"] / (df["HR"] + 1)).mean(),

            "Heart_Stress": (df["HR"] * (df["Stress"] + 1)).mean(),

            "Temp_SD_5": df["Temperature"].std()
        }

        return features