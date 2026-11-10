"""Consistency checks across the stock ledger, sales and returns.

Database constraints validate one row at a time. The checks here
validate relationships between rows that a constraint cannot
express, for example that each movement starts from the level the
previous one ended on.

``check_integrity`` returns a list of issues; an empty list means the
business's records reconcile. It is read-only.

The queries use SQLAlchemy constructs (including window functions)
so they run unchanged on PostgreSQL and on the SQLite test database.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from stockwise.app.models.category import Category
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.supplier import Supplier
from stockwise.app.services.inventory import weighted_average_cost


MAX_EXAMPLES = 5
MONEY_TOLERANCE = Decimal("0.005")
COSTED_INBOUND_TYPES = ("IN", "OPENING", "RETURN")


@dataclass
class IntegrityIssue:
    check: str
    description: str
    count: int
    examples: list[str] = field(default_factory=list)


def _issue(
    check: str,
    description: str,
    ids: list,
) -> list[IntegrityIssue]:
    if not ids:
        return []

    return [
        IntegrityIssue(
            check=check,
            description=description,
            count=len(ids),
            examples=[str(value) for value in ids[:MAX_EXAMPLES]],
        )
    ]


def _ids(db: Session, statement) -> list:
    return [row[0] for row in db.execute(statement).all()]


# ----------------------------------------------------------------- ledger


def _check_ledger_chain(db: Session, business_id: UUID):
    """Each movement must start where the previous one ended.

    The first movement of a product must start from zero, because
    opening stock is itself recorded as a movement.
    """
    previous_level = func.lag(StockMovement.stock_after).over(
        partition_by=StockMovement.product_id,
        order_by=(StockMovement.created_at, StockMovement.id),
    )

    ledger = (
        select(
            StockMovement.id.label("id"),
            StockMovement.stock_before.label("stock_before"),
            func.coalesce(previous_level, 0).label("expected_before"),
        )
        .where(StockMovement.business_id == business_id)
        .subquery()
    )

    return _issue(
        "ledger_chain_broken",
        "stock movement does not start from the level the previous "
        "movement of the same product ended on",
        _ids(
            db,
            select(ledger.c.id).where(
                ledger.c.stock_before != ledger.c.expected_before
            ),
        ),
    )


def _check_stock_matches_ledger(db: Session, business_id: UUID):
    """Current stock must equal the level after the last movement."""
    position = func.row_number().over(
        partition_by=StockMovement.product_id,
        order_by=(
            StockMovement.created_at.desc(),
            StockMovement.id.desc(),
        ),
    )

    ranked = (
        select(
            StockMovement.product_id.label("product_id"),
            StockMovement.stock_after.label("stock_after"),
            position.label("position"),
        )
        .where(StockMovement.business_id == business_id)
        .subquery()
    )

    latest = (
        select(ranked.c.product_id, ranked.c.stock_after)
        .where(ranked.c.position == 1)
        .subquery()
    )

    return _issue(
        "stock_level_mismatch",
        "product stock differs from the level after its last movement",
        _ids(
            db,
            select(Product.id)
            .outerjoin(latest, latest.c.product_id == Product.id)
            .where(
                Product.business_id == business_id,
                Product.stock_quantity
                != func.coalesce(latest.c.stock_after, 0),
            ),
        ),
    )


def _check_average_cost(db: Session, business_id: UUID):
    """Replay every movement and compare the resulting average cost."""
    products = {
        product.id: product
        for product in db.query(Product)
        .filter(Product.business_id == business_id)
        .all()
    }

    averages: dict[UUID, Decimal | None] = {}
    unverifiable: set[UUID] = set()

    movements = (
        db.query(
            StockMovement.product_id,
            StockMovement.movement_type,
            StockMovement.quantity,
            StockMovement.stock_before,
            StockMovement.unit_cost,
        )
        .filter(StockMovement.business_id == business_id)
        .order_by(
            StockMovement.product_id,
            StockMovement.created_at,
            StockMovement.id,
        )
    )

    for product_id, movement_type, quantity, stock_before, unit_cost in (
        movements
    ):
        if movement_type not in COSTED_INBOUND_TYPES:
            continue

        if unit_cost is None:
            unverifiable.add(product_id)
            continue

        average = averages.get(product_id)

        if average is None:
            if stock_before != 0:
                # Stock existed before any costed movement, so its
                # cost is unknown and the replay cannot be trusted.
                unverifiable.add(product_id)
                continue

            average = Decimal("0")

        averages[product_id] = weighted_average_cost(
            stock_before=stock_before,
            average_before=average,
            quantity=quantity,
            unit_cost=Decimal(unit_cost),
        )

    mismatched = [
        product_id
        for product_id, average in averages.items()
        if product_id not in unverifiable
        and average is not None
        and Decimal(products[product_id].average_cost) != average
    ]

    return _issue(
        "average_cost_mismatch",
        "product average cost differs from the value obtained by "
        "replaying its stock movements",
        mismatched,
    )


def _check_movement_links(db: Session, business_id: UUID):
    return _issue(
        "movement_missing_link",
        "SALE movement without a sale, or RETURN movement without a "
        "return",
        _ids(
            db,
            select(StockMovement.id).where(
                StockMovement.business_id == business_id,
                or_(
                    and_(
                        StockMovement.movement_type == "SALE",
                        StockMovement.sale_id.is_(None),
                    ),
                    and_(
                        StockMovement.movement_type == "RETURN",
                        StockMovement.sale_return_id.is_(None),
                    ),
                ),
            ),
        ),
    )


# ------------------------------------------------------------------ sales


def _check_sale_items_have_movements(db: Session, business_id: UUID):
    """Every sale line needs exactly one SALE movement of equal size."""
    matching = (
        select(func.count(StockMovement.id))
        .where(
            StockMovement.sale_id == SaleItem.sale_id,
            StockMovement.product_id == SaleItem.product_id,
            StockMovement.movement_type == "SALE",
            StockMovement.quantity == SaleItem.quantity,
        )
        .correlate(SaleItem)
        .scalar_subquery()
    )

    return _issue(
        "sale_item_movement_mismatch",
        "sale item does not have exactly one matching SALE movement",
        _ids(
            db,
            select(SaleItem.id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.business_id == business_id, matching != 1),
        ),
    )


def _check_sale_totals(db: Session, business_id: UUID):
    totals = (
        select(
            SaleItem.sale_id.label("sale_id"),
            func.sum(SaleItem.subtotal).label("amount"),
            func.sum(SaleItem.cost).label("cost"),
        )
        .group_by(SaleItem.sale_id)
        .subquery()
    )

    return _issue(
        "sale_totals_mismatch",
        "sale totals differ from the sum of its items",
        _ids(
            db,
            select(Sale.id)
            .outerjoin(totals, totals.c.sale_id == Sale.id)
            .where(
                Sale.business_id == business_id,
                or_(
                    func.abs(
                        Sale.total_amount
                        - func.coalesce(totals.c.amount, 0)
                    )
                    >= MONEY_TOLERANCE,
                    func.abs(
                        Sale.total_cost - func.coalesce(totals.c.cost, 0)
                    )
                    >= MONEY_TOLERANCE,
                ),
            ),
        ),
    )


# ---------------------------------------------------------------- returns


def _check_returns_within_sold(db: Session, business_id: UUID):
    returned = (
        select(
            SaleReturn.sale_item_id.label("sale_item_id"),
            func.sum(SaleReturn.quantity).label("quantity"),
        )
        .where(SaleReturn.business_id == business_id)
        .group_by(SaleReturn.sale_item_id)
        .subquery()
    )

    return _issue(
        "return_exceeds_sold",
        "more units returned than were sold on the sale item",
        _ids(
            db,
            select(SaleItem.id)
            .join(returned, returned.c.sale_item_id == SaleItem.id)
            .where(returned.c.quantity > SaleItem.quantity),
        ),
    )


def _check_returns_have_movements(db: Session, business_id: UUID):
    matching = (
        select(func.count(StockMovement.id))
        .where(
            StockMovement.sale_return_id == SaleReturn.id,
            StockMovement.movement_type == "RETURN",
            StockMovement.quantity == SaleReturn.quantity,
        )
        .correlate(SaleReturn)
        .scalar_subquery()
    )

    return _issue(
        "return_movement_mismatch",
        "return does not have exactly one matching RETURN movement",
        _ids(
            db,
            select(SaleReturn.id).where(
                SaleReturn.business_id == business_id,
                matching != 1,
            ),
        ),
    )


def _check_return_amounts(db: Session, business_id: UUID):
    return _issue(
        "return_amount_mismatch",
        "refund or cost amount differs from the prices frozen on the "
        "sale item",
        _ids(
            db,
            select(SaleReturn.id)
            .join(SaleItem, SaleItem.id == SaleReturn.sale_item_id)
            .where(
                SaleReturn.business_id == business_id,
                or_(
                    func.abs(
                        SaleReturn.refund_amount
                        - SaleItem.unit_sale_price * SaleReturn.quantity
                    )
                    >= MONEY_TOLERANCE,
                    func.abs(
                        SaleReturn.cost_amount
                        - SaleItem.unit_purchase_price * SaleReturn.quantity
                    )
                    >= MONEY_TOLERANCE,
                ),
            ),
        ),
    )


# ------------------------------------------------------------- chronology


def _check_chronology(db: Session, business_id: UUID):
    issues = _issue(
        "movement_before_product",
        "stock movement is dated before its product was created",
        _ids(
            db,
            select(StockMovement.id)
            .join(Product, Product.id == StockMovement.product_id)
            .where(
                StockMovement.business_id == business_id,
                StockMovement.created_at < Product.created_at,
            ),
        ),
    )

    issues += _issue(
        "return_before_sale",
        "return is dated before the sale it refers to",
        _ids(
            db,
            select(SaleReturn.id)
            .join(SaleItem, SaleItem.id == SaleReturn.sale_item_id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(
                SaleReturn.business_id == business_id,
                SaleReturn.created_at < Sale.created_at,
            ),
        ),
    )

    return issues


# ----------------------------------------------------------- multi-tenant


def _check_tenant_boundaries(db: Session, business_id: UUID):
    """No record of this business may reference another business."""
    issues = _issue(
        "movement_crosses_business",
        "stock movement and its product belong to different businesses",
        _ids(
            db,
            select(StockMovement.id)
            .join(Product, Product.id == StockMovement.product_id)
            .where(
                or_(
                    StockMovement.business_id == business_id,
                    Product.business_id == business_id,
                ),
                StockMovement.business_id != Product.business_id,
            ),
        ),
    )

    issues += _issue(
        "sale_item_crosses_business",
        "sale and the product on one of its items belong to different "
        "businesses",
        _ids(
            db,
            select(SaleItem.id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(Product, Product.id == SaleItem.product_id)
            .where(
                or_(
                    Sale.business_id == business_id,
                    Product.business_id == business_id,
                ),
                Sale.business_id != Product.business_id,
            ),
        ),
    )

    issues += _issue(
        "return_crosses_business",
        "return and its sale belong to different businesses",
        _ids(
            db,
            select(SaleReturn.id)
            .join(SaleItem, SaleItem.id == SaleReturn.sale_item_id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(
                or_(
                    SaleReturn.business_id == business_id,
                    Sale.business_id == business_id,
                ),
                SaleReturn.business_id != Sale.business_id,
            ),
        ),
    )

    category = aliased(Category)
    supplier = aliased(Supplier)

    issues += _issue(
        "product_reference_crosses_business",
        "product references a category or supplier of another business",
        _ids(
            db,
            select(Product.id)
            .outerjoin(category, category.id == Product.category_id)
            .outerjoin(supplier, supplier.id == Product.supplier_id)
            .where(
                Product.business_id == business_id,
                or_(
                    and_(
                        Product.category_id.is_not(None),
                        func.coalesce(
                            category.business_id != Product.business_id,
                            True,
                        ),
                    ),
                    and_(
                        Product.supplier_id.is_not(None),
                        func.coalesce(
                            supplier.business_id != Product.business_id,
                            True,
                        ),
                    ),
                ),
            ),
        ),
    )

    return issues


CHECKS = (
    _check_ledger_chain,
    _check_stock_matches_ledger,
    _check_average_cost,
    _check_movement_links,
    _check_sale_items_have_movements,
    _check_sale_totals,
    _check_returns_within_sold,
    _check_returns_have_movements,
    _check_return_amounts,
    _check_chronology,
    _check_tenant_boundaries,
)


def check_integrity(
    db: Session,
    business_id: UUID,
) -> list[IntegrityIssue]:
    """Run every check for one business. Empty list means clean."""
    issues: list[IntegrityIssue] = []

    for check in CHECKS:
        issues.extend(check(db, business_id))

    return issues
