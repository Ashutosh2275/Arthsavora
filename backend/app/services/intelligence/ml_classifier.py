"""
Arthsavora Machine-Learning Transaction Classifier Pipeline
Scikit-learn TF-IDF + Logistic Regression pipeline with calibrated probabilities,
stratified train/test evaluation, India-first synthetic dataset, and reproducible artifact versioning.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.domain.category_taxonomy import ConfidenceBand


@dataclass(frozen=True)
class MLPredictionResult:
    predicted_category_slug: str
    confidence_score: float
    confidence_band: str
    explanation: str
    model_version: str
    probabilities: Dict[str, float]


# ===========================================================================
# Curated, Balanced Synthetic & Canonical Training Dataset for India
# ===========================================================================

DATASET: List[Tuple[str, str]] = [
    # Salary & Income
    ("NEFT CR INFOSYS TECHNOLOGIES MONTHLY SALARY", "salary"),
    ("SALARY CREDIT TATA CONSULTANCY SERVICES LIMITED", "salary"),
    ("DIRECT DEPOSIT ACCENTURE SOLUTIONS PAYROLL", "salary"),
    ("WIPRO LIMITED SALARY CREDIT", "salary"),
    ("HCL TECH NET PAY SALARY NOVEMBER", "salary"),
    ("PAYROLL CREDIT GOOGLE INDIA PRIVATE LIMITED", "salary"),
    ("MONTHLY SALARY CREDIT RELIANCE INDUSTRIES", "salary"),
    ("FREELANCE CONSULTING RETAINER WIRE TRANSFER", "freelance-income"),
    ("UPWORK GLOBAL INC ESCROW DISBURSEMENT", "freelance-income"),
    ("CLIENT PAYMENT UI UX DESIGN PROJECT", "freelance-income"),
    ("FIVERR INTERNATIONAL FREELANCE EARNINGS", "freelance-income"),
    ("INVOICE SETTLEMENT B2B SOFTWARE CONTRACT", "business-income"),
    ("CLIENT PAYMENT CONSULTING SERVICES INVOICE", "business-income"),
    ("MERCHANT SETTLEMENT RAZORPAY BUSINESS INFLOW", "business-income"),
    ("CLIENT WIRE TRANSFER RETAINER SETTLEMENT", "revenue"),
    ("STRIPE REVENUE PAYOUT ECOMMERCE SALES", "revenue"),
    ("PRODUCT SALES PAYMENT GATEWAY SETTLEMENT", "revenue"),
    ("SAVINGS BANK INTEREST CREDIT QUARTERLY", "interest-income"),
    ("FIXED DEPOSIT INTEREST REINVESTMENT", "interest-income"),
    ("DIVIDEND RECEIVED ITC LIMITED", "dividends"),
    ("TCS INTERIM DIVIDEND DIRECT CREDIT", "dividends"),
    ("REFUND RECEIVED FOR CANCELLED ORDER", "refunds-cashbacks"),
    ("CASHBACK REWARD CREDITED CRED UPI", "refunds-cashbacks"),
    ("AMAZON PAY CASHBACK REWARD CREDIT", "refunds-cashbacks"),

    # Food & Dining
    ("SWIGGY BANGALORE ORDER FOOD ONLINE", "food-delivery"),
    ("ZOMATO LIMITED RESTAURANT ORDER", "food-delivery"),
    ("SWIGGY INSTAMART GROCERIES AND SNACKS", "groceries"),
    ("ZEPTO QUICK COMMERCE 10 MIN GROCERY", "groceries"),
    ("BLINKIT COMMERCE ESSENTIALS MILK FRUITS", "groceries"),
    ("BIGBASKET SUPERMARKET ORDER VEGETABLES", "groceries"),
    ("NATURES BASKET GOURMET SUPERMARKET", "groceries"),
    ("STARBUCKS COFFEE INDIRANAGAR BANGALORE", "cafes"),
    ("BLUE TOKAI COFFEE ROASTERS BANDRA", "cafes"),
    ("THIRD WAVE COFFEE ROASTERS KORAMANGALA", "cafes"),
    ("CAFE COFFEE DAY AIRPORT EXPRESS", "cafes"),
    ("CHAAYOS MASALA CHAI AND SNACKS", "cafes"),
    ("MCDONALDS BURGERS AND MEALS", "restaurants"),
    ("BURGER KING MEALS AND SHAKES", "restaurants"),
    ("KFC FRIED CHICKEN AND BEVERAGES", "restaurants"),
    ("DOMINOS PIZZA JUBILANT FOODWORKS", "restaurants"),
    ("PIZZA HUT DINE IN RESTAURANT", "restaurants"),
    ("BARBEQUE NATION HOSPITALITY DINNER BUFFET", "restaurants"),
    ("MAINLAND CHINA FINE DINING", "restaurants"),
    ("PUNJAB GRILL RESTAURANT LUNCH", "restaurants"),
    ("LOCAL BAKERY SWEETS AND MITHAI", "restaurants"),

    # Transportation & Travel
    ("UBER INDIA RIDES TRIP CHARGES", "ride-hailing"),
    ("UBER TRIP GURGAON TO AIRPORT", "ride-hailing"),
    ("OLA CABS ANI TECHNOLOGIES RIDE", "ride-hailing"),
    ("RAPIDO BIKE TAXI COMMUTE", "ride-hailing"),
    ("IRCTC RAILWAY TICKET BOOKING", "public-transit"),
    ("INDIAN RAILWAYS RESERVATION COUNTER", "public-transit"),
    ("DELHI METRO RAIL SMART CARD RECHARGE", "public-transit"),
    ("NAMMA METRO BANGALORE RECHARGE", "public-transit"),
    ("BEST BUS PASS MUMBAI TRANSIT", "public-transit"),
    ("INDIGO AIRLINES FLIGHT TICKET BOOKING", "flights"),
    ("AIR INDIA DOMESTIC AIRLINE TICKET", "flights"),
    ("SPICEJET AIRLINE WEB CHECKIN TICKET", "flights"),
    ("VISTARA AIRLINE INTERGLOBE FLIGHT", "flights"),
    ("MAKEMYTRIP INDIA HOLIDAYS FLIGHT HOTEL", "flights"),
    ("GOIBIBO TRAVEL HOTEL FLIGHTS", "flights"),
    ("TAJ HOTELS RESORTS AND PALACES", "hotels"),
    ("MARRIOTT INTERNATIONAL HOTEL STAY", "hotels"),
    ("TREEBO HOTELS BUDGET STAY RESERVATION", "hotels"),
    ("OYO ROOMS TRAVEL ACCOMMODATION", "hotels"),
    ("HPCL PETROL PUMP FUEL REFILL", "fuel"),
    ("BPCL FUEL STATION AUTO CARE DIESEL", "fuel"),
    ("INDIAN OIL PETROL PUMP IOCL", "fuel"),
    ("SHELL INDIA PETROL DIESEL V POWER", "fuel"),
    ("FASTAG TOLL PLAZA HIGHWAY DEDUCTION", "tolls-parking"),
    ("NATIONAL HIGHWAY TOLL PLAZA FASTAG", "tolls-parking"),
    ("AIRPORT MULTI LEVEL CAR PARKING", "tolls-parking"),

    # Housing & Utilities
    ("APARTMENT MONTHLY HOUSE RENT OWNER TRANSFER", "rent"),
    ("GATED COMMUNITY MAINTENANCE CHARGES", "rent"),
    ("SECURITY DEPOSIT RENTAL PROPERTY", "rent"),
    ("BESCOM ELECTRICITY BILL ONLINE PAYMENT", "electricity"),
    ("TATA POWER MUMBAI ELECTRIC BILL", "electricity"),
    ("MSEDCL ELECTRICITY BILL PAYMENT", "electricity"),
    ("ADANI ELECTRICITY POWER BILL", "electricity"),
    ("JIO FIBER BROADBAND HIGH SPEED INTERNET", "telecom-internet"),
    ("AIRTEL BROADBAND FIBER BILL", "telecom-internet"),
    ("ACT FIBERNET MONTHLY INTERNET BILL", "telecom-internet"),
    ("JIO PREPAID MOBILE RECHARGE", "telecom-internet"),
    ("AIRTEL POSTPAID MOBILE BILL", "telecom-internet"),
    ("VODAFONE IDEA VI RECHARGE", "telecom-internet"),
    ("INDRAPRASTHA GAS LIMITED IGL PIPED GAS", "water-gas"),
    ("MAHANAGAR GAS LIMITED MGL UTILITY", "water-gas"),
    ("HP GAS REFILL CYLINDER BOOKING", "water-gas"),
    ("BHARAT GAS CYLINDER REFILL PAYMENT", "water-gas"),
    ("MUNICIPAL WATER SUPPLY WATER BILL", "water-gas"),
    ("URBAN COMPANY HOME CLEANING AND REPAIRS", "home-repairs"),
    ("PLUMBER SANITARY HARDWARE REPAIR", "home-repairs"),
    ("ASIAN PAINTS HOME WALL PAINTING", "home-repairs"),

    # Shopping & Lifestyle
    ("AMAZON INDIA RETAIL MARKETPLACE ONLINE", "general-shopping"),
    ("FLIPKART INTERNET ECOMMERCE ORDER", "general-shopping"),
    ("TATA CLIQ LUXURY AND ELECTRONICS", "general-shopping"),
    ("CROMA ELECTRONICS LAPTOP REFRIGERATOR", "electronics"),
    ("RELIANCE DIGITAL MOBILE PHONE GADGET", "electronics"),
    ("VIJAY SALES HOME APPLIANCES TELEVISION", "electronics"),
    ("APPLE STORE RETAIL IPHONE MACBOOK", "electronics"),
    ("SAMSUNG BRAND SMARTPHONE PURCHASE", "electronics"),
    ("MYNTRA FASHION CLOTHING APPAREL", "clothing"),
    ("ZARA RETAIL INDIA APPAREL DRESS", "clothing"),
    ("H&M HNM CLOTHING STORE MALL", "clothing"),
    ("PANTALOONS FASHION RETAIL STORE", "clothing"),
    ("LIFESTYLE INTERNATIONAL CLOTHING", "clothing"),
    ("DECATHLON SPORTS GEAR SHOES JACKET", "general-shopping"),
    ("NIKE RETAIL SHOES AND SPORTSWEAR", "clothing"),
    ("ADIDAS RUNNING SHOES STORE", "clothing"),
    ("NYKAA BEAUTY COSMETICS SKINCARE", "personal-care"),
    ("SEPHORA MAKEUP LUXURY COSMETICS", "personal-care"),
    ("PURPLLE ONLINE BEAUTY COSMETICS", "personal-care"),
    ("IKEA HOME FURNITURE AND WARDROBE", "home-decor"),
    ("PEPPERFRY FURNITURE SOFA BED", "home-decor"),
    ("HOME CENTRE DECOR LAMPS FURNISHING", "home-decor"),

    # Healthcare & Medical
    ("APOLLO PHARMACY MEDICINES PRESCRIPTION", "pharmacy"),
    ("MEDPLUS PHARMACY HEALTH PRODUCTS", "pharmacy"),
    ("TATA 1MG HEALTHCARE MEDICINES DIAGNOSTICS", "pharmacy"),
    ("PHARMEASY ONLINE MEDICINE ORDER", "pharmacy"),
    ("PRACTO DOCTOR CONSULTATION CLINIC", "doctor-consultations"),
    ("DENTAL CLINIC ROOT CANAL TREATMENT", "doctor-consultations"),
    ("EYE CARE CONSULTATION DOCTOR OPHTHALMOLOGY", "doctor-consultations"),
    ("APOLLO HOSPITALS IP INPATIENT BILL", "hospitals"),
    ("FORTIS HEALTHCARE HOSPITAL ADMISSION", "hospitals"),
    ("MAX HEALTHCARE DIAGNOSTIC LAB REPORTS", "hospitals"),
    ("DR LAL PATHLABS BLOOD TEST RADIOLOGY", "hospitals"),
    ("STAR HEALTH INSURANCE ANNUAL PREMIUM", "health-insurance"),
    ("HDFC ERGO HEALTH SURAKSHA POLICY", "health-insurance"),
    ("CARE HEALTH INSURANCE PREMIUM", "health-insurance"),

    # Education & Learning
    ("KIDS INTERNATIONAL SCHOOL TUITION FEES", "tuition-fees"),
    ("DELHI PUBLIC SCHOOL QUARTERLY FEES", "tuition-fees"),
    ("UNIVERSITY TERM SEMESTER EXAM FEES", "tuition-fees"),
    ("COURSERA ANNUAL SUBSCRIPTION ONLINE LEARNING", "courses"),
    ("UDEMY PYTHON DATA SCIENCE CERTIFICATION", "courses"),
    ("LINKEDIN LEARNING PREMIUM EDUCATION", "courses"),
    ("CROSSWORD BOOKSTORE BOOKS AND STATIONERY", "books"),
    ("OXFORD BOOKSTORE NOVELS AND STUDY", "books"),

    # Entertainment & Subscriptions
    ("NETFLIX ENTERTAINMENT MONTHLY OTT SUBSCRIPTION", "streaming-ott"),
    ("SPOTIFY INDIA PREMIUM MUSIC SUBSCRIPTION", "streaming-ott"),
    ("DISNEY PLUS HOTSTAR ANNUAL SUBSCRIPTION", "streaming-ott"),
    ("AMAZON PRIME VIDEO ANNUAL MEMBERSHIP", "streaming-ott"),
    ("YOUTUBE PREMIUM FAMILY PLAN SUBSCRIPTION", "streaming-ott"),
    ("APPLE SERVICES ICLOUD STORAGE SUBSCRIPTION", "streaming-ott"),
    ("BOOKMYSHOW MOVIE TICKET BOOKING PVR", "movies-events"),
    ("PVR CINEMAS MULTIPLEX MOVIE THEATRE", "movies-events"),
    ("INOX LEISURE MULTIPLEX TICKETS", "movies-events"),
    ("SONY PLAYSTATION STORE PS5 GAME", "gaming"),
    ("STEAM GAMES VALVE DIGITAL STORE", "gaming"),
    ("NINTENDO ESHOP DIGITAL VIDEO GAME", "gaming"),

    # Financial Charges & Taxes
    ("HDFC BANK ANNUAL DEBIT CARD CHARGES", "bank-charges"),
    ("SBI SMS ALERT CHARGES QUARTERLY", "bank-charges"),
    ("ATM BALANCE INQUIRY OTHER BANK CHARGE", "bank-charges"),
    ("OVERDRAFT PENALTY FEE ACCOUNT", "bank-charges"),
    ("HOME LOAN MONTHLY EMI DEDUCTION", "loan-interest"),
    ("CAR LOAN EQUATED MONTHLY INSTALLMENT", "loan-interest"),
    ("PERSONAL LOAN REPAYMENT ICICI", "loan-interest"),
    ("INCOME TAX DEPARTMENT ADVANCE TAX SELF ASSESSMENT", "income-tax"),
    ("DIRECT TAXES CHALLAN 280 IT RETURN", "income-tax"),
    ("TAX DEDUCTED AT SOURCE TDS PAYMENT", "income-tax"),
    ("GST PORTAL TAX PAYMENT CHALLAN", "gst-taxes"),
    ("GOODS AND SERVICES TAX GSTIN PAYMENT", "gst-taxes"),
    ("GSTR3B MONTHLY RETURN CHALLAN TAX", "gst-taxes"),

    # Business Operating Expenses
    ("AMAZON WEB SERVICES AWS CLOUD HOSTING", "software-subscriptions"),
    ("GOOGLE CLOUD PLATFORM GCP CLOUD INFRA", "software-subscriptions"),
    ("MICROSOFT AZURE COMPUTE SERVERS", "software-subscriptions"),
    ("DIGITALOCEAN CLOUD VPS HOSTING", "software-subscriptions"),
    ("SLACK TECHNOLOGIES BUSINESS COMMUNICATION", "software-subscriptions"),
    ("GITHUB ENTERPRISE DEVELOPER SEATS", "software-subscriptions"),
    ("ATLASSIAN JIRA CONFLUENCE LICENSES", "software-subscriptions"),
    ("NOTION TEAM WORKSPACE PLAN", "software-subscriptions"),
    ("ZOHO ONE BUSINESS SUITE SUBSCRIPTION", "software-subscriptions"),
    ("RAZORPAY PAYMENT GATEWAY TRANSACTION FEE", "bank-charges"),
    ("OFFICE PRINTER PAPER CARTRIDGES TONER", "office-expenses"),
    ("DESK CHAIRS OFFICE STATIONERY SUPPLIES", "office-expenses"),
    ("GOOGLE ADS ONLINE MARKETING CAMPAIGN", "marketing"),
    ("FACEBOOK ADS META MARKETING PROMOTION", "marketing"),
    ("CHARTERED ACCOUNTANT CA AUDIT FEES", "professional-services"),
    ("LEGAL COUNSEL RETAINER ATTORNEY FEES", "professional-services"),
    ("PAYROLL STAFF SALARY DISBURSEMENT", "employee-salaries"),
    ("EMPLOYEE HEALTH INSURANCE CORPORATE POLICY", "employee-salaries"),
    ("COWORKING SPACE WEWORK DESK LEASE", "rent"),
    ("COMMERCIAL OFFICE UTILITIES CLEANING", "operating-expenses"),
    ("WAREHOUSE LOGISTICS DISPATCH EXPENSES", "operating-expenses"),
    ("FACILITY SECURITY AGENCY MONTHLY INVOICE", "operating-expenses"),
]


class MLTransactionClassifier:
    """
    Supervised machine-learning text classification engine for financial transactions.
    Uses TF-IDF character and word n-grams with calibrated linear classification.
    """

    MODEL_VERSION = "v1.0.0"
    DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models"
    MODEL_FILE = DEFAULT_MODEL_DIR / f"transaction_classifier_{MODEL_VERSION}.joblib"
    METADATA_FILE = DEFAULT_MODEL_DIR / f"transaction_classifier_{MODEL_VERSION}_metadata.json"

    def __init__(self):
        self.pipeline: Optional[Pipeline] = None
        self.classes: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self._load_or_train()

    def _load_or_train(self) -> None:
        """Loads cached model from disk if present; otherwise performs reproducible training."""
        if self.MODEL_FILE.exists() and self.METADATA_FILE.exists():
            try:
                self.pipeline = joblib.load(self.MODEL_FILE)
                with open(self.METADATA_FILE, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                self.classes = list(self.pipeline.classes_)
                return
            except Exception:
                # Re-train on corruption or incompatibility
                pass

        self.train_and_evaluate(persist=True)

    def is_trained(self) -> bool:
        """Returns True if the ML model pipeline is loaded and ready for inference."""
        return self.pipeline is not None

    def train_and_evaluate(self, persist: bool = True) -> Dict[str, Any]:
        """
        Executes stratified train-test split, trains pipeline, evaluates metrics, and saves artifact.
        """
        X = [item[0] for item in DATASET]
        y = [item[1] for item in DATASET]

        # Stratified Split with safety fallback
        n_classes = len(set(y))
        test_size = max(0.25, (n_classes + 1) / len(y))
        test_size = min(0.35, test_size)
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
        except Exception:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.20, random_state=42
            )

        # Scikit-learn Pipeline
        # Uses word and char_wb n-grams for typo-resilient subword representations
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 3),
                analyzer="char_wb",
                min_df=1,
                sublinear_tf=True,
            )),
            ("clf", LogisticRegression(
                C=2.0,
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            )),
        ])

        pipeline.fit(X_train, y_train)
        self.pipeline = pipeline
        self.classes = list(pipeline.classes_)

        # Evaluation on held-out test split
        y_pred = pipeline.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))
        macro_prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        macro_rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
        weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

        # Majority class baseline
        majority_class = max(set(y_test), key=y_test.count)
        baseline_acc = float(y_test.count(majority_class) / len(y_test))

        eval_metadata = {
            "model_version": self.MODEL_VERSION,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "total_examples": len(DATASET),
            "train_examples": len(X_train),
            "test_examples": len(X_test),
            "classes_count": len(self.classes),
            "classes": self.classes,
            "metrics": {
                "accuracy": round(acc, 4),
                "majority_baseline_accuracy": round(baseline_acc, 4),
                "macro_precision": round(macro_prec, 4),
                "macro_recall": round(macro_rec, 4),
                "macro_f1": round(macro_f1, 4),
                "weighted_f1": round(weighted_f1, 4),
            },
            "configuration": {
                "vectorizer": "TfidfVectorizer(char_wb, ngrams 1-3, sublinear_tf)",
                "classifier": "LogisticRegression(C=2.0, class_weight='balanced', random_state=42)",
            },
        }

        self.metadata = eval_metadata

        if persist:
            self.DEFAULT_MODEL_DIR.mkdir(parents=True, exist_ok=True)
            joblib.dump(self.pipeline, self.MODEL_FILE)
            with open(self.METADATA_FILE, "w", encoding="utf-8") as f:
                json.dump(eval_metadata, f, indent=2)

        return eval_metadata

    def predict(self, description: str) -> MLPredictionResult:
        """
        Classifies normalized description string, yielding top category, confidence score,
        confidence band, and transparent explanation.
        """
        if not self.pipeline:
            self._load_or_train()

        clean_text = (description or "").strip()
        if not clean_text or len(clean_text) < 2:
            return MLPredictionResult(
                predicted_category_slug="general-shopping",
                confidence_score=0.2000,
                confidence_band=ConfidenceBand.UNKNOWN.value,
                explanation="Description is too brief to classify confidently.",
                model_version=self.MODEL_VERSION,
                probabilities={},
            )

        # Predict Probabilities
        probs = self.pipeline.predict_proba([clean_text])[0]
        max_idx = int(np.argmax(probs))
        top_prob = float(probs[max_idx])
        top_category = self.classes[max_idx]

        # Top 3 probability dictionary
        top_indices = np.argsort(probs)[::-1][:3]
        prob_dict = {self.classes[i]: round(float(probs[i]), 4) for i in top_indices}

        # Determine Confidence Band
        if top_prob >= 0.85:
            band = ConfidenceBand.HIGH.value
        elif top_prob >= 0.60:
            band = ConfidenceBand.MEDIUM.value
        elif top_prob >= 0.40:
            band = ConfidenceBand.LOW.value
        else:
            band = ConfidenceBand.UNKNOWN.value

        conf_pct = round(top_prob * 100, 1)
        human_readable_cat = top_category.replace("-", " ").title()
        explanation = f"ML model predicted '{human_readable_cat}' with {conf_pct}% confidence based on text patterns."

        return MLPredictionResult(
            predicted_category_slug=top_category,
            confidence_score=round(top_prob, 4),
            confidence_band=band,
            explanation=explanation,
            model_version=self.MODEL_VERSION,
            probabilities=prob_dict,
        )


# Global singleton instance
ml_classifier = MLTransactionClassifier()
