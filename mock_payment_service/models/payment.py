from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# Supported countries
class CountryCode(str, Enum):
    INDIA = "IN"
    UNITED_STATES = "US"
    POLAND = "PL"

    # Additional SEPA test countries
    GERMANY = "DE"
    FRANCE = "FR"
    NETHERLANDS = "NL"


# Supported currencies
class Currency(str, Enum):
    INR = "INR"
    USD = "USD"
    PLN = "PLN"
    EUR = "EUR"


# Supported domestic and international payment methods
class PaymentRail(str, Enum):

    # India
    UPI = "UPI"
    IMPS = "IMPS"
    NEFT = "NEFT"
    RTGS = "RTGS"

    # United States
    ACH = "ACH"
    SAME_DAY_ACH = "SAME_DAY_ACH"
    FEDWIRE = "FEDWIRE"
    FEDNOW = "FEDNOW"

    # Poland
    ELIXIR = "ELIXIR"
    EXPRESS_ELIXIR = "EXPRESS_ELIXIR"
    EURO_ELIXIR = "EURO_ELIXIR"
    BLIK = "BLIK"
    SORBNET3 = "SORBNET3"

    # International
    SWIFT = "SWIFT"
    SEPA_SCT = "SEPA_SCT"
    SEPA_INST = "SEPA_INST"


# Payment lifecycle statuses
class PaymentStatus(str, Enum):
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


# Payment creation request
class PaymentRequest(BaseModel):

    source_account: str = Field(
        min_length=5,
        max_length=34,
        description="Synthetic source account identifier"
    )

    destination_account: str = Field(
        min_length=5,
        max_length=34,
        description="Synthetic destination account identifier"
    )

    source_country: CountryCode

    destination_country: CountryCode

    payment_rail: PaymentRail

    amount: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2
    )

    currency: Currency

    destination_currency: Optional[Currency] = None

    idempotency_key: str = Field(
        min_length=8,
        max_length=64
    )

    @field_validator(
        "source_account",
        "destination_account",
        "idempotency_key",
        mode="before",
    )
    @classmethod
    def strip_identifier_whitespace(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Identifiers cannot contain only whitespace.")
        return value

    @field_validator("amount")
    @classmethod
    def validate_finite_amount(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Amount must be finite.")
        return value

    @model_validator(mode="after")
    def validate_payment_accounts(self):

        if self.source_account == self.destination_account:
            raise ValueError(
                "Source and destination accounts cannot be identical"
            )

        return self


# Payment creation response
class PaymentResponse(BaseModel):

    payment_id: str

    source_account: str

    destination_account: str

    source_country: CountryCode

    destination_country: CountryCode

    payment_rail: PaymentRail

    amount: Decimal

    currency: Currency

    destination_currency: Optional[Currency] = None

    exchange_rate: Optional[Decimal] = None

    converted_amount: Optional[Decimal] = None

    status: PaymentStatus

    message: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )