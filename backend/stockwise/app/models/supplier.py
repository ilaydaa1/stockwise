import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from stockwise.app.db.base import Base
from stockwise.app.db.ids import new_uuid


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=new_uuid,
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Nominal number of days between placing an order and
    # receiving the goods.
    lead_time_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "name",
            name="uq_suppliers_business_name",
        ),
        CheckConstraint(
            "lead_time_days >= 0 AND lead_time_days <= 365",
            name="ck_suppliers_lead_time_days_range",
        ),
        # Target of the composite foreign key on products.
        UniqueConstraint(
            "business_id",
            "id",
            name="uq_suppliers_business_id_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<Supplier {self.name} lead={self.lead_time_days}d>"
