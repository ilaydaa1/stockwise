"""Sale creation.

A sale is all-or-nothing: every product row is locked, every line is
checked against stock, and only then are the sale, its items and the
stock movements written. Prices are read from the product at that
moment and stored on the sale item, so later price changes never
alter historical revenue or profit.

``create_sale`` flushes but does not commit; the caller owns the
transaction.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.services.inventory import (
    InsufficientStockError,
    apply_stock_change,
    lock_products,
)


# Largest total that fits the Numeric(14, 2) columns on sales.
MAX_SALE_TOTAL = Decimal("999999999999.99")


class SaleTotalTooLargeError(Exception):
    """The sale total does not fit the amount columns."""


class DuplicateProductError(Exception):
    """The same product appears on more than one line."""


class ProductNotFoundError(Exception):
    """A product is missing, inactive, or owned by another business."""


def create_sale(
    db: Session,
    *,
    business_id: UUID,
    items: Sequence[tuple[UUID, int]],
    at: datetime | None = None,
) -> Sale:
    """Create a sale from ``(product_id, quantity)`` lines.

    ``at`` backdates the sale and its stock movements. It exists for
    the historical data loader; the API never passes it.
    """
    if not items:
        raise ValueError("a sale needs at least one line")

    product_ids = [product_id for product_id, _ in items]

    if len(product_ids) != len(set(product_ids)):
        raise DuplicateProductError()

    products = lock_products(
        db,
        business_id=business_id,
        product_ids=product_ids,
    )

    if len(products) != len(product_ids):
        raise ProductNotFoundError()

    # Check every line before changing anything, so one short line
    # leaves all stock untouched.
    for product_id, quantity in items:
        if products[product_id].stock_quantity < quantity:
            raise InsufficientStockError(
                f"product {product_id}: have "
                f"{products[product_id].stock_quantity}, need {quantity}"
            )

    lines = []
    total_amount = Decimal("0.00")
    total_cost = Decimal("0.00")

    for product_id, quantity in items:
        product = products[product_id]

        unit_sale_price = Decimal(product.sale_price)
        # Cost of goods sold uses the moving weighted average cost
        # at the moment of sale, frozen on the sale item.
        unit_purchase_price = Decimal(product.average_cost).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        subtotal = unit_sale_price * quantity
        cost = unit_purchase_price * quantity

        total_amount += subtotal
        total_cost += cost

        lines.append(
            (
                product,
                quantity,
                unit_sale_price,
                unit_purchase_price,
                subtotal,
                cost,
            )
        )

    if total_amount > MAX_SALE_TOTAL or total_cost > MAX_SALE_TOTAL:
        raise SaleTotalTooLargeError()

    sale = Sale(
        business_id=business_id,
        total_amount=total_amount,
        total_cost=total_cost,
        gross_profit=total_amount - total_cost,
    )

    if at is not None:
        sale.created_at = at

    db.add(sale)

    # Assigns sale.id without committing.
    db.flush()

    for (
        product,
        quantity,
        unit_sale_price,
        unit_purchase_price,
        subtotal,
        cost,
    ) in lines:
        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=quantity,
                unit_sale_price=unit_sale_price,
                unit_purchase_price=unit_purchase_price,
                subtotal=subtotal,
                cost=cost,
                gross_profit=subtotal - cost,
            )
        )

        apply_stock_change(
            db,
            product=product,
            movement_type="SALE",
            quantity=quantity,
            sale_id=sale.id,
            note=f"Sale {sale.id}",
            at=at,
        )

    db.flush()

    return sale
