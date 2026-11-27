import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.payment_service import (
    IdempotencyConflictError,
    PaymentService,
)
from mock_payment_service.models.payment import (
    Currency,
    PaymentRequest,
    PaymentResponse,
)
from mock_payment_service.services.fx_service import InvalidFallbackRateError


router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)


def _database_unavailable() -> HTTPException:
    logger.exception("Payment database operation failed")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Payment storage is temporarily unavailable.",
    )


def _parse_currency(value: str) -> Currency:
    try:
        return Currency(value.upper())
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported currency.",
        ) from error


@router.get("/fx-rate")
def get_fx_rate(
    base: str = Query(min_length=3, max_length=3),
    quote: str = Query(min_length=3, max_length=3),
    db: Session = Depends(get_db),
):
    base_currency = _parse_currency(base)
    quote_currency = _parse_currency(quote)
    try:
        fx_rate = PaymentService(db).get_fx_rate(
            base_currency.value,
            quote_currency.value,
        )
    except (RuntimeError, InvalidFallbackRateError) as error:
        logger.exception("FX reference-rate lookup failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FX reference rate is temporarily unavailable.",
        ) from error

    return {
        "base_currency": fx_rate.base_currency,
        "quote_currency": fx_rate.quote_currency,
        "rate": fx_rate.rate,
        "rate_date": fx_rate.rate_date,
        "source": fx_rate.source,
        "is_fallback": fx_rate.is_fallback,
        "fetched_at": fx_rate.fetched_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payment(
    request: PaymentRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        payment, created = PaymentService(db).create_payment(request)
    except InvalidFallbackRateError as error:
        logger.exception("Configured FX fallback rate is invalid")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FX reference rate is temporarily unavailable.",
        ) from error
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        logger.exception("FX reference-rate lookup failed during payment")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FX reference rate is temporarily unavailable.",
        ) from error
    except SQLAlchemyError as error:
        raise _database_unavailable() from error

    if not created:
        response.status_code = status.HTTP_200_OK
    return payment


@router.get("", response_model=list[PaymentResponse])
def list_payments(db: Session = Depends(get_db)):
    try:
        return PaymentService(db).list_payments()
    except SQLAlchemyError as error:
        raise _database_unavailable() from error


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
):
    try:
        payment = PaymentService(db).get_payment(payment_id)
    except SQLAlchemyError as error:
        raise _database_unavailable() from error
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )
    return payment