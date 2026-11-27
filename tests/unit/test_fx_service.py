from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import httpx
import pytest

from mock_payment_service.services.fx_service import (
    get_exchange_rate,
    convert_currency,
    _rate_cache,
)


@pytest.fixture(autouse=True)
def clear_fx_cache():
    """Clear the FX cache before and after every test."""
    _rate_cache.clear()
    yield
    _rate_cache.clear()


def test_get_exchange_rate_success():
    """Verify successful FX rate retrieval."""

    mock_response = {
        "date": "2026-11-26",
        "base": "USD",
        "quote": "INR",
        "rate": 92.41,
    }

    with patch(
        "mock_payment_service.services.fx_service.httpx.get"
    ) as mock_get:

        mock_get.return_value = httpx.Response(
            200,
            json=mock_response,
            request=httpx.Request(
                "GET",
                "https://api.frankfurter.dev/v2/rate/USD/INR",
            ),
        )

        result = get_exchange_rate("USD", "INR")

    assert result.rate == Decimal("92.41")
    assert result.base_currency == "USD"
    assert result.quote_currency == "INR"
    assert result.source == "Frankfurter"
    assert result.is_fallback is False


def test_same_currency_exchange_rate():
    """Verify identical currencies return exchange rate 1."""

    result = get_exchange_rate("USD", "USD")

    assert result.rate == Decimal("1")
    assert result.source == "identity"


def test_currency_conversion():
    """Verify currency conversion using Decimal."""

    result = convert_currency(
        Decimal("100.00"),
        Decimal("92.41"),
    )

    assert result == Decimal("9241.00")


def test_currency_conversion_rejects_zero_amount():
    """Verify zero amount is rejected."""

    with pytest.raises(ValueError):
        convert_currency(
            Decimal("0"),
            Decimal("92.41"),
        )


def test_currency_conversion_rejects_negative_amount():
    with pytest.raises(ValueError):
        convert_currency(
            Decimal("-1"),
            Decimal("92.41"),
        )


def test_currency_conversion_rejects_negative_rate():
    """Verify negative exchange rate is rejected."""

    with pytest.raises(ValueError):
        convert_currency(
            Decimal("100"),
            Decimal("-1"),
        )


@pytest.mark.parametrize("amount", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_currency_conversion_rejects_non_finite_amounts(amount):
    with pytest.raises(ValueError):
        convert_currency(amount, Decimal("2"))


@pytest.mark.parametrize(
    "exchange_rate",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_currency_conversion_rejects_invalid_exchange_rates(exchange_rate):
    with pytest.raises(ValueError):
        convert_currency(Decimal("10"), exchange_rate)


@pytest.mark.parametrize(
    "provider_rate",
    [
        "NaN",
        "Infinity",
        "-Infinity",
        "0",
        "-1",
        "0.000000001",
    ],
)
def test_provider_invalid_rates_are_rejected(provider_rate):
    response = {
        "date": "2026-11-26",
        "rate": provider_rate,
    }

    with patch(
        "mock_payment_service.services.fx_service.httpx.get"
    ) as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=response,
            request=httpx.Request(
                "GET",
                "https://api.frankfurter.dev/v2/rate/USD/INR",
            ),
        )

        with pytest.raises(RuntimeError, match="Unable to retrieve FX rate"):
            get_exchange_rate("USD", "INR")


@pytest.mark.parametrize(
    "provider_response",
    [
        [],
        {"rate": "92.4"},
        {"date": "not-a-date", "rate": "92.4"},
        {"date": "2026-11-26", "rate": "not-a-number"},
    ],
)
def test_invalid_provider_responses_are_rejected(provider_response):
    with patch(
        "mock_payment_service.services.fx_service.httpx.get"
    ) as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=provider_response,
            request=httpx.Request(
                "GET",
                "https://api.frankfurter.dev/v2/rate/USD/INR",
            ),
        )

        with pytest.raises(RuntimeError, match="Unable to retrieve FX rate"):
            get_exchange_rate("USD", "INR")


