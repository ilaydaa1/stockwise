from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

from stockwise.app.core.config import settings

# Built in one place (Settings.database_url) so the application and
# the migrations can never disagree about where the database is.
DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    pool_size=settings.sqlalchemy_pool_size,
    max_overflow=settings.sqlalchemy_max_overflow,
    pool_timeout=settings.sqlalchemy_pool_timeout,
    # Replace connections the database closed while they sat idle,
    # for example after the database container restarts.
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)


class Base(DeclarativeBase):
    pass
