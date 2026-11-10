"""Rules the database enforces even when the API is bypassed."""
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.supplier import Supplier
from tests.test_products import (
    _create_product as _api_create_product,
    _csrf_headers,
    _setup_business,
)
from tests.test_sales import _create_product, _create_user_and_business


def _expect_rejected(db, *rows):
    db.add_all(rows)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def _movement(business, product, **overrides):
    values = dict(
        business_id=business.id,
        product_id=product.id,
        movement_type="IN",
        quantity=5,
        stock_before=10,
        stock_after=15,
        unit_cost=Decimal("10.00"),
    )
    values.update(overrides)

    return StockMovement(**values)


def _sale(business, **overrides):
    values = dict(
        business_id=business.id,
        total_amount=Decimal("30.00"),
        total_cost=Decimal("20.00"),
        gross_profit=Decimal("10.00"),
    )
    values.update(overrides)

    return Sale(**values)


def _sale_item(sale, product, **overrides):
    values = dict(
        sale_id=sale.id,
        product_id=product.id,
        quantity=2,
        unit_sale_price=Decimal("15.00"),
        unit_purchase_price=Decimal("10.00"),
        subtotal=Decimal("30.00"),
        cost=Decimal("20.00"),
        gross_profit=Decimal("10.00"),
    )
    values.update(overrides)

    return SaleItem(**values)


@pytest.fixture
def setup(db_session):
    _, business = _create_user_and_business(db_session)
    product = _create_product(db_session, business)

    return db_session, business, product


class TestProductConstraints:
    @pytest.mark.parametrize(
        "field, value",
        [
            ("stock_quantity", -1),
            ("minimum_stock", -1),
            ("purchase_price", Decimal("-0.01")),
            ("sale_price", Decimal("-0.01")),
            ("average_cost", Decimal("-0.0001")),
        ],
    )
    def test_negative_values_rejected(self, setup, field, value):
        db, _, product = setup
        setattr(product, field, value)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()


class TestSupplierConstraints:
    @pytest.mark.parametrize("lead_time", [-1, 366])
    def test_lead_time_out_of_range_rejected(self, setup, lead_time):
        db, business, _ = setup

        _expect_rejected(
            db,
            Supplier(
                business_id=business.id,
                name="Tedarikçi",
                lead_time_days=lead_time,
            ),
        )


class TestStockMovementConstraints:
    def test_valid_movement_accepted(self, setup):
        db, business, product = setup

        db.add(_movement(business, product))
        db.commit()

    @pytest.mark.parametrize(
        "overrides",
        [
            # zero and negative quantities
            dict(quantity=0, stock_after=10),
            dict(quantity=-5, stock_after=5),
            # levels that do not add up
            dict(stock_after=14),
            dict(movement_type="OUT", unit_cost=None),
            dict(movement_type="SALE", stock_after=4, unit_cost=None),
            # negative levels
            dict(
                movement_type="OUT",
                stock_before=2,
                stock_after=-3,
                unit_cost=None,
            ),
            # unknown type
            dict(movement_type="TELEPORT"),
            # costs
            dict(unit_cost=Decimal("-1.00")),
            dict(unit_cost=None),
        ],
    )
    def test_invalid_movement_rejected(self, setup, overrides):
        db, business, product = setup

        _expect_rejected(db, _movement(business, product, **overrides))

    def test_timestamp_defaults_when_omitted_in_raw_sql(self, setup):
        db, business, product = setup

        db.execute(
            text(
                "INSERT INTO stock_movements (id, business_id, product_id,"
                " movement_type, quantity, stock_before, stock_after,"
                " unit_cost) VALUES (:id, :business_id, :product_id,"
                " 'IN', 1, 0, 1, 1)"
            ),
            {
                "id": "0" * 32,
                "business_id": business.id.hex,
                "product_id": product.id.hex,
            },
        )
        db.commit()

        created_at = db.execute(
            text("SELECT created_at FROM stock_movements")
        ).scalar_one()

        assert created_at is not None


