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
    gross_profit: str
    sale_count: int
    gross_profit_margin: str
    critical_stock_count: int
    daily_performance: list[DailyPerformanceResponse]
    critical_products: list[CriticalProductResponse]