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


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=new_uuid,
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    movement_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stock_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stock_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Cost per unit used to value this movement. For IN it is the
    # price paid; for every other type it is the cost the units
    # carried (see docs/costing.md). Null only on rows that predate
    # cost tracking and could not be backfilled.
    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4),
        nullable=True,
    )

    # Set on SALE movements (and on RETURN movements, which point
    # back at the original sale).
    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sales.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Set on RETURN movements.
    sale_return_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sale_returns.id", ondelete="SET NULL"),
        nullable=True,
    )

    note: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="stock_movements",
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="stock_movements",
    )

    __table_args__ = (
        Index(
            "ix_stock_movements_business_id",
            "business_id",
        ),
        # Serves both "movements of a product" and the ordered
        # ledger walk used by the integrity checks.
        Index(
            "ix_stock_movements_product_created_at",
            "product_id",
            "created_at",
        ),
        Index(
            "ix_stock_movements_created_at",
            "created_at",
        ),
        Index(
            "ix_stock_movements_sale_id",
            "sale_id",
        ),
        Index(
            "ix_stock_movements_sale_return_id",
            "sale_return_id",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_stock_movements_quantity_positive",
        ),
        CheckConstraint(
            "stock_before >= 0 AND stock_after >= 0",
            name="ck_stock_movements_levels_non_negative",
        ),
        # Restricts the type to the known list and ties the levels
        # to the quantity in the direction that type implies.
        CheckConstraint(
            "(movement_type IN ('IN', 'ADJUSTMENT_IN', 'OPENING', 'RETURN')"
            " AND stock_after = stock_before + quantity)"
            " OR "
            "(movement_type IN ('OUT', 'ADJUSTMENT_OUT', 'SALE')"
            " AND stock_after = stock_before - quantity)",
            name="ck_stock_movements_type_matches_levels",
        ),
        CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name="ck_stock_movements_unit_cost_non_negative",
        ),
        CheckConstraint(
            "movement_type <> 'IN' OR unit_cost IS NOT NULL",
            name="ck_stock_movements_stock_in_has_unit_cost",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<StockMovement "
            f"{self.movement_type} "
            f"{self.quantity} "
            f"product={self.product_id}>"
        )