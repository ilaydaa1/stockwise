"""Stock changes and inventory costing.

Every change to ``Product.stock_quantity`` goes through
``apply_stock_change`` so that it is always paired with a
``StockMovement`` row recording the level before and after, and so
that the product's moving weighted average cost stays correct.

Costing rules (documented in docs/costing.md):

* IN       units enter at the price paid; the average is recalculated.
* OPENING  units enter at the product's purchase price.
* RETURN   units re-enter at the cost they were sold at.
* ADJUSTMENT_IN  found units enter at the current average, which
                 therefore does not move.
* OUT, ADJUSTMENT_OUT, SALE  units leave at the current average,
                 which therefore does not move.

Functions here never commit. The caller owns the transaction, which
lets the API commit one request at a time and the data loader commit
in batches.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from stockwise.app.models.product import Product
from stockwise.app.models.stock_movement import StockMovement


INBOUND_TYPES = frozenset({"IN", "ADJUSTMENT_IN", "OPENING", "RETURN"})
OUTBOUND_TYPES = frozenset({"OUT", "ADJUSTMENT_OUT", "SALE"})

# Movement types whose units arrive with their own cost and so
# change the weighted average.
_COSTED_INBOUND_TYPES = frozenset({"IN", "OPENING", "RETURN"})

COST_PRECISION = Decimal("0.0001")
PRICE_PRECISION = Decimal("0.01")


# Stock accumulates across movements, so each movement being bounded
# is not enough. This keeps the level inside the integer column.
MAX_STOCK_LEVEL = 1_000_000_000


class InsufficientStockError(Exception):
    """An outbound movement asked for more units than are on hand."""


class StockLimitExceededError(Exception):
    """An inbound movement would push stock past MAX_STOCK_LEVEL."""


def weighted_average_cost(
    *,
    stock_before: int,
    average_before: Decimal,
    quantity: int,
    unit_cost: Decimal,
) -> Decimal:
    """Average cost after ``quantity`` units arrive at ``unit_cost``."""
    total_value = (
        Decimal(stock_before) * average_before
        + Decimal(quantity) * unit_cost
    )

    return (total_value / Decimal(stock_before + quantity)).quantize(
        COST_PRECISION,
        rounding=ROUND_HALF_UP,
    )


def lock_products(
    db: Session,
    *,
    business_id: UUID,
    product_ids: Iterable[UUID],
    active_only: bool = True,
) -> dict[UUID, Product]:
    """Fetch products with row locks, keyed by id.

    Rows are locked in id order so that two concurrent transactions
    touching the same products cannot deadlock. Products that do not
    exist, belong to another business, or (by default) are inactive
    are simply absent from the result.
    """
    query = db.query(Product).filter(
        Product.id.in_(list(product_ids)),
        Product.business_id == business_id,
    )

    if active_only:
        query = query.filter(Product.is_active.is_(True))

    products = (
        query
        .order_by(Product.id)
        .with_for_update()
        .populate_existing()
        .all()
    )

    return {product.id: product for product in products}


def apply_stock_change(
    db: Session,
    *,
    product: Product,
    movement_type: str,
    quantity: int,
    unit_cost: Decimal | None = None,
    sale_id: UUID | None = None,
    sale_return_id: UUID | None = None,
    note: str | None = None,
    at: datetime | None = None,
) -> StockMovement:
    """Change a product's stock and record the movement.

    ``product`` must already be locked by the caller (see
    ``lock_products``).

    ``unit_cost`` is optional for IN and OPENING (defaulting to the
    product's purchase price), required for RETURN, and not accepted
    for any other type.

    ``at`` backdates the movement and is only used by the historical
    data loader; the API never passes it.
    """
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    if movement_type not in INBOUND_TYPES | OUTBOUND_TYPES:
        raise ValueError(f"unknown movement type: {movement_type}")

    if unit_cost is not None:
        if movement_type not in _COSTED_INBOUND_TYPES:
            raise ValueError(
                f"unit_cost is not accepted for {movement_type}"
            )

        unit_cost = Decimal(unit_cost)

        if unit_cost < 0:
            raise ValueError("unit_cost cannot be negative")

    elif movement_type == "RETURN":
        raise ValueError("RETURN requires the original unit cost")

    stock_before = product.stock_quantity
    average_before = Decimal(product.average_cost)

    if movement_type in OUTBOUND_TYPES:
        if stock_before < quantity:
            raise InsufficientStockError(
                f"product {product.id}: have {stock_before}, "
                f"need {quantity}"
            )

        stock_after = stock_before - quantity
        movement_cost = average_before

    else:
        stock_after = stock_before + quantity

        if stock_after > MAX_STOCK_LEVEL:
            raise StockLimitExceededError(
                f"product {product.id}: {stock_after} exceeds "
                f"{MAX_STOCK_LEVEL}"
            )

        if movement_type in _COSTED_INBOUND_TYPES:
            movement_cost = (
                unit_cost
                if unit_cost is not None
                else Decimal(product.purchase_price)
            )

            product.average_cost = weighted_average_cost(
                stock_before=stock_before,
                average_before=average_before,
                quantity=quantity,
                unit_cost=movement_cost,
            )

            if movement_type == "IN":
                # Remember the latest price paid to the supplier.
                product.purchase_price = movement_cost.quantize(
                    PRICE_PRECISION,
                    rounding=ROUND_HALF_UP,
                )

        else:
            movement_cost = average_before

    product.stock_quantity = stock_after

    movement = StockMovement(
        business_id=product.business_id,
        product_id=product.id,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        unit_cost=movement_cost,
        sale_id=sale_id,
        sale_return_id=sale_return_id,
        note=note,
    )

    if at is not None:
        movement.created_at = at

    db.add(movement)

    return movement
