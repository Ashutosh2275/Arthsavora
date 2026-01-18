from fastapi import APIRouter, Depends
from ..db.mongodb import get_database
from .deps import get_current_user
from datetime import datetime, timedelta
from ..services.ml.anomaly import detect_anomalies # New Import

router = APIRouter()

@router.get("/summary")
async def get_analytics_summary(current_user: dict = Depends(get_current_user)):
    db = get_database()
    uid = str(current_user["_id"])
    
    # 1. Total Spending (Current Month)
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    pipeline_total = [
        {"$match": {"user_id": uid, "date": {"$gte": start_of_month}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    total_res = await db.expenses.aggregate(pipeline_total).to_list(1)
    total_spent = total_res[0]["total"] if total_res else 0

    # 2. Category Distribution
    pipeline_category = [
        {"$match": {"user_id": uid}},
        {"$group": {"_id": "$category", "value": {"$sum": "$amount"}}},
        {"$project": {"name": "$_id", "value": 1, "_id": 0}}
    ]
    category_data = await db.expenses.aggregate(pipeline_category).to_list(100)

    # 3. Daily Spending Trend (Last 30 Days)
    last_30_days = datetime.utcnow() - timedelta(days=30)
    pipeline_trend = [
        {"$match": {"user_id": uid, "date": {"$gte": last_30_days}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
            "amount": {"$sum": "$amount"}
        }},
        {"$sort": {"_id": 1}},
        {"$project": {"date": "$_id", "amount": 1, "_id": 0}}
    ]
    trend_data = await db.expenses.aggregate(pipeline_trend).to_list(31)

    # 4. Phase 8: Anomaly Detection
    all_expenses_cursor = db.expenses.find({"user_id": uid}).sort("date", -1)
    all_expenses = await all_expenses_cursor.to_list(length=500)
    
    anomaly_ids = detect_anomalies(all_expenses)
    
    # Tag flagged expenses to show in the UI
    flagged_expenses = [exp for exp in all_expenses if str(exp["_id"]) in anomaly_ids]
    # Format for JSON response
    for exp in flagged_expenses:
        exp["_id"] = str(exp["_id"])

    return {
        "totalSpent": total_spent,
        "categoryData": category_data,
        "trendData": trend_data,
        "avgDaily": round(total_spent / datetime.utcnow().day, 2) if total_spent > 0 else 0,
        "anomalies": flagged_expenses # New field
    }