"""Reporting days follow the business's timezone, not UTC."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.services.periods import (
    business_timezone,
    ensure_utc,
    local_date,
    period_start_date,
    start_of_local_day,
)
from stockwise.app.services.product_analysis import get_product_performance
from tests.test_sales import (
    _create_product,
    _create_user_and_business,
    _set_auth_cookies,
)


ISTANBUL = ZoneInfo("Europe/Istanbul")


class TestHelpers:
    def test_late_evening_utc_is_already_tomorrow_in_istanbul(self):
        stored = datetime(2026, 3, 9, 22, 30, tzinfo=timezone.utc)

        assert local_date(stored, ISTANBUL) == date(2026, 3, 10)
        assert local_date(stored, timezone.utc) == date(2026, 3, 9)

    def test_naive_values_are_read_as_utc(self):
        naive = datetime(2026, 3, 9, 22, 30)

        assert ensure_utc(naive).tzinfo is timezone.utc
        assert local_date(naive, ISTANBUL) == date(2026, 3, 10)

    def test_local_day_starts_three_hours_before_utc_midnight(self):
        assert start_of_local_day(date(2026, 3, 10), ISTANBUL) == datetime(
            2026, 3, 9, 21, 0, tzinfo=timezone.utc
        )

    def test_period_includes_today(self):
        now = datetime(2026, 3, 9, 22, 30, tzinfo=timezone.utc)

        assert period_start_date(now, ISTANBUL, 1) == date(2026, 3, 10)
        assert period_start_date(now, ISTANBUL, 30) == date(2026, 2, 9)

    def test_unknown_timezone_falls_back_to_utc(self):
        assert business_timezone("Mars/Olympus") is timezone.utc
        assert business_timezone(None) is timezone.utc
        assert business_timezone("Europe/Istanbul") == ISTANBUL


def _sale_at(db, business, product, when):
    sale = Sale(
        business_id=business.id,
        total_amount=Decimal("15.00"),
        total_cost=Decimal("10.00"),
        gross_profit=Decimal("5.00"),
        created_at=when,
    )
    db.add(sale)
    db.flush()
    db.add(
        SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=1,
            unit_sale_price=Decimal("15.00"),
            unit_purchase_price=Decimal("10.00"),
            subtotal=Decimal("15.00"),
            cost=Decimal("10.00"),
            gross_profit=Decimal("5.00"),
        )
    )
    db.commit()


def _yesterday_2230_utc() -> tuple[datetime, date]:
    """A moment that is one calendar day later in Istanbul than in
    UTC, and that is safely in the past whatever time the test runs."""
    utc_day = datetime.now(timezone.utc).date() - timedelta(days=2)
    when = datetime.combine(
        utc_day,
        datetime.min.time(),
        tzinfo=timezone.utc,
    ) + timedelta(hours=22, minutes=30)

    return when, utc_day + timedelta(days=1)


class TestEndpointsBucketByBusinessDay:
    def test_analytics_summary(self, client, db_session):
        user, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)
        when, local_day = _yesterday_2230_utc()
        _sale_at(db_session, business, product, when)
        _set_auth_cookies(client, db_session, user)

        days = {
            row["date"]: row
            for row in client.get("/api/analytics/summary?days=30").json()[
                "daily_performance"
            ]
        }

        assert days[local_day.isoformat()]["sale_count"] == 1
        assert days[when.date().isoformat()]["sale_count"] == 0

    def test_dashboard_summary(self, client, db_session):
        user, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)
        when, local_day = _yesterday_2230_utc()
        _sale_at(db_session, business, product, when)
        _set_auth_cookies(client, db_session, user)

        days = {
            row["date"]: row
            for row in client.get("/api/dashboard/summary").json()[
                "daily_performance"
            ]
        }

        assert Decimal(days[local_day.isoformat()]["sales"]) == Decimal("15")
        assert Decimal(days[when.date().isoformat()]["sales"]) == Decimal("0")

    def test_utc_business_keeps_utc_days(self, client, db_session):
        user, business = _create_user_and_business(db_session)
        business.timezone = "UTC"
        db_session.commit()
        product = _create_product(db_session, business)
        when, _ = _yesterday_2230_utc()
        _sale_at(db_session, business, product, when)
        _set_auth_cookies(client, db_session, user)

        days = {
            row["date"]: row
            for row in client.get("/api/analytics/summary?days=30").json()[
                "daily_performance"
            ]
        }

        assert days[when.date().isoformat()]["sale_count"] == 1


class TestPeriodBoundaryFollowsBusinessDay:
    def test_sale_just_after_local_midnight_belongs_to_the_period(
        self, db_session
    ):
        _, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)

        now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
        # 00:30 on 10 March in Istanbul, still 9 March in UTC.
        when = datetime(2026, 3, 9, 21, 30, tzinfo=timezone.utc)
        product.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        db_session.commit()
        _sale_at(db_session, business, product, when)

        def sold(tz):
            return get_product_performance(
                db=db_session,
                business_id=business.id,
                period_days=1,
                now=now,
                tz=tz,
            )[0].metrics.quantity_sold

        assert sold(ISTANBUL) == 1
        assert sold(timezone.utc) == 0


class TestProductAnalysisExposesMinimumStock:
    def test_minimum_stock_in_response(self, client, db_session):
        user, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)
        product.minimum_stock = 7
        db_session.commit()
        _set_auth_cookies(client, db_session, user)

        products = client.get("/api/analytics/products").json()["products"]

        assert products[0]["minimum_stock"] == 7
