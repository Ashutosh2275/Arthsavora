from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models.budget import BudgetCreate, BudgetOut
from ..db.mongodb import get_database
from ..services.ml.forecaster import predict_monthly_spend
from .deps import get_current_user

router = APIRouter()

@router.post("/", response_model=BudgetOut)
async def set_budget(budget_in: BudgetCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    budget_dict = budget_in.model_dump()
    budget_dict["user_id"] = str(current_user["_id"])
    
    # Update if exists, else insert
    query = {"user_id": budget_dict["user_id"], "category": budget_dict["category"]}
    await db.budgets.replace_one(query, budget_dict, upsert=True)
    
    updated_budget = await db.budgets.find_one(query)
    updated_budget["_id"] = str(updated_budget["_id"])
    return updated_budget

@router.get("/forecast")
async def get_forecast(current_user: dict = Depends(get_current_user)):
    db = get_database()
    cursor = db.expenses.find({"user_id": str(current_user["_id"])})
    expenses = await cursor.to_list(length=500)
    
    if not expenses:
        return {"prediction": 0, "status": "No Data"}
        
    return predict_monthly_spend(expenses)

@router.get("/status")
async def get_budget_status(current_user: dict = Depends(get_current_user)):
    db = get_database()
    uid = str(current_user["_id"])
    
    # Get all budgets
    budgets = await db.budgets.find({"user_id": uid}).to_list(length=100)
    
    # Get spending per category for current month
    pipeline = [
        {"$match": {"user_id": uid}},
        {"$group": {"_id": "$category", "totalSpent": {"$sum": "$amount"}}}
    ]
    spending = await db.expenses.aggregate(pipeline).to_list(length=100)
    spend_map = {item["_id"]: item["totalSpent"] for item in spending}
    
    status = []
    for b in budgets:
        spent = spend_map.get(b["category"], 0)
        status.append({
            "category": b["category"],
            "limit": b["limit"],
            "spent": spent,
            "remaining": max(0, b["limit"] - spent),
            "percent": min(100, (spent / b["limit"]) * 100) if b["limit"] > 0 else 0
        })
    return status