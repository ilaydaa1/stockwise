from datetime import datetime, timedelta, timezone
from decimal import Decimal

from stockwise.app.models.business import Business
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.user import User
from stockwise.app.services.product_analysis import (
    calculate_average_daily_sales,
    calculate_gross_profit_margin,
    calculate_product_performance,
    calculate_sales_trend_percent,
    calculate_stock_coverage_days,
    get_product_performance,
)


ANALYSIS_NOW = datetime(
    2026,
    9,
    20,
    12,
    0,
    tzinfo=timezone.utc,
)


def _create_user(
    db_session,
    *,
    email: str,
) -> User:
    user = User(
        email=email,
        name="Analysis User",
        hashed_password="test-password-hash",
    )

    db_session.add(user)
    db_session.flush()

    return user


def _create_business(
    db_session,
    *,
    user: User,
    name: str = "Analysis Business",
) -> Business:
    business = Business(
        owner_id=user.id,
        name=name,
        currency="TRY",
        timezone="Europe/Istanbul",
    )

    db_session.add(business)
    db_session.flush()

    return business


def _create_product(
    db_session,
    *,
    business: Business,
    name: str = "Kalem",
    sku: str = "KLM-001",
    stock_quantity: int = 40,
    created_at: datetime | None = None,
) -> Product:
    product = Product(
        business_id=business.id,
        name=name,
        sku=sku,
        purchase_price=Decimal("12.00"),
        sale_price=Decimal("25.00"),
        stock_quantity=stock_quantity,
        minimum_stock=10,
        created_at=(
            created_at
            if created_at is not None
            else ANALYSIS_NOW - timedelta(days=60)
        ),
    )

    db_session.add(product)
    db_session.flush()

    return product


def _create_sale_item(
    db_session,
    *,
    business: Business,
    product: Product,
    created_at: datetime,
    quantity: int,
    unit_sale_price: Decimal = Decimal("20.00"),
    unit_purchase_price: Decimal = Decimal("10.00"),
) -> SaleItem:
    subtotal = (
        unit_sale_price
        * Decimal(quantity)
    )

    cost = (
        unit_purchase_price
        * Decimal(quantity)
    )

    gross_profit = (
        subtotal - cost
    )

    sale = Sale(
        business_id=business.id,
        total_amount=subtotal,
        total_cost=cost,
        gross_profit=gross_profit,
        created_at=created_at,
    )

    db_session.add(sale)
    db_session.flush()

    item = SaleItem(
        sale_id=sale.id,
        product_id=product.id,
        quantity=quantity,
        unit_sale_price=unit_sale_price,
        unit_purchase_price=unit_purchase_price,
        subtotal=subtotal,
        cost=cost,
        gross_profit=gross_profit,
    )

    db_session.add(item)
    db_session.flush()

    return item


def test_calculate_gross_profit_margin():
    result = calculate_gross_profit_margin(
        revenue=Decimal("1800.00"),
        gross_profit=Decimal("900.00"),
    )

    assert result == Decimal("50.00")


def test_gross_profit_margin_returns_zero_when_revenue_is_zero():
    result = calculate_gross_profit_margin(
        revenue=Decimal("0.00"),
        gross_profit=Decimal("0.00"),
    )

    assert result == Decimal("0.00")


def test_calculate_average_daily_sales():
    result = calculate_average_daily_sales(
        quantity_sold=90,
        observation_days=30,
    )

    assert result == Decimal("3.00")


def test_average_daily_sales_uses_actual_observation_days():
    result = calculate_average_daily_sales(
        quantity_sold=15,
        observation_days=5,
    )

    assert result == Decimal("3.00")


def test_average_daily_sales_returns_zero_when_no_sales():
    result = calculate_average_daily_sales(
        quantity_sold=0,
        observation_days=30,
    )

    assert result == Decimal("0.00")


def test_average_daily_sales_returns_zero_when_observation_days_invalid():
    result = calculate_average_daily_sales(
        quantity_sold=10,
        observation_days=0,
    )

    assert result == Decimal("0.00")


def test_calculate_stock_coverage_days():
    result = calculate_stock_coverage_days(
        current_stock=40,
        average_daily_sales=Decimal("3.00"),
    )

    assert result == Decimal("13.33")


def test_stock_coverage_returns_zero_when_stock_is_empty():
    result = calculate_stock_coverage_days(
        current_stock=0,
        average_daily_sales=Decimal("3.00"),
    )

    assert result == Decimal("0.00")


