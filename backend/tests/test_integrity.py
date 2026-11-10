"""The integrity checks must pass on data written through the API
and must each detect the specific corruption they exist for."""
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import text

from stockwise.app.models.business import Business
from stockwise.app.models.category import Category
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.services.integrity import check_integrity
from tests.test_products import (
    _create_business,
    _create_product,
    _csrf_headers,
    _register_and_login,
    _setup_business,
)


def _post(client, path, payload):
    response = client.post(path, json=payload, headers=_csrf_headers(client))

    assert response.status_code == 201, response.text

    return response.json()


@pytest.fixture
def history(client, db_session):
    """A small but complete history: opening stock, purchases at a
    new cost, adjustments, sales and a partial return."""
    _setup_business(client)

    first = _create_product(client, sku="A-1", stock_quantity=20).json()
    second = _create_product(client, sku="B-1", stock_quantity=0).json()

    _post(client, "/api/stock-movements", {
        "product_id": second["id"],
        "movement_type": "IN",
        "quantity": 12,
        "unit_cost": "7.50",
    })
    _post(client, "/api/stock-movements", {
        "product_id": first["id"],
        "movement_type": "IN",
        "quantity": 10,
        "unit_cost": "13.00",
    })
    _post(client, "/api/stock-movements", {
        "product_id": first["id"],
        "movement_type": "ADJUSTMENT_OUT",
        "quantity": 1,
    })

    sale = _post(client, "/api/sales", {
        "items": [
            {"product_id": first["id"], "quantity": 4},
            {"product_id": second["id"], "quantity": 3},
        ]
    })

    _post(client, f"/api/sales/{sale['id']}/returns", {
        "items": [
            {"sale_item_id": sale["items"][0]["id"], "quantity": 2},
        ]
    })

    _post(client, "/api/sales", {
        "items": [{"product_id": first["id"], "quantity": 5}]
    })

    business_id = db_session.query(Business).one().id

    return db_session, business_id


def _checks(db, business_id) -> set[str]:
    db.expire_all()

    return {issue.check for issue in check_integrity(db, business_id)}


def test_history_written_through_the_api_is_clean(history):
    db, business_id = history

    assert check_integrity(db, business_id) == []


def test_empty_business_is_clean(client, db_session):
    _setup_business(client)

    assert check_integrity(
        db_session, db_session.query(Business).one().id
    ) == []


def test_issue_reports_count_and_examples(history):
    db, business_id = history
    db.query(Product).update({Product.stock_quantity: 999})
    db.commit()

    issues = check_integrity(db, business_id)

    assert len(issues) == 1
    assert issues[0].check == "stock_level_mismatch"
    assert issues[0].count == 2
    assert len(issues[0].examples) == 2
    assert issues[0].description


class TestLedger:
    def test_detects_stock_changed_without_a_movement(self, history):
        db, business_id = history
        product = db.query(Product).filter(Product.sku == "A-1").one()
        product.stock_quantity += 1
        db.commit()

        assert _checks(db, business_id) == {"stock_level_mismatch"}

    def test_detects_a_deleted_movement(self, history):
        db, business_id = history
        movement = (
            db.query(StockMovement)
            .filter(StockMovement.movement_type == "ADJUSTMENT_OUT")
            .one()
        )
        db.delete(movement)
        db.commit()

        assert "ledger_chain_broken" in _checks(db, business_id)

    def test_detects_a_movement_starting_from_the_wrong_level(self, history):
        db, business_id = history
        movement = (
            db.query(StockMovement)
            .filter(StockMovement.movement_type == "ADJUSTMENT_OUT")
            .one()
        )
        movement.stock_before += 3
        movement.stock_after += 3
        db.commit()

        assert "ledger_chain_broken" in _checks(db, business_id)

    def test_detects_stock_that_never_entered_the_ledger(
        self, client, db_session
    ):
        _setup_business(client)
        business = db_session.query(Business).one()

        # Inserted directly, bypassing the OPENING movement.
        db_session.add(
            Product(
                business_id=business.id,
                name="Kayıt dışı",
                sku="X-1",
                purchase_price=Decimal("5.00"),
                sale_price=Decimal("9.00"),
                stock_quantity=7,
            )
        )
        db_session.commit()

        assert _checks(db_session, business.id) == {"stock_level_mismatch"}

    def test_detects_wrong_average_cost(self, history):
        db, business_id = history
        product = db.query(Product).filter(Product.sku == "A-1").one()
        product.average_cost = Decimal(product.average_cost) + Decimal("1")
        db.commit()

        assert _checks(db, business_id) == {"average_cost_mismatch"}

    def test_detects_sale_movement_without_sale_link(self, history):
        db, business_id = history
        movement = (
            db.query(StockMovement)
            .filter(StockMovement.movement_type == "SALE")
            .first()
        )
        movement.sale_id = None
        db.commit()

        assert {
            "movement_missing_link",
            "sale_item_movement_mismatch",
        } <= _checks(db, business_id)


