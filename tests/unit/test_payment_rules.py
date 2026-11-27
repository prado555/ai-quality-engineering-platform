import pytest

from mock_payment_service.models.payment import PaymentRequest
from mock_payment_service.services.payment_rules import (
    validate_payment_request,
)


@pytest.mark.parametrize(
    "payment_data",
    [
        {
            "source_account": "IN-ACC-1001",
            "destination_account": "IN-ACC-1002",
            "source_country": "IN",
            "destination_country": "IN",
            "payment_rail": "UPI",
            "amount": "1500.00",
            "currency": "INR",
            "idempotency_key": "IN-TXN-0001",
        },
        {
            "source_account": "US-ACC-1001",
            "destination_account": "US-ACC-1002",
            "source_country": "US",
            "destination_country": "US",
            "payment_rail": "ACH",
            "amount": "250.00",
            "currency": "USD",
            "idempotency_key": "US-TXN-0001",
        },
        {
            "source_account": "PL-ACC-2001",
            "destination_account": "PL-ACC-2002",
            "source_country": "PL",
            "destination_country": "PL",
            "payment_rail": "EXPRESS_ELIXIR",
            "amount": "750.00",
            "currency": "PLN",
            "idempotency_key": "PL-TXN-0001",
        },
        {
            "source_account": "US-ACC-1001",
            "destination_account": "PL-ACC-2001",
            "source_country": "US",
            "destination_country": "PL",
            "payment_rail": "SWIFT",
            "amount": "1000.00",
            "currency": "USD",
            "destination_currency": "PLN",
            "idempotency_key": "INT-TXN-0001",
        },
        {
            "source_account": "PL-ACC-2001",
            "destination_account": "DE-ACC-3001",
            "source_country": "PL",
            "destination_country": "DE",
            "payment_rail": "SEPA_SCT",
            "amount": "500.00",
            "currency": "EUR",
            "idempotency_key": "SEPA-TXN-0001",
        },
        {
            "source_account": "DE-ACC-3001",
            "destination_account": "FR-ACC-4001",
            "source_country": "DE",
            "destination_country": "FR",
            "payment_rail": "SEPA_INST",
            "amount": "300.00",
            "currency": "EUR",
            "idempotency_key": "SEPA-TXN-0002",
        },
    ],
)
def test_valid_payment_requests(payment_data):
    payment = PaymentRequest(**payment_data)

    validate_payment_request(payment)


@pytest.mark.parametrize(
    "payment_data",
    [
        {
            "source_account": "IN-ACC-1001",
            "destination_account": "IN-ACC-1002",
            "source_country": "IN",
            "destination_country": "IN",
            "payment_rail": "UPI",
            "amount": "1500.00",
            "currency": "USD",
            "idempotency_key": "NEG-TXN-0001",
        },
        {
            "source_account": "US-ACC-1001",
            "destination_account": "US-ACC-1002",
            "source_country": "US",
            "destination_country": "US",
            "payment_rail": "ACH",
            "amount": "250.00",
            "currency": "PLN",
            "idempotency_key": "NEG-TXN-0002",
        },
        {
            "source_account": "US-ACC-1001",
            "destination_account": "US-ACC-1002",
            "source_country": "US",
            "destination_country": "US",
            "payment_rail": "UPI",
            "amount": "100.00",
            "currency": "INR",
            "idempotency_key": "NEG-TXN-COUNTRY",
        },
        {
            "source_account": "US-ACC-1001",
            "destination_account": "PL-ACC-2001",
            "source_country": "US",
            "destination_country": "PL",
            "payment_rail": "ACH",
            "amount": "500.00",
            "currency": "USD",
            "idempotency_key": "NEG-TXN-0003",
        },
        {
            "source_account": "PL-ACC-2001",
            "destination_account": "DE-ACC-3001",
            "source_country": "PL",
            "destination_country": "DE",
            "payment_rail": "SEPA_SCT",
            "amount": "500.00",
            "currency": "USD",
            "idempotency_key": "NEG-TXN-0004",
        },
        {
            "source_account": "IN-ACC-1001",
            "destination_account": "IN-ACC-1002",
            "source_country": "IN",
            "destination_country": "IN",
            "payment_rail": "SWIFT",
            "amount": "500.00",
            "currency": "INR",
            "destination_currency": "USD",
            "idempotency_key": "NEG-TXN-0005",
        },
        {
            "source_account": "IN-ACC-1001",
            "destination_account": "DE-ACC-3001",
            "source_country": "IN",
            "destination_country": "DE",
            "payment_rail": "SEPA_SCT",
            "amount": "500.00",
            "currency": "EUR",
            "idempotency_key": "NEG-TXN-0006",
        },
    ],
)
def test_invalid_payment_requests(payment_data):
    payment = PaymentRequest(**payment_data)

    with pytest.raises(ValueError):
        validate_payment_request(payment)


@pytest.mark.parametrize(
    "payment_data",
    [
        {
            "source_account": "US-ACC-5001",
            "destination_account": "PL-ACC-5001",
            "source_country": "US",
            "destination_country": "PL",
            "payment_rail": "SWIFT",
            "amount": "100.00",
            "currency": "USD",
            "destination_currency": "USD",
            "idempotency_key": "SWIFT-SAME-0001",
        },
        {
            "source_account": "US-ACC-5002",
            "destination_account": "PL-ACC-5002",
            "source_country": "US",
            "destination_country": "PL",
            "payment_rail": "SWIFT",
            "amount": "100.00",
            "currency": "USD",
            "destination_currency": "PLN",
            "idempotency_key": "SWIFT-DIFF-0001",
        },
    ],
)
def test_swift_accepts_cross_border_supported_currencies(payment_data):
    validate_payment_request(PaymentRequest(**payment_data))


def test_swift_requires_destination_currency():
    payment = PaymentRequest(
        source_account="US-ACC-6001",
        destination_account="PL-ACC-6001",
        source_country="US",
        destination_country="PL",
        payment_rail="SWIFT",
        amount="100.00",
        currency="USD",
        idempotency_key="SWIFT-MISSING-1",
    )

    with pytest.raises(ValueError, match="Destination currency is required"):
        validate_payment_request(payment)


def test_swift_rejects_domestic_transfer():
    payment = PaymentRequest(
        source_account="US-ACC-7001",
        destination_account="US-ACC-7002",
        source_country="US",
        destination_country="US",
        payment_rail="SWIFT",
        amount="100.00",
        currency="USD",
        destination_currency="USD",
        idempotency_key="SWIFT-DOMESTIC-1",
    )

    with pytest.raises(ValueError, match="cross-border"):
        validate_payment_request(payment)