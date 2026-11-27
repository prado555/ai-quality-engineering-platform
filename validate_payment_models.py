from pydantic import ValidationError

from mock_payment_service.models.payment import (
    PaymentRequest,
)


test_payments = [
    {
        "name": "India UPI Payment",
        "data": {
            "source_account": "IN-ACC-1001",
            "destination_account": "IN-ACC-1002",
            "source_country": "IN",
            "destination_country": "IN",
            "payment_rail": "UPI",
            "amount": "1500.00",
            "currency": "INR",
            "idempotency_key": "IN-TXN-0001"
        }
    },
    {
        "name": "US ACH Payment",
        "data": {
            "source_account": "US-ACC-1001",
            "destination_account": "US-ACC-1002",
            "source_country": "US",
            "destination_country": "US",
            "payment_rail": "ACH",
            "amount": "250.00",
            "currency": "USD",
            "idempotency_key": "US-TXN-0001"
        }
    },
    {
        "name": "Poland Express Elixir Payment",
        "data": {
            "source_account": "PL-ACC-2001",
            "destination_account": "PL-ACC-2002",
            "source_country": "PL",
            "destination_country": "PL",
            "payment_rail": "EXPRESS_ELIXIR",
            "amount": "750.00",
            "currency": "PLN",
            "idempotency_key": "PL-TXN-0001"
        }
    },
    {
        "name": "International SWIFT Payment",
        "data": {
            "source_account": "US-ACC-1001",
            "destination_account": "PL-ACC-2001",
            "source_country": "US",
            "destination_country": "PL",
            "payment_rail": "SWIFT",
            "amount": "1000.00",
            "currency": "USD",
            "destination_currency": "PLN",
            "idempotency_key": "INT-TXN-0001"
        }
    },
    {
        "name": "SEPA SCT Payment",
        "data": {
            "source_account": "PL-ACC-2001",
            "destination_account": "PL-ACC-2002",
            "source_country": "PL",
            "destination_country": "PL",
            "payment_rail": "SEPA_SCT",
            "amount": "500.00",
            "currency": "EUR",
            "idempotency_key": "SEPA-TXN-0001"
        }
    }
]


print("\n=== POSITIVE PAYMENT MODEL VALIDATION ===")

for payment in test_payments:
    try:
        validated = PaymentRequest(**payment["data"])
        print(f"PASS: {payment['name']}")

    except ValidationError as error:
        print(f"FAIL: {payment['name']}")
        print(error)


print("\n=== NEGATIVE PAYMENT MODEL VALIDATION ===")

invalid_payment = test_payments[0]["data"].copy()
invalid_payment["amount"] = "-100"

try:
    PaymentRequest(**invalid_payment)
    print("FAIL: Negative amount was accepted")

except ValidationError:
    print("PASS: Negative amount rejected")


same_account_payment = test_payments[0]["data"].copy()
same_account_payment["destination_account"] = (
    same_account_payment["source_account"]
)

try:
    PaymentRequest(**same_account_payment)
    print("FAIL: Identical accounts were accepted")

except ValidationError:
    print("PASS: Identical accounts rejected")