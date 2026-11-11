from pydantic import BaseModel


class DailyPerformanceResponse(BaseModel):
    date: str
    sales: str
    gross_profit: str


class CriticalProductResponse(BaseModel):
    id: str
    name: str
    sku: str
    stock_quantity: int
    minimum_stock: int


class DashboardSummaryResponse(BaseModel):
    total_sales: str
    # Refunds issued in the period, and sales after subtracting them.
    refund_total: str
    net_sales: str
    # Cost of the returned units, and gross profit after giving back
    # the profit on them.
    returned_cost_total: str
    net_gross_profit: str
    gross_profit: str
    sale_count: int
    gross_profit_margin: str
    critical_stock_count: int
    daily_performance: list[DailyPerformanceResponse]
    critical_products: list[CriticalProductResponse]