from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd


def sample_transactions() -> pd.DataFrame:
    rows = [
        ("2026-07-01", "income", "Salary", 5200, "Monthly salary"),
        ("2026-07-03", "expense", "Housing", 1450, "Rent"),
        ("2026-07-05", "expense", "Food", 310, "Groceries and dining"),
        ("2026-07-08", "expense", "Transport", 180, "Fuel and transit"),
        ("2026-07-12", "expense", "Utilities", 155, "Electricity and internet"),
        ("2026-07-15", "expense", "Entertainment", 120, "Subscriptions"),
        ("2026-07-20", "expense", "Health", 90, "Pharmacy"),
        ("2026-07-28", "income", "Freelance", 650, "Design project"),
    ]
    return pd.DataFrame(rows, columns=["date", "type", "category", "amount", "description"])


def analyze(transactions: pd.DataFrame, debt: float = 0) -> dict[str, Any]:
    income = float(transactions.loc[transactions["type"] == "income", "amount"].sum())
    expenses = float(transactions.loc[transactions["type"] == "expense", "amount"].sum())
    savings = income - expenses
    savings_rate = (savings / income * 100) if income else 0
    expense_ratio = (expenses / income * 100) if income else 100
    score = max(0, min(100, round(45 + savings_rate * 0.7 - expense_ratio * 0.15 - debt / max(income, 1) * 20)))
    risk = "Low" if score >= 70 else "Medium" if score >= 45 else "High"
    category_spend = (
        transactions.loc[transactions["type"] == "expense"]
        .groupby("category")["amount"].sum()
        .sort_values(ascending=False)
    )
    return {
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "savings_rate": savings_rate,
        "expense_ratio": expense_ratio,
        "score": score,
        "risk": risk,
        "category_spend": category_spend,
    }


def goal_plan(target_amount: float, current_amount: float, target_date: date) -> float:
    months = max(1, (target_date.year - date.today().year) * 12 + target_date.month - date.today().month)
    return max(0, (target_amount - current_amount) / months)


def recommendations(summary: dict[str, Any]) -> list[str]:
    tips = []
    top_category = summary["category_spend"].index[0] if not summary["category_spend"].empty else None
    top_amount = float(summary["category_spend"].iloc[0]) if top_category else 0
    if summary["income"] <= 0:
        tips.append("Add at least one income transaction so your advice can be calibrated to cash flow.")
    elif summary["savings_rate"] < 10:
        tips.append(f"Your savings rate is {summary['savings_rate']:.1f}%. Set aside ${summary['income'] * 0.10:,.0f} next period before discretionary spending.")
    elif summary["savings_rate"] < 20:
        tips.append(f"You saved {summary['savings_rate']:.1f}% this period. Trim about ${max(0, summary['income'] * 0.20 - summary['savings']):,.0f} in monthly spending to reach a 20% buffer.")
    else:
        tips.append(f"You saved {summary['savings_rate']:.1f}% this period. Automate ${summary['savings'] * 0.25:,.0f} of that surplus toward an emergency fund or goal.")
    if top_category and summary["income"] and top_amount / summary["income"] >= 0.20:
        tips.append(f"{top_category} is your largest expense at ${top_amount:,.0f}. Review it first because it uses {top_amount / summary['income'] * 100:.0f}% of income.")
    if summary["expense_ratio"] > 70:
        tips.append(f"Expenses consume {summary['expense_ratio']:.1f}% of income. Set a weekly flexible-spend limit of ${summary['income'] * 0.10:,.0f}.")
    if summary["risk"] == "Low":
        tips.append("Your score indicates a healthy buffer. Keep three months of essential expenses as your next resilience milestone.")
    else:
        tips.append("Prioritize a one-month emergency buffer and pause new discretionary commitments until cash flow improves.")
    return tips


def notifications(summary: dict[str, Any]) -> list[dict[str, str]]:
    alerts = []
    if summary["savings_rate"] < 10:
        alerts.append({"type": "warning", "title": "Savings rate is low", "message": f"You saved {summary['savings_rate']:.1f}% this period. Aim for at least 10% next period."})
    if summary["expense_ratio"] > 70:
        alerts.append({"type": "warning", "title": "High expense load", "message": f"Expenses are {summary['expense_ratio']:.1f}% of income. Review your top category."})
    if summary["risk"] == "Low":
        alerts.append({"type": "success", "title": "Healthy financial buffer", "message": "Your current income and spending pattern is resilient."})
    if not alerts:
        alerts.append({"type": "info", "title": "Keep tracking", "message": "Add more transactions to improve advisor confidence."})
    return alerts