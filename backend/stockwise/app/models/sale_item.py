import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockwise.app.db.base import Base
from stockwise.app.db.ids import new_uuid


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=new_uuid,
    )

    sale_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_sale_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    unit_purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    gross_profit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    sale: Mapped["Sale"] = relationship(
        "Sale",
        back_populates="items",
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="sale_items",
    )

    __table_args__ = (
        Index("ix_sale_items_sale_id", "sale_id"),
        Index("ix_sale_items_product_id", "product_id"),
        UniqueConstraint(
            "sale_id",
            "product_id",
            name="uq_sale_items_sale_product",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_sale_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_sale_price >= 0 AND unit_purchase_price >= 0",
            name="ck_sale_items_unit_prices_non_negative",
        ),
        # Tolerances instead of equality: see the note on Sale.
        CheckConstraint(
            "ABS(subtotal - unit_sale_price * quantity) < 0.005",
            name="ck_sale_items_subtotal_consistent",
        ),
        CheckConstraint(
            "ABS(cost - unit_purchase_price * quantity) < 0.005",
            name="ck_sale_items_cost_consistent",
        ),
        CheckConstraint(
            "ABS(gross_profit - (subtotal - cost)) < 0.005",
            name="ck_sale_items_gross_profit_consistent",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SaleItem sale={self.sale_id} "
            f"product={self.product_id} quantity={self.quantity}>"
        )