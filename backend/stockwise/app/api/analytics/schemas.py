from pydantic import BaseModel


class AnalyticsDailyPerformanceResponse(BaseModel):
    date: str
    sales: str
    gross_profit: str
    sale_count: int


class ProductPerformanceResponse(BaseModel):
    product_id: str
    product_name: str
    product_sku: str
    quantity_sold: int
    revenue: str
    gross_profit: str


class ProductAnalysisMetricsResponse(BaseModel):
    period_days: int
    quantity_sold: int
    revenue: str
    gross_profit: str
    gross_profit_margin: str
    average_daily_sales: str
    current_stock: int
    stock_coverage_days: str | None
    sales_trend_percent: str | None


class ProductAnalysisResponse(BaseModel):
    product_id: str
    product_name: str
    product_sku: str
    observation_days: int
    metrics: ProductAnalysisMetricsResponse


class SaleHistoryItemResponse(BaseModel):
    product_id: str
    product_name: str
    product_sku: str
    quantity: int
    unit_sale_price: str
    subtotal: str


class SaleHistoryResponse(BaseModel):
    id: str
    created_at: str
    total_quantity: int
    total_amount: str
    gross_profit: str
    items: list[SaleHistoryItemResponse]


class AnalyticsSummaryResponse(BaseModel):
    period_days: int

    total_sales: str
    gross_profit: str
    sale_count: int
    average_order_value: str
    gross_profit_margin: str

    daily_performance: list[
        AnalyticsDailyPerformanceResponse
    ]

    product_performance: list[
        ProductPerformanceResponse
    ]

    sales_history: list[
        SaleHistoryResponse
    ]


class ProductAnalysisListResponse(BaseModel):
    period_days: int
    products: list[
        ProductAnalysisResponse
    ]