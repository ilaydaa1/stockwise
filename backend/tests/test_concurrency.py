"""Simultaneous transactions.

These only mean something on PostgreSQL: SQLite ignores row locks, so
they are skipped unless TEST_DATABASE_URL points at PostgreSQL.

Each worker uses its own database session, as separate API requests
would, and all workers are released at the same moment.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest

from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.services.integrity import check_integrity
from stockwise.app.services.inventory import (
    InsufficientStockError,
    apply_stock_change,
    lock_products,
)
from stockwise.app.services.returns import (
    ReturnExceedsSoldError,
    create_return,
)
from stockwise.app.services.sales import create_sale
from tests.conftest import TestingSessionLocal
from tests.test_sales import _create_user_and_business


pytestmark = pytest.mark.postgres_only


def _run_together(workers: int, action):
    """Run ``action(session)`` in ``workers`` threads at once.

    Returns one outcome per worker: "ok" or the name of the exception
    the action raised.
    """
    barrier = Barrier(workers)

    def attempt(_):
        session = TestingSessionLocal()

        try:
            barrier.wait(timeout=10)
            action(session)
            session.commit()

            return "ok"
        except (InsufficientStockError, ReturnExceedsSoldError) as error:
            session.rollback()

            return type(error).__name__
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(attempt, range(workers)))


def _product(db, business, stock):
    """A product whose stock entered through the ledger."""
    product = Product(
        business_id=business.id,
        name="Eşzamanlı Ürün",
        sku="CON-001",
        purchase_price=Decimal("10.00"),
        sale_price=Decimal("15.00"),
        stock_quantity=0,
    )
    db.add(product)
    db.flush()

    if stock:
        apply_stock_change(
            db,
            product=product,
            movement_type="OPENING",
            quantity=stock,
            unit_cost=Decimal("10.00"),
        )

    db.commit()

    return product.id


def test_two_buyers_of_the_last_unit_only_one_succeeds(db_session):
    _, business = _create_user_and_business(db_session)
    business_id = business.id
    product_id = _product(db_session, business, stock=1)

    outcomes = _run_together(
        2,
        lambda session: create_sale(
            session,
            business_id=business_id,
            items=[(product_id, 1)],
        ),
    )

    assert sorted(outcomes) == ["InsufficientStockError", "ok"]

    db_session.expire_all()

    assert db_session.get(Product, product_id).stock_quantity == 0
    assert db_session.query(Sale).count() == 1
    assert db_session.query(SaleItem).count() == 1
    assert check_integrity(db_session, business_id) == []


def test_many_buyers_never_oversell(db_session):
    _, business = _create_user_and_business(db_session)
    business_id = business.id
    product_id = _product(db_session, business, stock=3)

    outcomes = _run_together(
        8,
        lambda session: create_sale(
            session,
            business_id=business_id,
            items=[(product_id, 1)],
        ),
    )

    assert outcomes.count("ok") == 3
    assert outcomes.count("InsufficientStockError") == 5

    db_session.expire_all()

    assert db_session.get(Product, product_id).stock_quantity == 0
    assert (
        db_session.query(StockMovement)
        .filter(StockMovement.movement_type == "SALE")
        .count()
        == 3
    )
    # Every movement started exactly where the previous one ended.
    assert check_integrity(db_session, business_id) == []


def test_simultaneous_deliveries_are_all_counted(db_session):
    """Without row locks, two updates can read the same starting
    level and one of them is lost."""
    _, business = _create_user_and_business(db_session)
    business_id = business.id
    product_id = _product(db_session, business, stock=5)

    def receive(session):
        product = lock_products(
            session,
            business_id=business_id,
            product_ids=[product_id],
        )[product_id]

        apply_stock_change(
            session,
            product=product,
            movement_type="IN",
            quantity=2,
            unit_cost=Decimal("12.00"),
        )

    outcomes = _run_together(10, receive)

    assert outcomes == ["ok"] * 10

    db_session.expire_all()

    assert db_session.get(Product, product_id).stock_quantity == 25
    assert check_integrity(db_session, business_id) == []


def test_simultaneous_returns_cannot_exceed_what_was_sold(db_session):
    _, business = _create_user_and_business(db_session)
    business_id = business.id
    product_id = _product(db_session, business, stock=10)

    sale = create_sale(
        db_session,
        business_id=business_id,
        items=[(product_id, 5)],
    )
    db_session.commit()

    sale_id = sale.id
    sale_item_id = db_session.query(SaleItem.id).scalar()

    # Each asks for 3 of the 5 units; both together would be 6.
    outcomes = _run_together(
        2,
        lambda session: create_return(
            session,
            business_id=business_id,
            sale_id=sale_id,
            lines=[(sale_item_id, 3)],
        ),
    )

    assert sorted(outcomes) == ["ReturnExceedsSoldError", "ok"]

    db_session.expire_all()

    assert db_session.query(SaleReturn).count() == 1
    assert db_session.get(Product, product_id).stock_quantity == 8
    assert check_integrity(db_session, business_id) == []


def test_sale_and_delivery_at_the_same_time_both_apply(db_session):
    _, business = _create_user_and_business(db_session)
    business_id = business.id
    product_id = _product(db_session, business, stock=4)

    def sell(session):
        create_sale(
            session,
            business_id=business_id,
            items=[(product_id, 4)],
        )

    def receive(session):
        product = lock_products(
            session,
            business_id=business_id,
            product_ids=[product_id],
        )[product_id]

        apply_stock_change(
            session,
            product=product,
            movement_type="IN",
            quantity=6,
            unit_cost=Decimal("10.00"),
        )

    actions = [sell, receive]
    barrier = Barrier(2)

    def attempt(action):
        session = TestingSessionLocal()

        try:
            barrier.wait(timeout=10)
            action(session)
            session.commit()
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(attempt, actions))

    db_session.expire_all()

    # 4 - 4 + 6, whichever order the database chose.
    assert db_session.get(Product, product_id).stock_quantity == 6
    assert check_integrity(db_session, business_id) == []
