from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.services.returns import create_return
from tests.test_products import (
    _create_business,
    _create_product,
    _csrf_headers,
    _register_and_login,
    _setup_business,
)


def _sell(client, lines):
    response = client.post(
        "/api/sales",
        json={
            "items": [
                {"product_id": product_id, "quantity": quantity}
                for product_id, quantity in lines
            ]
        },
        headers=_csrf_headers(client),
    )

    assert response.status_code == 201

    return response.json()


def _return(client, sale_id, lines, **extra):
    return client.post(
        f"/api/sales/{sale_id}/returns",
        json={
            "items": [
                {"sale_item_id": sale_item_id, "quantity": quantity}
                for sale_item_id, quantity in lines
            ],
            **extra,
        },
        headers=_csrf_headers(client),
    )


def _product(client, product_id):
    return client.get(f"/api/products/{product_id}").json()


def _sale_with_one_line(client, quantity=5, stock=10):
    _setup_business(client)
    product_id = _create_product(client, stock_quantity=stock).json()["id"]
    sale = _sell(client, [(product_id, quantity)])

    return product_id, sale, sale["items"][0]["id"]


class TestCreateReturn:
    def test_partial_return_restores_stock_and_records_refund(self, client):
        product_id, sale, item_id = _sale_with_one_line(client)

        response = _return(
            client, sale["id"], [(item_id, 2)], reason="Hasarlı ürün"
        )

        assert response.status_code == 201

        returned = response.json()

        assert len(returned) == 1
        assert returned[0]["sale_id"] == sale["id"]
        assert returned[0]["sale_item_id"] == item_id
        assert returned[0]["product_id"] == product_id
        assert returned[0]["quantity"] == 2
        # Sold at 20.00, cost 10.00.
        assert Decimal(returned[0]["refund_amount"]) == Decimal("40")
        assert Decimal(returned[0]["cost_amount"]) == Decimal("20")
        assert returned[0]["reason"] == "Hasarlı ürün"

        assert _product(client, product_id)["stock_quantity"] == 7

    def test_return_writes_linked_stock_movement(self, client, db_session):
        product_id, sale, item_id = _sale_with_one_line(client)

        return_id = _return(client, sale["id"], [(item_id, 2)]).json()[0][
            "id"
        ]

        movement = (
            db_session.query(StockMovement)
            .filter(StockMovement.movement_type == "RETURN")
            .one()
        )

        assert movement.quantity == 2
        assert (movement.stock_before, movement.stock_after) == (5, 7)
        assert str(movement.sale_id) == sale["id"]
        assert str(movement.sale_return_id) == return_id
        assert str(movement.product_id) == product_id
        assert Decimal(movement.unit_cost) == Decimal("10")

    def test_original_sale_is_not_modified(self, client, db_session):
        _, sale, item_id = _sale_with_one_line(client)

        _return(client, sale["id"], [(item_id, 5)])

        stored_sale = db_session.get(Sale, UUID(sale["id"]))
        stored_item = db_session.get(SaleItem, UUID(item_id))

        assert Decimal(stored_sale.total_amount) == Decimal("100")
        assert Decimal(stored_sale.total_cost) == Decimal("50")
        assert stored_item.quantity == 5
        assert Decimal(stored_item.subtotal) == Decimal("100")

    def test_refund_uses_prices_frozen_on_the_sale(self, client):
        product_id, sale, item_id = _sale_with_one_line(client)

        client.patch(
            f"/api/products/{product_id}",
            json={"sale_price": "99.00", "purchase_price": "55.00"},
            headers=_csrf_headers(client),
        )

        returned = _return(client, sale["id"], [(item_id, 1)]).json()[0]

        assert Decimal(returned["refund_amount"]) == Decimal("20")
        assert Decimal(returned["cost_amount"]) == Decimal("10")

    def test_cannot_return_more_than_sold(self, client):
        product_id, sale, item_id = _sale_with_one_line(client)

        response = _return(client, sale["id"], [(item_id, 6)])

        assert response.status_code == 400
        assert response.json()["detail"] == "RETURN_EXCEEDS_SOLD"
        assert _product(client, product_id)["stock_quantity"] == 5

    def test_repeated_returns_cannot_exceed_sold_in_total(self, client):
        product_id, sale, item_id = _sale_with_one_line(client)

        assert _return(client, sale["id"], [(item_id, 3)]).status_code == 201
        assert _return(client, sale["id"], [(item_id, 2)]).status_code == 201

        response = _return(client, sale["id"], [(item_id, 1)])

        assert response.status_code == 400
        assert response.json()["detail"] == "RETURN_EXCEEDS_SOLD"
        assert _product(client, product_id)["stock_quantity"] == 10

    def test_one_bad_line_rejects_the_whole_return(self, client, db_session):
        _setup_business(client)
        first = _create_product(client, sku="A-1").json()["id"]
        second = _create_product(client, sku="B-1").json()["id"]
        sale = _sell(client, [(first, 2), (second, 2)])
        first_item, second_item = (item["id"] for item in sale["items"])

        response = _return(
            client, sale["id"], [(first_item, 1), (second_item, 3)]
        )

        assert response.status_code == 400
        assert db_session.query(SaleReturn).count() == 0
        assert _product(client, first)["stock_quantity"] == 8
        assert _product(client, second)["stock_quantity"] == 8

    def test_full_return_of_multi_line_sale_is_a_cancellation(self, client):
        _setup_business(client)
        first = _create_product(client, sku="A-1").json()["id"]
        second = _create_product(client, sku="B-1").json()["id"]
        sale = _sell(client, [(first, 2), (second, 3)])

        response = _return(
            client,
            sale["id"],
            [(item["id"], item["quantity"]) for item in sale["items"]],
        )

        assert response.status_code == 201

        refunded = sum(
            Decimal(line["refund_amount"]) for line in response.json()
        )

        assert refunded == Decimal(sale["total_amount"])
        assert _product(client, first)["stock_quantity"] == 10
        assert _product(client, second)["stock_quantity"] == 10

    def test_return_recalculates_average_cost(self, client):
        product_id, sale, item_id = _sale_with_one_line(client, quantity=6)

        # 4 units at 10.00, then 4 arrive at 20.00 -> average 15.00.
        client.post(
            "/api/stock-movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 4,
                "unit_cost": "20.00",
            },
            headers=_csrf_headers(client),
        )

        _return(client, sale["id"], [(item_id, 2)])

        # (8 * 15 + 2 * 10) / 10 = 14
        assert Decimal(_product(client, product_id)["average_cost"]) == (
            Decimal("14")
        )

    def test_return_allowed_for_deactivated_product(self, client, db_session):
        product_id, sale, item_id = _sale_with_one_line(client)

        client.delete(
            f"/api/products/{product_id}",
            headers=_csrf_headers(client),
        )

        assert _return(client, sale["id"], [(item_id, 1)]).status_code == 201

    def test_duplicate_lines_rejected(self, client):
        _, sale, item_id = _sale_with_one_line(client)

        response = _return(client, sale["id"], [(item_id, 1), (item_id, 1)])

        assert response.status_code == 400
        assert response.json()["detail"] == "DUPLICATE_SALE_ITEM"

    def test_item_from_another_sale_rejected(self, client):
        product_id, sale, _ = _sale_with_one_line(client)
        other_sale = _sell(client, [(product_id, 1)])

        response = _return(
            client, sale["id"], [(other_sale["items"][0]["id"], 1)]
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "SALE_ITEM_NOT_FOUND"

    def test_unknown_sale_rejected(self, client):
        _, _, item_id = _sale_with_one_line(client)

        response = _return(client, str(uuid4()), [(item_id, 1)])

        assert response.status_code == 404
        assert response.json()["detail"] == "SALE_NOT_FOUND"

    def test_other_business_cannot_return_a_sale(self, client):
        product_id, sale, item_id = _sale_with_one_line(client)

        client.cookies.clear()
        _register_and_login(client, email="other@example.com", name="Other")
        _create_business(client, name="Diğer İşletme")

        response = _return(client, sale["id"], [(item_id, 1)])

        assert response.status_code == 404
        assert response.json()["detail"] == "SALE_NOT_FOUND"

    @pytest.mark.parametrize("quantity", [0, -1])
    def test_non_positive_quantity_rejected(self, client, quantity):
        _, sale, item_id = _sale_with_one_line(client)

        assert (
            _return(client, sale["id"], [(item_id, quantity)]).status_code
            == 422
        )

    def test_empty_return_rejected(self, client):
        _, sale, _ = _sale_with_one_line(client)

        assert _return(client, sale["id"], []).status_code == 422

    def test_requires_csrf(self, client):
        _, sale, item_id = _sale_with_one_line(client)

        response = client.post(
            f"/api/sales/{sale['id']}/returns",
            json={"items": [{"sale_item_id": item_id, "quantity": 1}]},
        )

        assert response.status_code == 403

    def test_requires_authentication(self, client):
        _, sale, item_id = _sale_with_one_line(client)
        client.cookies.clear()

        response = _return(client, sale["id"], [(item_id, 1)])

        assert response.status_code in (401, 403)


class TestListReturns:
    def test_lists_returns_of_a_sale(self, client):
        _, sale, item_id = _sale_with_one_line(client)
        _return(client, sale["id"], [(item_id, 1)])
        _return(client, sale["id"], [(item_id, 2)])

        response = client.get(f"/api/sales/{sale['id']}/returns")

        assert response.status_code == 200
        assert [line["quantity"] for line in response.json()] == [1, 2]

    def test_other_business_cannot_list(self, client):
        _, sale, item_id = _sale_with_one_line(client)
        _return(client, sale["id"], [(item_id, 1)])

        client.cookies.clear()
        _register_and_login(client, email="other@example.com", name="Other")
        _create_business(client, name="Diğer İşletme")

        assert (
            client.get(f"/api/sales/{sale['id']}/returns").status_code == 404
        )


class TestReturnService:
    def test_return_cannot_predate_its_sale(self, client, db_session):
        _, sale, item_id = _sale_with_one_line(client)
        stored_sale = db_session.get(Sale, UUID(sale["id"]))

        with pytest.raises(ValueError):
            create_return(
                db_session,
                business_id=stored_sale.business_id,
                sale_id=stored_sale.id,
                lines=[(UUID(item_id), 1)],
                at=datetime.now(timezone.utc) - timedelta(days=1),
            )

    def test_backdated_return_keeps_its_timestamp(self, client, db_session):
        _, sale, item_id = _sale_with_one_line(client)
        stored_sale = db_session.get(Sale, UUID(sale["id"]))
        when = datetime.now(timezone.utc) + timedelta(days=3)

        created = create_return(
            db_session,
            business_id=stored_sale.business_id,
            sale_id=stored_sale.id,
            lines=[(UUID(item_id), 1)],
            at=when,
        )
        db_session.commit()
        db_session.refresh(created[0])

        stored = created[0].created_at

        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)

        assert stored == when
