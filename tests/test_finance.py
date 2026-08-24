from datetime import date

from services.finance import analyze, goal_plan, notifications, recommendations, sample_transactions


def test_analysis_balances_income_and_expenses():
    result = analyze(sample_transactions())
    assert result["income"] == 5850
    assert result["expenses"] == 2305
    assert result["savings"] == 3545
    assert 0 <= result["score"] <= 100


def test_goal_plan_never_returns_negative():
    assert goal_plan(1000, 1500, date(2027, 1, 1)) == 0


def test_advisor_recommendations_use_spending_context():
    result = analyze(sample_transactions())
    tips = recommendations(result)
    assert any("Housing" in tip for tip in tips)


def test_notifications_are_generated_from_summary():
    result = analyze(sample_transactions())
    alerts = notifications(result)
    assert alerts and {"type", "title", "message"} <= alerts[0].keys()