from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from database.mongodb import check_connection, load_transactions, save_transaction
from services.finance import analyze, goal_plan, recommendations, sample_transactions

app = FastAPI(title="AI Financial Advisor API", version="1.0.0")

class Transaction(BaseModel):
    type: str = Field(pattern="^(income|expense)$")
    category: str
    amount: float = Field(gt=0)
    date: date
    description: str = ""

class Goal(BaseModel):
    target_amount: float = Field(gt=0)
    current_amount: float = Field(ge=0)
    target_date: date

@app.get("/")
def root() -> dict[str, str]:
    return {"name": "AI Financial Advisor", "status": "ready"}

@app.get("/health/database")
def database_health() -> dict[str, str]:
    try:
        check_connection()
        return {"database": "connected"}
    except Exception:
        return {"database": "unavailable"}

@app.get("/transactions")
def get_transactions() -> list[dict[str, Any]]:
    try:
        stored_transactions = load_transactions()
        return stored_transactions or []
    except Exception as error:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from error

@app.post("/transactions")
def add_transaction(transaction: Transaction) -> dict[str, Any]:
    transaction_data = transaction.model_dump()
    try:
        save_transaction(transaction_data)
    except Exception as error:
        raise HTTPException(status_code=503, detail="Transaction could not be saved to MongoDB") from error
    return {"message": "Transaction saved", "transaction": transaction_data}

@app.get("/analysis")
def get_analysis() -> dict[str, Any]:
    result = analyze(sample_transactions())
    result.pop("category_spend")
    return result

@app.get("/advisor")
def get_advisor() -> dict[str, Any]:
    result = analyze(sample_transactions())
    return {"score": result["score"], "risk": result["risk"], "recommendations": recommendations(result)}

@app.post("/goals")
def create_goal(goal: Goal) -> dict[str, Any]:
    return {"goal": goal.model_dump(), "required_monthly_saving": goal_plan(goal.target_amount, goal.current_amount, goal.target_date)}

@app.get("/report")
def get_report() -> dict[str, Any]:
    result = analyze(sample_transactions())
    return {"summary": {key: value for key, value in result.items() if key != "category_spend"}, "recommendations": recommendations(result)}