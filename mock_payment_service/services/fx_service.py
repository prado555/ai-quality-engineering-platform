from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

import httpx


FRANKFURTER_BASE_URL = "https://api.frankfurter.dev"
CACHE_DURATION = timedelta(hours=24)
REQUEST_TIMEOUT = 10.0
EXCHANGE_RATE_QUANTUM = Decimal("0.00000001")
MONEY_QUANTUM = Decimal("0.01")


class InvalidFallbackRateError(ValueError):
    """Raised when an explicitly configured fallback rate is invalid."""


@dataclass
class FXRate:
    base_currency: str
    quote_currency: str
    rate: Decimal
    rate_date: date
    source: str
    is_fallback: bool
    fetched_at: datetime


# In-memory cache: {(base_currency, quote_currency): (FXRate, expiry_time)}
_rate_cache: dict[tuple[str, str], tuple[FXRate, datetime]] = {}


def get_exchange_rate(
    base_currency: str,
    quote_currency: str,
    fallback_rates: Optional[dict[tuple[str, str], Decimal]] = None,
) -> FXRate:
    """
    Fetch the latest available reference exchange rate.

    Frankfurter is the primary source. A configured fallback rate
    is used only when the API request fails.
    """

    base = base_currency.upper()
    quote = quote_currency.upper()

    if base == quote:
        return FXRate(
            base_currency=base,
            quote_currency=quote,
            rate=Decimal("1"),
            rate_date=date.today(),
            source="identity",
            is_fallback=False,
            fetched_at=datetime.now(timezone.utc),
        )

    cache_key = (base, quote)
    configured_fallback_rate = None
    if fallback_rates is not None and cache_key in fallback_rates:
        try:
            configured_fallback_rate = quantize_exchange_rate(
                Decimal(str(fallback_rates[cache_key]))
            )
        except (InvalidOperation, TypeError, ValueError) as fallback_error:
            raise InvalidFallbackRateError(
                "The configured fallback FX rate is invalid."
            ) from fallback_error

    now = datetime.now(timezone.utc)

    # Return a cached rate if it has not expired.
    cached = _rate_cache.get(cache_key)

    if cached and cached[1] > now:
        return cached[0]

    try:
        url = f"{FRANKFURTER_BASE_URL}/v2/rate/{base}/{quote}"

        response = httpx.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("The FX API returned an invalid response.")

        rate = quantize_exchange_rate(Decimal(str(data["rate"])))

        fx_rate = FXRate(
            base_currency=base,
            quote_currency=quote,
            rate=rate,
            rate_date=date.fromisoformat(data["date"]),
            source="Frankfurter",
            is_fallback=False,
            fetched_at=now,
        )

        # Cache the successfully retrieved rate.
        _rate_cache[cache_key] = (
            fx_rate,
            now + CACHE_DURATION,
        )

        return fx_rate

    except (
        httpx.HTTPError,
        KeyError,
        TypeError,
        ValueError,
        InvalidOperation,
    ) as error:

        # Use a fallback only when one has been explicitly configured.
        if configured_fallback_rate is None:
            raise RuntimeError(
                f"Unable to retrieve FX rate for {base}/{quote}, "
                "and no fallback rate is configured."
            ) from error

        return FXRate(
            base_currency=base,
            quote_currency=quote,
            rate=configured_fallback_rate,
            rate_date=date.today(),
            source="Configured fallback",
            is_fallback=True,
            fetched_at=datetime.now(timezone.utc),
        )


def convert_currency(
    amount: Decimal,
    exchange_rate: Decimal,
) -> Decimal:
    """
    Convert an amount using Decimal arithmetic.
    The result is rounded half-up to two decimal places.
    """

    if not amount.is_finite():
        raise ValueError("Amount must be finite.")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    if not exchange_rate.is_finite():
        raise ValueError("Exchange rate must be finite.")

    normalized_rate = quantize_exchange_rate(exchange_rate)
    converted_amount = amount * normalized_rate

    return converted_amount.quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def quantize_exchange_rate(exchange_rate: Decimal) -> Decimal:
    """Normalize rates half-up to the database's Numeric(18, 8) precision."""
    if not exchange_rate.is_finite():
        raise ValueError("Exchange rate must be finite.")

    if exchange_rate <= 0:
        raise ValueError("Exchange rate must be greater than zero.")

    try:
        normalized_rate = exchange_rate.quantize(
            EXCHANGE_RATE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
    except InvalidOperation as error:
        raise ValueError("Exchange rate exceeds supported precision.") from error

    if normalized_rate <= 0:
        raise ValueError("Exchange rate is below supported precision.")
    return normalized_rate