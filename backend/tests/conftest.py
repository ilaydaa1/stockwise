"""Test configuration.

By default the suite runs on an in-memory SQLite database: fast, and
needing nothing installed. Set TEST_DATABASE_URL to run the same
suite on PostgreSQL, which is what production uses and the only place
row locking and foreign keys are fully enforced:

    TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/stockwise_test

The database name must end in "_test". Every table in it is emptied
between tests, so this guard keeps the suite away from real data.

Markers:
    postgres_only  needs behaviour only PostgreSQL has (row locks,
                   enforced foreign keys); skipped on SQLite
    sqlite_only    deliberately writes rows that PostgreSQL would
                   refuse, to exercise the integrity checks
"""
import os
from contextlib import contextmanager

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stockwise.app.main import app
from stockwise.app.db.base import Base
from stockwise.app.db.session import get_db


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite:///:memory:",
)

IS_POSTGRES = make_url(TEST_DATABASE_URL).get_backend_name() == "postgresql"

if IS_POSTGRES:
    database_name = make_url(TEST_DATABASE_URL).database or ""

    if not database_name.endswith("_test"):
        raise RuntimeError(
            "TEST_DATABASE_URL must point at a database whose name ends "
            f"in '_test' (got '{database_name}'). The suite empties "
            "every table between tests."
        )

    engine = create_engine(TEST_DATABASE_URL)
else:
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def pytest_collection_modifyitems(config, items):
    skip_postgres = pytest.mark.skip(
        reason="needs PostgreSQL; set TEST_DATABASE_URL"
    )
    skip_sqlite = pytest.mark.skip(
        reason="writes rows PostgreSQL refuses; runs on SQLite only"
    )

    for item in items:
        if "postgres_only" in item.keywords and not IS_POSTGRES:
            item.add_marker(skip_postgres)

        if "sqlite_only" in item.keywords and IS_POSTGRES:
            item.add_marker(skip_sqlite)


@pytest.fixture(scope="session", autouse=True)
def _postgres_schema():
    """On PostgreSQL the tables are created once for the whole run."""
    if IS_POSTGRES:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    yield

    if IS_POSTGRES:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _truncate_all_tables():
    tables = ", ".join(
        f'"{table.name}"' for table in Base.metadata.sorted_tables
    )

    with engine.begin() as connection:
        # Fail fast instead of hanging if a test left a transaction
        # open that still holds a lock.
        connection.execute(text("SET LOCAL lock_timeout = '10s'"))
        connection.execute(
            text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
        )


@pytest.fixture(autouse=True)
def setup_db(_postgres_schema):
    if IS_POSTGRES:
        yield
        _truncate_all_tables()
    else:
        Base.metadata.create_all(bind=engine)

        yield

        Base.metadata.drop_all(bind=engine)


@contextmanager
def enforced_foreign_keys(db):
    """Make the database enforce foreign keys for a block of code.

    PostgreSQL always does. SQLite only does when asked, so it is
    switched on for the block and off again afterwards.
    """
    if IS_POSTGRES:
        yield
        return

    db.execute(text("PRAGMA foreign_keys = ON"))

    try:
        yield
    finally:
        db.rollback()
        db.execute(text("PRAGMA foreign_keys = OFF"))


@pytest.fixture
def db_session():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _no_rate_limit():
    from stockwise.app.core.limiter import limiter

    original = limiter.enabled
    limiter.enabled = False

    yield

    limiter.enabled = original
