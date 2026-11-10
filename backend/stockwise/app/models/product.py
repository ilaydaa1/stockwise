import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockwise.app.db.base import Base
from stockwise.app.db.ids import new_uuid


def _initial_average_cost(context) -> Decimal:
    # A new product has no purchase history yet, so its average
    # cost starts at the purchase price it was created with.
    return context.get_current_parameters()["purchase_price"]


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=new_uuid,
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Both are optional. The composite foreign keys in
    # __table_args__ guarantee they belong to the same business.
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # Moving weighted average cost of the units currently in stock.
    # Maintained by services.inventory; never edited directly.
    # purchase_price above is the latest price paid to the supplier.
    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=_initial_average_cost,
    )

    stock_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    minimum_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="products",
    )

    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    sale_items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem",
        back_populates="product",
    )

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "sku",
            name="uq_products_business_sku",
        ),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_products_stock_quantity_non_negative",
        ),
        CheckConstraint(
            "minimum_stock >= 0",
            name="ck_products_minimum_stock_non_negative",
        ),
        CheckConstraint(
            "purchase_price >= 0 AND sale_price >= 0 "
            "AND average_cost >= 0",
            name="ck_products_prices_non_negative",
        ),
        ForeignKeyConstraint(
            ["business_id", "category_id"],
            ["categories.business_id", "categories.id"],
            name="fk_products_category_same_business",
        ),
        ForeignKeyConstraint(
            ["business_id", "supplier_id"],
            ["suppliers.business_id", "suppliers.id"],
            name="fk_products_supplier_same_business",
        ),
        Index("ix_products_business_id", "business_id"),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_supplier_id", "supplier_id"),
    )

    def __repr__(self) -> str:
        return f"<Product {self.sku} {self.name}>"