import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from stockwise.app.models.category import Category
from stockwise.app.models.product import Product
from stockwise.app.models.supplier import Supplier
from tests.conftest import TestingSessionLocal
from tests.test_products import (
    _create_business,
    _create_product,
    _csrf_headers,
    _register_and_login,
    _setup_business,
)


def _create_category(client, name="Kırtasiye"):
    return client.post(
        "/api/categories",
        json={"name": name},
        headers=_csrf_headers(client),
    )


def _create_supplier(client, name="Anadolu Toptan", lead_time_days=5):
    return client.post(
        "/api/suppliers",
        json={"name": name, "lead_time_days": lead_time_days},
        headers=_csrf_headers(client),
    )


def _switch_to_second_business(client):
    client.cookies.clear()
    _register_and_login(client, email="other@example.com", name="Other")
    _create_business(client, name="Diğer İşletme")


class TestCategories:
    def test_create_and_list(self, client):
        _setup_business(client)

        assert _create_category(client, "  Kırtasiye  ").status_code == 201
        assert _create_category(client, "İçecek").status_code == 201

        response = client.get("/api/categories")

        assert response.status_code == 200
        assert sorted(c["name"] for c in response.json()) == sorted(
            ["Kırtasiye", "İçecek"]
        )

    def test_duplicate_name_rejected(self, client):
        _setup_business(client)
        _create_category(client)

        response = _create_category(client)

        assert response.status_code == 409
        assert response.json()["detail"] == "CATEGORY_ALREADY_EXISTS"

    def test_same_name_allowed_in_other_business(self, client):
        _setup_business(client)
        _create_category(client)
        _switch_to_second_business(client)

        assert _create_category(client).status_code == 201

    def test_short_name_rejected(self, client):
        _setup_business(client)

        assert _create_category(client, " a ").status_code == 422

    def test_list_only_own_business(self, client):
        _setup_business(client)
        _create_category(client)
        _switch_to_second_business(client)

        assert client.get("/api/categories").json() == []

    def test_requires_authentication(self, client):
        assert client.get("/api/categories").status_code == 401

    def test_create_requires_csrf(self, client):
        _setup_business(client)

        response = client.post("/api/categories", json={"name": "Test"})

        assert response.status_code == 403