def test_stock_coverage_is_unknown_when_product_has_no_sales():
    result = calculate_stock_coverage_days(
        current_stock=40,
        average_daily_sales=Decimal("0.00"),
    )

    assert result is None


def test_calculate_complete_product_performance():
    result = calculate_product_performance(
        period_days=30,
        observation_days=30,
        quantity_sold=90,
        revenue=Decimal("1800.00"),
        gross_profit=Decimal("900.00"),
        current_stock=40,
    )

    assert result.period_days == 30
    assert result.quantity_sold == 90
    assert result.revenue == Decimal("1800.00")
    assert result.gross_profit == Decimal("900.00")
    assert result.gross_profit_margin == Decimal("50.00")
    assert result.average_daily_sales == Decimal("3.00")
    assert result.current_stock == 40
    assert result.stock_coverage_days == Decimal("13.33")


def test_complete_product_performance_with_no_sales():
    result = calculate_product_performance(
        period_days=30,
        observation_days=30,
        quantity_sold=0,
        revenue=Decimal("0.00"),
        gross_profit=Decimal("0.00"),
        current_stock=50,
    )

    assert result.quantity_sold == 0
    assert result.revenue == Decimal("0.00")
    assert result.gross_profit == Decimal("0.00")
    assert result.gross_profit_margin == Decimal("0.00")
    assert result.average_daily_sales == Decimal("0.00")
    assert result.current_stock == 50
    assert result.stock_coverage_days is None


def test_product_performance_uses_unrounded_average_for_stock_coverage():
    result = calculate_product_performance(
        period_days=30,
        observation_days=6,
        quantity_sold=10,
        revenue=Decimal("200.00"),
        gross_profit=Decimal("100.00"),
        current_stock=100,
    )

    assert result.average_daily_sales == Decimal("1.67")
    assert result.stock_coverage_days == Decimal("60.00")


def test_database_product_performance_uses_sale_item_values(
    db_session,
):
    user = _create_user(
        db_session,
        email="analysis@example.com",
    )

    business = _create_business(
        db_session,
        user=user,
    )

    product = _create_product(
        db_session,
        business=business,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=40)
        ),
    )

    item = _create_sale_item(
        db_session,
        business=business,
        product=product,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=5)
        ),
        quantity=90,
    )

    db_session.commit()

    stored_item = (
        db_session.query(SaleItem)
        .filter(
            SaleItem.id == item.id
        )
        .one()
    )

    assert stored_item.quantity == 90

    assert Decimal(
        stored_item.subtotal
    ) == Decimal("1800.00")

    assert Decimal(
        stored_item.cost
    ) == Decimal("900.00")

    assert Decimal(
        stored_item.gross_profit
    ) == Decimal("900.00")

    assert Decimal(
        stored_item.unit_sale_price
    ) == Decimal("20.00")

    assert Decimal(
        stored_item.unit_purchase_price
    ) == Decimal("10.00")

    assert Decimal(
        product.purchase_price
    ) == Decimal("12.00")

    assert Decimal(
        product.sale_price
    ) == Decimal("25.00")


def test_service_includes_sales_inside_period(
    db_session,
):
    user = _create_user(
        db_session,
        email="inside@example.com",
    )

    business = _create_business(
        db_session,
        user=user,
    )

    product = _create_product(
        db_session,
        business=business,
        stock_quantity=40,
    )

    _create_sale_item(
        db_session,
        business=business,
        product=product,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=5)
        ),
        quantity=30,
    )

    db_session.commit()

    results = get_product_performance(
        db=db_session,
        business_id=business.id,
        period_days=30,
        now=ANALYSIS_NOW,
    )

    assert len(results) == 1

    result = results[0]

    assert result.product_id == product.id
    assert result.product_name == "Kalem"
    assert result.product_sku == "KLM-001"
    assert result.observation_days == 30

    assert result.metrics.quantity_sold == 30
    assert result.metrics.revenue == Decimal("600.00")
    assert result.metrics.gross_profit == Decimal("300.00")
    assert result.metrics.gross_profit_margin == Decimal("50.00")
    assert result.metrics.average_daily_sales == Decimal("1.00")
    assert result.metrics.current_stock == 40
    assert result.metrics.stock_coverage_days == Decimal("40.00")


