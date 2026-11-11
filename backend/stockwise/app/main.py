from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from stockwise.app.core.config import settings
from stockwise.app.core.limiter import limiter
from stockwise.app.api import health, ready
from stockwise.app.api.auth import router as auth_router
from stockwise.app.api.analytics.router import router as analytics_router
from stockwise.app.api.business import router as business_router
from stockwise.app.api.categories import router as categories_router
from stockwise.app.api.suppliers import router as suppliers_router
from stockwise.app.api.dashboard.router import router as dashboard_router
from stockwise.app.api.products import router as products_router
from stockwise.app.api.sales.router import router as sales_router
from stockwise.app.api.stock_movements import router as stock_movements_router


def create_application() -> FastAPI:
    application = FastAPI(
        title="StockWise",
        version="0.1.0",
    )

    application.state.limiter = limiter

    application.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Lets a browser on another origin read the paging total.
        expose_headers=["X-Total-Count"],
    )

    application.include_router(
        health.router,
        prefix="/api",
        tags=["health"],
    )

    application.include_router(
        ready.router,
        prefix="/api",
        tags=["ready"],
    )

    application.include_router(
        auth_router,
        prefix="/api",
        tags=["auth"],
    )

    application.include_router(
        business_router,
        prefix="/api",
        tags=["businesses"],
    )

    application.include_router(
        categories_router,
        prefix="/api",
        tags=["categories"],
    )

    application.include_router(
        suppliers_router,
        prefix="/api",
        tags=["suppliers"],
    )

    application.include_router(
        products_router,
        prefix="/api",
        tags=["products"],
    )

    application.include_router(
        stock_movements_router,
        prefix="/api",
        tags=["stock-movements"],
    )

    application.include_router(
        sales_router,
        prefix="/api",
        tags=["sales"],
    )

    application.include_router(
        analytics_router,
        prefix="/api",
        tags=["analytics"],
    )

    application.include_router(
        dashboard_router,
        prefix="/api",
        tags=["dashboard"],
    )

    return application


app = create_application()