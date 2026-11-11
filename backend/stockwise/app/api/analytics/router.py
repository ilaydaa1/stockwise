from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from stockwise.app.api.analytics.schemas import (
    AnalyticsDailyPerformanceResponse,
    AnalyticsSummaryResponse,
    ProductAnalysisListResponse,
    ProductAnalysisMetricsResponse,
    ProductAnalysisResponse,
    ProductPerformanceResponse,
    SaleHistoryItemResponse,
    SaleHistoryResponse,
)
from stockwise.app.core.deps import get_current_user
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.user import User
from stockwise.app.services.product_analysis import (
    get_product_performance,
)
from stockwise.app.services.returns import return_totals
from stockwise.app.services.periods import (
    business_timezone,
    local_date,
    period_start_date,
    start_of_local_day,
)


router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


def get_user_business(
    *,
    user: User,
    db: Session,
) -> Business:
    business = (
        db.query(Business)
        .filter(
            Business.owner_id == user.id
        )
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="BUSINESS_NOT_FOUND",
        )

    return business


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
)
def get_analytics_summary(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsSummaryResponse:
    business = get_user_business(
        user=user,
        db=db,
    )

    # Days are calendar days where the business is, not UTC days.
    tz = business_timezone(business.timezone)
    now = datetime.now(timezone.utc)
    start_date = period_start_date(now, tz, days)
    start_datetime = start_of_local_day(start_date, tz)

    sales = (
        db.query(Sale)
        .options(
            joinedload(
                Sale.items
            ).joinedload(
                SaleItem.product
            )
        )
        .filter(
            Sale.business_id
            == business.id,
            Sale.created_at
            >= start_datetime,
        )
        .order_by(
            Sale.created_at.desc()
        )
        .all()
    )

    total_sales = sum(
        (
            Decimal(
                sale.total_amount
            )
            for sale in sales
        ),
        Decimal("0.00"),
    )

    gross_profit = sum(
        (
            Decimal(
                sale.gross_profit
            )
            for sale in sales
        ),
        Decimal("0.00"),
    )

    sale_count = len(sales)

    refunds, returned_cost = return_totals(
        db,
        business_id=business.id,
        since=start_datetime,
    )

    if sale_count > 0:
        average_order_value = (
            total_sales
            / Decimal(sale_count)
        ).quantize(
            Decimal("0.01")
        )
    else:
        average_order_value = (
            Decimal("0.00")
        )

    if total_sales > 0:
        gross_profit_margin = (
            gross_profit
            / total_sales
            * Decimal("100")
        ).quantize(
            Decimal("0.01")
        )
    else:
        gross_profit_margin = (
            Decimal("0.00")
        )

    daily_totals = defaultdict(
        lambda: {
            "sales": Decimal(
                "0.00"
            ),
            "gross_profit": Decimal(
                "0.00"
            ),
            "sale_count": 0,
        }
    )

    for sale in sales:
        sale_date = local_date(sale.created_at, tz)

        daily_totals[
            sale_date
        ]["sales"] += Decimal(
            sale.total_amount
        )

        daily_totals[
            sale_date
        ]["gross_profit"] += Decimal(
            sale.gross_profit
        )

        daily_totals[
            sale_date
        ]["sale_count"] += 1

    daily_performance: list[
        AnalyticsDailyPerformanceResponse
    ] = []

    for offset in range(days):
        current_date = (
            start_date
            + timedelta(days=offset)
        )

        values = daily_totals[
            current_date
        ]

        daily_performance.append(
            AnalyticsDailyPerformanceResponse(
                date=(
                    current_date.isoformat()
                ),
                sales=str(
                    values["sales"]
                ),
                gross_profit=str(
                    values[
                        "gross_profit"
                    ]
                ),
                sale_count=int(
                    values[
                        "sale_count"
                    ]
                ),
            )
        )

    product_totals = defaultdict(
        lambda: {
            "product_name": "",
            "product_sku": "",
            "quantity_sold": 0,
            "revenue": Decimal(
                "0.00"
            ),
            "gross_profit": Decimal(
                "0.00"
            ),
        }
    )

    for sale in sales:
        for item in sale.items:
            product_id = str(
                item.product_id
            )

            product_data = (
                product_totals[
                    product_id
                ]
            )

            if item.product:
                product_data[
                    "product_name"
                ] = item.product.name

                product_data[
                    "product_sku"
                ] = item.product.sku
            else:
                product_data[
                    "product_name"
                ] = "Silinmiş ürün"

                product_data[
                    "product_sku"
                ] = "-"

            product_data[
                "quantity_sold"
            ] += item.quantity

            product_data[
                "revenue"
            ] += Decimal(
                item.subtotal
            )

            product_data[
                "gross_profit"
            ] += Decimal(
                item.gross_profit
            )

    product_performance = [
        ProductPerformanceResponse(
            product_id=product_id,
            product_name=str(
                values[
                    "product_name"
                ]
            ),
            product_sku=str(
                values[
                    "product_sku"
                ]
            ),
            quantity_sold=int(
                values[
                    "quantity_sold"
                ]
            ),
            revenue=str(
                values["revenue"]
            ),
            gross_profit=str(
                values[
                    "gross_profit"
                ]
            ),
        )
        for product_id, values
        in product_totals.items()
    ]

    product_performance.sort(
        key=lambda item: (
            Decimal(
                item.revenue
            ),
            item.quantity_sold,
        ),
        reverse=True,
    )

    sales_history: list[
        SaleHistoryResponse
    ] = []

    for sale in sales:
        history_items: list[
            SaleHistoryItemResponse
        ] = []

        total_quantity = 0

        for item in sale.items:
            total_quantity += (
                item.quantity
            )

            if item.product:
                product_name = (
                    item.product.name
                )

                product_sku = (
                    item.product.sku
                )
            else:
                product_name = (
                    "Silinmiş ürün"
                )

                product_sku = "-"

            history_items.append(
                SaleHistoryItemResponse(
                    product_id=str(
                        item.product_id
                    ),
                    product_name=(
                        product_name
                    ),
                    product_sku=(
                        product_sku
                    ),
                    quantity=(
                        item.quantity
                    ),
                    unit_sale_price=str(
                        item.unit_sale_price
                    ),
                    subtotal=str(
                        item.subtotal
                    ),
                )
            )

        sales_history.append(
            SaleHistoryResponse(
                id=str(
                    sale.id
                ),
                created_at=(
                    sale.created_at.isoformat()
                ),
                total_quantity=(
                    total_quantity
                ),
                total_amount=str(
                    sale.total_amount
                ),
                gross_profit=str(
                    sale.gross_profit
                ),
                items=history_items,
            )
        )

    return AnalyticsSummaryResponse(
        period_days=days,
        total_sales=str(
            total_sales
        ),
        refund_total=str(refunds),
        net_sales=str(total_sales - refunds),
        returned_cost_total=str(returned_cost),
        net_gross_profit=str(
            gross_profit - (refunds - returned_cost)
        ),
        gross_profit=str(
            gross_profit
        ),
        sale_count=sale_count,
        average_order_value=str(
            average_order_value
        ),
        gross_profit_margin=str(
            gross_profit_margin
        ),
        daily_performance=(
            daily_performance
        ),
        product_performance=(
            product_performance
        ),
        sales_history=(
            sales_history
        ),
    )


@router.get(
    "/products",
    response_model=ProductAnalysisListResponse,
)
def get_product_analysis(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductAnalysisListResponse:
    business = get_user_business(
        user=user,
        db=db,
    )

    results = get_product_performance(
        db=db,
        business_id=business.id,
        period_days=days,
        tz=business_timezone(business.timezone),
    )

    products = [
        ProductAnalysisResponse(
            product_id=str(
                result.product_id
            ),
            product_name=result.product_name,
            product_sku=result.product_sku,
            observation_days=(
                result.observation_days
            ),
            minimum_stock=result.minimum_stock,
            metrics=ProductAnalysisMetricsResponse(
                period_days=(
                    result.metrics.period_days
                ),
                quantity_sold=(
                    result.metrics.quantity_sold
                ),
                revenue=str(
                    result.metrics.revenue
                ),
                gross_profit=str(
                    result.metrics.gross_profit
                ),
                gross_profit_margin=str(
                    result.metrics.gross_profit_margin
                ),
                average_daily_sales=str(
                    result.metrics.average_daily_sales
                ),
                current_stock=(
                    result.metrics.current_stock
                ),
                stock_coverage_days=(
                    (
                        str(
                            result.metrics
                            .stock_coverage_days
                        )
                    )
                    if (
                        result.metrics
                        .stock_coverage_days
                        is not None
                    )
                    else None
                ),
                sales_trend_percent=(
                    (
                        str(
                            result.metrics
                            .sales_trend_percent
                        )
                    )
                    if (
                        result.metrics
                        .sales_trend_percent
                        is not None
                    )
                    else None
                ),
            ),
        )
        for result in results
    ]

    products.sort(
        key=lambda product: (
            Decimal(
                product.metrics.revenue
            ),
            product.metrics.quantity_sold,
        ),
        reverse=True,
    )

    return ProductAnalysisListResponse(
        period_days=days,
        products=products,
    )