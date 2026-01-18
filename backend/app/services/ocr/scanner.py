import pytesseract
from PIL import Image
import re
import io
import os

# Point to your Windows Tesseract installation
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def scan_receipt(image_bytes: bytes):
    """
    Uses OCR to extract financial data from a receipt image.
    """
    try:
        # 1. Load image and convert to grayscale for OCR accuracy
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('L') 
        
        # 2. Extract raw text
        raw_text = pytesseract.image_to_string(img)
        lines = raw_text.split('\n')
        
        # 3. Extract Amount (Looking for decimal numbers like 120.50)
        # We clean the text of commas first
        clean_text = raw_text.replace(',', '')
        amounts = re.findall(r'\d+\.\d{2}', clean_text)
        
        # In a receipt, the largest found amount is typically the Total
        total_amount = 0.0
        if amounts:
            total_amount = max([float(a) for a in amounts])

        # 4. Extract Merchant (The first line that isn't empty or numeric)
        merchant = "Unknown Merchant"
        for line in lines:
            val = line.strip()
            if len(val) > 3 and not any(char.isdigit() for char in val):
                merchant = val
                break

        return {
            "amount": total_amount,
            "description": merchant.upper(),
            "source": "OCR"
        }
    except Exception as e:
        print(f"OCR Logic Error: {e}")
        return {"amount": 0.0, "description": "SCAN FAILED", "source": "OCR"}