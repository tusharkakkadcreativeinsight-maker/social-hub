from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


UTC = timezone.utc
INDIA_TZ = ZoneInfo("Asia/Kolkata")


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def utcnow_naive() -> datetime:
    """Return UTC without tzinfo for existing SQLAlchemy DateTime columns.

    The project stores database timestamps as naive UTC for SQLite/PostgreSQL
    compatibility. Always generate from aware UTC first to avoid local machine
    timezone leakage.
    """
    return utc_now().replace(tzinfo=None)


def ensure_utc(value: datetime | None) -> datetime | None:
    """Treat naive datetimes as UTC and convert aware datetimes to UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_utc_naive(value: datetime | None) -> datetime | None:
    """Normalize any datetime to naive UTC for database storage."""
    aware = ensure_utc(value)
    return aware.replace(tzinfo=None) if aware else None


def to_india_time(value: datetime | None) -> datetime | None:
    """Convert a database/API datetime to Asia/Kolkata timezone."""
    aware = ensure_utc(value)
    return aware.astimezone(INDIA_TZ) if aware else None


def isoformat_utc_z(value: datetime | None) -> str | None:
    """Serialize datetime as unambiguous UTC ISO-8601 with trailing Z."""
    aware = ensure_utc(value)
    if aware is None:
        return None
    return aware.isoformat(timespec="microseconds").replace("+00:00", "Z")


def format_time_ago(value: datetime | None, now: datetime | None = None) -> str:
    """Format relative time for India-facing UI labels."""
    aware = ensure_utc(value)
    if aware is None:
        return ""
    current = ensure_utc(now) or utc_now()
    diff = max(0, int((current - aware).total_seconds()))
    if diff < 60:
        return "Just now"
    if diff < 3600:
        mins = diff // 60
        return "1 min ago" if mins == 1 else f"{mins} mins ago"
    if diff < 86400:
        hours = diff // 3600
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"
    if diff < 172800:
        return "Yesterday"
    if diff < 604800:
        return f"{diff // 86400} days ago"
    return to_india_time(aware).strftime("%d %b %Y")


def expires_after(hours: int) -> datetime:
    """Return naive UTC expiry timestamp after the requested hours."""
    return utcnow_naive() + timedelta(hours=hours)