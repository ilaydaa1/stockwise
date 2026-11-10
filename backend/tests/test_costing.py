"""Moving weighted average cost and the stock ledger."""
from decimal import Decimal
from uuid import UUID

import pytest

from stockwise.app.models.product import Product
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.services.inventory import (
    apply_stock_change,
    weighted_average_cost,
)
from tests.conftest import TestingSessionLocal
from tests.test_products import (
    _create_product,
    _csrf_headers,
    _setup_business,
)


def _move(client, product_id, movement_type, quantity, **extra):
    return client.post(
        "/api/stock-movements",
        json={
            "product_id": product_id,
            "movement_type": movement_type,
            "quantity": quantity,
            **extra,
        },
        headers=_csrf_headers(client),
    )


def _sell(client, product_id, quantity):
    response = client.post(
        "/api/sales",
        json={"items": [{"product_id": product_id, "quantity": quantity}]},
        headers=_csrf_headers(client),
    )

    assert response.status_code == 201

    return response.json()


def _product(client, product_id):
    return client.get(f"/api/products/{product_id}").json()


class TestWeightedAverageFormula:
    def test_blends_existing_and_new_units(self):
        assert weighted_average_cost(
            stock_before=10,
            average_before=Decimal("10"),
            quantity=10,
            unit_cost=Decimal("20"),
        ) == Decimal("15.0000")

    def test_empty_stock_takes_the_new_cost(self):
        assert weighted_average_cost(
            stock_before=0,
            average_before=Decimal("99"),
            quantity=5,
            unit_cost=Decimal("12.50"),
        ) == Decimal("12.5000")

    def test_rounds_half_up_to_four_places(self):
        # (2 * 10 + 1 * 10.0001) / 3 = 10.00003333...
        assert weighted_average_cost(
            stock_before=2,
            average_before=Decimal("10"),
            quantity=1,
            unit_cost=Decimal("10.0001"),
        ) == Decimal("10.0000")

        # (1 * 1 + 2 * 2) / 3 = 1.66666...
        assert weighted_average_cost(
            stock_before=1,
            average_before=Decimal("1"),
            quantity=2,
            unit_cost=Decimal("2"),
        ) == Decimal("1.6667")


class TestOpeningStock:
    def test_creating_a_product_with_stock_writes_opening_movement(
        self, client
    ):
        _setup_business(client)
        product = _create_product(client, stock_quantity=10).json()

        assert product["stock_quantity"] == 10
        assert Decimal(product["average_cost"]) == Decimal("10")

        movements = client.get("/api/stock-movements").json()

        assert len(movements) == 1
        assert movements[0]["movement_type"] == "OPENING"
        assert movements[0]["quantity"] == 10
        assert movements[0]["stock_before"] == 0
        assert movements[0]["stock_after"] == 10
        assert Decimal(movements[0]["unit_cost"]) == Decimal("10")

    def test_creating_a_product_without_stock_writes_no_movement(
        self, client
    ):
        _setup_business(client)
        _create_product(client, stock_quantity=0)

        assert client.get("/api/stock-movements").json() == []


class TestStockIn:
    def test_unit_cost_recalculates_average_and_purchase_price(
        self, client
    ):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=10).json()["id"]

        response = _move(client, product_id, "IN", 10, unit_cost="20.00")

        assert response.status_code == 201
        assert Decimal(response.json()["unit_cost"]) == Decimal("20")

        product = _product(client, product_id)

        assert Decimal(product["average_cost"]) == Decimal("15")
        assert Decimal(product["purchase_price"]) == Decimal("20")
        assert product["stock_quantity"] == 20

    def test_without_unit_cost_uses_purchase_price(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=10).json()["id"]

        response = _move(client, product_id, "IN", 5)

        assert response.status_code == 201
        assert Decimal(response.json()["unit_cost"]) == Decimal("10")
        assert Decimal(_product(client, product_id)["average_cost"]) == (
            Decimal("10")
        )

    def test_restocking_from_zero_takes_the_new_cost(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=4).json()["id"]

        _move(client, product_id, "OUT", 4)
        _move(client, product_id, "IN", 6, unit_cost="13.00")

        assert Decimal(_product(client, product_id)["average_cost"]) == (
            Decimal("13")
        )

    @pytest.mark.parametrize("unit_cost", ["-1", "1.234", "abc"])
    def test_invalid_unit_cost_rejected(self, client, unit_cost):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]

        response = _move(client, product_id, "IN", 1, unit_cost=unit_cost)

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "movement_type", ["OUT", "ADJUSTMENT_IN", "ADJUSTMENT_OUT"]
    )
    def test_unit_cost_rejected_for_other_types(self, client, movement_type):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]

        response = _move(
            client, product_id, movement_type, 1, unit_cost="5.00"
        )

        assert response.status_code == 422


