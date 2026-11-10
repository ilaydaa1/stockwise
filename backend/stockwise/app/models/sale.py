import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockwise.app.db.base import Base
from stockwise.app.db.ids import new_uuid


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=new_uuid,
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    gross_profit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="sales",
    )

    items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_sales_business_id", "business_id"),
        Index("ix_sales_business_created_at", "business_id", "created_at"),
        CheckConstraint(
            "total_amount >= 0 AND total_cost >= 0",
            name="ck_sales_totals_non_negative",
        ),
        # Written as a tolerance rather than equality so the same
        # expression is safe on SQLite, which stores numerics as
        # floats. Amounts have two decimals, so 0.005 is exact.
        CheckConstraint(
            "ABS(gross_profit - (total_amount - total_cost)) < 0.005",
            name="ck_sales_gross_profit_consistent",
        ),
    )

    def __repr__(self) -> str:
        return f"<Sale {self.id} total={self.total_amount}>"