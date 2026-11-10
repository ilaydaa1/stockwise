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
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.stock_movement import StockMovement
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
    name: str = "Test Product",
    stock: int = 10,
    purchase_price: float = 10.00,
    sale_price: float = 15.00,
):
    product = Product(
        business_id=business.id,
        name=name,
        sku=f"SKU-{uuid.uuid4().hex[:8].upper()}",
        purchase_price=purchase_price,
        sale_price=sale_price,
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


def test_create_single_product_sale(
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
        purchase_price=10.00,
        sale_price=15.00,
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["total_amount"] == "30.00"
    assert data["total_cost"] == "20.00"
    assert data["gross_profit"] == "10.00"

    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["product_name"] == product.name

    db_session.refresh(product)

    assert product.stock_quantity == 8


def test_create_multi_product_sale(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product1 = _create_product(
        db_session,
        business,
        name="Product 1",
        stock=10,
        purchase_price=10.00,
        sale_price=20.00,
    )

    product2 = _create_product(
        db_session,
        business,
        name="Product 2",
        stock=20,
        purchase_price=5.00,
        sale_price=10.00,
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product1.id),
                    "quantity": 2,
                },
                {
                    "product_id": str(product2.id),
                    "quantity": 3,
                },
            ]
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["total_amount"] == "70.00"
    assert data["total_cost"] == "35.00"
    assert data["gross_profit"] == "35.00"

    assert len(data["items"]) == 2

    db_session.refresh(product1)
    db_session.refresh(product2)

    assert product1.stock_quantity == 8
    assert product2.stock_quantity == 17

    sale = db_session.query(Sale).one()

    assert sale.total_amount == 70
    assert sale.total_cost == 35
    assert sale.gross_profit == 35

    sale_items = (
        db_session.query(SaleItem)
        .filter(SaleItem.sale_id == sale.id)
        .all()
    )

    assert len(sale_items) == 2


def test_sale_creates_stock_movements(
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
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 3,
                }
            ]
        },
    )

    assert response.status_code == 201

    movement = (
        db_session.query(StockMovement)
        .filter(
            StockMovement.product_id == product.id,
            StockMovement.movement_type == "SALE",
        )
        .one()
    )

    assert movement.quantity == 3
    assert movement.stock_before == 10
    assert movement.stock_after == 7


def test_insufficient_stock_rejects_entire_sale(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    product1 = _create_product(
        db_session,
        business,
        name="Product 1",
        stock=10,
    )

    product2 = _create_product(
        db_session,
        business,
        name="Product 2",
        stock=1,
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product1.id),
                    "quantity": 2,
                },
                {
                    "product_id": str(product2.id),
                    "quantity": 5,
                },
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "INSUFFICIENT_STOCK"

    db_session.refresh(product1)
    db_session.refresh(product2)

    assert product1.stock_quantity == 10
    assert product2.stock_quantity == 1

    assert db_session.query(Sale).count() == 0
    assert db_session.query(SaleItem).count() == 0

    sale_movements = (
        db_session.query(StockMovement)
        .filter(StockMovement.movement_type == "SALE")
        .count()
    )

    assert sale_movements == 0


def test_duplicate_product_rejected(
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
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 1,
                },
                {
                    "product_id": str(product.id),
                    "quantity": 2,
                },
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "DUPLICATE_PRODUCT"

    db_session.refresh(product)

    assert product.stock_quantity == 10
    assert db_session.query(Sale).count() == 0


def test_other_business_product_rejected(
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
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product2.id),
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "PRODUCT_NOT_FOUND"

    db_session.refresh(product2)

    assert product2.stock_quantity == 10
    assert db_session.query(Sale).count() == 0


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
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "PRODUCT_NOT_FOUND"


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
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 0,
                }
            ]
        },
    )

    assert response.status_code == 422
    assert db_session.query(Sale).count() == 0


def test_empty_sale_rejected(
    client,
    db_session,
):
    user, business = _create_user_and_business(
        db_session
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.post(
        "/api/sales",
        json={
            "items": []
        },
    )

    assert response.status_code == 422
    assert db_session.query(Sale).count() == 0


def test_unauthenticated_sale_rejected(
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
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 401


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
        "/api/sales",
        json={
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 403