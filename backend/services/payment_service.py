from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.models.payment_record import PaymentRecord
from backend.services.payment_repository import PaymentRepository
from mock_payment_service.models.payment import (
    CountryCode,
    Currency,
    PaymentRail,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
)
from mock_payment_service.services.fx_service import (
    FXRate,
    convert_currency,
    get_exchange_rate,
    quantize_exchange_rate,
)
from mock_payment_service.services.payment_rules import validate_payment_request


FALLBACK_RATES = {
    ("USD", "INR"): Decimal("92.50"),
    ("INR", "USD"): Decimal("0.0108"),
    ("USD", "PLN"): Decimal("3.75"),
    ("PLN", "USD"): Decimal("0.267"),
    ("EUR", "USD"): Decimal("1.08"),
    ("USD", "EUR"): Decimal("0.93"),
}

# A deterministic simulation outcome, not a banking or payment-network limit.
SIMULATION_FAILURE_THRESHOLD = Decimal("100000")


class IdempotencyConflictError(ValueError):
    pass


class PaymentService:
    def __init__(self, db: Session):
        self.repository = PaymentRepository(db)

    def create_payment(self, request: PaymentRequest) -> tuple[PaymentResponse, bool]:
        validate_payment_request(request)

        existing = self.repository.get_by_idempotency_key(request.idempotency_key)
        if existing:
            if self._payload_differs(existing, request):
                raise IdempotencyConflictError(
                    "The idempotency key was already used with a different payment."
                )
            return self._to_response(existing), False

        destination_currency = (
            request.destination_currency
            if request.destination_currency is not None
            else request.currency
        )

        exchange_rate = None
        converted_amount = None

        if request.currency != destination_currency:
            fx_rate = get_exchange_rate(
                request.currency.value,
                destination_currency.value,
                fallback_rates=FALLBACK_RATES,
            )
            exchange_rate = quantize_exchange_rate(fx_rate.rate)
            converted_amount = convert_currency(request.amount, exchange_rate)

        if request.amount >= SIMULATION_FAILURE_THRESHOLD:
            status = PaymentStatus.FAILED
            message = "Payment simulation failed: amount exceeds the simulation limit."
        else:
            status = PaymentStatus.SUCCESS
            message = "Payment simulated successfully."

        record = PaymentRecord(
            payment_id=f"pay_{uuid4().hex}",
            idempotency_key=request.idempotency_key,
            source_account=request.source_account,
            destination_account=request.destination_account,
            source_country=request.source_country.value,
            destination_country=request.destination_country.value,
            payment_rail=request.payment_rail.value,
            amount=request.amount,
            currency=request.currency.value,
            destination_currency=destination_currency.value,
            exchange_rate=exchange_rate,
            converted_amount=converted_amount,
            status=status.value,
            message=message,
        )

        saved, created = self.repository.add_or_get(record)
        if not created and self._payload_differs(saved, request):
            raise IdempotencyConflictError(
                "The idempotency key was already used with a different payment."
            )
        return self._to_response(saved), created

    def get_payment(self, payment_id: str) -> PaymentResponse | None:
        record = self.repository.get_by_id(payment_id)
        if record is None:
            return None
        return self._to_response(record)

    def list_payments(self) -> list[PaymentResponse]:
        return [
            self._to_response(record)
            for record in self.repository.list()
        ]

    def get_fx_rate(self, base: str, quote: str) -> FXRate:
        return get_exchange_rate(
            base,
            quote,
            fallback_rates=FALLBACK_RATES,
        )

    def _payload_differs(
        self,
        record: PaymentRecord,
        request: PaymentRequest,
    ) -> bool:
        destination_currency = (
            request.destination_currency
            if request.destination_currency is not None
            else request.currency
        )
        fields = (
            record.source_account == request.source_account,
            record.destination_account == request.destination_account,
            record.source_country == request.source_country.value,
            record.destination_country == request.destination_country.value,
            record.payment_rail == request.payment_rail.value,
            Decimal(record.amount) == request.amount,
            record.currency == request.currency.value,
            record.destination_currency == destination_currency.value,
        )
        return not all(fields)

    def _to_response(self, record: PaymentRecord) -> PaymentResponse:
        return PaymentResponse(
            payment_id=record.payment_id,
            source_account=record.source_account,
            destination_account=record.destination_account,
            source_country=CountryCode(record.source_country),
            destination_country=CountryCode(record.destination_country),
            payment_rail=PaymentRail(record.payment_rail),
            amount=Decimal(record.amount),
            currency=Currency(record.currency),
            destination_currency=(
                Currency(record.destination_currency)
                if record.destination_currency
                else None
            ),
            exchange_rate=(
                Decimal(record.exchange_rate)
                if record.exchange_rate is not None
                else None
            ),
            converted_amount=(
                Decimal(record.converted_amount)
                if record.converted_amount is not None
                else None
            ),
            status=PaymentStatus(record.status),
            message=record.message,
            created_at=record.created_at,
        )
