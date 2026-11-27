from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.database import Base
from backend.models.payment_record import PaymentRecord
from backend.services.payment_repository import PaymentRepository


def payment_record(payment_id: str) -> PaymentRecord:
    return PaymentRecord(
        payment_id=payment_id,
        idempotency_key="REPOSITORY-TXN-01",
        source_account="IN-ACC-1001",
        destination_account="IN-ACC-1002",
        source_country="IN",
        destination_country="IN",
        payment_rail="UPI",
        amount=Decimal("10.00"),
        currency="INR",
        destination_currency="INR",
        status="SUCCESS",
        message="Payment simulated successfully.",
    )


def test_integrity_conflict_rolls_back_and_returns_existing_record(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'repository.db'}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        repository = PaymentRepository(session)
        original, created = repository.add_or_get(payment_record("pay_original"))

        assert created is True
        existing, created = repository.add_or_get(payment_record("pay_duplicate"))

        assert created is False
        assert existing.payment_id == original.payment_id
        assert session.is_active
        assert len(repository.list()) == 1

    engine.dispose()
