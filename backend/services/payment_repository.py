from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.payment_record import PaymentRecord


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, payment_id: str) -> PaymentRecord | None:
        return self.db.get(PaymentRecord, payment_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> PaymentRecord | None:
        statement = select(PaymentRecord).where(
            PaymentRecord.idempotency_key == idempotency_key
        )
        return self.db.execute(statement).scalar_one_or_none()

    def list(self) -> list[PaymentRecord]:
        statement = select(PaymentRecord).order_by(
            PaymentRecord.created_at.desc()
        )
        return list(self.db.execute(statement).scalars().all())

    def add_or_get(
        self,
        record: PaymentRecord,
    ) -> tuple[PaymentRecord, bool]:
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.get_by_idempotency_key(record.idempotency_key)
            if existing is None:
                raise
            return existing, False

        self.db.refresh(record)
        return record, True
