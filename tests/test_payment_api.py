from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.api.main as main_module
from backend.api.main import app
from backend.database import Base, get_db
from backend.services.payment_repository import PaymentRepository
from mock_payment_service.services.fx_service import FXRate


@pytest.fixture
def test_client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    test_database = tmp_path / "test_payments.db"
    engine = create_engine(
        f"sqlite:///{test_database}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)
    initialization_calls: list[bool] = []
    monkeypatch.setattr(
        main_module,
        "create_database",
        lambda: initialization_calls.append(True),
    )

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    existing_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    app.state.test_database_path = test_database
    try:
        with TestClient(app) as client:
            yield client
        assert initialization_calls == [True]
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(existing_overrides)
        engine.dispose()


def domestic_payment(idempotency_key: str = "API-TXN-0001") -> dict[str, str]:
    return {
        "source_account": "IN-ACC-1001",
        "destination_account": "IN-ACC-1002",
        "source_country": "IN",
        "destination_country": "IN",
        "payment_rail": "UPI",
        "amount": "1500.00",
        "currency": "INR",
        "idempotency_key": idempotency_key,
    }


def test_create_retrieve_and_list_payment(test_client):
    create_response = test_client.post(
        "/payments",
        json=domestic_payment(),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["payment_id"].startswith("pay_")
    assert created["status"] == "SUCCESS"

    get_response = test_client.get(f"/payments/{created['payment_id']}")
    assert get_response.status_code == 200
    assert get_response.json()["payment_id"] == created["payment_id"]

    list_response = test_client.get("/payments")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_duplicate_idempotency_key_returns_existing_payment(test_client):
    first = test_client.post("/payments", json=domestic_payment())
    second = test_client.post("/payments", json=domestic_payment())

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["payment_id"] == first.json()["payment_id"]


def test_reused_idempotency_key_with_different_payload_is_conflict(test_client):
    test_client.post("/payments", json=domestic_payment())
    changed = domestic_payment()
    changed["amount"] = "2500.00"

    response = test_client.post("/payments", json=changed)

    assert response.status_code == 409
    assert "different payment" in response.json()["detail"]


def test_concurrent_requests_with_same_idempotency_key_create_one_payment(
    test_client,
    monkeypatch,
):
    barrier = Barrier(2)
    original_lookup = PaymentRepository.get_by_idempotency_key

    def synchronized_lookup(repository, idempotency_key):
        result = original_lookup(repository, idempotency_key)
        if result is None and idempotency_key == "API-TXN-CONCURRENT":
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(
        PaymentRepository,
        "get_by_idempotency_key",
        synchronized_lookup,
    )
    payload = domestic_payment("API-TXN-CONCURRENT")

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: test_client.post("/payments", json=payload),
                range(2),
            )
        )

    assert sorted(response.status_code for response in responses) == [200, 201]
    assert len({response.json()["payment_id"] for response in responses}) == 1
    assert len(test_client.get("/payments").json()) == 1


@pytest.mark.parametrize(
    "payment",
    [
        {
            **domestic_payment(),
            "currency": "USD",
        },
        {
            **domestic_payment(),
            "amount": "NaN",
        },
        {
            **domestic_payment(),
            "amount": "Infinity",
        },
        {
            "source_account": "IN-ACC-1001",
            "destination_account": "IN-ACC-1001",
            "source_country": "IN",
            "destination_country": "IN",
            "payment_rail": "UPI",
            "amount": "100.00",
            "currency": "INR",
            "idempotency_key": "API-TXN-0002",
        },
    ],
)
def test_invalid_payment_returns_unprocessable_entity(test_client, payment):
    response = test_client.post("/payments", json=payment)

    assert response.status_code == 422


def test_missing_payment_returns_not_found(test_client):
    response = test_client.get("/payments/pay_missing")

    assert response.status_code == 404


def test_large_amount_returns_deterministic_failed_status(test_client):
    payment = domestic_payment("API-TXN-10000")
    payment["amount"] = "100000.00"

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 201
    assert response.json()["status"] == "FAILED"


def test_amount_below_simulation_threshold_succeeds(test_client):
    payment = domestic_payment("API-TXN-99999")
    payment["amount"] = "99999.99"

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 201
    assert response.json()["status"] == "SUCCESS"


def test_same_currency_fx_rate(test_client):
    response = test_client.get(
        "/payments/fx-rate",
        params={"base": "usd", "quote": "usd"},
    )

    assert response.status_code == 200
    rate = response.json()
    assert rate["base_currency"] == "USD"
    assert rate["quote_currency"] == "USD"
    assert rate["rate"] == 1
    assert rate["source"] == "identity"
    assert rate["is_fallback"] is False
    assert "rate_date" in rate
    assert "fetched_at" in rate


def test_test_client_uses_temporary_database_only(test_client):
    test_database = Path(test_client.app.state.test_database_path)

    assert test_database.exists()
    assert test_database.name == "test_payments.db"
    assert get_db in app.dependency_overrides


