from datetime import UTC, datetime
from zoneinfo import ZoneInfo


TAIPEI_TIMEZONE = ZoneInfo("Asia/Taipei")


def as_utc(value: datetime | None) -> datetime | None:
    """Return database timestamps as timezone-aware UTC values."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def as_taipei(value: datetime) -> datetime:
    utc_value = as_utc(value)
    assert utc_value is not None
    return utc_value.astimezone(TAIPEI_TIMEZONE)
