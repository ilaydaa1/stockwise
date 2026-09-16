import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockwise.app.db.base import Base


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
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
        Index("ix_stock_movements_business_id", "business_id"),
        Index("ix_stock_movements_product_id", "product_id"),
        Index("ix_stock_movements_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<StockMovement {self.movement_type} {self.quantity} product={self.product_id}>"