def test_service_excludes_sales_outside_period(
    db_session,
):
    user = _create_user(
        db_session,
        email="outside@example.com",
    )

    business = _create_business(
        db_session,
        user=user,
    )

    product = _create_product(
        db_session,
        business=business,
        stock_quantity=40,
    )

    _create_sale_item(
        db_session,
        business=business,
        product=product,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=40)
        ),
        quantity=100,
    )

    _create_sale_item(
        db_session,
        business=business,
        product=product,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=3)
        ),
        quantity=10,
    )

    db_session.commit()

    results = get_product_performance(
        db=db_session,
        business_id=business.id,
        period_days=30,
        now=ANALYSIS_NOW,
    )

    assert len(results) == 1

    result = results[0]

    assert result.metrics.quantity_sold == 10
    assert result.metrics.revenue == Decimal("200.00")
    assert result.metrics.gross_profit == Decimal("100.00")


def test_service_uses_product_age_for_observation_days(
    db_session,
):
    user = _create_user(
        db_session,
        email="new-product@example.com",
    )

    business = _create_business(
        db_session,
        user=user,
    )

    product = _create_product(
        db_session,
        business=business,
        stock_quantity=20,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=4)
        ),
    )

    _create_sale_item(
        db_session,
        business=business,
        product=product,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=2)
        ),
        quantity=10,
    )

    db_session.commit()

    results = get_product_performance(
        db=db_session,
        business_id=business.id,
        period_days=30,
        now=ANALYSIS_NOW,
    )

    assert len(results) == 1

    result = results[0]

    assert result.observation_days == 5
    assert result.metrics.average_daily_sales == Decimal("2.00")
    assert result.metrics.stock_coverage_days == Decimal("10.00")


def test_service_includes_product_without_sales(
    db_session,
):
    user = _create_user(
        db_session,
        email="no-sales@example.com",
    )

    business = _create_business(
        db_session,
        user=user,
    )

    product = _create_product(
        db_session,
        business=business,
        name="Defter",
        sku="DFT-001",
        stock_quantity=50,
    )

    db_session.commit()

    results = get_product_performance(
        db=db_session,
        business_id=business.id,
        period_days=30,
        now=ANALYSIS_NOW,
    )

    assert len(results) == 1

    result = results[0]

    assert result.product_id == product.id
    assert result.product_name == "Defter"
    assert result.metrics.quantity_sold == 0
    assert result.metrics.revenue == Decimal("0.00")
    assert result.metrics.gross_profit == Decimal("0.00")
    assert result.metrics.average_daily_sales == Decimal("0.00")
    assert result.metrics.current_stock == 50
    assert result.metrics.stock_coverage_days is None


def test_service_does_not_mix_business_data(
    db_session,
):
    first_user = _create_user(
        db_session,
        email="first@example.com",
    )

    first_business = _create_business(
        db_session,
        user=first_user,
        name="First Business",
    )

    first_product = _create_product(
        db_session,
        business=first_business,
        name="Kalem",
        sku="KLM-001",
        stock_quantity=40,
    )

    second_user = _create_user(
        db_session,
        email="second@example.com",
    )

    second_business = _create_business(
        db_session,
        user=second_user,
        name="Second Business",
    )

    second_product = _create_product(
        db_session,
        business=second_business,
        name="Kalem",
        sku="KLM-001",
        stock_quantity=500,
    )

    _create_sale_item(
        db_session,
        business=first_business,
        product=first_product,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=2)
        ),
        quantity=10,
    )

    _create_sale_item(
        db_session,
        business=second_business,
        product=second_product,
        created_at=(
            ANALYSIS_NOW
            - timedelta(days=2)
        ),
        quantity=200,
    )

    db_session.commit()

    results = get_product_performance(
        db=db_session,
        business_id=first_business.id,
        period_days=30,
        now=ANALYSIS_NOW,
    )

    assert len(results) == 1

    result = results[0]

    assert result.product_id == first_product.id
    assert result.metrics.quantity_sold == 10
    assert result.metrics.revenue == Decimal("200.00")
    assert result.metrics.gross_profit == Decimal("100.00")
    assert result.metrics.current_stock == 40