class TestSales:
    def test_detects_sale_item_quantity_changed_after_the_fact(
        self, history
    ):
        db, business_id = history
        item = db.query(SaleItem).filter(SaleItem.quantity == 5).one()

        # Keep the row internally consistent so only the cross-row
        # checks can notice.
        item.quantity = 6
        item.subtotal = Decimal(item.unit_sale_price) * 6
        item.cost = Decimal(item.unit_purchase_price) * 6
        item.gross_profit = Decimal(item.subtotal) - Decimal(item.cost)
        db.commit()

        assert {
            "sale_item_movement_mismatch",
            "sale_totals_mismatch",
        } <= _checks(db, business_id)

    def test_detects_sale_totals_not_matching_items(self, history):
        db, business_id = history
        sale = db.query(Sale).first()
        sale.total_amount = Decimal(sale.total_amount) + Decimal("10")
        sale.gross_profit = Decimal(sale.gross_profit) + Decimal("10")
        db.commit()

        assert _checks(db, business_id) == {"sale_totals_mismatch"}


class TestReturns:
    def test_detects_return_larger_than_the_sale_line(self, history):
        db, business_id = history
        sale_return = db.query(SaleReturn).one()
        sale_return.quantity = 50
        db.commit()

        assert {
            "return_exceeds_sold",
            "return_movement_mismatch",
            "return_amount_mismatch",
        } <= _checks(db, business_id)

    def test_detects_refund_not_matching_frozen_price(self, history):
        db, business_id = history
        sale_return = db.query(SaleReturn).one()
        sale_return.refund_amount = Decimal("1.00")
        db.commit()

        assert _checks(db, business_id) == {"return_amount_mismatch"}

    def test_detects_return_dated_before_its_sale(self, history):
        db, business_id = history
        sale_return = db.query(SaleReturn).one()
        sale_return.created_at = sale_return.created_at - timedelta(days=30)
        db.commit()

        assert "return_before_sale" in _checks(db, business_id)


class TestChronology:
    def test_detects_movement_dated_before_its_product(self, history):
        db, business_id = history
        product = db.query(Product).filter(Product.sku == "B-1").one()
        product.created_at = product.created_at + timedelta(days=30)
        db.commit()

        assert "movement_before_product" in _checks(db, business_id)


class TestTenantBoundaries:
    def test_detects_references_into_another_business(
        self, client, history
    ):
        db, business_id = history

        client.cookies.clear()
        _register_and_login(client, email="other@example.com", name="Other")
        _create_business(client, name="Diğer İşletme")

        other_business_id = (
            db.query(Business.id)
            .filter(Business.id != business_id)
            .scalar()
        )

        foreign_category = Category(
            business_id=other_business_id,
            name="Yabancı",
        )
        db.add(foreign_category)
        db.flush()

        # SQLite does not enforce foreign keys by default, which lets
        # this test write what PostgreSQL would refuse.
        product = db.query(Product).filter(Product.sku == "A-1").one()
        product.category_id = foreign_category.id

        movement = db.query(StockMovement).first()
        movement.business_id = other_business_id
        db.commit()

        assert {
            "product_reference_crosses_business",
            "movement_crosses_business",
        } <= _checks(db, business_id)
