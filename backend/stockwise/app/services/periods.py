"""Reporting periods in a business's own timezone.

Timestamps are stored in UTC, but "today" and "the last 30 days"
mean calendar days where the shop is. A sale at 01:30 on Tuesday in
Istanbul is 22:30 on Monday in UTC; grouping by the UTC date would
report it on the wrong day.
"""
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def business_timezone(name: str | None) -> tzinfo:
    """Timezone for a stored name, falling back to UTC if unknown."""
    if not name:
        return timezone.utc

    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def ensure_utc(value: datetime) -> datetime:
    """Treat naive datetimes (as SQLite returns them) as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def local_date(value: datetime, tz: tzinfo) -> date:
    """Calendar date of a stored timestamp where the business is."""
    return ensure_utc(value).astimezone(tz).date()


def start_of_local_day(day: date, tz: tzinfo) -> datetime:
    """UTC instant at which a local calendar day begins.

    Returned in UTC because some databases compare timestamps as
    plain values, so query bounds must be in the stored timezone.
    """
    return datetime.combine(day, time.min, tzinfo=tz).astimezone(
        timezone.utc
    )


def period_start_date(now: datetime, tz: tzinfo, days: int) -> date:
    """First local day of a period of ``days`` days ending today."""
    return local_date(now, tz) - timedelta(days=days - 1)
