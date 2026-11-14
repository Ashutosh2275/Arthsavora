"""
Arthsavora Double-Entry Accounting Domain Types & Standard Chart of Accounts
Defines fundamental classifications, normal balances, lifecycle statuses, and template schemas.
"""

from enum import Enum
from typing import NamedTuple


class AccountType(str, Enum):
    """The five major accounting classifications."""
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class NormalBalance(str, Enum):
    """Normal balance side for general ledger accounts."""
    DEBIT = "debit"
    CREDIT = "credit"


class JournalStatus(str, Enum):
    """Lifecycle status of a double-entry journal entry."""
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"


class JournalSourceType(str, Enum):
    """Origin of a journal entry."""
    TRANSACTION = "transaction"
    MANUAL = "manual"
    REVERSAL = "reversal"
    SYSTEM = "system"
    OPENING_BALANCE = "opening_balance"


class PeriodStatus(str, Enum):
    """Status of an accounting fiscal period."""
    OPEN = "open"
    CLOSED = "closed"


# Default normal balance per account type
NORMAL_BALANCE_MAP: dict[AccountType, NormalBalance] = {
    AccountType.ASSET: NormalBalance.DEBIT,
    AccountType.EXPENSE: NormalBalance.DEBIT,
    AccountType.LIABILITY: NormalBalance.CREDIT,
    AccountType.EQUITY: NormalBalance.CREDIT,
    AccountType.REVENUE: NormalBalance.CREDIT,
}


class TemplateAccount(NamedTuple):
    code: str
    name: str
    account_type: AccountType
    normal_balance: NormalBalance
    sub_type: str | None = None
    is_system: bool = False
    description: str | None = None
    parent_code: str | None = None


