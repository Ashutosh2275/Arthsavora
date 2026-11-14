"""
Arthsavora Category Taxonomy & Intelligence Constants
Authoritative classification hierarchy for Personal, Family, and Business domains,
merchant definitions, confidence scoring bands, and Indian fintech aliases.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    SYSTEM = "system"


class CategoryStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConfidenceBand(str, Enum):
    HIGH = "high"        # >= 0.85
    MEDIUM = "medium"    # 0.60 - 0.84
    LOW = "low"          # 0.40 - 0.59
    UNKNOWN = "unknown"  # < 0.40


class ClassificationMethod(str, Enum):
    SYSTEM_RULE = "system_rule"
    USER_RULE = "user_rule"
    MERCHANT_ALIAS = "merchant_alias"
    ML_MODEL = "ml_model"
    MANUAL = "manual"


class FeedbackAction(str, Enum):
    ACCEPT = "accept"
    CORRECT_CATEGORY = "correct_category"
    CORRECT_MERCHANT = "correct_merchant"
    MARK_UNKNOWN = "mark_unknown"
    CREATE_RULE = "create_rule"


class RuleScope(str, Enum):
    SYSTEM = "system"
    WORKSPACE = "workspace"
    USER = "user"


# ===========================================================================
# Standard Hierarchical Category Taxonomy for India
# ===========================================================================

SYSTEM_CATEGORIES: List[Dict[str, Any]] = [
    # -----------------------------------------------------------------------
    # INCOME TAXONOMY
    # -----------------------------------------------------------------------
    {
        "name": "Income",
        "slug": "income",
        "category_type": CategoryType.INCOME.value,
        "workspace_type": "all",
        "icon": "wallet",
        "color": "#10B981",
        "display_order": 100,
        "subcategories": [
            {"name": "Salary", "slug": "salary", "workspace_type": "all", "display_order": 101},
            {"name": "Freelance Income", "slug": "freelance-income", "workspace_type": "all", "display_order": 102},
            {"name": "Business Income", "slug": "business-income", "workspace_type": "business", "display_order": 103},
            {"name": "Revenue", "slug": "revenue", "workspace_type": "business", "display_order": 104},
            {"name": "Interest Income", "slug": "interest-income", "workspace_type": "all", "display_order": 105},
            {"name": "Refunds & Cashbacks", "slug": "refunds-cashbacks", "workspace_type": "all", "display_order": 106},
            {"name": "Investments & Dividends", "slug": "dividends", "workspace_type": "all", "display_order": 107},
            {"name": "Other Income", "slug": "other-income", "workspace_type": "all", "display_order": 108},
        ],
    },

    # -----------------------------------------------------------------------
    # PERSONAL & FAMILY EXPENSES
    # -----------------------------------------------------------------------
    {
        "name": "Food & Dining",
        "slug": "food-dining",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "all",
        "icon": "utensils",
        "color": "#F59E0B",
        "display_order": 200,
        "subcategories": [
            {"name": "Restaurants & Dining", "slug": "restaurants", "workspace_type": "all", "display_order": 201},
            {"name": "Food Delivery", "slug": "food-delivery", "workspace_type": "all", "display_order": 202},
            {"name": "Groceries & Supermarkets", "slug": "groceries", "workspace_type": "all", "display_order": 203},
            {"name": "Cafes & Coffee", "slug": "cafes", "workspace_type": "all", "display_order": 204},
        ],
    },
    {
        "name": "Transportation & Travel",
        "slug": "transportation",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "all",
        "icon": "car",
        "color": "#3B82F6",
        "display_order": 300,
        "subcategories": [
            {"name": "Fuel & Petrol", "slug": "fuel", "workspace_type": "all", "display_order": 301},
            {"name": "Ride Hailing & Cabs", "slug": "ride-hailing", "workspace_type": "all", "display_order": 302},
            {"name": "Public Transit & Rail", "slug": "public-transit", "workspace_type": "all", "display_order": 303},
            {"name": "Flights & Air Travel", "slug": "flights", "workspace_type": "all", "display_order": 304},
            {"name": "Hotels & Lodging", "slug": "hotels", "workspace_type": "all", "display_order": 305},
            {"name": "Tolls & Parking", "slug": "tolls-parking", "workspace_type": "all", "display_order": 306},
        ],
    },
    {
        "name": "Housing & Utilities",
        "slug": "housing-utilities",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "all",
        "icon": "home",
        "color": "#8B5CF6",
        "display_order": 400,
        "subcategories": [
            {"name": "Rent & Maintenance", "slug": "rent", "workspace_type": "all", "display_order": 401},
            {"name": "Electricity & Power", "slug": "electricity", "workspace_type": "all", "display_order": 402},
            {"name": "Mobile & Internet", "slug": "telecom-internet", "workspace_type": "all", "display_order": 403},
            {"name": "Water & Gas", "slug": "water-gas", "workspace_type": "all", "display_order": 404},
            {"name": "Household Supplies", "slug": "household-supplies", "workspace_type": "family", "display_order": 405},
            {"name": "Home Repairs & Improvement", "slug": "home-repairs", "workspace_type": "all", "display_order": 406},
        ],
    },
    {
        "name": "Shopping & Lifestyle",
        "slug": "shopping",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "all",
        "icon": "shopping-bag",
        "color": "#EC4899",
        "display_order": 500,
        "subcategories": [
            {"name": "Electronics & Gadgets", "slug": "electronics", "workspace_type": "all", "display_order": 501},
            {"name": "Clothing & Apparel", "slug": "clothing", "workspace_type": "all", "display_order": 502},
            {"name": "Beauty & Personal Care", "slug": "personal-care", "workspace_type": "all", "display_order": 503},
            {"name": "Home Decor & Furnishing", "slug": "home-decor", "workspace_type": "all", "display_order": 504},
            {"name": "General Shopping", "slug": "general-shopping", "workspace_type": "all", "display_order": 505},
        ],
    },
    {
        "name": "Healthcare & Medical",
        "slug": "healthcare",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "all",
        "icon": "activity",
        "color": "#EF4444",
        "display_order": 600,
        "subcategories": [
            {"name": "Pharmacies & Medicines", "slug": "pharmacy", "workspace_type": "all", "display_order": 601},
            {"name": "Doctor Consultations", "slug": "doctor-consultations", "workspace_type": "all", "display_order": 602},
            {"name": "Hospitals & Diagnostics", "slug": "hospitals", "workspace_type": "all", "display_order": 603},
            {"name": "Health Insurance", "slug": "health-insurance", "workspace_type": "all", "display_order": 604},
        ],
    },
    {
        "name": "Education & Learning",
        "slug": "education",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "all",
        "icon": "book-open",
        "color": "#06B6D4",
        "display_order": 700,
        "subcategories": [
            {"name": "Tuition & School Fees", "slug": "tuition-fees", "workspace_type": "all", "display_order": 701},
            {"name": "Courses & Certifications", "slug": "courses", "workspace_type": "all", "display_order": 702},
            {"name": "Books & Study Material", "slug": "books", "workspace_type": "all", "display_order": 703},
        ],
    },
    {
        "name": "Entertainment & Subscriptions",
        "slug": "entertainment",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "all",
        "icon": "film",
        "color": "#6366F1",
        "display_order": 800,
        "subcategories": [
            {"name": "Streaming & OTT Services", "slug": "streaming-ott", "workspace_type": "all", "display_order": 801},
            {"name": "Movies & Events", "slug": "movies-events", "workspace_type": "all", "display_order": 802},
            {"name": "Gaming & Hobbies", "slug": "gaming", "workspace_type": "all", "display_order": 803},
            {"name": "Digital Subscriptions", "slug": "digital-subscriptions", "workspace_type": "all", "display_order": 804},
        ],
    },
    {
        "name": "Financial Charges & Taxes",
        "slug": "financial-charges-taxes",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "all",
        "icon": "percent",
        "color": "#64748B",
        "display_order": 900,
        "subcategories": [
            {"name": "Bank Charges & Fees", "slug": "bank-charges", "workspace_type": "all", "display_order": 901},
            {"name": "Loan Interest & EMI", "slug": "loan-interest", "workspace_type": "all", "display_order": 902},
            {"name": "Income Tax & Advance Tax", "slug": "income-tax", "workspace_type": "all", "display_order": 903},
            {"name": "GST & Statutory Dues", "slug": "gst-taxes", "workspace_type": "business", "display_order": 904},
        ],
    },

    # -----------------------------------------------------------------------
    # BUSINESS-SPECIFIC OPERATING EXPENSES
    # -----------------------------------------------------------------------
    {
        "name": "Business Operations",
        "slug": "business-operations",
        "category_type": CategoryType.EXPENSE.value,
        "workspace_type": "business",
        "icon": "briefcase",
        "color": "#0EA5E9",
        "display_order": 1000,
        "subcategories": [
            {"name": "Software & Cloud Subscriptions", "slug": "software-subscriptions", "workspace_type": "business", "display_order": 1001},
            {"name": "Office Supplies & Equipment", "slug": "office-expenses", "workspace_type": "business", "display_order": 1002},
            {"name": "Marketing & Advertising", "slug": "marketing", "workspace_type": "business", "display_order": 1003},
            {"name": "Professional & Legal Services", "slug": "professional-services", "workspace_type": "business", "display_order": 1004},
            {"name": "Employee Salaries & Benefits", "slug": "employee-salaries", "workspace_type": "business", "display_order": 1005},
            {"name": "Contractor & Freelancer Fees", "slug": "contractor-fees", "workspace_type": "business", "display_order": 1006},
            {"name": "Operating Expenses", "slug": "operating-expenses", "workspace_type": "business", "display_order": 1007},
        ],
    },

    # -----------------------------------------------------------------------
    # TRANSFERS & SYSTEM ADJUSTMENTS
    # -----------------------------------------------------------------------
    {
        "name": "Transfers & Adjustments",
        "slug": "transfers-adjustments",
        "category_type": CategoryType.TRANSFER.value,
        "workspace_type": "all",
        "icon": "arrow-left-right",
        "color": "#94A3B8",
        "display_order": 1100,
        "subcategories": [
            {"name": "Internal Account Transfer", "slug": "internal-transfer", "workspace_type": "all", "display_order": 1101},
            {"name": "Credit Card Payment", "slug": "credit-card-bill-payment", "workspace_type": "all", "display_order": 1102},
            {"name": "Investment Transfer", "slug": "investment-transfer", "workspace_type": "all", "display_order": 1103},
            {"name": "Opening Balance Offset", "slug": "opening-balance-offset", "workspace_type": "all", "display_order": 1104},
        ],
    },
]


# ===========================================================================
# Canonical Indian Merchants & Aliases
# ===========================================================================

SYSTEM_MERCHANTS: List[Dict[str, Any]] = [
    # Food & Grocery
    {
        "canonical_name": "Swiggy",
        "slug": "swiggy",
        "merchant_type": "food_delivery",
        "default_category_slug": "food-delivery",
        "aliases": ["SWIGGY", "SWIGGY BANGALORE", "BUNDL TECHNOLOGIES", "SWIGGY INSTAMART", "SWIGGY-PAY"],
    },
    {
        "canonical_name": "Zomato",
        "slug": "zomato",
        "merchant_type": "food_delivery",
        "default_category_slug": "food-delivery",
        "aliases": ["ZOMATO", "ZOMATO LIMITED", "ZOMATO RESTAURANT", "ZOMATO ONLINE"],
    },
    {
        "canonical_name": "Blinkit",
        "slug": "blinkit",
        "merchant_type": "grocery",
        "default_category_slug": "groceries",
        "aliases": ["BLINKIT", "GROFERS", "BLINK COMMERCE"],
    },
    {
        "canonical_name": "Zepto",
        "slug": "zepto",
        "merchant_type": "grocery",
        "default_category_slug": "groceries",
        "aliases": ["ZEPTO", "KIRANAKART", "ZEPTO QUICK"],
    },
    {
        "canonical_name": "BigBasket",
        "slug": "bigbasket",
        "merchant_type": "grocery",
        "default_category_slug": "groceries",
        "aliases": ["BIGBASKET", "SUPERMARKET GROCERY", "BB DAILY", "BIG BASKET"],
    },
    {
        "canonical_name": "Starbucks",
        "slug": "starbucks",
        "merchant_type": "cafe",
        "default_category_slug": "cafes",
        "aliases": ["STARBUCKS", "TATA STARBUCKS", "STARBUCKS COFFEE"],
    },
    {
        "canonical_name": "McDonald's",
        "slug": "mcdonalds",
        "merchant_type": "restaurant",
        "default_category_slug": "restaurants",
        "aliases": ["MCDONALDS", "HARDCASTLE RESTAURANTS", "CONNAUGHT PLAZA REST"],
    },
    {
        "canonical_name": "Domino's Pizza",
        "slug": "dominos",
        "merchant_type": "restaurant",
        "default_category_slug": "restaurants",
        "aliases": ["DOMINOS", "DOMINOS PIZZA", "JUBILANT FOODWORKS"],
    },

    # Transportation & Travel
    {
        "canonical_name": "Uber",
        "slug": "uber",
        "merchant_type": "ride_hailing",
        "default_category_slug": "ride-hailing",
        "aliases": ["UBER", "UBER INDIA", "UBER TRIP", "UBER BV"],
    },
    {
        "canonical_name": "Ola Cabs",
        "slug": "ola",
        "merchant_type": "ride_hailing",
        "default_category_slug": "ride-hailing",
        "aliases": ["OLA", "ANI TECHNOLOGIES", "OLA RIDES", "OLA MONEY"],
    },
    {
        "canonical_name": "Rapido",
        "slug": "rapido",
        "merchant_type": "ride_hailing",
        "default_category_slug": "ride-hailing",
        "aliases": ["RAPIDO", "ROPPEN TRANSPORTATION", "RAPIDO BIKE"],
    },
    {
        "canonical_name": "IRCTC",
        "slug": "irctc",
        "merchant_type": "railway",
        "default_category_slug": "public-transit",
        "aliases": ["IRCTC", "INDIAN RAILWAYS", "IRCTC TICKETING", "IRCTC TOURISM"],
    },
    {
        "canonical_name": "MakeMyTrip",
        "slug": "makemytrip",
        "merchant_type": "travel",
        "default_category_slug": "flights",
        "aliases": ["MAKEMYTRIP", "MMT", "MAKEMYTRIP INDIA"],
    },
    {
        "canonical_name": "IndiGo Airlines",
        "slug": "indigo",
        "merchant_type": "airline",
        "default_category_slug": "flights",
        "aliases": ["INDIGO", "INTERGLOBE AVIATION", "GOINDIGO"],
    },
    {
        "canonical_name": "Hindustan Petroleum (HPCL)",
        "slug": "hpcl",
        "merchant_type": "fuel",
        "default_category_slug": "fuel",
        "aliases": ["HPCL", "HINDUSTAN PETROLEUM", "HP AUTO CARE", "HP PETROL"],
    },
    {
        "canonical_name": "Bharat Petroleum (BPCL)",
        "slug": "bpcl",
        "merchant_type": "fuel",
        "default_category_slug": "fuel",
        "aliases": ["BPCL", "BHARAT PETROLEUM", "BPCL PETROL", "GHAR OUTLET"],
    },
    {
        "canonical_name": "Indian Oil (IOCL)",
        "slug": "iocl",
        "merchant_type": "fuel",
        "default_category_slug": "fuel",
        "aliases": ["IOCL", "INDIAN OIL", "INDIANOIL CORP", "XP95 PETROL"],
    },

    # Shopping & E-Commerce
    {
        "canonical_name": "Amazon India",
        "slug": "amazon",
        "merchant_type": "e_commerce",
        "default_category_slug": "general-shopping",
        "aliases": ["AMAZON", "AMZN MKTP", "AMAZON PAY", "AMAZON SELLER", "AMAZON RETAIL"],
    },
    {
        "canonical_name": "Flipkart",
        "slug": "flipkart",
        "merchant_type": "e_commerce",
        "default_category_slug": "general-shopping",
        "aliases": ["FLIPKART", "FLIPKART INTERNET", "FKMP"],
    },
    {
        "canonical_name": "Myntra",
        "slug": "myntra",
        "merchant_type": "fashion",
        "default_category_slug": "clothing",
        "aliases": ["MYNTRA", "MYNTRA DESIGNS"],
    },
    {
        "canonical_name": "Nykaa",
        "slug": "nykaa",
        "merchant_type": "beauty",
        "default_category_slug": "personal-care",
        "aliases": ["NYKAA", "FSN E-COMMERCE", "NYKAA FASHION"],
    },
    {
        "canonical_name": "Croma",
        "slug": "croma",
        "merchant_type": "electronics",
        "default_category_slug": "electronics",
        "aliases": ["CROMA", "INFINITI RETAIL", "CROMA ELECTRONICS"],
    },
    {
        "canonical_name": "Reliance Digital",
        "slug": "reliance-digital",
        "merchant_type": "electronics",
        "default_category_slug": "electronics",
        "aliases": ["RELIANCE DIGITAL", "RELIANCE RETAIL"],
    },
    {
        "canonical_name": "Decathlon",
        "slug": "decathlon",
        "merchant_type": "sports",
        "default_category_slug": "general-shopping",
        "aliases": ["DECATHLON", "DECATHLON SPORTS"],
    },

    # Utilities & Telecom
    {
        "canonical_name": "Jio",
        "slug": "jio",
        "merchant_type": "telecom",
        "default_category_slug": "telecom-internet",
        "aliases": ["JIO", "RELIANCE JIO", "JIO RECHARGE", "JIO FIBER"],
    },
    {
        "canonical_name": "Airtel",
        "slug": "airtel",
        "merchant_type": "telecom",
        "default_category_slug": "telecom-internet",
        "aliases": ["AIRTEL", "BHARTI AIRTEL", "AIRTEL BROADBAND", "AIRTEL POSTPAID"],
    },
    {
        "canonical_name": "BESCOM",
        "slug": "bescom",
        "merchant_type": "utility",
        "default_category_slug": "electricity",
        "aliases": ["BESCOM", "BANGALORE ELECTRICITY", "BESCOM POWER"],
    },
    {
        "canonical_name": "Tata Power",
        "slug": "tata-power",
        "merchant_type": "utility",
        "default_category_slug": "electricity",
        "aliases": ["TATA POWER", "TPDDL", "TATA POWER DDL"],
    },
    {
        "canonical_name": "Indraprastha Gas (IGL)",
        "slug": "igl",
        "merchant_type": "utility",
        "default_category_slug": "water-gas",
        "aliases": ["IGL", "INDRAPRASTHA GAS", "IGL GAS"],
    },

    # Entertainment & Streaming
    {
        "canonical_name": "Netflix",
        "slug": "netflix",
        "merchant_type": "streaming",
        "default_category_slug": "streaming-ott",
        "aliases": ["NETFLIX", "NETFLIX ENTERTAINMENT", "NETFLIX INDIA"],
    },
    {
        "canonical_name": "Spotify",
        "slug": "spotify",
        "merchant_type": "streaming",
        "default_category_slug": "streaming-ott",
        "aliases": ["SPOTIFY", "SPOTIFY INDIA", "SPOTIFY AB"],
    },
    {
        "canonical_name": "Disney+ Hotstar",
        "slug": "disney-hotstar",
        "merchant_type": "streaming",
        "default_category_slug": "streaming-ott",
        "aliases": ["HOTSTAR", "DISNEY HOTSTAR", "NOVI DIGITAL"],
    },
    {
        "canonical_name": "BookMyShow",
        "slug": "bookmyshow",
        "merchant_type": "entertainment",
        "default_category_slug": "movies-events",
        "aliases": ["BOOKMYSHOW", "BIGTREE ENTERTAINMENT", "BMS"],
    },
    {
        "canonical_name": "PVR Inox",
        "slug": "pvr-inox",
        "merchant_type": "cinema",
        "default_category_slug": "movies-events",
        "aliases": ["PVR", "PVR CINEMAS", "INOX", "PVR INOX LIMITED"],
    },

    # Healthcare & Pharmacy
    {
        "canonical_name": "Apollo Pharmacy",
        "slug": "apollo-pharmacy",
        "merchant_type": "pharmacy",
        "default_category_slug": "pharmacy",
        "aliases": ["APOLLO PHARMACY", "APOLLO HOSPITALS", "APOLLO 247"],
    },
    {
        "canonical_name": "Tata 1mg",
        "slug": "tata-1mg",
        "merchant_type": "pharmacy",
        "default_category_slug": "pharmacy",
        "aliases": ["1MG", "TATA 1MG", "1MG TECHNOLOGIES"],
    },

    # Business & Cloud
    {
        "canonical_name": "Amazon Web Services (AWS)",
        "slug": "aws",
        "merchant_type": "cloud_provider",
        "default_category_slug": "software-subscriptions",
        "aliases": ["AWS", "AMAZON WEB SERVICES", "AWS CLOUD"],
    },
    {
        "canonical_name": "Google Cloud",
        "slug": "google-cloud",
        "merchant_type": "cloud_provider",
        "default_category_slug": "software-subscriptions",
        "aliases": ["GOOGLE CLOUD", "GOOGLE WORKSPACE", "GOOGLE APPS"],
    },
    {
        "canonical_name": "GitHub",
        "slug": "github",
        "merchant_type": "software_tool",
        "default_category_slug": "software-subscriptions",
        "aliases": ["GITHUB", "GITHUB INC"],
    },
    {
        "canonical_name": "Atlassian",
        "slug": "atlassian",
        "merchant_type": "software_tool",
        "default_category_slug": "software-subscriptions",
        "aliases": ["ATLASSIAN", "JIRA", "CONFLUENCE"],
    },
    {
        "canonical_name": "Notion",
        "slug": "notion",
        "merchant_type": "software_tool",
        "default_category_slug": "software-subscriptions",
        "aliases": ["NOTION", "NOTION LABS"],
    },
    {
        "canonical_name": "Zoho",
        "slug": "zoho",
        "merchant_type": "software_tool",
        "default_category_slug": "software-subscriptions",
        "aliases": ["ZOHO", "ZOHO CORPORATION"],
    },
]
