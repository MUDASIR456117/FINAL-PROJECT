from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier


def _training_data() -> tuple[np.ndarray, np.ndarray]:
    features = np.array([
        [85, 15, 5], [78, 22, 8], [72, 28, 12], [65, 35, 18],
        [56, 44, 25], [48, 52, 35], [38, 62, 45], [25, 75, 60],
        [92, 8, 2], [60, 40, 15], [44, 56, 32], [30, 70, 55],
    ])
    labels = np.array(["low", "low", "low", "low", "medium", "medium", "high", "high", "low", "medium", "high", "high"])
    return features, labels


def predict_risk(savings_rate: float, expense_ratio: float, debt_ratio: float) -> dict[str, float | str]:
    features, labels = _training_data()
    model = RandomForestClassifier(n_estimators=80, random_state=42, min_samples_leaf=1)
    model.fit(features, labels)
    sample = np.array([[savings_rate, expense_ratio, debt_ratio]])
    probabilities = model.predict_proba(sample)[0]
    index = int(np.argmax(probabilities))
    return {"risk": str(model.classes_[index]).title(), "confidence": round(float(probabilities[index]), 3)}