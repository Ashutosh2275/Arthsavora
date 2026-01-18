import re
from .classifier import ai_categorizer

def parse_upi_sms(text: str):
    """
    Combines Regex (Phase 4) and Scikit-Learn (Phase 5) to parse and categorize.
    """
    # 1. Clean the text
    clean_text = text.replace(',', '') 
    
    # 2. Extract Amount (Regex)
    amount_patterns = [
        r'(?:Rs|INR|Amt|Sent|Paid|Debited)\.?\s*([\d.]+)',
        r'([\d.]+)\s*(?:sent|paid|debited)'
    ]
    
    amount = 0.0
    for pattern in amount_patterns:
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1))
                break
            except ValueError:
                continue

    # 3. Extract Merchant (Regex)
    merchant = "Unknown Merchant"
    merchant_match = re.search(r'(?:to|at|vpa|into)\s+([A-Za-z0-9\s.\-]+?)(?:\s+on|\s+at|\s+ref|\s+from|\s+using|\.|\d)', clean_text, re.IGNORECASE)
    
    if merchant_match:
        merchant = merchant_match.group(1).strip()
        # Clean banking noise
        noise_words = ['bank', 'ac', 'a/c', 'ref', 'vpa', 'upi', 'using']
        merchant_words = [word for word in merchant.split() if word.lower() not in noise_words]
        merchant = " ".join(merchant_words).upper()

    # 4. AI Categorization (Scikit-Learn)
    # This uses the model we built in classifier.py
    category = ai_categorizer.predict(merchant)

    return {
        "amount": amount,
        "description": merchant if merchant else "GENERAL EXPENSE",
        "category": category,
        "source": "SMS"
    }