from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase
from stockwise.app.core.config import settings

DATABASE_URL = (
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=settings.sqlalchemy_pool_size,
    max_overflow=settings.sqlalchemy_max_overflow,
    pool_timeout=settings.sqlalchemy_pool_timeout,
    connect_args={"connect_timeout": 5},
)


class Base(DeclarativeBase):
    pass
