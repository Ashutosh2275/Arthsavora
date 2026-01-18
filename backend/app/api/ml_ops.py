from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from ..services.ml.parser import parse_upi_sms
from ..services.ocr.scanner import scan_receipt
from ..services.ml.classifier import ai_categorizer
from ..services.ml.chatbot import get_financial_advice # Import Chatbot
from ..core.supabase import upload_receipt_to_supabase
from ..db.mongodb import get_database
from .deps import get_current_user

router = APIRouter()

@router.post("/parse-sms")
async def api_parse_sms(payload: dict, current_user: dict = Depends(get_current_user)):
    text = payload.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    return parse_upi_sms(text)

@router.post("/scan-receipt")
async def api_scan_receipt(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    image_bytes = await file.read()
    ocr_result = scan_receipt(image_bytes)
    ocr_result["category"] = ai_categorizer.predict(ocr_result["description"])
    image_url = await upload_receipt_to_supabase(image_bytes, file.filename)
    ocr_result["image_url"] = image_url
    return ocr_result

@router.post("/chat")
async def chat_with_ai(payload: dict, current_user: dict = Depends(get_current_user)):
    """
    Gathers user context from DB and sends to Gemini.
    """
    user_query = payload.get("message")
    if not user_query:
        raise HTTPException(status_code=400, detail="Empty message")

    db = get_database()
    uid = str(current_user["_id"])

    # Fetch Real Context
    expenses = await db.expenses.find({"user_id": uid}).to_list(100)
    goals = await db.goals.find({"user_id": uid}).to_list(10)
    
    context = {
        "total_spent": sum(e['amount'] for e in expenses),
        "categories": list(set([e['category'] for e in expenses])),
        "goals": [g['name'] for g in goals]
    }

    reply = get_financial_advice(user_query, context)
    return {"reply": reply}