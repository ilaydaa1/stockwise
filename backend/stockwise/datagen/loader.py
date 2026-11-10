"""Replays simulated events into the database.

Events go through the same services the API uses (``create_sale``,
``create_return``, ``apply_stock_change``), in chronological order.
Imported history is therefore subject to exactly the same stock
checks, costing and constraints as live transactions, and a bug in
the simulation fails loudly instead of writing inconsistent rows.

All data is written to one dedicated demo account, identified by
``DEMO_USER_EMAIL``. Nothing outside that account is touched.
"""
import os
from dataclasses import dataclass
from datetime import datetime, time, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from stockwise.app.core.security import hash_password
from stockwise.app.db.ids import deterministic_uuids
from stockwise.app.models.business import Business
from stockwise.app.models.category import Category
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.session import AuthSession
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.supplier import Supplier
from stockwise.app.models.user import User
from stockwise.app.services.inventory import apply_stock_change
from stockwise.app.services.returns import create_return
from stockwise.app.services.sales import create_sale
from stockwise.datagen import config as cfg
from stockwise.datagen.simulation import (
    PriceChanged,
    ProductCreated,
    ReturnMade,
    SaleMade,
    SimulationResult,
    StockAdjusted,
    StockReceived,
)


DEMO_PASSWORD_ENV = "DEMO_USER_PASSWORD"

# Not a valid password hash, so nobody can log in with it.
UNUSABLE_PASSWORD_HASH = "!"

COMMIT_EVERY_EVENTS = 2000


class DemoDataExistsError(Exception):
    """The demo account already holds data; pass reset to replace it."""


@dataclass(frozen=True)
class LoadResult:
    business_id: UUID
    events_loaded: int
    demo_login_enabled: bool


def find_demo_business(db: Session) -> Business | None:
    return (
        db.query(Business)
        .join(User, User.id == Business.owner_id)
        .filter(User.email == cfg.DEMO_USER_EMAIL)
        .first()
    )


def delete_demo_data(db: Session) -> bool:
    """Remove the demo account and everything it owns.

    Rows are deleted explicitly, children first, rather than relying
    on database cascades, so this behaves the same on SQLite.
    """
    user = db.query(User).filter(User.email == cfg.DEMO_USER_EMAIL).first()

    if user is None:
        return False

    business_ids = select(Business.id).where(Business.owner_id == user.id)
    sale_ids = select(Sale.id).where(Sale.business_id.in_(business_ids))

    for statement in (
        delete(StockMovement).where(
            StockMovement.business_id.in_(business_ids)
        ),
        delete(SaleReturn).where(SaleReturn.business_id.in_(business_ids)),
        delete(SaleItem).where(SaleItem.sale_id.in_(sale_ids)),
        delete(Sale).where(Sale.business_id.in_(business_ids)),
        delete(Product).where(Product.business_id.in_(business_ids)),
        delete(Category).where(Category.business_id.in_(business_ids)),
        delete(Supplier).where(Supplier.business_id.in_(business_ids)),
        delete(Business).where(Business.owner_id == user.id),
        delete(AuthSession).where(AuthSession.user_id == user.id),
        delete(User).where(User.id == user.id),
    ):
        db.execute(statement.execution_options(synchronize_session=False))

    db.commit()
    db.expire_all()

    return True


def _demo_password_hash() -> tuple[str, bool]:
    password = os.environ.get(DEMO_PASSWORD_ENV)

    if password:
        return hash_password(password), True

    return UNUSABLE_PASSWORD_HASH, False


