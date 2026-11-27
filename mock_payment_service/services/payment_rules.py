from mock_payment_service.models.payment import (
    CountryCode,
    Currency,
    PaymentRail,
    PaymentRequest,
)


DOMESTIC_PAYMENT_RULES = {
    PaymentRail.UPI: {
        "country": CountryCode.INDIA,
        "currency": Currency.INR,
    },
    PaymentRail.IMPS: {
        "country": CountryCode.INDIA,
        "currency": Currency.INR,
    },
    PaymentRail.NEFT: {
        "country": CountryCode.INDIA,
        "currency": Currency.INR,
    },
    PaymentRail.RTGS: {
        "country": CountryCode.INDIA,
        "currency": Currency.INR,
    },
    PaymentRail.ACH: {
        "country": CountryCode.UNITED_STATES,
        "currency": Currency.USD,
    },
    PaymentRail.SAME_DAY_ACH: {
        "country": CountryCode.UNITED_STATES,
        "currency": Currency.USD,
    },
    PaymentRail.FEDWIRE: {
        "country": CountryCode.UNITED_STATES,
        "currency": Currency.USD,
    },
    PaymentRail.FEDNOW: {
        "country": CountryCode.UNITED_STATES,
        "currency": Currency.USD,
    },
    PaymentRail.ELIXIR: {
        "country": CountryCode.POLAND,
        "currency": Currency.PLN,
    },
    PaymentRail.EXPRESS_ELIXIR: {
        "country": CountryCode.POLAND,
        "currency": Currency.PLN,
    },
    PaymentRail.EURO_ELIXIR: {
        "country": CountryCode.POLAND,
        "currency": Currency.EUR,
    },
    PaymentRail.BLIK: {
        "country": CountryCode.POLAND,
        "currency": Currency.PLN,
    },
    PaymentRail.SORBNET3: {
        "country": CountryCode.POLAND,
        "currency": Currency.PLN,
    },
}


SEPA_COUNTRIES = {
    CountryCode.POLAND,
    CountryCode.GERMANY,
    CountryCode.FRANCE,
    CountryCode.NETHERLANDS,
}


def validate_payment_request(payment: PaymentRequest) -> None:
    """
    Validate country, currency and rail compatibility for the simulation.

    SWIFT is cross-border only and requires a supported destination currency.
    Matching currencies do not trigger conversion; differing supported
    currencies are converted using the configured reference-rate service.
    """

    source_country = payment.source_country
    destination_country = payment.destination_country
    payment_rail = payment.payment_rail

    # Domestic payment validation
    if payment_rail in DOMESTIC_PAYMENT_RULES:

        rules = DOMESTIC_PAYMENT_RULES[payment_rail]

        if source_country != rules["country"]:
            raise ValueError(
                f"{payment_rail.value} is not supported "
                f"for source country {source_country.value}"
            )

        if destination_country != source_country:
            raise ValueError(
                f"{payment_rail.value} supports domestic "
                "payments only in this simulation"
            )

        if payment.currency != rules["currency"]:
            raise ValueError(
                f"{payment_rail.value} requires "
                f"{rules['currency'].value}"
            )

        if payment.destination_currency not in (
            None,
            payment.currency,
        ):
            raise ValueError(
                "Domestic payments cannot use a different "
                "destination currency"
            )

        return

    # SWIFT cross-border validation
    if payment_rail == PaymentRail.SWIFT:

        if source_country == destination_country:
            raise ValueError(
                "SWIFT simulation requires a cross-border payment"
            )

        if payment.destination_currency is None:
            raise ValueError(
                "Destination currency is required for SWIFT payments"
            )

        return

    # SEPA validation
    if payment_rail in (
        PaymentRail.SEPA_SCT,
        PaymentRail.SEPA_INST,
    ):

        if source_country not in SEPA_COUNTRIES:
            raise ValueError(
                "Source country is not supported for SEPA simulation"
            )

        if destination_country not in SEPA_COUNTRIES:
            raise ValueError(
                "Destination country is not supported for SEPA simulation"
            )

        if payment.currency != Currency.EUR:
            raise ValueError(
                "SEPA payments must use EUR"
            )

        if payment.destination_currency not in (
            None,
            Currency.EUR,
        ):
            raise ValueError(
                "SEPA destination currency must be EUR"
            )

        return

    raise ValueError(
        f"Unsupported payment rail: {payment_rail.value}"
    )