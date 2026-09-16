import uuid

from fastapi import Response
from sqlalchemy.orm import Session

from stockwise.app.core.deps import (
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    create_session,
)
from stockwise.app.models.business import Business
from stockwise.app.models.product import Product
from stockwise.app.models.user import User


def _create_user_and_business(db: Session):
    user = User(
        email=f"user_{uuid.uuid4().hex}@example.com",
        name="Test User",
        hashed_password="hashed",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    business = Business(
        owner_id=user.id,
        name="Test Business",
    )

    db.add(business)
    db.commit()
    db.refresh(business)

    return user, business


def _create_product(
    db: Session,
    business: Business,
    stock: int = 10,
):
    product = Product(
        business_id=business.id,
        name="Test Product",
        sku=f"SKU-{uuid.uuid4().hex[:8].upper()}",
        purchase_price=10.00,
        sale_price=15.00,
        stock_quantity=stock,
        minimum_stock=0,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def _extract_cookie(
    response: Response,
    cookie_name: str,
) -> str:
    cookie_headers = response.headers.getlist("set-cookie")

    for cookie_header in cookie_headers:
        if cookie_header.startswith(f"{cookie_name}="):
            return cookie_header.split(";", 1)[0].split("=", 1)[1]

    raise AssertionError(
        f"{cookie_name} cookie was not created"
    )


def _set_auth_cookies(
    client,
    db: Session,
    user: User,
):
    response = Response()

    create_session(
        response=response,
        db=db,
        user=user,
    )

    session_token = _extract_cookie(
        response,
        SESSION_COOKIE_NAME,
    )

    csrf_token = _extract_cookie(
        response,
        CSRF_COOKIE_NAME,
    )

    client.cookies.set(
        SESSION_COOKIE_NAME,
        session_token,
    )

    client.cookies.set(
        CSRF_COOKIE_NAME,
        csrf_token,
    )

    client.headers[CSRF_HEADER_NAME] = csrf_token
    client.headers["Origin"] = "http://localhost:3000"


def _set_session_without_csrf(
    client,
    db: Session,
    user: User,
):
    response = Response()

    create_session(
        response=response,
        db=db,
        user=user,
    )

    session_token = _extract_cookie(
        response,
        SESSION_COOKIE_NAME,
    )

    client.cookies.set(
        SESSION_COOKIE_NAME,
        session_token,
    )

    client.cookies.delete(CSRF_COOKIE_NAME)
    client.headers.pop(CSRF_HEADER_NAME, None)
    client.headers["Origin"] = "http://localhost:3000"


def test_create_in_movement(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product = _create_product(
        db_session,
        business,
        stock=5,
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product.id),
            "movement_type": "IN",
            "quantity": 3,
            "note": "restock",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["stock_before"] == 5
    assert data["stock_after"] == 8
    assert data["quantity"] == 3
    assert data["movement_type"] == "IN"

    db_session.refresh(product)

    assert product.stock_quantity == 8


def test_create_out_movement(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product = _create_product(
        db_session,
        business,
        stock=10,
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product.id),
            "movement_type": "OUT",
            "quantity": 4,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["stock_before"] == 10
    assert data["stock_after"] == 6

    db_session.refresh(product)

    assert product.stock_quantity == 6


def test_zero_quantity_rejected(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product = _create_product(
        db_session,
        business,
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product.id),
            "movement_type": "IN",
            "quantity": 0,
        },
    )

    assert response.status_code == 422


def test_negative_quantity_rejected(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product = _create_product(
        db_session,
        business,
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product.id),
            "movement_type": "IN",
            "quantity": -1,
        },
    )

    assert response.status_code == 422


def test_insufficient_stock_rejected(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product = _create_product(
        db_session,
        business,
        stock=2,
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product.id),
            "movement_type": "OUT",
            "quantity": 5,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "INSUFFICIENT_STOCK"

    db_session.refresh(product)

    assert product.stock_quantity == 2


def test_movement_for_other_business_rejected(
    client,
    db_session,
):
    user1, business1 = _create_user_and_business(
        db_session
    )

    user2, business2 = _create_user_and_business(
        db_session
    )

    product2 = _create_product(
        db_session,
        business2,
    )

    _set_auth_cookies(
        client,
        db_session,
        user1,
    )

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product2.id),
            "movement_type": "IN",
            "quantity": 1,
        },
    )

    assert response.status_code == 404


def test_inactive_product_rejected(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product = _create_product(
        db_session,
        business,
    )

    product.is_active = False
    db_session.commit()

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product.id),
            "movement_type": "IN",
            "quantity": 1,
        },
    )

    assert response.status_code == 404


def test_unauthenticated_rejected(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product = _create_product(
        db_session,
        business,
    )

    client.cookies.clear()

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product.id),
            "movement_type": "IN",
            "quantity": 1,
        },
    )

    assert response.status_code == 401


def test_get_movements_only_own_business(
    client,
    db_session,
):
    user1, business1 = _create_user_and_business(
        db_session
    )

    user2, business2 = _create_user_and_business(
        db_session
    )

    product1 = _create_product(
        db_session,
        business1,
    )

    _create_product(
        db_session,
        business2,
    )

    _set_auth_cookies(
        client,
        db_session,
        user1,
    )

    create_response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product1.id),
            "movement_type": "IN",
            "quantity": 2,
        },
    )

    assert create_response.status_code == 201

    _set_auth_cookies(
        client,
        db_session,
        user2,
    )

    response = client.get(
        "/api/stock-movements"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 0


def test_csrf_protection_enforced(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product = _create_product(
        db_session,
        business,
    )

    _set_session_without_csrf(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/stock-movements",
        json={
            "product_id": str(product.id),
            "movement_type": "IN",
            "quantity": 1,
        },
    )

    assert response.status_code == 403