def test_trend_is_positive_when_recent_sales_are_higher():
    previous_quantity = 28
    recent_quantity = 42

    previous_days = 14
    recent_days = 14

    previous_daily_sales = (
        Decimal(previous_quantity)
        / Decimal(previous_days)
    )

    recent_daily_sales = (
        Decimal(recent_quantity)
        / Decimal(recent_days)
    )

    change_percent = (
        (
            recent_daily_sales
            - previous_daily_sales
        )
        / previous_daily_sales
        * Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding="ROUND_HALF_UP",
    )

    assert previous_daily_sales == Decimal("2")
    assert recent_daily_sales == Decimal("3")
    assert change_percent == Decimal("50.00")


def test_trend_is_negative_when_recent_sales_are_lower():
    previous_quantity = 42
    recent_quantity = 28

    previous_days = 14
    recent_days = 14

    previous_daily_sales = (
        Decimal(previous_quantity)
        / Decimal(previous_days)
    )

    recent_daily_sales = (
        Decimal(recent_quantity)
        / Decimal(recent_days)
    )

    change_percent = (
        (
            recent_daily_sales
            - previous_daily_sales
        )
        / previous_daily_sales
        * Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding="ROUND_HALF_UP",
    )

    assert previous_daily_sales == Decimal("3")
    assert recent_daily_sales == Decimal("2")
    assert change_percent == Decimal("-33.33")


def test_trend_is_stable_when_sales_are_unchanged():
    previous_quantity = 28
    recent_quantity = 28

    previous_days = 14
    recent_days = 14

    previous_daily_sales = (
        Decimal(previous_quantity)
        / Decimal(previous_days)
    )

    recent_daily_sales = (
        Decimal(recent_quantity)
        / Decimal(recent_days)
    )

    change_percent = (
        (
            recent_daily_sales
            - previous_daily_sales
        )
        / previous_daily_sales
        * Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding="ROUND_HALF_UP",
    )

    assert previous_daily_sales == Decimal("2")
    assert recent_daily_sales == Decimal("2")
    assert change_percent == Decimal("0.00")


def test_trend_is_unknown_when_previous_period_has_no_sales():
    previous_quantity = 0
    recent_quantity = 20

    previous_days = 14
    recent_days = 14

    previous_daily_sales = (
        Decimal(previous_quantity)
        / Decimal(previous_days)
    )

    recent_daily_sales = (
        Decimal(recent_quantity)
        / Decimal(recent_days)
    )

    assert previous_daily_sales == Decimal("0")
    assert recent_daily_sales == (
        Decimal("20")
        / Decimal("14")
    )

    change_percent = None

    assert change_percent is None


def test_trend_calculation_uses_unrounded_daily_sales():
    previous_quantity = 10
    recent_quantity = 11

    previous_days = 6
    recent_days = 6

    previous_daily_sales = (
        Decimal(previous_quantity)
        / Decimal(previous_days)
    )

    recent_daily_sales = (
        Decimal(recent_quantity)
        / Decimal(recent_days)
    )

    change_percent = (
        (
            recent_daily_sales
            - previous_daily_sales
        )
        / previous_daily_sales
        * Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding="ROUND_HALF_UP",
    )

    assert previous_daily_sales == (
        Decimal("1.666666666666666666666666667")
    )

    assert recent_daily_sales == (
        Decimal("1.833333333333333333333333333")
    )

    assert change_percent == Decimal("10.00")


def test_calculate_sales_trend_percent_positive():
    result = calculate_sales_trend_percent(
        recent_quantity_sold=20,
        previous_quantity_sold=10,
    )

    assert result == Decimal("100.00")


def test_calculate_sales_trend_percent_negative():
    result = calculate_sales_trend_percent(
        recent_quantity_sold=10,
        previous_quantity_sold=20,
    )

    assert result == Decimal("-50.00")


def test_calculate_sales_trend_percent_stable():
    result = calculate_sales_trend_percent(
        recent_quantity_sold=20,
        previous_quantity_sold=20,
    )

    assert result == Decimal("0.00")


def test_calculate_sales_trend_percent_previous_period_has_no_sales():
    result = calculate_sales_trend_percent(
        recent_quantity_sold=20,
        previous_quantity_sold=0,
    )

    assert result is None


def test_calculate_sales_trend_percent_both_periods_have_no_sales():
    result = calculate_sales_trend_percent(
        recent_quantity_sold=0,
        previous_quantity_sold=0,
    )

    assert result is None


def test_calculate_sales_trend_percent_uses_unrounded_values():
    result = calculate_sales_trend_percent(
        recent_quantity_sold=7,
        previous_quantity_sold=3,
    )

    assert result == Decimal("133.33")