def load(
    db: Session,
    result: SimulationResult,
    *,
    reset: bool = False,
) -> LoadResult:
    """Write the simulated history into the demo account."""
    if find_demo_business(db) is not None or (
        db.query(User).filter(User.email == cfg.DEMO_USER_EMAIL).first()
    ):
        if not reset:
            raise DemoDataExistsError()

        delete_demo_data(db)

    config = result.config
    password_hash, login_enabled = _demo_password_hash()

    opened_at = datetime.combine(
        config.start,
        time(7, 0),
        tzinfo=ZoneInfo(config.timezone),
    ).astimezone(timezone.utc)

    # Seeded identifiers make two runs with the same seed produce
    # identical rows, and therefore identical exported files.
    with deterministic_uuids(config.seed):
        user = User(
            email=cfg.DEMO_USER_EMAIL,
            name=cfg.DEMO_USER_NAME,
            hashed_password=password_hash,
            created_at=opened_at,
            updated_at=opened_at,
        )
        db.add(user)
        db.flush()

        business = Business(
            owner_id=user.id,
            name=cfg.DEMO_BUSINESS_NAME,
            currency="TRY",
            timezone=config.timezone,
            created_at=opened_at,
            updated_at=opened_at,
        )
        db.add(business)
        db.flush()

        categories: dict[str, Category] = {}

        for spec in config.categories:
            categories[spec.key] = Category(
                business_id=business.id,
                name=spec.name,
                created_at=opened_at,
            )

        suppliers: dict[str, Supplier] = {}

        for spec in config.suppliers:
            suppliers[spec.key] = Supplier(
                business_id=business.id,
                name=spec.name,
                lead_time_days=spec.lead_time_days,
                created_at=opened_at,
            )

        db.add_all([*categories.values(), *suppliers.values()])
        db.flush()

        products: dict[str, Product] = {}
        sale_ids: dict[int, UUID] = {}

        # Only sales that are later returned need to be remembered.
        returned_refs = {
            event.sale_ref
            for event in result.events
            if isinstance(event, ReturnMade)
        }

        for count, event in enumerate(result.events, start=1):
            if isinstance(event, SaleMade):
                sale = create_sale(
                    db,
                    business_id=business.id,
                    items=[
                        (products[sku].id, quantity)
                        for sku, quantity in event.lines
                    ],
                    at=event.at,
                )

                if event.ref in returned_refs:
                    sale_ids[event.ref] = sale.id

            elif isinstance(event, StockReceived):
                apply_stock_change(
                    db,
                    product=products[event.sku],
                    movement_type="IN",
                    quantity=event.quantity,
                    unit_cost=event.unit_cost,
                    note=event.note,
                    at=event.at,
                )

            elif isinstance(event, ReturnMade):
                sale_id = sale_ids[event.sale_ref]

                sale_item_id = (
                    db.query(SaleItem.id)
                    .filter(
                        SaleItem.sale_id == sale_id,
                        SaleItem.product_id == products[event.sku].id,
                    )
                    .scalar()
                )

                create_return(
                    db,
                    business_id=business.id,
                    sale_id=sale_id,
                    lines=[(sale_item_id, event.quantity)],
                    reason=event.reason,
                    at=event.at,
                )

            elif isinstance(event, StockAdjusted):
                apply_stock_change(
                    db,
                    product=products[event.sku],
                    movement_type=event.movement_type,
                    quantity=event.quantity,
                    note=event.note,
                    at=event.at,
                )

            elif isinstance(event, PriceChanged):
                products[event.sku].sale_price = event.price

            elif isinstance(event, ProductCreated):
                product = Product(
                    business_id=business.id,
                    category_id=categories[event.category].id,
                    supplier_id=suppliers[event.supplier].id,
                    name=event.name,
                    sku=event.sku,
                    purchase_price=event.cost,
                    sale_price=event.price,
                    average_cost=event.cost,
                    stock_quantity=0,
                    minimum_stock=event.minimum_stock,
                    created_at=event.at,
                    updated_at=event.at,
                )
                db.add(product)
                db.flush()

                products[event.sku] = product

                if event.opening_stock > 0:
                    apply_stock_change(
                        db,
                        product=product,
                        movement_type="OPENING",
                        quantity=event.opening_stock,
                        unit_cost=event.cost,
                        note="Açılış stoku",
                        at=event.at,
                    )

            else:
                raise TypeError(f"unknown event: {event!r}")

            # The services reload product rows when they lock them,
            # so every change must reach the database first.
            db.flush()

            if count % COMMIT_EVERY_EVENTS == 0:
                db.commit()

        db.commit()

    return LoadResult(
        business_id=business.id,
        events_loaded=len(result.events),
        demo_login_enabled=login_enabled,
    )
