import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal

from fastapi import Response
from sqlalchemy.orm import Session

from stockwise.app.api.analytics.router import router as analytics_router
from stockwise.app.core.deps import (
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    create_session,
)
from stockwise.app.main import app
from stockwise.app.models.business import Business
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.user import User


def _ensure_analytics_router_registered():
    route_paths = {
        route.path
        for route in app.routes
        if hasattr(route, "path")
    }

    if "/api/analytics/summary" not in route_paths:
        app.include_router(
            analytics_router,
            prefix="/api",
        )


_ensure_analytics_router_registered()


def _create_user_and_business(
    db: Session,
):
    user = User(
        email=(
            f"user_{uuid.uuid4().hex}"
            "@example.com"
        ),
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
    name: str,
    sku: str,
    purchase_price: Decimal,
    sale_price: Decimal,
):
    product = Product(
        business_id=business.id,
        name=name,
        sku=(
            f"{sku}-"
            f"{uuid.uuid4().hex[:6]}"
        ),
        purchase_price=purchase_price,
        sale_price=sale_price,
        stock_quantity=100,
        minimum_stock=5,
        is_active=True,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def _create_sale(
    db: Session,
    business: Business,
    items: list[
        tuple[Product, int]
    ],
    created_at: datetime | None = None,
):
    total_amount = Decimal("0.00")
    total_cost = Decimal("0.00")
    gross_profit = Decimal("0.00")

    calculated_items = []

    for product, quantity in items:
        unit_sale_price = Decimal(
            product.sale_price
        )

        unit_purchase_price = Decimal(
            product.purchase_price
        )

        subtotal = (
            unit_sale_price * quantity
        )

        cost = (
            unit_purchase_price
            * quantity
        )

        item_profit = subtotal - cost

        total_amount += subtotal
        total_cost += cost
        gross_profit += item_profit

        calculated_items.append(
            (
                product,
                quantity,
                unit_sale_price,
                unit_purchase_price,
                subtotal,
                cost,
                item_profit,
            )
        )

    sale = Sale(
        business_id=business.id,
        total_amount=total_amount,
        total_cost=total_cost,
        gross_profit=gross_profit,
        created_at=(
            created_at
            or datetime.now(
                timezone.utc
            )
        ),
    )

    db.add(sale)
    db.flush()

    for (
        product,
        quantity,
        unit_sale_price,
        unit_purchase_price,
        subtotal,
        cost,
        item_profit,
    ) in calculated_items:
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=quantity,
            unit_sale_price=(
                unit_sale_price
            ),
            unit_purchase_price=(
                unit_purchase_price
            ),
            subtotal=subtotal,
            cost=cost,
            gross_profit=item_profit,
        )

        db.add(sale_item)

    db.commit()
    db.refresh(sale)

    return sale