def test_cross_border_swift_same_currency_skips_conversion(test_client):
    payment = {
        "source_account": "US-ACC-1001",
        "destination_account": "PL-ACC-2001",
        "source_country": "US",
        "destination_country": "PL",
        "payment_rail": "SWIFT",
        "amount": "100.00",
        "currency": "USD",
        "destination_currency": "USD",
        "idempotency_key": "SWIFT-SAME-0001",
    }

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 201
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["exchange_rate"] is None
    assert response.json()["converted_amount"] is None


def test_cross_border_swift_converts_different_supported_currencies(
    test_client,
    monkeypatch,
):
    def fixed_rate(base, quote, fallback_rates=None):
        return FXRate(
            base_currency=base,
            quote_currency=quote,
            rate=Decimal("3.765432195"),
            rate_date=date(2026, 11, 26),
            source="Frankfurter",
            is_fallback=False,
            fetched_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        "backend.services.payment_service.get_exchange_rate",
        fixed_rate,
    )
    payment = {
        "source_account": "US-ACC-1001",
        "destination_account": "PL-ACC-2001",
        "source_country": "US",
        "destination_country": "PL",
        "payment_rail": "SWIFT",
        "amount": "100.00",
        "currency": "USD",
        "destination_currency": "PLN",
        "idempotency_key": "SWIFT-FX-0001",
    }

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 201
    payment_response = response.json()
    exchange_rate = Decimal(payment_response["exchange_rate"])
    converted_amount = Decimal(payment_response["converted_amount"])
    expected_amount = (Decimal("100.00") * exchange_rate).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    assert exchange_rate == Decimal("3.76543220")
    assert converted_amount == expected_amount == Decimal("376.54")
    fetched = test_client.get(
        f"/payments/{response.json()['payment_id']}"
    ).json()
    assert Decimal(fetched["exchange_rate"]) == exchange_rate
    assert Decimal(fetched["converted_amount"]) == converted_amount


@pytest.mark.parametrize(
    "changes",
    [
        {"destination_currency": None},
        {"destination_currency": "CAD"},
    ],
)
def test_swift_rejects_missing_or_unsupported_destination_currency(
    test_client,
    changes,
):
    payment = {
        "source_account": "US-ACC-1001",
        "destination_account": "PL-ACC-2001",
        "source_country": "US",
        "destination_country": "PL",
        "payment_rail": "SWIFT",
        "amount": "100.00",
        "currency": "USD",
        "destination_currency": "PLN",
        "idempotency_key": "SWIFT-INVALID-0001",
    }
    payment.update(changes)

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 422


def test_fx_provider_failure_returns_generic_api_error(test_client, monkeypatch):
    def fail_provider(*args, **kwargs):
        raise RuntimeError("private provider response")

    monkeypatch.setattr(
        "backend.services.payment_service.get_exchange_rate",
        fail_provider,
    )
    payment = {
        "source_account": "US-ACC-1001",
        "destination_account": "PL-ACC-2001",
        "source_country": "US",
        "destination_country": "PL",
        "payment_rail": "SWIFT",
        "amount": "100.00",
        "currency": "USD",
        "destination_currency": "PLN",
        "idempotency_key": "SWIFT-ERROR-0001",
    }

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 503
    assert "private provider response" not in response.text


@pytest.mark.parametrize(
    "field",
    ["source_account", "destination_account", "idempotency_key"],
)
def test_whitespace_only_identifiers_are_rejected(test_client, field):
    payment = domestic_payment()
    payment[field] = "   "

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 422


def test_identifiers_are_trimmed_before_storage(test_client):
    payment = domestic_payment()
    payment["source_account"] = "  IN-ACC-1001  "
    payment["destination_account"] = "  IN-ACC-1002  "
    payment["idempotency_key"] = "  API-TXN-TRIM  "

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 201
    assert response.json()["source_account"] == "IN-ACC-1001"
    assert response.json()["destination_account"] == "IN-ACC-1002"


@pytest.mark.parametrize(
    "source_account",
    ["IN", "I" * 35],
)
def test_invalid_account_identifier_lengths_are_rejected(
    test_client,
    source_account,
):
    payment = domestic_payment()
    payment["source_account"] = source_account

    response = test_client.post("/payments", json=payment)

    assert response.status_code == 422


def test_database_errors_are_not_exposed_to_api_consumers(
    test_client,
    monkeypatch,
):
    from sqlalchemy.exc import SQLAlchemyError

    def fail_database(repository):
        raise SQLAlchemyError("private database connection detail")

    monkeypatch.setattr(PaymentRepository, "list", fail_database)

    response = test_client.get("/payments")

    assert response.status_code == 503
    assert "private database connection detail" not in response.text


def test_payment_creation_database_errors_are_not_exposed(
    test_client,
    monkeypatch,
):
    from sqlalchemy.exc import SQLAlchemyError

    def fail_insert(repository, record):
        raise SQLAlchemyError("private database connection detail")

    monkeypatch.setattr(PaymentRepository, "add_or_get", fail_insert)

    response = test_client.post("/payments", json=domestic_payment())

    assert response.status_code == 503
    assert "private database connection detail" not in response.text