def test_fx_rate_uses_cache():
    """Verify repeated requests reuse the cached rate."""

    mock_response = {
        "date": "2026-11-26",
        "base": "USD",
        "quote": "INR",
        "rate": 92.41,
    }

    with patch(
        "mock_payment_service.services.fx_service.httpx.get"
    ) as mock_get:

        mock_get.return_value = httpx.Response(
            200,
            json=mock_response,
            request=httpx.Request(
                "GET",
                "https://api.frankfurter.dev/v2/rate/USD/INR",
            ),
        )

        first = get_exchange_rate("USD", "INR")
        second = get_exchange_rate("USD", "INR")

    assert first is second
    assert mock_get.call_count == 1


def test_fx_fallback_on_api_failure():
    """Verify configured fallback is used when API fails."""

    fallback = {
        ("USD", "INR"): Decimal("92.50")
    }

    with patch(
        "mock_payment_service.services.fx_service.httpx.get",
        side_effect=httpx.ConnectError("Connection failed"),
    ):

        result = get_exchange_rate(
            "USD",
            "INR",
            fallback_rates=fallback,
        )

    assert result.rate == Decimal("92.50")
    assert result.source == "Configured fallback"
    assert result.is_fallback is True


@pytest.mark.parametrize(
    "fallback_rate",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("0"),
        Decimal("-1"),
        Decimal("0.000000001"),
        None,
        "invalid",
    ],
)
def test_invalid_fallback_rates_are_rejected(fallback_rate):
    with patch(
        "mock_payment_service.services.fx_service.httpx.get",
        side_effect=httpx.ConnectError("Connection failed"),
    ):
        with pytest.raises(ValueError, match="fallback FX rate is invalid"):
            get_exchange_rate(
                "USD",
                "INR",
                fallback_rates={("USD", "INR"): fallback_rate},
            )


def test_invalid_configured_fallback_is_rejected_when_provider_succeeds():
    mock_response = {
        "date": "2026-11-26",
        "rate": "92.41",
    }

    with patch(
        "mock_payment_service.services.fx_service.httpx.get"
    ) as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=mock_response,
            request=httpx.Request(
                "GET",
                "https://api.frankfurter.dev/v2/rate/USD/INR",
            ),
        )

        with pytest.raises(ValueError, match="fallback FX rate is invalid"):
            get_exchange_rate(
                "USD",
                "INR",
                fallback_rates={("USD", "INR"): Decimal("NaN")},
            )

    mock_get.assert_not_called()


def test_fx_failure_without_fallback():
    """Verify API failure raises an error without fallback."""

    with patch(
        "mock_payment_service.services.fx_service.httpx.get",
        side_effect=httpx.ConnectError("Connection failed"),
    ):

        with pytest.raises(RuntimeError):
            get_exchange_rate("USD", "INR")


def test_expired_cache_entry_is_refreshed():
    first_response = {
        "date": "2026-11-26",
        "rate": "92.41",
    }
    second_response = {
        "date": "2026-11-27",
        "rate": "92.42",
    }

    with patch(
        "mock_payment_service.services.fx_service.httpx.get"
    ) as mock_get:
        mock_get.side_effect = [
            httpx.Response(
                200,
                json=first_response,
                request=httpx.Request("GET", "https://api.frankfurter.dev/v2/rate/USD/INR"),
            ),
            httpx.Response(
                200,
                json=second_response,
                request=httpx.Request("GET", "https://api.frankfurter.dev/v2/rate/USD/INR"),
            ),
        ]
        first = get_exchange_rate("USD", "INR")
        _rate_cache[("USD", "INR")] = (
            first,
            datetime.now(timezone.utc) - timedelta(seconds=1),
        )

        refreshed = get_exchange_rate("USD", "INR")

    assert refreshed.rate == Decimal("92.42000000")
    assert mock_get.call_count == 2


def test_exchange_rate_is_normalized_to_database_precision():
    mock_response = {
        "date": "2026-11-26",
        "rate": "3.765432195",
    }

    with patch(
        "mock_payment_service.services.fx_service.httpx.get"
    ) as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=mock_response,
            request=httpx.Request(
                "GET",
                "https://api.frankfurter.dev/v2/rate/USD/PLN",
            ),
        )
        rate = get_exchange_rate("USD", "PLN")
        converted = convert_currency(Decimal("100"), rate.rate)

    assert rate.rate == Decimal("3.76543220")
    assert converted == Decimal("376.54")