class TestSuppliers:
    def test_create_and_list(self, client):
        _setup_business(client)

        response = _create_supplier(client, lead_time_days=7)

        assert response.status_code == 201
        assert response.json()["lead_time_days"] == 7

        listed = client.get("/api/suppliers").json()

        assert len(listed) == 1
        assert listed[0]["name"] == "Anadolu Toptan"

    def test_duplicate_name_rejected(self, client):
        _setup_business(client)
        _create_supplier(client)

        response = _create_supplier(client)

        assert response.status_code == 409
        assert response.json()["detail"] == "SUPPLIER_ALREADY_EXISTS"

    @pytest.mark.parametrize("lead_time", [-1, 366, 1.5, None])
    def test_invalid_lead_time_rejected(self, client, lead_time):
        _setup_business(client)

        response = client.post(
            "/api/suppliers",
            json={"name": "Tedarikçi", "lead_time_days": lead_time},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 422

    def test_update_lead_time(self, client):
        _setup_business(client)
        supplier_id = _create_supplier(client).json()["id"]

        response = client.patch(
            f"/api/suppliers/{supplier_id}",
            json={"lead_time_days": 14},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 200
        assert response.json()["lead_time_days"] == 14
        assert response.json()["name"] == "Anadolu Toptan"

    def test_cannot_update_other_business_supplier(self, client):
        _setup_business(client)
        supplier_id = _create_supplier(client).json()["id"]
        _switch_to_second_business(client)

        response = client.patch(
            f"/api/suppliers/{supplier_id}",
            json={"lead_time_days": 1},
            headers=_csrf_headers(client),
        )

        assert response.status_code == 404

    def test_list_only_own_business(self, client):
        _setup_business(client)
        _create_supplier(client)
        _switch_to_second_business(client)

        assert client.get("/api/suppliers").json() == []


class TestProductReferences:
    def test_product_without_references_still_works(self, client):
        _setup_business(client)

        response = _create_product(client)

        assert response.status_code == 201
        assert response.json()["category_id"] is None
        assert response.json()["supplier_id"] is None

    def test_create_product_with_category_and_supplier(self, client):
        _setup_business(client)
        category_id = _create_category(client).json()["id"]
        supplier_id = _create_supplier(client).json()["id"]

        response = _create_product(
            client,
            category_id=category_id,
            supplier_id=supplier_id,
        )

        assert response.status_code == 201
        assert response.json()["category_id"] == category_id
        assert response.json()["supplier_id"] == supplier_id

    def test_update_and_clear_references(self, client):
        _setup_business(client)
        category_id = _create_category(client).json()["id"]
        product_id = _create_product(client).json()["id"]

        assigned = client.patch(
            f"/api/products/{product_id}",
            json={"category_id": category_id},
            headers=_csrf_headers(client),
        )

        assert assigned.status_code == 200
        assert assigned.json()["category_id"] == category_id

        cleared = client.patch(
            f"/api/products/{product_id}",
            json={"category_id": None},
            headers=_csrf_headers(client),
        )

        assert cleared.status_code == 200
        assert cleared.json()["category_id"] is None

    def test_unknown_category_rejected(self, client):
        _setup_business(client)

        response = _create_product(client, category_id=str(uuid.uuid4()))

        assert response.status_code == 404
        assert response.json()["detail"] == "CATEGORY_NOT_FOUND"

    def test_other_business_category_rejected_on_create(self, client):
        _setup_business(client)
        foreign_category_id = _create_category(client).json()["id"]
        _switch_to_second_business(client)

        response = _create_product(client, category_id=foreign_category_id)

        assert response.status_code == 404
        assert response.json()["detail"] == "CATEGORY_NOT_FOUND"

    def test_other_business_supplier_rejected_on_create(self, client):
        _setup_business(client)
        foreign_supplier_id = _create_supplier(client).json()["id"]
        _switch_to_second_business(client)

        response = _create_product(client, supplier_id=foreign_supplier_id)

        assert response.status_code == 404
        assert response.json()["detail"] == "SUPPLIER_NOT_FOUND"

    def test_other_business_references_rejected_on_update(self, client):
        _setup_business(client)
        foreign_category_id = _create_category(client).json()["id"]
        foreign_supplier_id = _create_supplier(client).json()["id"]
        _switch_to_second_business(client)
        product_id = _create_product(client).json()["id"]

        for payload, detail in (
            ({"category_id": foreign_category_id}, "CATEGORY_NOT_FOUND"),
            ({"supplier_id": foreign_supplier_id}, "SUPPLIER_NOT_FOUND"),
        ):
            response = client.patch(
                f"/api/products/{product_id}",
                json=payload,
                headers=_csrf_headers(client),
            )

            assert response.status_code == 404
            assert response.json()["detail"] == detail

    def test_database_rejects_cross_business_reference(self, client):
        """The composite foreign key holds even if the API is bypassed."""
        _setup_business(client)
        foreign_category_id = _create_category(client).json()["id"]
        foreign_supplier_id = _create_supplier(client).json()["id"]
        _switch_to_second_business(client)
        product_id = _create_product(client).json()["id"]

        for column, value in (
            ("category_id", foreign_category_id),
            ("supplier_id", foreign_supplier_id),
        ):
            db = TestingSessionLocal()

            try:
                db.execute(text("PRAGMA foreign_keys = ON"))
                product = db.get(Product, uuid.UUID(product_id))
                setattr(product, column, uuid.UUID(value))

                with pytest.raises(IntegrityError):
                    db.commit()
            finally:
                db.rollback()
                db.execute(text("PRAGMA foreign_keys = OFF"))
                db.close()

    def test_database_accepts_same_business_reference(self, client):
        _setup_business(client)
        product_id = _create_product(client).json()["id"]

        db = TestingSessionLocal()

        try:
            db.execute(text("PRAGMA foreign_keys = ON"))
            product = db.get(Product, uuid.UUID(product_id))

            category = Category(business_id=product.business_id, name="A")
            supplier = Supplier(
                business_id=product.business_id,
                name="B",
                lead_time_days=3,
            )
            db.add_all([category, supplier])
            db.flush()

            product.category_id = category.id
            product.supplier_id = supplier.id
            db.commit()
        finally:
            db.execute(text("PRAGMA foreign_keys = OFF"))
            db.close()
