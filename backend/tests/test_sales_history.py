"""Sales list endpoint and refunds in the summary figures."""
from decimal import Decimal

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


def _return(client, sale_id, sale_item_id, quantity):
    response = client.post(
        f"/api/sales/{sale_id}/returns",
        json={"items": [{"sale_item_id": sale_item_id, "quantity": quantity}]},
        headers=_csrf_headers(client),
    )

    assert response.status_code == 201


class TestListSales:
    def test_empty(self, client):
        _setup_business(client)

        response = client.get("/api/sales")

        assert response.status_code == 200
        assert response.json() == {
            "total": 0,
            "limit": 20,
            "offset": 0,
            "items": [],
        }

    def test_lists_sales_with_their_lines(self, client):
        _setup_business(client)
        pen = _create_product(client, name="Kalem", sku="A-1").json()["id"]
        book = _create_product(client, name="Defter", sku="B-1").json()["id"]
        sale = _sell(client, [(pen, 2), (book, 1)])

        body = client.get("/api/sales").json()

        assert body["total"] == 1

        entry = body["items"][0]

        assert entry["id"] == sale["id"]
        assert Decimal(entry["total_amount"]) == Decimal("60")
        assert Decimal(entry["refund_amount"]) == Decimal("0")
        assert [line["product_name"] for line in entry["items"]] == [
            "Defter",
            "Kalem",
        ]
        assert {line["id"] for line in entry["items"]} == {
            item["id"] for item in sale["items"]
        }
        assert all(line["returned_quantity"] == 0 for line in entry["items"])

    def test_reports_returned_quantity_and_refund(self, client):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]
        sale = _sell(client, [(product_id, 5)])
        item_id = sale["items"][0]["id"]

        _return(client, sale["id"], item_id, 1)
        _return(client, sale["id"], item_id, 2)

        entry = client.get("/api/sales").json()["items"][0]

        assert entry["items"][0]["quantity"] == 5
        assert entry["items"][0]["returned_quantity"] == 3
        assert Decimal(entry["refund_amount"]) == Decimal("60")
        # The sale itself is unchanged.
        assert Decimal(entry["total_amount"]) == Decimal("100")

    def test_newest_first_and_paginated(self, client):
        _setup_business(client)
        product_id = _create_product(client, stock_quantity=50).json()["id"]
        created = [_sell(client, [(product_id, 1)])["id"] for _ in range(5)]

        first = client.get("/api/sales?limit=2").json()
        second = client.get("/api/sales?limit=2&offset=2").json()
        last = client.get("/api/sales?limit=2&offset=4").json()

        assert first["total"] == second["total"] == 5

        listed = [
            entry["id"]
            for page in (first, second, last)
            for entry in page["items"]
        ]

        assert listed == list(reversed(created))
        assert len(last["items"]) == 1

    def test_only_own_business(self, client):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]
        _sell(client, [(product_id, 1)])

        client.cookies.clear()
        _register_and_login(client, email="other@example.com", name="Other")
        _create_business(client, name="Diğer İşletme")

        assert client.get("/api/sales").json()["total"] == 0

    def test_invalid_paging_rejected(self, client):
        _setup_business(client)

        assert client.get("/api/sales?limit=0").status_code == 422
        assert client.get("/api/sales?limit=101").status_code == 422
        assert client.get("/api/sales?offset=-1").status_code == 422

    def test_requires_authentication(self, client):
        assert client.get("/api/sales").status_code == 401


class TestNetSales:
    def test_summaries_report_refunds_and_net_sales(self, client):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]
        sale = _sell(client, [(product_id, 5)])

        _return(client, sale["id"], sale["items"][0]["id"], 2)

        for path in ("/api/dashboard/summary", "/api/analytics/summary"):
            body = client.get(path).json()

            assert Decimal(body["total_sales"]) == Decimal("100"), path
            assert Decimal(body["refund_total"]) == Decimal("40"), path
            assert Decimal(body["net_sales"]) == Decimal("60"), path

    def test_no_returns_means_net_equals_gross(self, client):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]
        _sell(client, [(product_id, 2)])

        body = client.get("/api/dashboard/summary").json()

        assert Decimal(body["refund_total"]) == Decimal("0")
        assert Decimal(body["net_sales"]) == Decimal(body["total_sales"])

    def test_refunds_of_other_businesses_are_not_counted(self, client):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]
        sale = _sell(client, [(product_id, 2)])
        _return(client, sale["id"], sale["items"][0]["id"], 1)

        client.cookies.clear()
        _register_and_login(client, email="other@example.com", name="Other")
        _create_business(client, name="Diğer İşletme")

        body = client.get("/api/analytics/summary").json()

        assert Decimal(body["refund_total"]) == Decimal("0")
