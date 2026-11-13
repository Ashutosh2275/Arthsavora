"""
Arthsavora Domain Tests — Money Value Object
Verifies exact decimal arithmetic, Bankers Rounding, minor unit conversions,
strict currency mismatch prevention, and immutability invariants.
"""

from decimal import Decimal
import pytest
from app.domain.money import Money
from app.domain.exceptions import CurrencyMismatchError, DomainValidationError


def test_money_initialization_exact_decimal():
    """Verify Money preserves exact decimal representation without floating-point drift."""
    m1 = Money("100.50", "INR")
    assert m1.amount == Decimal("100.5000")
    assert m1.currency == "INR"
    assert m1.display_amount == Decimal("100.50")

    # From int
    m2 = Money(100, "INR")
    assert m2.amount == Decimal("100.0000")
    assert m2.display_amount == Decimal("100.00")

    # From Decimal
    m3 = Money(Decimal("250.75"), "INR")
    assert m3.amount == Decimal("250.7500")
    assert m3.display_amount == Decimal("250.75")


def test_money_bankers_rounding():
    """Verify Bankers Rounding (ROUND_HALF_EVEN) prevents cumulative rounding biases."""
    # 1. At 4-decimal-place internal quantization:
    # 10.00025 -> 10.0002 (rounds to even digit 2)
    # 10.00035 -> 10.0004 (rounds to even digit 4)
    m_even = Money(Decimal("10.00025"), "INR")
    assert m_even.amount == Decimal("10.0002")

    m_odd = Money(Decimal("10.00035"), "INR")
    assert m_odd.amount == Decimal("10.0004")

    # 2. At 2-decimal-place display quantization:
    # 10.025 -> 10.02 (rounds to even digit 2)
    # 10.035 -> 10.04 (rounds to even digit 4)
    disp_even = Money(Decimal("10.025"), "INR")
    assert disp_even.display_amount == Decimal("10.02")

    disp_odd = Money(Decimal("10.035"), "INR")
    assert disp_odd.display_amount == Decimal("10.04")


def test_money_addition_and_subtraction():
    """Verify exact addition and subtraction of identical currencies."""
    m1 = Money("100.20", "INR")
    m2 = Money("200.30", "INR")

    result_add = m1 + m2
    assert result_add.amount == Decimal("300.5000")
    assert result_add.display_amount == Decimal("300.50")
    assert result_add.currency == "INR"

    result_sub = m2 - m1
    assert result_sub.amount == Decimal("100.1000")
    assert result_sub.display_amount == Decimal("100.10")
    assert result_sub.currency == "INR"


def test_money_currency_mismatch_raises_error():
    """Verify strict prohibition of cross-currency arithmetic without explicit conversion."""
    inr = Money("500.00", "INR")
    usd = Money("10.00", "USD")

    with pytest.raises(CurrencyMismatchError) as exc_info:
        _ = inr + usd
    assert "differing currencies" in str(exc_info.value).lower()

    with pytest.raises(CurrencyMismatchError):
        _ = inr - usd

    with pytest.raises(CurrencyMismatchError):
        _ = inr < usd


def test_money_multiplication_and_division():
    """Verify scalar multiplication and division with Bankers Rounding."""
    m = Money("100.00", "INR")

    # Multiplied by scalar
    res_mult = m * 3
    assert res_mult.amount == Decimal("300.0000")
    assert res_mult.display_amount == Decimal("300.00")
    assert res_mult.currency == "INR"

    # Multiplied by Decimal
    res_tax = m * Decimal("0.18")
    assert res_tax.amount == Decimal("18.0000")
    assert res_tax.display_amount == Decimal("18.00")

    # Divided by scalar
    res_div = m / 3
    # 100 / 3 = 33.3333333333... -> rounded to 33.3333 internally, 33.33 on display
    assert res_div.amount == Decimal("33.3333")
    assert res_div.display_amount == Decimal("33.33")


def test_money_division_by_zero():
    """Verify division by zero raises DomainValidationError."""
    m = Money("100.00", "INR")
    with pytest.raises(DomainValidationError):
        _ = m / 0


def test_money_comparisons():
    """Verify equality and ordering comparisons."""
    m1 = Money("50.00", "INR")
    m2 = Money("50.00", "INR")
    m3 = Money("75.00", "INR")

    assert m1 == m2
    assert m1 != m3
    assert m1 < m3
    assert m1 <= m2
    assert m3 > m1
    assert m3 >= m2


def test_money_predicates():
    """Verify is_zero, is_positive, is_negative, and abs_val predicates."""
    zero = Money("0.00", "INR")
    pos = Money("150.00", "INR")
    neg = Money("-75.50", "INR")

    assert zero.is_zero is True
    assert zero.is_positive is False
    assert zero.is_negative is False

    assert pos.is_zero is False
    assert pos.is_positive is True
    assert pos.is_negative is False

    assert neg.is_zero is False
    assert neg.is_positive is False
    assert neg.is_negative is True

    assert neg.abs_val().amount == Decimal("75.5000")
    assert neg.abs_val().display_amount == Decimal("75.50")


def test_money_minor_units_conversion():
    """Verify paise to rupees and minor units integer conversion."""
    # 100.50 INR = 10050 paise
    m = Money("100.50", "INR")
    assert m.to_minor_units() == 10050
    assert m.paise == 10050

    from_paise = Money.from_minor_units(10050, "INR")
    assert from_paise.display_amount == Decimal("100.50")
    assert from_paise.currency == "INR"

    # Single paise test
    one_paise = Money.from_minor_units(1, "INR")
    assert one_paise.display_amount == Decimal("0.01")
    assert one_paise.to_minor_units() == 1


def test_money_string_formatting():
    """Verify formatted string outputs."""
    m = Money("1234567.89", "INR")
    assert str(m) == "INR 1234567.89"
    assert m.format() == "₹ 1,234,567.89"
    assert m.format(symbol=False) == "INR 1,234,567.89"


def test_money_immutability():
    """Verify frozen dataclass prevents accidental attribute modification."""
    m = Money("100.00", "INR")
    with pytest.raises(AttributeError):
        m.amount = Decimal("200.00")
