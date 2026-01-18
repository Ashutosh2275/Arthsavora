from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models.goal import GoalCreate, GoalOut
from ..db.mongodb import get_database
from .deps import get_current_user
from datetime import datetime, timedelta
from bson import ObjectId

router = APIRouter()

@router.post("/", response_model=GoalOut)
async def create_goal(goal_in: GoalCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    goal_dict = goal_in.model_dump()
    goal_dict["user_id"] = str(current_user["_id"])
    
    new_goal = await db.goals.insert_one(goal_dict)
    goal_dict["_id"] = str(new_goal.inserted_id)
    return goal_dict

@router.get("/", response_model=List[GoalOut])
async def get_goals(current_user: dict = Depends(get_current_user)):
    db = get_database()
    uid = str(current_user["_id"])
    
    # 1. Fetch Goals
    goals = await db.goals.find({"user_id": uid}).to_list(length=100)
    
    # 2. Fetch Spending to calculate Savings Velocity
    # Assume a default monthly income for logic (or could be a user setting)
    # For now, let's assume average savings is ₹10,000/mo if no data, 
    # or (Target Budget - Actual Spent)
    
    # Calculate last month's surplus
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    expenses = await db.expenses.find({"user_id": uid, "date": {"$gte": thirty_days_ago}}).to_list(500)
    total_spent = sum(e["amount"] for e in expenses)
    
    # Mock income for prediction logic (₹50,000 baseline)
    estimated_income = 50000 
    monthly_savings = max(500, estimated_income - total_spent)

    for g in goals:
        g["_id"] = str(g["_id"])
        remaining = g["target_amount"] - g["current_amount"]
        if monthly_savings > 0:
            months_needed = remaining / monthly_savings
            completion_date = datetime.utcnow() + timedelta(days=int(months_needed * 30))
            g["predicted_completion_date"] = completion_date.strftime("%b %Y")
            
            if g["deadline"] and completion_date > g["deadline"]:
                g["is_on_track"] = False
        else:
            g["predicted_completion_date"] = "Never (Increase Savings)"
            g["is_on_track"] = False

    return goals

@router.get("/insights")
async def get_investment_insights(current_user: dict = Depends(get_current_user)):
    """
    Educational, non-advisory insights based on budget surplus.
    """
    db = get_database()
    uid = str(current_user["_id"])
    
    # Calculate surplus
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    expenses = await db.expenses.find({"user_id": uid, "date": {"$gte": thirty_days_ago}}).to_list(500)
    total_spent = sum(e["amount"] for e in expenses)
    
    surplus = 50000 - total_spent # Using mock income
    
    insights = []
    if surplus > 15000:
        insights.append({"type": "Aggressive", "text": "High surplus detected. Consider Diversified Equity Mutual Funds for long-term growth."})
    elif surplus > 5000:
        insights.append({"type": "Balanced", "text": "Stable surplus. A mix of Index Funds and Fixed Deposits (FD) is recommended for safety."})
    else:
        insights.append({"type": "Conservative", "text": "Surplus is low. Focus on building an Emergency Fund in a High-Yield Savings Account first."})
        
    return {"surplus": surplus, "recommendations": insights}

@router.delete("/{goal_id}")
async def delete_goal(goal_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    await db.goals.delete_one({"_id": ObjectId(goal_id), "user_id": str(current_user["_id"])})
    return {"message": "Goal deleted"}