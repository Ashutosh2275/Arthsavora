from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from ..db.mongodb import get_database
from .deps import get_current_user
import pandas as pd
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

router = APIRouter()

@router.get("/excel")
async def export_excel(current_user: dict = Depends(get_current_user)):
    db = get_database()
    cursor = db.expenses.find({"user_id": str(current_user["_id"])}).sort("date", -1)
    expenses = await cursor.to_list(length=1000)
    
    # Convert to DataFrame
    df = pd.DataFrame(expenses)
    if df.empty:
        return {"message": "No data to export"}
    
    # Clean data for Excel
    df = df.drop(columns=['_id', 'user_id'])
    df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M')
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Expenses')
    
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="Arthsavora_Report.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/pdf")
async def export_pdf(current_user: dict = Depends(get_current_user)):
    db = get_database()
    cursor = db.expenses.find({"user_id": str(current_user["_id"])}).sort("date", -1)
    expenses = await cursor.to_list(length=100)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph(f"ARTHSAVORA - Financial Statement", styles['Title']))
    elements.append(Paragraph(f"User: {current_user['full_name']}", styles['Normal']))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Table Header
    data = [["Date", "Description", "Category", "Amount (INR)"]]
    total = 0
    for exp in expenses:
        data.append([
            exp['date'].strftime('%Y-%m-%d'),
            exp['description'],
            exp['category'],
            f"{exp['amount']:.2f}"
        ])
        total += exp['amount']

    # Final Total Row
    data.append(["", "", "TOTAL SPENT", f"{total:.2f}"])

    # Table Styling
    t = Table(data, colWidths=[80, 200, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.indigo),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(t)
    doc.build(elements)
    
    buffer.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="Arthsavora_Report.pdf"'}
    return StreamingResponse(buffer, headers=headers, media_type='application/pdf')