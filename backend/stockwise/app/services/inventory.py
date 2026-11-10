"""Stock changes.

Every change to ``Product.stock_quantity`` goes through
``apply_stock_change`` so that it is always paired with a
``StockMovement`` row recording the level before and after.

Functions here never commit. The caller owns the transaction, which
lets the API commit one request at a time and the data loader commit
in batches.
"""
from datetime import datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from stockwise.app.models.product import Product
from stockwise.app.models.stock_movement import StockMovement


INBOUND_TYPES = frozenset({"IN", "ADJUSTMENT_IN"})
OUTBOUND_TYPES = frozenset({"OUT", "ADJUSTMENT_OUT", "SALE"})


class InsufficientStockError(Exception):
    """An outbound movement asked for more units than are on hand."""


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
    note: str | None = None,
    at: datetime | None = None,
) -> StockMovement:
    """Change a product's stock and record the movement.

    ``product`` must already be locked by the caller (see
    ``lock_products``). ``at`` backdates the movement and is only
    used by the historical data loader; the API never passes it.
    """
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    stock_before = product.stock_quantity

    if movement_type in INBOUND_TYPES:
        stock_after = stock_before + quantity
    elif movement_type in OUTBOUND_TYPES:
        if stock_before < quantity:
            raise InsufficientStockError(
                f"product {product.id}: have {stock_before}, "
                f"need {quantity}"
            )

        stock_after = stock_before - quantity
    else:
        raise ValueError(f"unknown movement type: {movement_type}")

    product.stock_quantity = stock_after

    movement = StockMovement(
        business_id=product.business_id,
        product_id=product.id,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        note=note,
    )

    if at is not None:
        movement.created_at = at

    db.add(movement)

    return movement
