from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem


ZERO = Decimal("0.00")
TWO_DECIMALS = Decimal("0.01")


@dataclass(frozen=True)
class ProductPerformanceMetrics:
    period_days: int
    quantity_sold: int
    revenue: Decimal
    gross_profit: Decimal
    gross_profit_margin: Decimal
    average_daily_sales: Decimal
    current_stock: int
    stock_coverage_days: Decimal | None
    sales_trend_percent: Decimal | None


@dataclass(frozen=True)
class ProductAnalysisResult:
    product_id: UUID
    product_name: str
    product_sku: str
    observation_days: int
    metrics: ProductPerformanceMetrics
    minimum_stock: int = 0


def _round_decimal(
    value: Decimal,
) -> Decimal:
    return value.quantize(
        TWO_DECIMALS,
        rounding=ROUND_HALF_UP,
    )


def _ensure_utc(
    value: datetime,
) -> datetime:
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def _calculate_average_daily_sales_raw(
    quantity_sold: int,
    observation_days: int,
) -> Decimal:
    if observation_days <= 0:
        return ZERO

    if quantity_sold <= 0:
        return ZERO

    return (
        Decimal(quantity_sold)
        / Decimal(observation_days)
    )


def calculate_gross_profit_margin(
    revenue: Decimal,
    gross_profit: Decimal,
) -> Decimal:
    if revenue <= ZERO:
        return ZERO

    margin = (
        gross_profit
        / revenue
        * Decimal("100")
    )

    return _round_decimal(margin)


def calculate_average_daily_sales(
    quantity_sold: int,
    observation_days: int,
) -> Decimal:
    average = (
        _calculate_average_daily_sales_raw(
            quantity_sold=quantity_sold,
            observation_days=observation_days,
        )
    )

    return _round_decimal(
        average
    )


def calculate_stock_coverage_days(
    current_stock: int,
    average_daily_sales: Decimal,
) -> Decimal | None:
    if current_stock <= 0:
        return ZERO

    if average_daily_sales <= ZERO:
        return None

    coverage = (
        Decimal(current_stock)
        / average_daily_sales
    )

    return _round_decimal(
        coverage
    )


def calculate_sales_trend_percent(
    recent_quantity_sold: int,
    previous_quantity_sold: int,
) -> Decimal | None:
    if previous_quantity_sold <= 0:
        return None

    trend = (
        Decimal(
            recent_quantity_sold
            - previous_quantity_sold
        )
        / Decimal(
            previous_quantity_sold
        )
        * Decimal("100")
    )

    return _round_decimal(
        trend
    )


def calculate_product_performance(
    *,
    period_days: int,
    observation_days: int,
    quantity_sold: int,
    revenue: Decimal,
    gross_profit: Decimal,
    current_stock: int,
    sales_trend_percent: Decimal | None = None,
) -> ProductPerformanceMetrics:
    gross_profit_margin = (
        calculate_gross_profit_margin(
            revenue=revenue,
            gross_profit=gross_profit,
        )
    )

    raw_average_daily_sales = (
        _calculate_average_daily_sales_raw(
            quantity_sold=quantity_sold,
            observation_days=observation_days,
        )
    )

    average_daily_sales = (
        _round_decimal(
            raw_average_daily_sales
        )
    )

    stock_coverage_days = (
        calculate_stock_coverage_days(
            current_stock=current_stock,
            average_daily_sales=(
                raw_average_daily_sales
            ),
        )
    )

    return ProductPerformanceMetrics(
        period_days=period_days,
        quantity_sold=quantity_sold,
        revenue=_round_decimal(
            revenue
        ),
        gross_profit=_round_decimal(
            gross_profit
        ),
        gross_profit_margin=(
            gross_profit_margin
        ),
        average_daily_sales=(
            average_daily_sales
        ),
        current_stock=current_stock,
        stock_coverage_days=(
            stock_coverage_days
        ),
        sales_trend_percent=(
            sales_trend_percent
        ),
    )


def _calculate_observation_days(
    *,
    product_created_at: datetime,
    period_start: datetime,
    now: datetime,
    period_days: int,
    tz: tzinfo = timezone.utc,
) -> int:
    product_created_at_utc = (
        _ensure_utc(
            product_created_at
        )
    )

    period_start_utc = (
        _ensure_utc(
            period_start
        )
    )

    now_utc = _ensure_utc(
        now
    )

    observation_start = max(
        product_created_at_utc,
        period_start_utc,
    )

    if observation_start > now_utc:
        return 0

    observed_days = (
        now_utc.astimezone(tz).date()
        - observation_start.astimezone(tz).date()
    ).days + 1

    return min(
        max(observed_days, 1),
        period_days,
    )