class TestSaleConstraints:
    def test_valid_sale_accepted(self, setup):
        db, business, product = setup
        sale = _sale(business)
        db.add(sale)
        db.flush()
        db.add(_sale_item(sale, product))
        db.commit()

    @pytest.mark.parametrize(
        "overrides",
        [
            dict(gross_profit=Decimal("11.00")),
            dict(total_amount=Decimal("-30.00"), gross_profit=Decimal("-50")),
            dict(total_cost=Decimal("-20.00"), gross_profit=Decimal("50")),
        ],
    )
    def test_inconsistent_sale_totals_rejected(self, setup, overrides):
        db, business, _ = setup

        _expect_rejected(db, _sale(business, **overrides))

    @pytest.mark.parametrize(
        "overrides",
        [
            dict(quantity=0, subtotal=Decimal("0"), cost=Decimal("0"),
                 gross_profit=Decimal("0")),
            dict(subtotal=Decimal("31.00"), gross_profit=Decimal("11.00")),
            dict(cost=Decimal("19.00"), gross_profit=Decimal("11.00")),
            dict(gross_profit=Decimal("9.00")),
            dict(unit_sale_price=Decimal("-15.00"),
                 subtotal=Decimal("-30.00"), gross_profit=Decimal("-50.00")),
        ],
    )
    def test_inconsistent_sale_item_rejected(self, setup, overrides):
        db, business, product = setup
        sale = _sale(business)
        db.add(sale)
        db.commit()

        _expect_rejected(db, _sale_item(sale, product, **overrides))

    def test_same_product_twice_in_one_sale_rejected(self, setup):
        db, business, product = setup
        sale = _sale(business)
        db.add(sale)
        db.flush()
        db.add(_sale_item(sale, product))
        db.commit()

        _expect_rejected(db, _sale_item(sale, product))

    def test_prices_with_cents_pass_the_consistency_checks(self, setup):
        """Guards the float-safe form of the checks on SQLite."""
        db, business, product = setup
        sale = _sale(
            business,
            total_amount=Decimal("59.97"),
            total_cost=Decimal("32.01"),
            gross_profit=Decimal("27.96"),
        )
        db.add(sale)
        db.flush()
        db.add(
            _sale_item(
                sale,
                product,
                quantity=3,
                unit_sale_price=Decimal("19.99"),
                unit_purchase_price=Decimal("10.67"),
                subtotal=Decimal("59.97"),
                cost=Decimal("32.01"),
                gross_profit=Decimal("27.96"),
            )
        )
        db.commit()


class TestSaleReturnConstraints:
    @pytest.mark.parametrize(
        "overrides",
        [
            dict(quantity=0),
            dict(quantity=-1),
            dict(refund_amount=Decimal("-1.00")),
            dict(cost_amount=Decimal("-1.00")),
        ],
    )
    def test_invalid_return_rejected(self, setup, overrides):
        db, business, product = setup
        sale = _sale(business)
        db.add(sale)
        db.flush()
        item = _sale_item(sale, product)
        db.add(item)
        db.commit()

        values = dict(
            business_id=business.id,
            sale_item_id=item.id,
            quantity=1,
            refund_amount=Decimal("15.00"),
            cost_amount=Decimal("10.00"),
        )
        values.update(overrides)

        _expect_rejected(db, SaleReturn(**values))


class TestRequestBounds:
    def test_oversized_quantities_rejected(self, client):
        _setup_business(client)
        product_id = _api_create_product(client).json()["id"]

        movement = client.post(
            "/api/stock-movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 1_000_001,
            },
            headers=_csrf_headers(client),
        )
        sale = client.post(
            "/api/sales",
            json={
                "items": [{"product_id": product_id, "quantity": 1_000_001}]
            },
            headers=_csrf_headers(client),
        )

        assert movement.status_code == 422
        assert sale.status_code == 422

    @pytest.mark.parametrize("field", ["stock_quantity", "minimum_stock"])
    def test_oversized_product_stock_rejected(self, client, field):
        _setup_business(client)

        response = _api_create_product(client, **{field: 1_000_001})

        assert response.status_code == 422

    def test_accumulated_stock_cannot_pass_the_limit(self, client, db_session):
        _setup_business(client)
        product_id = _api_create_product(client).json()["id"]

        product = db_session.query(Product).one()
        product.stock_quantity = 999_999_999
        db_session.commit()

        response = client.post(
            "/api/stock-movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 2,
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "STOCK_LIMIT_EXCEEDED"

    def test_sale_total_too_large_rejected(self, client):
        _setup_business(client)
        product_id = _api_create_product(
            client,
            sale_price="9999999999.99",
            stock_quantity=1000,
        ).json()["id"]

        response = client.post(
            "/api/sales",
            json={"items": [{"product_id": product_id, "quantity": 500}]},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "SALE_TOTAL_TOO_LARGE"