class TestAverageIsStableOnOutboundAndAdjustments:
    @pytest.mark.parametrize(
        "movement_type", ["OUT", "ADJUSTMENT_OUT", "ADJUSTMENT_IN"]
    )
    def test_average_unchanged(self, client, movement_type):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=10).json()["id"]
        _move(client, product_id, "IN", 10, unit_cost="20.00")

        response = _move(client, product_id, movement_type, 3)

        assert response.status_code == 201
        # The movement is valued at the average cost in force.
        assert Decimal(response.json()["unit_cost"]) == Decimal("15")
        assert Decimal(_product(client, product_id)["average_cost"]) == (
            Decimal("15")
        )


class TestSaleCostSnapshot:
    def test_sale_uses_average_cost(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=10).json()["id"]
        _move(client, product_id, "IN", 10, unit_cost="20.00")

        sale = _sell(client, product_id, 4)
        item = sale["items"][0]

        # Sale price 20.00, average cost 15.00.
        assert Decimal(item["unit_purchase_price"]) == Decimal("15")
        assert Decimal(item["cost"]) == Decimal("60")
        assert Decimal(item["gross_profit"]) == Decimal("20")
        assert Decimal(sale["total_cost"]) == Decimal("60")

    def test_later_purchases_do_not_change_past_sales(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=10).json()["id"]

        first_sale = _sell(client, product_id, 5)

        # 5 units left at 10.00, then 5 arrive at 30.00 -> average 20.00.
        _move(client, product_id, "IN", 5, unit_cost="30.00")

        second_sale = _sell(client, product_id, 5)

        db = TestingSessionLocal()

        try:
            stored = {
                str(item.sale_id): item
                for item in db.query(SaleItem).all()
            }
        finally:
            db.close()

        earlier = stored[first_sale["id"]]
        later = stored[second_sale["id"]]

        assert Decimal(earlier.unit_purchase_price) == Decimal("10")
        assert Decimal(earlier.cost) == Decimal("50")
        assert Decimal(earlier.gross_profit) == Decimal("50")

        assert Decimal(later.unit_purchase_price) == Decimal("20")
        assert Decimal(later.cost) == Decimal("100")
        assert Decimal(later.gross_profit) == Decimal("0")

    def test_average_with_many_decimals_is_snapshotted_to_two(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=1).json()["id"]

        # (1 * 10 + 2 * 11) / 3 = 10.6667
        _move(client, product_id, "IN", 2, unit_cost="11.00")

        assert Decimal(_product(client, product_id)["average_cost"]) == (
            Decimal("10.6667")
        )

        item = _sell(client, product_id, 3)["items"][0]

        assert Decimal(item["unit_purchase_price"]) == Decimal("10.67")
        assert Decimal(item["cost"]) == Decimal("32.01")

    def test_sale_movement_is_linked_to_the_sale(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=10).json()["id"]

        sale = _sell(client, product_id, 2)

        movements = [
            movement
            for movement in client.get("/api/stock-movements").json()
            if movement["movement_type"] == "SALE"
        ]

        assert len(movements) == 1
        assert movements[0]["sale_id"] == sale["id"]


class TestReturnCosting:
    def test_return_requires_original_cost(self, db_session, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=5).json()["id"]
        product = db_session.get(Product, UUID(product_id))

        with pytest.raises(ValueError):
            apply_stock_change(
                db_session,
                product=product,
                movement_type="RETURN",
                quantity=1,
            )

    def test_returned_units_re_enter_at_their_sold_cost(
        self, db_session, client
    ):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=10).json()["id"]

        # Sell 6 at cost 10, restock 4 at 20 -> 8 units, average 15.
        _sell(client, product_id, 6)
        _move(client, product_id, "IN", 4, unit_cost="20.00")

        product = db_session.get(Product, UUID(product_id))

        apply_stock_change(
            db_session,
            product=product,
            movement_type="RETURN",
            quantity=2,
            unit_cost=Decimal("10.00"),
        )
        db_session.commit()

        # (8 * 15 + 2 * 10) / 10 = 14
        assert product.stock_quantity == 10
        assert Decimal(product.average_cost) == Decimal("14")

        movement = (
            db_session.query(StockMovement)
            .filter(StockMovement.movement_type == "RETURN")
            .one()
        )

        assert Decimal(movement.unit_cost) == Decimal("10")
