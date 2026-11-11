"""Customer returns.

A return always refers to a line of an existing sale. It restores
stock through a RETURN movement and records the refund, without
touching the original sale or sale item. A cancelled sale is simply
a return of every line.

``create_return`` flushes but does not commit; the caller owns the
transaction.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.services.inventory import (
    apply_stock_change,
    lock_products,
)


class SaleNotFoundError(Exception):
    """The sale is missing or owned by another business."""


class SaleItemNotFoundError(Exception):
    """A line does not belong to the sale being returned."""


class DuplicateReturnLineError(Exception):
    """The same sale item appears on more than one return line."""


class ReturnExceedsSoldError(Exception):
    """Returned units would exceed the units sold on that line."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def return_totals(
    db: Session,
    *,
    business_id: UUID,
    since: datetime,
) -> tuple[Decimal, Decimal]:
    """Refunds and returned cost on or after ``since`` (UTC).

    Returns ``(refund_total, returned_cost_total)``. A return is
    counted in the period in which it happened, not the period of
    the original sale. The profit given back by returns is the
    refund minus the cost of the units that came back.
    """
    refunds, cost = (
        db.query(
            func.coalesce(func.sum(SaleReturn.refund_amount), 0),
            func.coalesce(func.sum(SaleReturn.cost_amount), 0),
        )
        .filter(
            SaleReturn.business_id == business_id,
            SaleReturn.created_at >= since,
        )
        .one()
    )

    cents = Decimal("0.01")

    return (
        Decimal(str(refunds)).quantize(cents),
        Decimal(str(cost)).quantize(cents),
    )


def returned_quantities(
    db: Session,
    sale_item_ids: Sequence[UUID],
) -> dict[UUID, int]:
    """Units already returned for each sale item."""
    rows = (
        db.query(
            SaleReturn.sale_item_id,
            func.coalesce(func.sum(SaleReturn.quantity), 0),
        )
        .filter(SaleReturn.sale_item_id.in_(list(sale_item_ids)))
        .group_by(SaleReturn.sale_item_id)
        .all()
    )

    return {sale_item_id: int(quantity) for sale_item_id, quantity in rows}


def create_return(
    db: Session,
    *,
    business_id: UUID,
    sale_id: UUID,
    lines: Sequence[tuple[UUID, int]],
    reason: str | None = None,
    at: datetime | None = None,
) -> list[SaleReturn]:
    """Return ``(sale_item_id, quantity)`` lines of one sale.

    All lines succeed or none do. ``at`` backdates the return and is
    only used by the historical data loader.
    """
    if not lines:
        raise ValueError("a return needs at least one line")

    sale_item_ids = [sale_item_id for sale_item_id, _ in lines]

    if len(sale_item_ids) != len(set(sale_item_ids)):
        raise DuplicateReturnLineError()

    for _, quantity in lines:
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")

    # Locking the sale row serialises concurrent returns of the same
    # sale, so two requests cannot both pass the quantity check.
    sale = (
        db.query(Sale)
        .filter(
            Sale.id == sale_id,
            Sale.business_id == business_id,
        )
        .with_for_update()
        .first()
    )

    if not sale:
        raise SaleNotFoundError()

    if at is not None and _as_utc(at) < _as_utc(sale.created_at):
        raise ValueError("a return cannot predate its sale")

    items = {
        item.id: item
        for item in (
            db.query(SaleItem)
            .filter(
                SaleItem.sale_id == sale.id,
                SaleItem.id.in_(sale_item_ids),
            )
            .all()
        )
    }

    if len(items) != len(sale_item_ids):
        raise SaleItemNotFoundError()

    already_returned = returned_quantities(db, sale_item_ids)

    for sale_item_id, quantity in lines:
        remaining = (
            items[sale_item_id].quantity
            - already_returned.get(sale_item_id, 0)
        )

        if quantity > remaining:
            raise ReturnExceedsSoldError(
                f"sale item {sale_item_id}: {remaining} left to "
                f"return, asked for {quantity}"
            )

    # A product may have been deactivated since the sale; the units
    # still come back into its stock.
    products = lock_products(
        db,
        business_id=business_id,
        product_ids=[item.product_id for item in items.values()],
        active_only=False,
    )

    created: list[SaleReturn] = []

    for sale_item_id, quantity in lines:
        item = items[sale_item_id]

        sale_return = SaleReturn(
            business_id=business_id,
            sale_item_id=item.id,
            quantity=quantity,
            refund_amount=Decimal(item.unit_sale_price) * quantity,
            cost_amount=Decimal(item.unit_purchase_price) * quantity,
            reason=reason,
        )

        if at is not None:
            sale_return.created_at = at

        db.add(sale_return)
        db.flush()

        # Units re-enter stock at the cost they left with, which
        # reverses the cost of goods sold for exactly these units.
        apply_stock_change(
            db,
            product=products[item.product_id],
            movement_type="RETURN",
            quantity=quantity,
            unit_cost=Decimal(item.unit_purchase_price),
            sale_id=sale.id,
            sale_return_id=sale_return.id,
            note=f"Return of sale {sale.id}",
            at=at,
        )

        created.append(sale_return)

    db.flush()

    return created
