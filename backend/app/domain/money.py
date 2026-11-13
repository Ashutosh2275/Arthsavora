"""
Arthsavora Financial Money Value Object
Immutable, currency-aware, exact decimal financial representation.
Guarantees absolute decimal precision, Bankers Rounding, and strict currency safety.
Zero floating-point arithmetic permitted.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
from typing import Any, Dict, Optional, Union
from app.domain.exceptions import CurrencyMismatchError, DomainValidationError

# Supported currency minor unit precisions (ISO 4217)
CURRENCY_PRECISIONS: Dict[str, int] = {
    "INR": 2,  # 100 Paise
    "USD": 2,  # 100 Cents
    "EUR": 2,  # 100 Cents
    "GBP": 2,  # 100 Pence
    "SGD": 2,  # 100 Cents
    "AED": 2,  # 100 Fils
    "JPY": 0,  # 1 Yen (Zero decimal)
    "KWD": 3,  # 1000 Fils
    "BHD": 3,  # 1000 Fils
}

SUPPORTED_CURRENCIES = set(CURRENCY_PRECISIONS.keys())

# Internal high-precision ledger quantization (4 decimal places)
INTERNAL_QUANTIZATION = Decimal("0.0001")


@dataclass(frozen=True)
class Money:
    """
    Immutable value object representing monetary amounts.
    Enforces exact Decimal arithmetic with Bankers Rounding (ROUND_HALF_EVEN).
    """

    amount: Decimal
    currency: str = "INR"

    def __post_init__(self):
        curr = self.currency.upper().strip()
        if not curr or len(curr) != 3:
            raise DomainValidationError(
                message=f"Invalid currency code '{self.currency}'. Must be a 3-letter ISO code.",
                field="currency",
            )
        if curr not in SUPPORTED_CURRENCIES:
            raise DomainValidationError(
                message=f"Unsupported currency code '{self.currency}'. Supported currencies: {sorted(SUPPORTED_CURRENCIES)}",
                field="currency",
            )
        # Use object.__setattr__ because the dataclass is frozen
        object.__setattr__(self, "currency", curr)

        # Quantize amount to internal precision using Bankers Rounding
        try:
            if not isinstance(self.amount, Decimal):
                dec_val = Decimal(str(self.amount))
            else:
                dec_val = self.amount

            if dec_val.is_nan() or dec_val.is_infinite():
                raise DomainValidationError(
                    message="Monetary amount cannot be NaN or Infinite.",
                    field="amount",
                )

            quantized = dec_val.quantize(INTERNAL_QUANTIZATION, rounding=ROUND_HALF_EVEN)
            object.__setattr__(self, "amount", quantized)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise DomainValidationError(
                message=f"Invalid monetary amount '{self.amount}': {exc}",
                field="amount",
            )

    @classmethod
    def from_amount(
        cls,
        amount: Union[str, int, float, Decimal],
        currency: str = "INR",
    ) -> "Money":
        """Factory method constructing Money from numeric or string input."""
        if isinstance(amount, float):
            # Convert float through string representation to prevent IEEE 754 precision distortion
            amount = str(amount)
        return cls(amount=Decimal(str(amount)), currency=currency)

    @classmethod
    def from_paise(cls, paise: int, currency: str = "INR") -> "Money":
        """Factory method constructing Money from integer minor units (paise/cents)."""
        precision = CURRENCY_PRECISIONS.get(currency.upper(), 2)
        factor = Decimal(10 ** precision)
        amount = Decimal(paise) / factor
        return cls(amount=amount, currency=currency)

    @classmethod
    def from_minor_units(cls, minor_units: int, currency: str = "INR") -> "Money":
        """Factory method constructing Money from minor units."""
        return cls.from_paise(minor_units, currency=currency)

    @classmethod
    def zero(cls, currency: str = "INR") -> "Money":
        """Returns a zero-valued Money instance in the specified currency."""
        return cls(amount=Decimal("0.0000"), currency=currency)

    @property
    def minor_units(self) -> int:
        """Returns the amount converted to integer minor units (e.g. paise for INR)."""
        precision = CURRENCY_PRECISIONS.get(self.currency, 2)
        factor = Decimal(10 ** precision)
        quantized_display = self.amount.quantize(
            Decimal(10) ** -precision, rounding=ROUND_HALF_EVEN
        )
        return int(quantized_display * factor)

    def to_minor_units(self) -> int:
        """Returns the amount converted to integer minor units."""
        return self.minor_units

    @property
    def paise(self) -> int:
        """Alias for minor units when currency is INR."""
        return self.minor_units

    @property
    def display_amount(self) -> Decimal:
        """Returns amount rounded to standard currency display decimal places (2 for INR)."""
        precision = CURRENCY_PRECISIONS.get(self.currency, 2)
        return self.amount.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_EVEN)

    @property
    def is_zero(self) -> bool:
        return self.amount == Decimal("0.0000")

    @property
    def is_positive(self) -> bool:
        return self.amount > Decimal("0.0000")

    @property
    def is_negative(self) -> bool:
        return self.amount < Decimal("0.0000")

    def abs_val(self) -> "Money":
        """Returns the absolute value of this Money."""
        return Money(amount=abs(self.amount), currency=self.currency)

    def _assert_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(self.currency, other.currency)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, scalar: Union[int, float, Decimal]) -> "Money":
        if isinstance(scalar, (int, Decimal)):
            factor = Decimal(scalar)
        elif isinstance(scalar, float):
            factor = Decimal(str(scalar))
        else:
            return NotImplemented
        return Money(amount=self.amount * factor, currency=self.currency)

    def __rmul__(self, scalar: Union[int, float, Decimal]) -> "Money":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: Union[int, float, Decimal]) -> "Money":
        if isinstance(scalar, (int, Decimal)):
            factor = Decimal(scalar)
        elif isinstance(scalar, float):
            factor = Decimal(str(scalar))
        else:
            return NotImplemented

        if factor == Decimal("0"):
            raise DomainValidationError(
                message="Cannot divide monetary amount by zero.",
                field="amount",
            )
        return Money(amount=self.amount / factor, currency=self.currency)

    def __neg__(self) -> "Money":
        return Money(amount=-self.amount, currency=self.currency)

    def __abs__(self) -> "Money":
        return Money(amount=abs(self.amount), currency=self.currency)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Money):
            return False
        return self.currency == other.currency and self.amount == other.amount

    def __lt__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._assert_same_currency(other)
        return self.amount >= other.amount

    def format(self, symbol: bool = True) -> str:
        """Formats money into human-readable representation."""
        display_dec = self.display_amount
        prefix = "₹ " if (symbol and self.currency == "INR") else f"{self.currency} "
        return f"{prefix}{display_dec:,.2f}"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Money to JSON-serializable contract dictionary."""
        return {
            "amount": str(self.display_amount),
            "raw_amount": str(self.amount),
            "paise": self.minor_units,
            "currency": self.currency,
        }

    def __str__(self) -> str:
        return f"{self.currency} {self.display_amount}"

    def __repr__(self) -> str:
        return f"Money({self.amount}, '{self.currency}')"
