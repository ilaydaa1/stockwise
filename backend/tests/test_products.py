from uuid import UUID

from stockwise.app.models.product import Product
from tests.conftest import TestingSessionLocal


def _register_and_login(
    client,
    email="test@example.com",
    name="Test User",
):
    register_response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "securepassword123",
        },
    )
    assert login_response.status_code == 200

    return login_response


def _csrf_headers(client):
    csrf = client.cookies.get("sw_csrf", "")

    return {
        "x-csrf-token": csrf,
    }


def _create_business(
    client,
    name="Test İşletme",
):
    response = client.post(
        "/api/businesses",
        json={
            "name": name,
            "currency": "TRY",
            "timezone": "Europe/Istanbul",
        },
        headers=_csrf_headers(client),
    )

    assert response.status_code == 201

    return response


def _create_product(
    client,
    **overrides,
):
    payload = {
        "name": "Pilot Kalem",
        "sku": "KLM-001",
        "purchase_price": "10.00",
        "sale_price": "20.00",
        "stock_quantity": 10,
        "minimum_stock": 3,
        **overrides,
    }

    return client.post(
        "/api/products",
        json=payload,
        headers=_csrf_headers(client),
    )


def _setup_business(client):
    _register_and_login(client)
    _create_business(client)


class TestCreateProduct:
    def test_create_product_success(self, client):
        _setup_business(client)

        response = _create_product(client)

        assert response.status_code == 201

        data = response.json()

        assert data["name"] == "Pilot Kalem"
        assert data["sku"] == "KLM-001"
        assert data["purchase_price"] == "10.00"
        assert data["sale_price"] == "20.00"
        assert data["stock_quantity"] == 10
        assert data["minimum_stock"] == 3
        assert data["is_active"] is True
        assert "id" in data
        assert "business_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_product_trims_name_and_normalizes_sku(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            name="  Pilot Kalem  ",
            sku="  klm-001  ",
        )

        assert response.status_code == 201

        data = response.json()

        assert data["name"] == "Pilot Kalem"
        assert data["sku"] == "KLM-001"

    def test_create_product_rejects_duplicate_sku(
        self,
        client,
    ):
        _setup_business(client)

        first_response = _create_product(client)

        assert first_response.status_code == 201

        second_response = _create_product(
            client,
            name="Başka Kalem",
        )

        assert second_response.status_code == 409

    def test_create_product_rejects_duplicate_sku_case_insensitive(
        self,
        client,
    ):
        _setup_business(client)

        first_response = _create_product(
            client,
            sku="KLM-001",
        )

        assert first_response.status_code == 201

        second_response = _create_product(
            client,
            name="Başka Kalem",
            sku="klm-001",
        )

        assert second_response.status_code == 409

    def test_create_product_rejects_negative_purchase_price(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            purchase_price="-1.00",
        )

        assert response.status_code == 422

    def test_create_product_rejects_negative_sale_price(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            sale_price="-1.00",
        )

        assert response.status_code == 422

    def test_create_product_rejects_more_than_two_decimal_places(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            purchase_price="10.999",
        )

        assert response.status_code == 422

    def test_create_product_rejects_price_exceeding_numeric_precision(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            sale_price="12345678901.12",
        )

        assert response.status_code == 422

    def test_create_product_accepts_maximum_valid_price(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            purchase_price="9999999999.99",
            sale_price="9999999999.99",
        )

        assert response.status_code == 201

        data = response.json()

        assert data["purchase_price"] == "9999999999.99"
        assert data["sale_price"] == "9999999999.99"

    def test_create_product_rejects_negative_stock(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            stock_quantity=-1,
        )

        assert response.status_code == 422

    def test_create_product_rejects_negative_minimum_stock(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            minimum_stock=-1,
        )

        assert response.status_code == 422

    def test_create_product_rejects_blank_sku(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            sku="   ",
        )

        assert response.status_code == 422

    def test_create_product_rejects_short_name(
        self,
        client,
    ):
        _setup_business(client)

        response = _create_product(
            client,
            name="A",
        )

        assert response.status_code == 422

    def test_create_product_rejects_sku_of_deleted_product(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(
            client,
            name="Kalem",
            sku="KLM-001",
        )

        assert created.status_code == 201

        product_id = created.json()["id"]

        delete_response = client.delete(
            f"/api/products/{product_id}",
            headers=_csrf_headers(client),
        )

        assert delete_response.status_code == 204

        recreate_response = _create_product(
            client,
            name="Yeni Kalem",
            sku="KLM-001",
        )

        assert recreate_response.status_code == 409


class TestListProducts:
    def test_list_products_success(self, client):
        _setup_business(client)

        _create_product(
            client,
            name="Kalem",
            sku="KLM-001",
        )

        _create_product(
            client,
            name="Silgi",
            sku="SLG-001",
        )

        response = client.get("/api/products")

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 2

        skus = {
            product["sku"]
            for product in data
        }

        assert skus == {
            "KLM-001",
            "SLG-001",
        }

    def test_list_products_empty(self, client):
        _setup_business(client)

        response = client.get("/api/products")

        assert response.status_code == 200
        assert response.json() == []


class TestGetProduct:
    def test_get_product_success(self, client):
        _setup_business(client)

        created = _create_product(client)

        product_id = created.json()["id"]

        response = client.get(
            f"/api/products/{product_id}"
        )

        assert response.status_code == 200
        assert response.json()["id"] == product_id
        assert response.json()["sku"] == "KLM-001"

    def test_get_product_not_found(self, client):
        _setup_business(client)

        response = client.get(
            "/api/products/"
            "00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "PRODUCT_NOT_FOUND"
        )

    def test_get_product_rejects_invalid_uuid(self, client):
        _setup_business(client)

        response = client.get(
            "/api/products/not-a-valid-uuid"
        )

        assert response.status_code == 422


class TestUpdateProduct:
    def test_update_product_success(self, client):
        _setup_business(client)

        created = _create_product(client)

        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={
                "name": "Yeni Kalem",
                "sku": "YENI-001",
                "purchase_price": "12.00",
                "sale_price": "25.00",
                "minimum_stock": 5,
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["name"] == "Yeni Kalem"
        assert data["sku"] == "YENI-001"
        assert data["purchase_price"] == "12.00"
        assert data["sale_price"] == "25.00"
        assert data["minimum_stock"] == 5

        # Product editing must not alter stock.
        assert data["stock_quantity"] == 10

    def test_update_product_rejects_duplicate_sku(
        self,
        client,
    ):
        _setup_business(client)

        first = _create_product(
            client,
            name="Kalem",
            sku="KLM-001",
        )

        second = _create_product(
            client,
            name="Silgi",
            sku="SLG-001",
        )

        assert first.status_code == 201
        assert second.status_code == 201

        second_id = second.json()["id"]

        response = client.patch(
            f"/api/products/{second_id}",
            json={
                "sku": "KLM-001",
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 409

    def test_update_product_rejects_stock_quantity(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)

        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={
                "stock_quantity": 999,
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422

        db = TestingSessionLocal()

        try:
            product = (
                db.query(Product)
                .filter(
                    Product.id == UUID(product_id)
                )
                .first()
            )

            assert product is not None
            assert product.stock_quantity == 10
        finally:
            db.close()

    def test_update_product_rejects_more_than_two_decimal_places(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)
        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={
                "sale_price": "10.999",
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422

    def test_update_product_rejects_price_exceeding_numeric_precision(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)
        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={
                "purchase_price": "12345678901.12",
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422

    def test_update_product_accepts_maximum_valid_price(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)
        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={
                "purchase_price": "9999999999.99",
                "sale_price": "9999999999.99",
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["purchase_price"] == "9999999999.99"
        assert data["sale_price"] == "9999999999.99"

    def test_update_product_rejects_null_name(self, client):
        _setup_business(client)

        created = _create_product(client)
        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={"name": None},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422

    def test_update_product_rejects_null_sku(self, client):
        _setup_business(client)

        created = _create_product(client)
        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={"sku": None},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422

    def test_update_product_rejects_null_purchase_price(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)
        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={"purchase_price": None},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422

    def test_update_product_rejects_null_sale_price(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)
        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={"sale_price": None},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422

    def test_update_product_rejects_null_minimum_stock(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)
        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={"minimum_stock": None},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422


class TestDeleteProduct:
    def test_delete_product_soft_deletes(self, client):
        _setup_business(client)

        created = _create_product(client)

        product_id = created.json()["id"]

        response = client.delete(
            f"/api/products/{product_id}",
            headers=_csrf_headers(client),
        )

        assert response.status_code == 204

        db = TestingSessionLocal()

        try:
            product = (
                db.query(Product)
                .filter(
                    Product.id == UUID(product_id)
                )
                .first()
            )

            assert product is not None
            assert product.is_active is False
        finally:
            db.close()

    def test_deleted_product_not_in_list(self, client):
        _setup_business(client)

        created = _create_product(client)

        product_id = created.json()["id"]

        delete_response = client.delete(
            f"/api/products/{product_id}",
            headers=_csrf_headers(client),
        )

        assert delete_response.status_code == 204

        response = client.get("/api/products")

        assert response.status_code == 200
        assert response.json() == []

    def test_deleted_product_cannot_be_fetched(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)

        product_id = created.json()["id"]

        delete_response = client.delete(
            f"/api/products/{product_id}",
            headers=_csrf_headers(client),
        )

        assert delete_response.status_code == 204

        response = client.get(
            f"/api/products/{product_id}"
        )

        assert response.status_code == 404


class TestProductIsolation:
    def test_user_cannot_access_other_business_product(
        self,
        client,
    ):
        _register_and_login(
            client,
            email="user1@example.com",
            name="User 1",
        )

        _create_business(
            client,
            name="User 1 Business",
        )

        created = _create_product(client)

        product_id = created.json()["id"]

        client.cookies.clear()

        _register_and_login(
            client,
            email="user2@example.com",
            name="User 2",
        )

        _create_business(
            client,
            name="User 2 Business",
        )

        response = client.get(
            f"/api/products/{product_id}"
        )

        assert response.status_code == 404

    def test_user_cannot_update_other_business_product(
        self,
        client,
    ):
        _register_and_login(
            client,
            email="user1@example.com",
            name="User 1",
        )

        _create_business(
            client,
            name="User 1 Business",
        )

        created = _create_product(client)
        product_id = created.json()["id"]

        client.cookies.clear()

        _register_and_login(
            client,
            email="user2@example.com",
            name="User 2",
        )

        _create_business(
            client,
            name="User 2 Business",
        )

        response = client.patch(
            f"/api/products/{product_id}",
            json={"name": "Yetkisiz Değişiklik"},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 404

    def test_user_cannot_delete_other_business_product(
        self,
        client,
    ):
        _register_and_login(
            client,
            email="user1@example.com",
            name="User 1",
        )

        _create_business(
            client,
            name="User 1 Business",
        )

        created = _create_product(client)
        product_id = created.json()["id"]

        client.cookies.clear()

        _register_and_login(
            client,
            email="user2@example.com",
            name="User 2",
        )

        _create_business(
            client,
            name="User 2 Business",
        )

        response = client.delete(
            f"/api/products/{product_id}",
            headers=_csrf_headers(client),
        )

        assert response.status_code == 404


class TestProductSecurity:
    def test_create_product_unauthenticated(
        self,
        client,
    ):
        response = client.post(
            "/api/products",
            json={
                "name": "Kalem",
                "sku": "KLM-001",
                "purchase_price": "10.00",
                "sale_price": "20.00",
                "stock_quantity": 10,
                "minimum_stock": 3,
            },
        )

        assert response.status_code == 401

    def test_create_product_without_csrf(
        self,
        client,
    ):
        _setup_business(client)

        response = client.post(
            "/api/products",
            json={
                "name": "Kalem",
                "sku": "KLM-001",
                "purchase_price": "10.00",
                "sale_price": "20.00",
                "stock_quantity": 10,
                "minimum_stock": 3,
            },
        )

        assert response.status_code == 403

    def test_update_product_without_csrf(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)

        product_id = created.json()["id"]

        response = client.patch(
            f"/api/products/{product_id}",
            json={
                "name": "Değişmiş Kalem",
            },
        )

        assert response.status_code == 403

    def test_delete_product_without_csrf(
        self,
        client,
    ):
        _setup_business(client)

        created = _create_product(client)

        product_id = created.json()["id"]

        response = client.delete(
            f"/api/products/{product_id}"
        )

        assert response.status_code == 403