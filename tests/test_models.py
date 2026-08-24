from dl.behavior_model import predict_savings
from ml.risk_model import predict_risk


def test_ml_risk_model_returns_valid_prediction():
    result = predict_risk(35, 65, 10)
    assert result["risk"] in {"Low", "Medium", "High"}
    assert 0 <= result["confidence"] <= 1


def test_dl_model_returns_savings_prediction():
    result = predict_savings(60, 40, 6)
    assert "neural network" in str(result["model"]).lower()
    assert result["projected_savings_rate"] >= 0
    assert result["months"] == 6