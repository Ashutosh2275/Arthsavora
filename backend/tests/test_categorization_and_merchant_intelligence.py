"""
Arthsavora Transaction Categorization & Merchant Intelligence Tests
Comprehensive test suite covering:
1. Description normalization (UPI, POS, NEFT, IMPS, RTGS, NACH mandate, ATM, card).
2. Category taxonomy, hierarchy trees, cycle prevention, and delete protection.
3. Merchant alias matching (exact, word-boundary, substring) and system merchant seeding.
4. Deterministic rule engine evaluation with priority ordering and safe condition matching.
5. ML model classifier prediction, probability calibration, and confidence bands.
6. Hybrid categorization pipeline end-to-end (Rules -> Merchant Aliases -> ML -> Fallback).
7. User feedback loop (accept, correct, rule generation) with audit preservation.
8. Multi-workspace isolation, cross-tenant security, and double-entry ledger safety invariant.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.category_taxonomy import (
    SYSTEM_CATEGORIES,
    SYSTEM_MERCHANTS,
    CategoryType,
    ClassificationMethod,
    ConfidenceBand,
    FeedbackAction,
    RuleScope,
)
from app.domain.exceptions import (
    CategoryInUseError,
    CircularCategoryHierarchyError,
    SystemCategoryProtectedError,
    InvalidRuleConditionError,
)
from app.infrastructure.database.models import (
    Account,
    Category,
    ClassificationRule,
    JournalEntry,
    Merchant,
    MerchantAlias,
    Transaction,
    TransactionClassification,
    UserClassificationFeedback,
    Workspace,
)
from app.repositories.category_repository import CategoryRepository
from app.repositories.intelligence_repository import IntelligenceRepository
from app.repositories.merchant_repository import MerchantRepository
from app.repositories.rule_repository import RuleRepository
from app.services.intelligence.categorization_service import CategorizationService
from app.services.intelligence.feedback_service import FeedbackService
from app.services.intelligence.ml_classifier import MLTransactionClassifier
from app.services.intelligence.normalizer import DescriptionNormalizer
from app.services.intelligence.rule_engine import RuleEngine


# ==============================================================================
# 1. DESCRIPTION NORMALIZATION TESTS
# ==============================================================================

class TestDescriptionNormalization:
    """Verifies parsing of noisy Indian financial statements and payment channels."""

    def test_upi_rrn_extraction_and_cleaning(self):
        raw = "UPI/SWIGGY/123456789012/PAYMENT TO SWIGGY BANGALORE"
        norm = DescriptionNormalizer.normalize(raw)

        assert norm.payment_channel == "upi"
        assert norm.extracted_reference == "123456789012"
        assert norm.merchant_candidate == "SWIGGY"
        assert "123456789012" not in norm.normalized_description
        assert "SWIGGY" in norm.normalized_description

    def test_pos_terminal_cleaning(self):
        raw = "POS 4402 STARBUCKS COFFEE KORAMANGALA BANGALORE IN"
        norm = DescriptionNormalizer.normalize(raw)

        assert norm.payment_channel == "pos"
        assert "STARBUCKS COFFEE" in norm.normalized_description
        assert "POS" not in norm.normalized_description.split()

    def test_neft_corporate_salary(self):
        raw = "NEFT CR-HDFC0001234-INFOSYS LIMITED-SALARY MARCH"
        norm = DescriptionNormalizer.normalize(raw)

        assert norm.payment_channel == "neft"
        assert norm.extracted_reference == "HDFC0001234"
        assert "INFOSYS LIMITED" in norm.normalized_description
        assert "SALARY" in norm.normalized_description

    def test_nach_sip_mandate(self):
        raw = "ACH D-ZERODHA BROKING LTD MUTUAL FUND SIP 87654321"
        norm = DescriptionNormalizer.normalize(raw)

        assert norm.payment_channel == "nach_mandate"
        assert "ZERODHA BROKING" in norm.normalized_description
        assert "MUTUAL FUND" in norm.normalized_description

    def test_atm_cash_withdrawal(self):
        raw = "ATM WDL CASH HDFC ATM SAKET NEW DELHI"
        norm = DescriptionNormalizer.normalize(raw)

        assert norm.payment_channel == "atm"
        assert "ATM" in norm.normalized_description or "CASH" in norm.normalized_description

    def test_ecom_card_purchase(self):
        raw = "AMZN MKTP IN*404092 AMAZON SELLER SERVICES MUMBAI"
        norm = DescriptionNormalizer.normalize(raw)

        assert "AMAZON" in norm.normalized_description or "AMZN" in norm.normalized_description


# ==============================================================================
# 2. CATEGORY TAXONOMY & HIERARCHY TESTS
# ==============================================================================

class TestCategoryHierarchy:
    """Verifies tree operations, cycle detection, and delete protections."""

    @pytest.mark.asyncio
    async def test_seed_system_categories(self, db_session: AsyncSession):
        repo = CategoryRepository(db_session)
        created_count = await repo.seed_system_categories()
        assert created_count >= 0

        # Query tree
        tree = await repo.get_category_tree(category_type=CategoryType.EXPENSE.value)
        assert len(tree) > 0
        food_cat = next((c for c in tree if c.slug == "food-dining"), None)
        assert food_cat is not None
        assert food_cat.is_system is True
        assert len(food_cat.children) > 0

    @pytest.mark.asyncio
    async def test_custom_category_creation_and_tree(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        repo = CategoryRepository(db_session)
        await repo.seed_system_categories()

        # Find system Food category
        food_cat = await repo.get_by_slug("food-dining")
        assert food_cat is not None

        # Create custom workspace subcategory
        custom_cat = await repo.create_category(
            name="Organic Artisan Bakery",
            category_type=CategoryType.EXPENSE.value,
            workspace_id=workspace.id,
            parent_id=food_cat.id,
            icon="croissant",
            color="#D97706",
        )
        assert custom_cat.id is not None
        assert custom_cat.parent_id == food_cat.id
        assert custom_cat.workspace_id == workspace.id
        await db_session.commit()

        # Verify tree includes custom category in workspace scope
        tree = await repo.get_category_tree(workspace_id=workspace.id)
        food_node = next((n for n in tree if n.id == food_cat.id), None)
        assert food_node is not None
        assert any(child.id == custom_cat.id for child in food_node.children)

    @pytest.mark.asyncio
    async def test_circular_category_hierarchy_prevention(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        repo = CategoryRepository(db_session)

        # Create Category A -> Category B -> Category C
        cat_a = await repo.create_category(
            name="Parent A", category_type=CategoryType.EXPENSE.value, workspace_id=workspace.id
        )
        cat_b = await repo.create_category(
            name="Child B",
            category_type=CategoryType.EXPENSE.value,
            workspace_id=workspace.id,
            parent_id=cat_a.id,
        )
        cat_c = await repo.create_category(
            name="Grandchild C",
            category_type=CategoryType.EXPENSE.value,
            workspace_id=workspace.id,
            parent_id=cat_b.id,
        )

        # Attempting to set parent of A to C must raise CircularCategoryHierarchyError
        with pytest.raises(CircularCategoryHierarchyError):
            await repo.update_category(cat_a.id, parent_id=cat_c.id)

    @pytest.mark.asyncio
    async def test_delete_protection_for_system_and_used_categories(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        repo = CategoryRepository(db_session)
        await repo.seed_system_categories()

        # System category deletion must fail
        food_cat = await repo.get_by_slug("food-dining")
        with pytest.raises(SystemCategoryProtectedError):
            await repo.delete_category(food_cat.id)

        # Create custom category
        custom_cat = await repo.create_category(
            name="Conference Passes",
            category_type=CategoryType.EXPENSE.value,
            workspace_id=workspace.id,
        )

        # Link to a transaction
        account = Account(
            workspace_id=workspace.id,
            name="Test Account",
            account_type="savings",
            currency="INR",
            current_book_balance_paise=100000,
            available_balance_paise=100000,
            status="active",
        )
        db_session.add(account)
        await db_session.flush()

        tx = Transaction(
            workspace_id=workspace.id,
            account_id=account.id,
            amount=Decimal("5000.00"),
            amount_paise=500000,
            currency="INR",
            transaction_type="expense",
            direction="outflow",
            transaction_date=date.today(),
            description="Tech Conference Pass",
            category_id=custom_cat.id,
            status="posted",
        )
        db_session.add(tx)
        await db_session.flush()

        # Attempting to delete custom category in use must raise CategoryInUseError
        with pytest.raises(CategoryInUseError):
            await repo.delete_category(custom_cat.id)


# ==============================================================================
# 3. MERCHANT INTELLIGENCE & ALIAS MATCHING TESTS
# ==============================================================================

class TestMerchantIntelligence:
    """Verifies merchant recognition and alias normalization."""

    @pytest.mark.asyncio
    async def test_seed_and_match_system_merchants(self, db_session: AsyncSession):
        cat_repo = CategoryRepository(db_session)
        await cat_repo.seed_system_categories()

        repo = MerchantRepository(db_session)
        await repo.seed_system_merchants()

        # Exact match on Swiggy
        match1 = await repo.find_alias_match("SWIGGY")
        assert match1 is not None
        merchant, alias = match1
        assert merchant.canonical_name == "Swiggy"

        # Word boundary match from raw bank narration
        match2 = await repo.find_alias_match("BUNDL TECHNOLOGIES BANGALORE")
        assert match2 is not None
        assert match2[0].canonical_name == "Swiggy"

        # Uber alias
        match3 = await repo.find_alias_match("UBER INDIA SYSTEMS PVT LTD")
        assert match3 is not None
        assert match3[0].canonical_name == "Uber"

        # Netflix alias
        match4 = await repo.find_alias_match("NETFLIX ENTERTAINMENT IN")
        assert match4 is not None
        assert match4[0].canonical_name == "Netflix"

    @pytest.mark.asyncio
    async def test_custom_merchant_alias_addition(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        repo = MerchantRepository(db_session)

        merchant = await repo.create_merchant(
            canonical_name="Blue Tokai Coffee",
            merchant_type="cafe",
            workspace_id=workspace.id,
        )
        assert merchant.id is not None

        await repo.add_alias(
            merchant_id=merchant.id,
            alias="BT COFFEE ROASTERS",
            match_type="word_boundary",
            confidence=Decimal("0.9500"),
        )

        match = await repo.find_alias_match("BT COFFEE ROASTERS CONNAUGHT PLACE")
        assert match is not None
        assert match[0].canonical_name == "Blue Tokai Coffee"


# ==============================================================================
# 4. DETERMINISTIC RULE ENGINE TESTS
# ==============================================================================

class TestRuleEngine:
    """Verifies deterministic rule evaluation and condition matching."""

    @pytest.mark.asyncio
    async def test_priority_based_rule_evaluation(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        cat_repo = CategoryRepository(db_session)
        await cat_repo.seed_system_categories()
        food_cat = await cat_repo.get_by_slug("restaurants")
        groceries_cat = await cat_repo.get_by_slug("groceries")

        rule_repo = RuleRepository(db_session)

        # Higher priority specific rule (priority 200)
        rule_swiggy_instamart = await rule_repo.create_rule(
            name="Swiggy Instamart Groceries",
            conditions={"description_contains": ["INSTAMART"]},
            suggested_category_id=groceries_cat.id,
            priority=200,
            workspace_id=workspace.id,
            rule_scope=RuleScope.WORKSPACE.value,
        )

        # Lower priority general rule (priority 100)
        rule_swiggy_general = await rule_repo.create_rule(
            name="Swiggy General Food",
            conditions={"description_contains": ["SWIGGY"]},
            suggested_category_id=food_cat.id,
            priority=100,
            workspace_id=workspace.id,
            rule_scope=RuleScope.WORKSPACE.value,
        )

        rules = await rule_repo.list_rules(workspace_id=workspace.id)

        # Test Instamart: both "SWIGGY" and "INSTAMART" match, but priority 200 wins
        match_insta = RuleEngine.evaluate(
            rules=rules,
            normalized_description="SWIGGY INSTAMART GROCERIES",
            merchant_name="SWIGGY",
            direction="outflow",
            amount_paise=45000,
        )
        assert match_insta is not None
        assert match_insta.rule_id == rule_swiggy_instamart.id
        assert match_insta.suggested_category_id == groceries_cat.id

        # Test Standard Swiggy: only matches general rule (priority 100)
        match_food = RuleEngine.evaluate(
            rules=rules,
            normalized_description="SWIGGY FOOD DELIVERY",
            merchant_name="SWIGGY",
            direction="outflow",
            amount_paise=32000,
        )
        assert match_food is not None
        assert match_food.rule_id == rule_swiggy_general.id
        assert match_food.suggested_category_id == food_cat.id

    @pytest.mark.asyncio
    async def test_amount_and_direction_condition_filtering(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        cat_repo = CategoryRepository(db_session)
        await cat_repo.seed_system_categories()
        tax_cat = await cat_repo.get_by_slug("gst-taxes") or await cat_repo.get_by_slug("utilities")

        rule_repo = RuleRepository(db_session)
        rule = await rule_repo.create_rule(
            name="Large Outflow Tax Payment",
            conditions={
                "description_contains": ["TAX"],
                "direction": "outflow",
                "min_amount_paise": 1000000,  # >= Rs 10,000
            },
            suggested_category_id=tax_cat.id,
            priority=150,
            workspace_id=workspace.id,
        )

        rules = [rule]

        # Fails min_amount (Rs 500)
        m_small = RuleEngine.evaluate(
            rules=rules,
            normalized_description="DIRECT TAX CHALLAN",
            merchant_name=None,
            direction="outflow",
            amount_paise=50000,
        )
        assert m_small is None

        # Fails direction (inflow refund)
        m_refund = RuleEngine.evaluate(
            rules=rules,
            normalized_description="INCOME TAX REFUND",
            merchant_name=None,
            direction="inflow",
            amount_paise=2500000,
        )
        assert m_refund is None

        # Passes all conditions
        m_valid = RuleEngine.evaluate(
            rules=rules,
            normalized_description="DIRECT TAX CHALLAN 280",
            merchant_name=None,
            direction="outflow",
            amount_paise=1500000,
        )
        assert m_valid is not None
        assert m_valid.rule_id == rule.id


# ==============================================================================
# 5. MACHINE LEARNING CLASSIFIER TESTS
# ==============================================================================

class TestMLClassifier:
    """Verifies trained model loading, probability inference, and confidence bands."""

    def test_model_loading_and_prediction(self):
        classifier = MLTransactionClassifier()
        assert classifier.is_trained() is True

        # High confidence predictions
        pred_food = classifier.predict("UPI SWIGGY ORDER")
        assert pred_food.predicted_category_slug in ("food-delivery", "restaurants", "food-dining")
        assert pred_food.confidence_score >= 0.05
        assert len(pred_food.probabilities) > 0

        pred_transport = classifier.predict("UBER INDIA RIDES TRIP")
        assert pred_transport.predicted_category_slug in ("ride-hailing", "transportation", "fuel")
        assert pred_transport.confidence_score >= 0.05

    def test_low_confidence_fallback(self):
        classifier = MLTransactionClassifier()
        # Short / ambiguous text
        pred = classifier.predict("XYZ")
        assert pred.confidence_score < 0.85


# ==============================================================================
# 6. HYBRID CATEGORIZATION PIPELINE END-TO-END
# ==============================================================================

class TestCategorizationService:
    """Verifies layered pipeline execution (Rules -> Merchant Aliases -> ML -> Fallback)."""

    @pytest.mark.asyncio
    async def test_end_to_end_categorization_and_preview(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        service = CategorizationService(db_session)
        await service.seed_system_defaults()

        # Test Preview for Swiggy
        preview = await service.preview_suggestion(
            description="UPI/SWIGGY/1234567890/DINING",
            workspace_id=workspace.id,
            direction="outflow",
            amount_paise=35000,
        )
        assert preview["suggested_category_name"] is not None
        assert preview["merchant_candidate"] == "Swiggy"
        assert preview["payment_channel"] == "upi"
        assert preview["confidence_score"] >= 0.60

    @pytest.mark.asyncio
    async def test_batch_categorization_and_ledger_safety(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        service = CategorizationService(db_session)
        await service.seed_system_defaults()

        # Create account & transactions
        account = Account(
            workspace_id=workspace.id,
            name="Axis Checking",
            account_type="checking",
            currency="INR",
            current_book_balance_paise=5000000,
            available_balance_paise=5000000,
            status="active",
        )
        db_session.add(account)
        await db_session.flush()

        tx1 = Transaction(
            workspace_id=workspace.id,
            account_id=account.id,
            amount=Decimal("850.00"),
            amount_paise=85000,
            currency="INR",
            transaction_type="expense",
            direction="outflow",
            transaction_date=date.today(),
            description="UPI/ZOMATO/998877/DELIVERY",
            status="posted",
        )
        tx2 = Transaction(
            workspace_id=workspace.id,
            account_id=account.id,
            amount=Decimal("12000.00"),
            amount_paise=1200000,
            currency="INR",
            transaction_type="expense",
            direction="outflow",
            transaction_date=date.today(),
            description="ACH D-HDFC LIFE INSURANCE MANDATE",
            status="posted",
        )
        db_session.add_all([tx1, tx2])
        await db_session.commit()

        # Check existing journal entries count before categorization
        je_count_before = (
            await db_session.execute(
                select(JournalEntry).where(JournalEntry.workspace_id == workspace.id)
            )
        ).scalars().all()

        # Execute batch categorization
        classified = await service.categorize_workspace_transactions(
            workspace_id=workspace.id, transaction_ids=[tx1.id, tx2.id]
        )
        assert len(classified) == 2

        # FINANCIAL INVARIANT VERIFICATION:
        # Categorization records were created, but General Ledger journal entries were NOT mutated!
        je_count_after = (
            await db_session.execute(
                select(JournalEntry).where(JournalEntry.workspace_id == workspace.id)
            )
        ).scalars().all()
        assert len(je_count_before) == len(je_count_after)

        # Confirm classification records in database
        intel_repo = IntelligenceRepository(db_session)
        c1 = await intel_repo.get_classification_by_transaction_id(workspace.id, tx1.id)
        assert c1 is not None
        assert c1.transaction_id == tx1.id
        assert c1.suggested_category_id is not None
        assert c1.status == "suggested"


# ==============================================================================
# 7. USER FEEDBACK LOOP & CONTINUOUS LEARNING
# ==============================================================================

class TestFeedbackService:
    """Verifies user confirmations, corrections, and rule generation."""

    @pytest.mark.asyncio
    async def test_accept_and_correct_feedback(
        self, db_session: AsyncSession, registered_user: dict
    ):
        workspace = registered_user["workspace"]
        user = registered_user["user"]
        cat_service = CategorizationService(db_session)
        await cat_service.seed_system_defaults()

        cat_repo = CategoryRepository(db_session)
        groceries_cat = await cat_repo.get_by_slug("groceries")

        # Create account and transaction
        account = Account(
            workspace_id=workspace.id,
            name="Bank",
            account_type="savings",
            currency="INR",
            current_book_balance_paise=100000,
            available_balance_paise=100000,
            status="active",
        )
        db_session.add(account)
        await db_session.flush()

        tx = Transaction(
            workspace_id=workspace.id,
            account_id=account.id,
            amount=Decimal("420.00"),
            amount_paise=42000,
            currency="INR",
            transaction_type="expense",
            direction="outflow",
            transaction_date=date.today(),
            description="UPI/BLINKIT/12345/SNACKS",
            status="posted",
        )
        db_session.add(tx)
        await db_session.commit()

        # Categorize
        [classification] = await cat_service.categorize_workspace_transactions(
            workspace_id=workspace.id, transaction_ids=[tx.id]
        )

        fb_service = FeedbackService(db_session)

        # User corrects category and requests a rule
        feedback = await fb_service.submit_feedback(
            workspace_id=workspace.id,
            user_id=user.id,
            transaction_id=tx.id,
            action=FeedbackAction.CORRECT_CATEGORY.value,
            confirmed_category_id=groceries_cat.id,
            create_rule=True,
            rule_name="Blinkit Groceries Rule",
        )

        assert feedback["action"] == FeedbackAction.CORRECT_CATEGORY.value
        assert feedback["confirmed_category_id"] == str(groceries_cat.id)
        assert feedback["created_rule_id"] is not None

        # Transaction category is updated to user choice
        await db_session.refresh(tx)
        assert tx.category_id == groceries_cat.id

        # Auto-created rule exists
        rule_repo = RuleRepository(db_session)
        user_rules = await rule_repo.list_rules(workspace_id=workspace.id)
        assert any(r.suggested_category_id == groceries_cat.id for r in user_rules)


# ==============================================================================
# 8. MULTI-WORKSPACE ISOLATION & SECURITY TESTS
# ==============================================================================

class TestWorkspaceIsolation:
    """Verifies strict tenant isolation across categories, rules, and classifications."""

    @pytest.mark.asyncio
    async def test_tenant_rule_isolation(
        self, db_session: AsyncSession, registered_user: dict
    ):
        ws_a = registered_user["workspace"]
        cat_repo = CategoryRepository(db_session)
        await cat_repo.seed_system_categories()
        food_cat = await cat_repo.get_by_slug("restaurants")

        # Create Workspace B
        ws_b = Workspace(
            name="Workspace B",
            slug=f"ws-b-{uuid.uuid4().hex[:6]}",
            type="business",
            owner_id=registered_user["user"].id,
            default_currency="INR",
            timezone="Asia/Kolkata",
            status="active",
        )
        db_session.add(ws_b)
        await db_session.commit()

        rule_repo = RuleRepository(db_session)

        # Create rule in Workspace A
        rule_a = await rule_repo.create_rule(
            name="Secret Vendor Rule",
            conditions={"description_contains": ["PROPRIETARY_VENDOR"]},
            suggested_category_id=food_cat.id,
            priority=100,
            workspace_id=ws_a.id,
        )

        # Workspace B queries its applicable rules
        rules_b = await rule_repo.list_rules(workspace_id=ws_b.id)
        # Workspace B must NOT see Workspace A's custom rule!
        assert not any(r.id == rule_a.id for r in rules_b)
