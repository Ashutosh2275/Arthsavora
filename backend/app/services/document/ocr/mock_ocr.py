"""
Arthsavora Deterministic Mock OCR Engine for Testing
Provides repeatable, zero-flakiness receipt OCR outputs for automated test suites.
"""

from pathlib import Path
from typing import Dict, Optional
from app.services.document.ocr.base_ocr import BaseOCREngine, OCRRawResult

# Standardized deterministic Indian receipt templates for CI/CD tests
SAMPLE_INDIAN_RECEIPTS: Dict[str, str] = {
    "swiggy": """
SWIGGY ORDER INVOICE
Bundl Technologies Pvt Ltd
GSTIN: 29AABCB2212M1Z2
Invoice No: SWG-BLR-2026-9812
Date: 12/10/2026

Item Description           Qty    Price     Amount
--------------------------------------------------
Paneer Butter Masala         1    280.00    280.00
Butter Naan (2 pcs)          2     60.00    120.00
Jeera Rice                   1    150.00    150.00
--------------------------------------------------
Subtotal:                                   550.00
CGST (2.5%):                                 13.75
SGST (2.5%):                                 13.75
Delivery Fee:                                40.00
Discount:                                   -50.00
--------------------------------------------------
Total Amount:                              ₹567.50

Payment Mode: UPI (Google Pay)
UPI Ref / UTR: 628491028472
Thank you for ordering with Swiggy!
""",
    "reliance": """
RELIANCE RETAIL LIMITED
Reliance Fresh - Koramangala
GSTIN: 27AABCR4587R1ZM
Tax Invoice / Cash Memo: RF-2026-88412
Date: 15-11-2026

Items:
Organic Whole Wheat Atta 5kg   1    245.00
Sunflower Cooking Oil 1L       2    140.00    280.00
Tata Salt 1kg                  1     28.00     28.00

Sub Total:                                  553.00
CGST (5%):                                   13.82
SGST (5%):                                   13.82
Total:                                      580.64
Paid by: HDFC Credit Card (Ending 4092)
""",
    "fuel": """
HINDUSTAN PETROLEUM CORPORATION LTD
HP Auto Care Centre
GSTIN: 07AAACH1118B1ZE
Bill No: HP-DEL-40918
Date: 2026-11-10

Product: SPEED PETROL
Quantity: 15.00 Ltrs
Rate: 98.40 / Ltr
Total Amount: Rs. 1,476.00
Mode of Payment: UPI / BharatPe
""",
    "default": """
TAX INVOICE
Merchant: Blue Tokai Coffee Roasters
GSTIN: 07AAFCB9481E1ZR
Invoice Number: BTC-2026-00451
Date: 25/11/2026

Iced Americano               1    210.00
Almond Croissant             1    190.00

Subtotal:                   400.00
CGST (2.5%):                 10.00
SGST (2.5%):                 10.00
Total:                      ₹420.00
Payment Method: Card
"""
}


class MockDeterministicOCREngine(BaseOCREngine):
    """Deterministic OCR engine emitting verified text for unit and integration testing."""

    def __init__(self, override_text: Optional[str] = None):
        self.override_text = override_text

    async def extract_text(self, file_path: str, mime_type: str = "image/png") -> OCRRawResult:
        if self.override_text:
            text = self.override_text
        else:
            filename = Path(file_path).name.lower()
            if "swiggy" in filename:
                text = SAMPLE_INDIAN_RECEIPTS["swiggy"]
            elif "reliance" in filename:
                text = SAMPLE_INDIAN_RECEIPTS["reliance"]
            elif "fuel" in filename or "petrol" in filename:
                text = SAMPLE_INDIAN_RECEIPTS["fuel"]
            else:
                text = SAMPLE_INDIAN_RECEIPTS["default"]

        return OCRRawResult(
            text=text.strip(),
            confidence=0.98,
            provider="mock_deterministic",
            version="1.0.0",
            page_count=1,
            metadata={"source": "mock_fixture"},
        )