# Comprehensive Standard Indian FinTech Chart of Accounts Template
DEFAULT_CHART_OF_ACCOUNTS: list[TemplateAccount] = [
    # --- ASSETS (1000s) ---
    TemplateAccount("1000", "Current Assets", AccountType.ASSET, NormalBalance.DEBIT, "header", True, "Liquid and short-term assets"),
    TemplateAccount("1010", "Cash on Hand", AccountType.ASSET, NormalBalance.DEBIT, "cash", True, "Physical currency and petty cash", "1000"),
    TemplateAccount("1011", "Petty Cash", AccountType.ASSET, NormalBalance.DEBIT, "cash", False, "Office and daily petty cash", "1010"),
    TemplateAccount("1020", "Bank Accounts", AccountType.ASSET, NormalBalance.DEBIT, "bank", True, "Operating and savings bank deposits", "1000"),
    TemplateAccount("1021", "Primary Operating Bank Account", AccountType.ASSET, NormalBalance.DEBIT, "bank", True, "Primary operating bank account", "1020"),
    TemplateAccount("1022", "Secondary / Savings Account", AccountType.ASSET, NormalBalance.DEBIT, "bank", False, "Reserve or secondary savings bank account", "1020"),
    TemplateAccount("1030", "Digital Wallets & UPI", AccountType.ASSET, NormalBalance.DEBIT, "digital_wallet", False, "Stored-value digital wallets and prepaid instruments", "1000"),
    TemplateAccount("1040", "Accounts Receivable", AccountType.ASSET, NormalBalance.DEBIT, "receivables", False, "Monies owed by customers or debtors", "1000"),
    TemplateAccount("1500", "Investments & Fixed Deposits", AccountType.ASSET, NormalBalance.DEBIT, "investment", False, "Long term capital assets and mutual fund deposits"),
    TemplateAccount("1510", "Mutual Funds & Equities", AccountType.ASSET, NormalBalance.DEBIT, "investment", False, "Securities and market investments", "1500"),
    TemplateAccount("1520", "Fixed Deposits (FD & RD)", AccountType.ASSET, NormalBalance.DEBIT, "investment", False, "Term bank deposits and recurring deposits", "1500"),

    # --- LIABILITIES (2000s) ---
    TemplateAccount("2000", "Current Liabilities", AccountType.LIABILITY, NormalBalance.CREDIT, "header", True, "Short-term obligations due within one year"),
    TemplateAccount("2010", "Credit Card Payable", AccountType.LIABILITY, NormalBalance.CREDIT, "credit_card", True, "Outstanding revolving credit card debt", "2000"),
    TemplateAccount("2020", "Accounts Payable", AccountType.LIABILITY, NormalBalance.CREDIT, "payables", False, "Short-term liabilities owed to suppliers or vendors", "2000"),
    TemplateAccount("2030", "Short-Term Borrowings", AccountType.LIABILITY, NormalBalance.CREDIT, "loan", False, "Overdraft and short-term lines of credit", "2000"),
    TemplateAccount("2040", "Statutory Dues & Taxes Payable", AccountType.LIABILITY, NormalBalance.CREDIT, "tax_payable", False, "GST, TDS, and statutory obligations payable", "2000"),
    TemplateAccount("2500", "Long-Term Liabilities", AccountType.LIABILITY, NormalBalance.CREDIT, "loan", False, "Term loans and long-term financing debts"),
    TemplateAccount("2510", "Term Loans & Mortgages Payable", AccountType.LIABILITY, NormalBalance.CREDIT, "loan", False, "Principal outstanding on term loans", "2500"),

    # --- EQUITY (3000s) ---
    TemplateAccount("3000", "Equity & Capital", AccountType.EQUITY, NormalBalance.CREDIT, "header", True, "Net worth and owner interest"),
    TemplateAccount("3010", "Owner's Capital", AccountType.EQUITY, NormalBalance.CREDIT, "equity", False, "Initial capital invested by workspace owners", "3000"),
    TemplateAccount("3020", "Retained Earnings", AccountType.EQUITY, NormalBalance.CREDIT, "retained_earnings", True, "Cumulative historical net profit retained", "3000"),
    TemplateAccount("3030", "Opening Balance Equity", AccountType.EQUITY, NormalBalance.CREDIT, "opening_balance_equity", True, "Clearing account for historical opening balances", "3000"),

    # --- REVENUE / INCOME (4000s) ---
    TemplateAccount("4000", "Operating Revenue", AccountType.REVENUE, NormalBalance.CREDIT, "header", False, "Primary earnings from operations"),
    TemplateAccount("4010", "Salary & Wages Income", AccountType.REVENUE, NormalBalance.CREDIT, "income", False, "Regular employment remuneration", "4000"),
    TemplateAccount("4020", "Business & Professional Revenue", AccountType.REVENUE, NormalBalance.CREDIT, "income", False, "Commercial sales and client billing", "4000"),
    TemplateAccount("4030", "Consulting & Freelance Fees", AccountType.REVENUE, NormalBalance.CREDIT, "income", False, "Contractual project earnings", "4000"),
    TemplateAccount("4500", "Other Income", AccountType.REVENUE, NormalBalance.CREDIT, "header", False, "Secondary and non-operating revenue"),
    TemplateAccount("4510", "Interest Income", AccountType.REVENUE, NormalBalance.CREDIT, "income", False, "Bank savings and fixed deposit interest", "4500"),
    TemplateAccount("4520", "Dividend Income", AccountType.REVENUE, NormalBalance.CREDIT, "income", False, "Equities and fund dividend payouts", "4500"),
    TemplateAccount("4530", "Cashback & Rewards", AccountType.REVENUE, NormalBalance.CREDIT, "income", False, "Credit card and UPI reward credits", "4500"),

    # --- EXPENSES (5000s) ---
    TemplateAccount("5000", "Operating & Living Expenses", AccountType.EXPENSE, NormalBalance.DEBIT, "header", False, "Core recurring operational costs"),
    TemplateAccount("5010", "Housing & Rent", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Lease rent and residential maintenance", "5000"),
    TemplateAccount("5020", "Groceries & Food", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Supermarket provisions and household food", "5000"),
    TemplateAccount("5030", "Utilities & Internet", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Electricity, water, mobile and broadband", "5000"),
    TemplateAccount("5040", "Transport & Fuel", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Vehicle fuel, rideshare, and transit fares", "5000"),
    TemplateAccount("5050", "Healthcare & Medical", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Doctor consultations, medicines, and insurance", "5000"),
    TemplateAccount("5060", "Office Supplies & Admin", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Stationery, postage, and administrative costs", "5000"),
    TemplateAccount("5070", "Software & Cloud Subscriptions", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "SaaS platforms and web hosting services", "5000"),
    TemplateAccount("5080", "Bank Charges & Merchant Fees", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Banking transaction fees, AMC, and gateway cuts", "5000"),
    TemplateAccount("5090", "Loan Interest Expense", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Financing charges and EMI interest portions", "5000"),
    TemplateAccount("5100", "Taxes & Statutory Fees", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "Direct income tax, advance tax, and professional fees", "5000"),
    TemplateAccount("5990", "Miscellaneous Expenses", AccountType.EXPENSE, NormalBalance.DEBIT, "expense", False, "General unclassified expenditures", "5000"),
]


# Default financial account type to ledger account code mapping
ACCOUNT_TYPE_TO_LEDGER_CODE: dict[str, str] = {
    "cash": "1010",
    "petty_cash": "1011",
    "savings": "1021",
    "salary": "1021",
    "current": "1021",
    "business_bank": "1021",
    "business_current": "1021",
    "digital_wallet": "1030",
    "credit_card": "2010",
    "business_credit_card": "2010",
    "loan": "2510",
    "loan_account": "2510",
    "investment": "1510",
    "fixed_deposit": "1520",
    "recurring_deposit": "1520",
}
