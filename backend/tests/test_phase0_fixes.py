"""Stock movement paging, profit after returns, and account deletion."""
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from stockwise.app.models.business import Business
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.user import User
from tests.test_products import (
    _create_business,
    _create_product,
    _csrf_headers,
    _register_and_login,
    _setup_business,
)


def _move(client, product_id, movement_type, quantity, **extra):
    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": product_id,
            "movement_type": movement_type,
            "quantity": quantity,
            **extra,
        },
        headers=_csrf_headers(client),
    )

    assert response.status_code == 201

    return response.json()


def _sell(client, product_id, quantity):
    response = client.post(
        "/api/sales",
        json={"items": [{"product_id": product_id, "quantity": quantity}]},
        headers=_csrf_headers(client),
    )

    assert response.status_code == 201

    return response.json()


class TestStockMovementPaging:
    def test_total_is_reported_in_a_header(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=0).json()["id"]

        for _ in range(5):
            _move(client, product_id, "IN", 1)

        response = client.get("/api/stock-movements?limit=2")

        assert response.status_code == 200
        assert response.headers["x-total-count"] == "5"
        assert len(response.json()) == 2

    def test_pages_are_newest_first_and_do_not_overlap(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=0).json()["id"]
        created = [
            _move(client, product_id, "IN", 1)["id"] for _ in range(5)
        ]

        pages = [
            client.get(f"/api/stock-movements?limit=2&offset={offset}").json()
            for offset in (0, 2, 4)
        ]
        listed = [movement["id"] for page in pages for movement in page]

        assert listed == list(reversed(created))

    def test_default_page_is_bounded(self, client):
        _setup_business(client)
        _create_product(client, stock_quantity=1)

        response = client.get("/api/stock-movements")

        assert response.status_code == 200
        assert client.get("/api/stock-movements?limit=501").status_code == 422
        assert client.get("/api/stock-movements?limit=0").status_code == 422
        assert client.get("/api/stock-movements?offset=-1").status_code == 422

    def test_search_matches_product_name_sku_and_note(self, client):
        _setup_business(client)
        pen = _create_product(
            client, name="Mavi Kalem", sku="KLM-9", stock_quantity=0
        ).json()["id"]
        book = _create_product(
            client, name="Defter", sku="DFT-1", stock_quantity=0
        ).json()["id"]

        _move(client, pen, "IN", 1)
        _move(client, book, "IN", 1, note="Hasarlı koli")
        _move(client, book, "IN", 1)

        def count(query):
            response = client.get(
                "/api/stock-movements", params={"q": query}
            )

            return int(response.headers["x-total-count"])

        assert count("kalem") == 1
        assert count("dft") == 2
        assert count("hasarlı") == 1
        assert count("yok-böyle-bir-şey") == 0

    def test_search_treats_wildcards_literally(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=0).json()["id"]

        _move(client, product_id, "IN", 1, note="%50 indirimli parti")
        _move(client, product_id, "IN", 1, note="normal")

        def count(query):
            return int(
                client.get(
                    "/api/stock-movements", params={"q": query}
                ).headers["x-total-count"]
            )

        assert count("%50") == 1
        assert count("%") == 1
        assert count("_") == 0

    def test_search_combines_with_product_filter(self, client):
        _setup_business(client)
        first = _create_product(client, sku="A-1", stock_quantity=0).json()["id"]
        second = _create_product(client, sku="B-1", stock_quantity=0).json()["id"]

        _move(client, first, "IN", 1, note="teslimat")
        _move(client, second, "IN", 1, note="teslimat")

        response = client.get(
            "/api/stock-movements",
            params={"q": "teslimat", "product_id": first},
        )

        assert response.headers["x-total-count"] == "1"

    def test_total_counts_only_own_business(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=0).json()["id"]
        _move(client, product_id, "IN", 1)

        client.cookies.clear()
        _register_and_login(client, email="other@example.com", name="Other")
        _create_business(client, name="Diğer İşletme")

        response = client.get("/api/stock-movements")

        assert response.headers["x-total-count"] == "0"
        assert response.json() == []


class TestProfitAfterReturns:
    def test_summaries_report_profit_net_of_returns(self, client):
        _setup_business(client)
        # Cost 10.00, price 20.00: profit of 10.00 per unit.
        product_id = _create_product(client).json()["id"]
        sale = _sell(client, product_id, 5)

        response = client.post(
            f"/api/sales/{sale['id']}/returns",
            json={
                "items": [
                    {"sale_item_id": sale["items"][0]["id"], "quantity": 2}
                ]
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 201

        for path in ("/api/dashboard/summary", "/api/analytics/summary"):
            body = client.get(path).json()

            assert Decimal(body["gross_profit"]) == Decimal("50"), path
            assert Decimal(body["refund_total"]) == Decimal("40"), path
            assert Decimal(body["returned_cost_total"]) == Decimal("20"), path
            assert Decimal(body["net_gross_profit"]) == Decimal("30"), path

    def test_without_returns_net_profit_equals_gross(self, client):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]
        _sell(client, product_id, 3)

        body = client.get("/api/dashboard/summary").json()

        assert Decimal(body["returned_cost_total"]) == Decimal("0")
        assert Decimal(body["net_gross_profit"]) == Decimal(
            body["gross_profit"]
        )


@pytest.mark.postgres_only
class TestAccountDeletion:
    """SQLite does not enforce foreign keys by default, so only
    PostgreSQL can show whether the delete is accepted."""

    def test_business_with_sales_can_be_deleted(self, client, db_session):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]
        _sell(client, product_id, 2)

        user_id = db_session.query(User.id).scalar()

        db_session.execute(
            text("DELETE FROM users WHERE id = :id"), {"id": user_id}
        )
        db_session.commit()

        for model in (User, Business, Product, Sale, SaleItem, StockMovement):
            assert db_session.query(model).count() == 0, model.__name__

    def test_product_with_sale_lines_still_cannot_be_deleted(
        self, client, db_session
    ):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]
        _sell(client, product_id, 2)

        db_session.execute(
            text("DELETE FROM stock_movements"),
        )
        db_session.execute(
            text("DELETE FROM products WHERE id = :id"), {"id": product_id}
        )

        # The check is deferred, so it fires here rather than above.
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        assert db_session.query(Product).count() == 1