def _extract_cookie(
    response: Response,
    cookie_name: str,
) -> str:
    cookie_headers = (
        response.headers.getlist(
            "set-cookie"
        )
    )

    for cookie_header in cookie_headers:
        if cookie_header.startswith(
            f"{cookie_name}="
        ):
            return (
                cookie_header
                .split(";", 1)[0]
                .split("=", 1)[1]
            )

    raise AssertionError(
        f"{cookie_name} cookie "
        "was not created"
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


def test_analytics_summary_totals(
    client,
    db_session,
):
    user, business = (
        _create_user_and_business(
            db_session
        )
    )

    pen = _create_product(
        db_session,
        business,
        name="Pen",
        sku="PEN",
        purchase_price=Decimal(
            "10.00"
        ),
        sale_price=Decimal(
            "20.00"
        ),
    )

    eraser = _create_product(
        db_session,
        business,
        name="Eraser",
        sku="ERASER",
        purchase_price=Decimal(
            "5.00"
        ),
        sale_price=Decimal(
            "10.00"
        ),
    )

    _create_sale(
        db_session,
        business,
        [
            (pen, 2),
            (eraser, 3),
        ],
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.get(
        "/api/analytics/summary"
        "?days=30"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["period_days"] == 30
    assert data["total_sales"] == "70.00"
    assert data["gross_profit"] == "35.00"
    assert data["sale_count"] == 1
    assert (
        data["average_order_value"]
        == "70.00"
    )
    assert (
        data["gross_profit_margin"]
        == "50.00"
    )


def test_analytics_product_performance(
    client,
    db_session,
):
    user, business = (
        _create_user_and_business(
            db_session
        )
    )

    pen = _create_product(
        db_session,
        business,
        name="Pen",
        sku="PEN",
        purchase_price=Decimal(
            "10.00"
        ),
        sale_price=Decimal(
            "20.00"
        ),
    )

    eraser = _create_product(
        db_session,
        business,
        name="Eraser",
        sku="ERASER",
        purchase_price=Decimal(
            "5.00"
        ),
        sale_price=Decimal(
            "10.00"
        ),
    )

    _create_sale(
        db_session,
        business,
        [
            (pen, 2),
            (eraser, 3),
        ],
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.get(
        "/api/analytics/summary"
        "?days=30"
    )

    assert response.status_code == 200

    products = response.json()[
        "product_performance"
    ]

    assert len(products) == 2

    pen_data = next(
        item
        for item in products
        if item["product_id"]
        == str(pen.id)
    )

    eraser_data = next(
        item
        for item in products
        if item["product_id"]
        == str(eraser.id)
    )

    assert (
        pen_data["quantity_sold"]
        == 2
    )
    assert (
        pen_data["revenue"]
        == "40.00"
    )
    assert (
        pen_data["gross_profit"]
        == "20.00"
    )

    assert (
        eraser_data["quantity_sold"]
        == 3
    )
    assert (
        eraser_data["revenue"]
        == "30.00"
    )
    assert (
        eraser_data["gross_profit"]
        == "15.00"
    )

    assert (
        products[0]["product_id"]
        == str(pen.id)
    )


def test_analytics_sales_history(
    client,
    db_session,
):
    user, business = (
        _create_user_and_business(
            db_session
        )
    )

    product = _create_product(
        db_session,
        business,
        name="Notebook",
        sku="NOTEBOOK",
        purchase_price=Decimal(
            "15.00"
        ),
        sale_price=Decimal(
            "25.00"
        ),
    )

    sale = _create_sale(
        db_session,
        business,
        [
            (product, 4),
        ],
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.get(
        "/api/analytics/summary"
        "?days=30"
    )

    assert response.status_code == 200

    history = response.json()[
        "sales_history"
    ]

    assert len(history) == 1

    history_sale = history[0]

    assert (
        history_sale["id"]
        == str(sale.id)
    )
    assert (
        history_sale[
            "total_quantity"
        ]
        == 4
    )
    assert (
        history_sale[
            "total_amount"
        ]
        == "100.00"
    )
    assert (
        history_sale[
            "gross_profit"
        ]
        == "40.00"
    )

    assert (
        len(
            history_sale["items"]
        )
        == 1
    )

    assert (
        history_sale["items"][0][
            "product_name"
        ]
        == "Notebook"
    )

    assert (
        history_sale["items"][0][
            "quantity"
        ]
        == 4
    )


def test_analytics_daily_performance(
    client,
    db_session,
):
    user, business = (
        _create_user_and_business(
            db_session
        )
    )

    product = _create_product(
        db_session,
        business,
        name="Product",
        sku="PRODUCT",
        purchase_price=Decimal(
            "10.00"
        ),
        sale_price=Decimal(
            "20.00"
        ),
    )

    now = datetime.now(
        timezone.utc
    )

    _create_sale(
        db_session,
        business,
        [(product, 1)],
        created_at=now,
    )

    _create_sale(
        db_session,
        business,
        [(product, 2)],
        created_at=(
            now
            - timedelta(days=1)
        ),
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.get(
        "/api/analytics/summary"
        "?days=7"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        len(
            data[
                "daily_performance"
            ]
        )
        == 7
    )

    assert (
        data["total_sales"]
        == "60.00"
    )
    assert (
        data["gross_profit"]
        == "30.00"
    )
    assert data["sale_count"] == 2
    assert (
        data[
            "average_order_value"
        ]
        == "30.00"
    )

    # Days are reported in the business's timezone (the default,
    # Europe/Istanbul), which can differ from the UTC date.
    local_today = now.astimezone(
        ZoneInfo(business.timezone)
    ).date()

    today = local_today.isoformat()

    yesterday = (
        local_today
        - timedelta(days=1)
    ).isoformat()

    today_data = next(
        item
        for item
        in data["daily_performance"]
        if item["date"] == today
    )

    yesterday_data = next(
        item
        for item
        in data["daily_performance"]
        if item["date"] == yesterday
    )

    assert (
        today_data["sales"]
        == "20.00"
    )
    assert (
        today_data["sale_count"]
        == 1
    )

    assert (
        yesterday_data["sales"]
        == "40.00"
    )
    assert (
        yesterday_data[
            "sale_count"
        ]
        == 1
    )


def test_analytics_period_filter(
    client,
    db_session,
):
    user, business = (
        _create_user_and_business(
            db_session
        )
    )

    product = _create_product(
        db_session,
        business,
        name="Product",
        sku="PRODUCT",
        purchase_price=Decimal(
            "10.00"
        ),
        sale_price=Decimal(
            "20.00"
        ),
    )

    now = datetime.now(
        timezone.utc
    )

    _create_sale(
        db_session,
        business,
        [(product, 1)],
        created_at=now,
    )

    _create_sale(
        db_session,
        business,
        [(product, 5)],
        created_at=(
            now
            - timedelta(days=20)
        ),
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response_7 = client.get(
        "/api/analytics/summary"
        "?days=7"
    )

    assert (
        response_7.status_code
        == 200
    )

    data_7 = response_7.json()

    assert (
        data_7["total_sales"]
        == "20.00"
    )
    assert (
        data_7["sale_count"]
        == 1
    )

    response_30 = client.get(
        "/api/analytics/summary"
        "?days=30"
    )

    assert (
        response_30.status_code
        == 200
    )

    data_30 = response_30.json()

    assert (
        data_30["total_sales"]
        == "120.00"
    )
    assert (
        data_30["sale_count"]
        == 2
    )


def test_analytics_90_day_period(
    client,
    db_session,
):
    user, business = (
        _create_user_and_business(
            db_session
        )
    )

    product = _create_product(
        db_session,
        business,
        name="Product",
        sku="PRODUCT",
        purchase_price=Decimal(
            "10.00"
        ),
        sale_price=Decimal(
            "20.00"
        ),
    )

    now = datetime.now(
        timezone.utc
    )

    _create_sale(
        db_session,
        business,
        [(product, 1)],
        created_at=(
            now
            - timedelta(days=60)
        ),
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.get(
        "/api/analytics/summary"
        "?days=90"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["period_days"]
        == 90
    )
    assert (
        data["total_sales"]
        == "20.00"
    )
    assert (
        data["sale_count"]
        == 1
    )
    assert (
        len(
            data[
                "daily_performance"
            ]
        )
        == 90
    )


def test_analytics_empty_data(
    client,
    db_session,
):
    user, _business = (
        _create_user_and_business(
            db_session
        )
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response = client.get(
        "/api/analytics/summary"
        "?days=30"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["total_sales"]
        == "0.00"
    )
    assert (
        data["gross_profit"]
        == "0.00"
    )
    assert data["sale_count"] == 0
    assert (
        data[
            "average_order_value"
        ]
        == "0.00"
    )
    assert (
        data[
            "gross_profit_margin"
        ]
        == "0.00"
    )
    assert (
        data[
            "product_performance"
        ]
        == []
    )
    assert (
        data["sales_history"]
        == []
    )
    assert (
        len(
            data[
                "daily_performance"
            ]
        )
        == 30
    )


def test_analytics_does_not_leak_other_business(
    client,
    db_session,
):
    user1, business1 = (
        _create_user_and_business(
            db_session
        )
    )

    _user2, business2 = (
        _create_user_and_business(
            db_session
        )
    )

    product1 = _create_product(
        db_session,
        business1,
        name="Business 1 Product",
        sku="B1",
        purchase_price=Decimal(
            "10.00"
        ),
        sale_price=Decimal(
            "20.00"
        ),
    )

    product2 = _create_product(
        db_session,
        business2,
        name="Business 2 Product",
        sku="B2",
        purchase_price=Decimal(
            "50.00"
        ),
        sale_price=Decimal(
            "100.00"
        ),
    )

    _create_sale(
        db_session,
        business1,
        [(product1, 1)],
    )

    _create_sale(
        db_session,
        business2,
        [(product2, 10)],
    )

    _set_auth_cookies(
        client,
        db_session,
        user1,
    )

    response = client.get(
        "/api/analytics/summary"
        "?days=30"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["total_sales"]
        == "20.00"
    )
    assert (
        data["gross_profit"]
        == "10.00"
    )
    assert data["sale_count"] == 1

    assert (
        len(
            data[
                "product_performance"
            ]
        )
        == 1
    )

    assert (
        data[
            "product_performance"
        ][0]["product_name"]
        == "Business 1 Product"
    )


def test_analytics_requires_authentication(
    client,
):
    client.cookies.clear()

    response = client.get(
        "/api/analytics/summary"
        "?days=30"
    )

    assert response.status_code == 401


def test_analytics_rejects_invalid_period(
    client,
    db_session,
):
    user, _business = (
        _create_user_and_business(
            db_session
        )
    )

    _set_auth_cookies(
        client,
        db_session,
        user,
    )

    response_zero = client.get(
        "/api/analytics/summary"
        "?days=0"
    )

    assert (
        response_zero.status_code
        == 422
    )

    response_too_large = client.get(
        "/api/analytics/summary"
        "?days=366"
    )

    assert (
        response_too_large.status_code
        == 422
    )