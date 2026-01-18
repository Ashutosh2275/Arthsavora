from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models.expense import ExpenseCreate, ExpenseOut
from ..db.mongodb import get_database
from .deps import get_current_user
from ..services.ml.classifier import ai_categorizer
from bson import ObjectId

router = APIRouter()

@router.post("/", response_model=ExpenseOut)
async def create_expense(
    expense_in: ExpenseCreate, 
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    expense_dict = expense_in.model_dump()
    expense_dict["user_id"] = str(current_user["_id"])
    
    # Production Logic: Even if the user leaves it as 'Shopping', 
    # the AI will analyze the description and correct the category.
    ai_category = ai_categorizer.predict(expense_dict["description"])
    expense_dict["category"] = ai_category
    
    new_expense = await db.expenses.insert_one(expense_dict)
    expense_dict["_id"] = str(new_expense.inserted_id)
    return expense_dict

@router.get("/", response_model=List[ExpenseOut])
async def get_expenses(current_user: dict = Depends(get_current_user)):
    db = get_database()
    cursor = db.expenses.find({"user_id": str(current_user["_id"])}).sort("date", -1)
    expenses = await cursor.to_list(length=100)
    return expenses

@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str, 
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    delete_result = await db.expenses.delete_one({
        "_id": ObjectId(expense_id),
        "user_id": str(current_user["_id"])
    })
    if delete_result.deleted_count == 1:
        return {"message": "Deleted successfully"}
    raise HTTPException(status_code=404, detail="Expense not found")