def _get_period_quantity_sold(
    *,
    db: Session,
    business_id: UUID,
    product_id: UUID,
    start_datetime: datetime,
    end_datetime: datetime,
) -> int:
    sale_items = (
        db.query(SaleItem)
        .join(
            Sale,
            Sale.id == SaleItem.sale_id,
        )
        .filter(
            Sale.business_id
            == business_id,
            SaleItem.product_id
            == product_id,
            Sale.created_at
            >= start_datetime,
            Sale.created_at
            <= end_datetime,
        )
        .all()
    )

    return sum(
        item.quantity
        for item in sale_items
    )


def get_product_performance(
    *,
    db: Session,
    business_id: UUID,
    period_days: int = 30,
    now: datetime | None = None,
    tz: tzinfo = timezone.utc,
) -> list[ProductAnalysisResult]:
    if period_days <= 0:
        raise ValueError(
            "period_days must be greater than zero"
        )

    analysis_now = (
        _ensure_utc(now)
        if now is not None
        else datetime.now(
            timezone.utc
        )
    )

    # The period is made of calendar days in ``tz`` (the business's
    # timezone); its start is converted back to UTC for querying.
    current_period_start_date = (
        analysis_now.astimezone(tz).date()
        - timedelta(
            days=period_days - 1
        )
    )

    current_period_start = (
        datetime.combine(
            current_period_start_date,
            datetime.min.time(),
            tzinfo=tz,
        ).astimezone(timezone.utc)
    )

    previous_period_start = (
        current_period_start
        - timedelta(
            days=period_days
        )
    )

    previous_period_end = (
        current_period_start
        - timedelta(
            microseconds=1
        )
    )

    products = (
        db.query(Product)
        .filter(
            Product.business_id
            == business_id,
            Product.is_active.is_(True),
        )
        .order_by(
            Product.name.asc(),
            Product.id.asc(),
        )
        .all()
    )

    results: list[
        ProductAnalysisResult
    ] = []

    for product in products:
        current_sale_items = (
            db.query(SaleItem)
            .join(
                Sale,
                Sale.id == SaleItem.sale_id,
            )
            .filter(
                Sale.business_id
                == business_id,
                SaleItem.product_id
                == product.id,
                Sale.created_at
                >= current_period_start,
                Sale.created_at
                <= analysis_now,
            )
            .all()
        )

        quantity_sold = sum(
            item.quantity
            for item in current_sale_items
        )

        revenue = sum(
            (
                Decimal(
                    item.subtotal
                )
                for item
                in current_sale_items
            ),
            ZERO,
        )

        gross_profit = sum(
            (
                Decimal(
                    item.gross_profit
                )
                for item
                in current_sale_items
            ),
            ZERO,
        )

        previous_quantity_sold = (
            _get_period_quantity_sold(
                db=db,
                business_id=business_id,
                product_id=product.id,
                start_datetime=(
                    previous_period_start
                ),
                end_datetime=(
                    previous_period_end
                ),
            )
        )

        sales_trend_percent = (
            calculate_sales_trend_percent(
                recent_quantity_sold=(
                    quantity_sold
                ),
                previous_quantity_sold=(
                    previous_quantity_sold
                ),
            )
        )

        observation_days = (
            _calculate_observation_days(
                product_created_at=(
                    product.created_at
                ),
                period_start=(
                    current_period_start
                ),
                now=analysis_now,
                period_days=period_days,
                tz=tz,
            )
        )

        metrics = (
            calculate_product_performance(
                period_days=period_days,
                observation_days=(
                    observation_days
                ),
                quantity_sold=quantity_sold,
                revenue=revenue,
                gross_profit=gross_profit,
                current_stock=(
                    product.stock_quantity
                ),
                sales_trend_percent=(
                    sales_trend_percent
                ),
            )
        )

        results.append(
            ProductAnalysisResult(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                observation_days=(
                    observation_days
                ),
                metrics=metrics,
                minimum_stock=product.minimum_stock,
            )
        )

    return results