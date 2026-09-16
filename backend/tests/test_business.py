import pytest
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from stockwise.app.models.user import User
from stockwise.app.models.business import Business


def _register_and_login(client, email="test@example.com", name="Test User"):
    client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "securepassword123",
        "password_confirm": "securepassword123",
    })
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "securepassword123",
    })
    return resp


def _create_business(client, **kwargs):
    payload = {
        "name": "Test İşletme",
        "currency": "TRY",
        "timezone": "Europe/Istanbul",
        **kwargs,
    }
    csrf = client.cookies.get("sw_csrf", "")
    return client.post(
        "/api/businesses",
        json=payload,
        headers={"x-csrf-token": csrf},
    )


class TestCreateBusiness:
    def test_create_business_success(self, client):
        _register_and_login(client)
        response = _create_business(client)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test İşletme"
        assert data["currency"] == "TRY"
        assert data["timezone"] == "Europe/Istanbul"
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_business_custom_values(self, client):
        _register_and_login(client)
        response = _create_business(
            client,
            name="My Store",
            currency="USD",
            timezone="America/New_York",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Store"
        assert data["currency"] == "USD"
        assert data["timezone"] == "America/New_York"

    def test_create_business_default_values(self, client):
        _register_and_login(client)
        response = _create_business(client)
        assert response.status_code == 201
        data = response.json()
        assert data["currency"] == "TRY"
        assert data["timezone"] == "Europe/Istanbul"

    def test_create_business_rejects_second(self, client):
        _register_and_login(client)
        response1 = _create_business(client, name="First")
        assert response1.status_code == 201
        response2 = _create_business(client, name="Second")
        assert response2.status_code == 409
        assert "işletme" in response2.json()["detail"].lower()

    def test_create_business_name_too_short(self, client):
        _register_and_login(client)
        response = _create_business(client, name="A")
        assert response.status_code == 422

    def test_create_business_name_blank(self, client):
        _register_and_login(client)
        response = _create_business(client, name="  ")
        assert response.status_code == 422

    def test_create_business_name_too_long(self, client):
        _register_and_login(client)
        response = _create_business(client, name="A" * 101)
        assert response.status_code == 422

    def test_create_business_invalid_currency(self, client):
        _register_and_login(client)
        response = _create_business(client, currency="GBP")
        assert response.status_code == 422

    def test_create_business_invalid_timezone(self, client):
        _register_and_login(client)
        response = _create_business(client, timezone="Invalid/Zone")
        assert response.status_code == 422

    def test_create_business_trims_name(self, client):
        _register_and_login(client)
        response = _create_business(client, name="  Trimmed Name  ")
        assert response.status_code == 201
        assert response.json()["name"] == "Trimmed Name"

    def test_create_business_currency_case_insensitive(self, client):
        _register_and_login(client)
        response = _create_business(client, currency="usd")
        assert response.status_code == 201
        assert response.json()["currency"] == "USD"


class TestGetMyBusiness:
    def test_get_my_business_success(self, client):
        _register_and_login(client)
        _create_business(client, name="My Biz")
        response = client.get("/api/businesses/me")
        assert response.status_code == 200
        assert response.json()["name"] == "My Biz"

    def test_get_my_business_not_found(self, client):
        _register_and_login(client)
        response = client.get("/api/businesses/me")
        assert response.status_code == 404
        assert "BUSINESS_NOT_FOUND" in response.json()["detail"]

    def test_get_my_business_isolation(self, client):
        _register_and_login(client, email="user1@example.com", name="User 1")
        _create_business(client, name="User 1 Biz")

        client.cookies.clear()
        _register_and_login(client, email="user2@example.com", name="User 2")
        response = client.get("/api/businesses/me")
        assert response.status_code == 404

    def test_two_users_separate_businesses(self, client):
        _register_and_login(client, email="user1@example.com", name="User 1")
        _create_business(client, name="User 1 Biz")
        resp1 = client.get("/api/businesses/me")
        user1_business = resp1.json()

        client.cookies.clear()
        _register_and_login(client, email="user2@example.com", name="User 2")
        _create_business(client, name="User 2 Biz")
        resp2 = client.get("/api/businesses/me")
        user2_business = resp2.json()

        assert user1_business["id"] != user2_business["id"]
        assert user1_business["name"] == "User 1 Biz"
        assert user2_business["name"] == "User 2 Biz"


class TestBusinessAuth:
    def test_create_business_unauthenticated(self, client):
        response = client.post(
            "/api/businesses",
            json={"name": "Test", "currency": "TRY", "timezone": "Europe/Istanbul"},
        )
        assert response.status_code == 401

    def test_get_business_unauthenticated(self, client):
        response = client.get("/api/businesses/me")
        assert response.status_code == 401

    def test_create_business_no_csrf(self, client):
        _register_and_login(client)
        response = client.post(
            "/api/businesses",
            json={"name": "Test", "currency": "TRY", "timezone": "Europe/Istanbul"},
        )
        assert response.status_code == 403

    def test_create_business_wrong_csrf(self, client):
        _register_and_login(client)
        response = client.post(
            "/api/businesses",
            json={"name": "Test", "currency": "TRY", "timezone": "Europe/Istanbul"},
            headers={"x-csrf-token": "wrong_token"},
        )
        assert response.status_code == 403

    def test_create_business_untrusted_origin(self, client):
        _register_and_login(client)
        csrf = client.cookies.get("sw_csrf", "")
        response = client.post(
            "/api/businesses",
            json={"name": "Test", "currency": "TRY", "timezone": "Europe/Istanbul"},
            headers={
                "x-csrf-token": csrf,
                "Origin": "https://evil.example",
            },
        )
        assert response.status_code == 403


class TestExistingAuthStillWorks:
    def test_register_still_works(self, client):
        response = client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "new@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        })
        assert response.status_code == 201

    def test_login_still_works(self, client):
        _register_and_login(client)
        client.cookies.clear()
        resp = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "securepassword123",
        })
        assert resp.status_code == 200

    def test_me_still_works(self, client):
        _register_and_login(client)
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
