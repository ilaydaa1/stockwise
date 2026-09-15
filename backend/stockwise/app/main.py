from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stockwise.app.core.config import settings
from stockwise.app.db.session import engine, SessionLocal
from stockwise.app.db.base import Base
from stockwise.app.api import health, ready


def create_application() -> FastAPI:
    application = FastAPI(title="StockWise", version="0.1.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix="/api", tags=["health"])
    application.include_router(ready.router, prefix="/api", tags=["ready"])

    return application


app = create_application()


@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass


@app.on_event("shutdown")
def on_shutdown():
    SessionLocal.close()
