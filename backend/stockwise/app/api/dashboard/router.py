from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from stockwise.app.api.dashboard.schemas import (
    CriticalProductResponse,
    DailyPerformanceResponse,
    DashboardSummaryResponse,
)
from stockwise.app.core.deps import get_current_user
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.user import User
from stockwise.app.services.returns import return_totals
from stockwise.app.services.periods import (
    business_timezone,
    local_date,
    period_start_date,
    start_of_local_day,
)


router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
)
def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    business = (
        db.query(Business)
        .filter(Business.owner_id == user.id)
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="BUSINESS_NOT_FOUND",
        )

    # Dashboard şu an son 15 günü gösterir.
    # Bugün dahil olmak üzere 15 günlük aralık oluşturuyoruz.
    # Days are calendar days where the business is, not UTC days.
    tz = business_timezone(business.timezone)
    now = datetime.now(timezone.utc)
    start_date = period_start_date(now, tz, 15)
    start_datetime = start_of_local_day(start_date, tz)

    sales = (
        db.query(Sale)
        .filter(
            Sale.business_id == business.id,
            Sale.created_at >= start_datetime,
        )
        .order_by(Sale.created_at.asc())
        .all()
    )

    total_sales = sum(
        (
            Decimal(sale.total_amount)
            for sale in sales
        ),
        Decimal("0.00"),
    )

    gross_profit = sum(
        (
            Decimal(sale.gross_profit)
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

    if total_sales > 0:
        gross_profit_margin = (
            gross_profit / total_sales
        ) * Decimal("100")
    else:
        gross_profit_margin = Decimal("0.00")

    gross_profit_margin = gross_profit_margin.quantize(
        Decimal("0.01")
    )

    # Günlük satış ve brüt kâr değerlerini topluyoruz.
    daily_totals = defaultdict(
        lambda: {
            "sales": Decimal("0.00"),
            "gross_profit": Decimal("0.00"),
        }
    )

    for sale in sales:
        sale_date = local_date(sale.created_at, tz)

        daily_totals[sale_date]["sales"] += Decimal(
            sale.total_amount
        )

        daily_totals[sale_date][
            "gross_profit"
        ] += Decimal(sale.gross_profit)

    # Satış olmayan günleri de 0 olarak gönderiyoruz.
    # Böylece grafik 15 günlük kesintisiz bir zaman serisi alır.
    daily_performance: list[
        DailyPerformanceResponse
    ] = []

    for offset in range(15):
        current_date = start_date + timedelta(
            days=offset
        )

        values = daily_totals[current_date]

        daily_performance.append(
            DailyPerformanceResponse(
                date=current_date.isoformat(),
                sales=str(values["sales"]),
                gross_profit=str(
                    values["gross_profit"]
                ),
            )
        )

    # Aktif ve minimum stok seviyesine ulaşmış / altına
    # düşmüş ürünlerin toplam sayısını hesaplıyoruz.
    critical_stock_count = (
        db.query(func.count(Product.id))
        .filter(
            Product.business_id == business.id,
            Product.is_active.is_(True),
            Product.stock_quantity
            <= Product.minimum_stock,
        )
        .scalar()
        or 0
    )

    # Dashboard tablosunda en fazla 5 kritik ürün
    # gösteriyoruz. En düşük stoklu ürünler önce gelir.
    critical_products = (
        db.query(Product)
        .filter(
            Product.business_id == business.id,
            Product.is_active.is_(True),
            Product.stock_quantity
            <= Product.minimum_stock,
        )
        .order_by(
            Product.stock_quantity.asc(),
            Product.name.asc(),
        )
        .limit(5)
        .all()
    )

    critical_product_responses = [
        CriticalProductResponse(
            id=str(product.id),
            name=product.name,
            sku=product.sku,
            stock_quantity=product.stock_quantity,
            minimum_stock=product.minimum_stock,
        )
        for product in critical_products
    ]

    return DashboardSummaryResponse(
        total_sales=str(total_sales),
        refund_total=str(refunds),
        net_sales=str(total_sales - refunds),
        returned_cost_total=str(returned_cost),
        net_gross_profit=str(
            gross_profit - (refunds - returned_cost)
        ),
        gross_profit=str(gross_profit),
        sale_count=sale_count,
        gross_profit_margin=str(
            gross_profit_margin
        ),
        critical_stock_count=int(
            critical_stock_count
        ),
        daily_performance=daily_performance,
        critical_products=critical_product_responses,
    )