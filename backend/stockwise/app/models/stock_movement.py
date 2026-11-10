import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
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
        Index(
            "ix_stock_movements_product_id",
            "product_id",
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
    )

    def __repr__(self) -> str:
        return (
            f"<StockMovement "
            f"{self.movement_type} "
            f"{self.quantity} "
            f"product={self.product_id}>"
        )