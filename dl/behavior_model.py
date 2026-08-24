from __future__ import annotations

import os
import numpy as np


def _numpy_neural_network(savings_rate: float, expense_ratio: float, months: int) -> dict[str, float | str]:
    x_train = np.array([
        [0.05, 0.95], [0.10, 0.90], [0.15, 0.85], [0.20, 0.80],
        [0.25, 0.75], [0.30, 0.70], [0.40, 0.60], [0.50, 0.50],
    ], dtype=np.float32)
    y_train = np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50], dtype=np.float32).reshape(-1, 1)
    rng = np.random.default_rng(42)
    weights = rng.normal(0, 0.2, (2, 1)).astype(np.float32)
    bias = np.zeros((1, 1), dtype=np.float32)
    for _ in range(1500):
        predictions = x_train @ weights + bias
        error = predictions - y_train
        weights -= 0.08 * (x_train.T @ error) / len(x_train)
        bias -= 0.08 * error.mean(axis=0, keepdims=True)
    sample = np.array([[savings_rate / 100, expense_ratio / 100]], dtype=np.float32)
    projected_rate = float((sample @ weights + bias)[0, 0] * 100)
    return {"model": "NumPy neural network fallback", "projected_savings_rate": round(max(0, projected_rate), 1), "months": months}


def predict_savings(savings_rate: float, expense_ratio: float, months: int) -> dict[str, float | str]:
    """Train a compact Keras regression model and forecast savings.

    The synthetic training set represents normalized monthly financial behavior.
    In production, replace it with a user's historical monthly feature rows.
    """
    if os.getenv("DL_BACKEND", "numpy").lower() != "tensorflow":
        return _numpy_neural_network(savings_rate, expense_ratio, months)

    try:
        import tensorflow as tf
    except (ImportError, OSError, RuntimeError):
        return _numpy_neural_network(savings_rate, expense_ratio, months)

    tf.keras.utils.set_random_seed(42)
    x_train = np.array([
        [0.05, 0.95], [0.10, 0.90], [0.15, 0.85], [0.20, 0.80],
        [0.25, 0.75], [0.30, 0.70], [0.40, 0.60], [0.50, 0.50],
    ], dtype=np.float32)
    y_train = np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50], dtype=np.float32)
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(2,)),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(8, activation="relu"),
        tf.keras.layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(x_train, y_train, epochs=80, verbose=0)
    normalized_savings = float(model.predict(np.array([[savings_rate / 100, expense_ratio / 100]], dtype=np.float32), verbose=0)[0][0])
    return {"model": "TensorFlow neural network", "projected_savings_rate": round(max(0, normalized_savings * 100), 1), "months": months}