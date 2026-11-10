import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockwise.app.db.base import Base
from stockwise.app.db.ids import new_uuid


class SaleReturn(Base):
    """Units from one sale line that the customer brought back.

    The original sale and sale item are never modified. Net sales
    are gross sales minus ``refund_amount``; net cost of goods sold
    is gross cost minus ``cost_amount``. Both amounts are computed
    from the prices frozen on the sale item, not from the product's
    current prices.
    """

    __tablename__ = "sale_returns"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=new_uuid,
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )

    sale_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sale_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # quantity x the sale item's unit_sale_price
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    # quantity x the sale item's unit_purchase_price
    cost_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    sale_item: Mapped["SaleItem"] = relationship("SaleItem")

    __table_args__ = (
        Index("ix_sale_returns_sale_item_id", "sale_item_id"),
        Index(
            "ix_sale_returns_business_created_at",
            "business_id",
            "created_at",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_sale_returns_quantity_positive",
        ),
        CheckConstraint(
            "refund_amount >= 0 AND cost_amount >= 0",
            name="ck_sale_returns_amounts_non_negative",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SaleReturn item={self.sale_item_id} "
            f"quantity={self.quantity}>"
        )
