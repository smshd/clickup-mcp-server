"""Natural language date parsing to Unix milliseconds."""
from typing import Optional
from datetime import datetime, timedelta
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta
import re
import time


def parse_date(value: str) -> Optional[int]:
    """
    Parse a date string to Unix milliseconds.

    Accepts:
    - Unix ms timestamp (pass-through if numeric)
    - ISO 8601: "2026-03-15", "2026-03-15T09:00:00"
    - Relative: "tomorrow", "next Monday", "in 3 days", "end of month"
    - Natural: "March 15 at 2pm", "next Friday at 9am"

    Returns Unix milliseconds or None if unparseable.
    """
    if value is None:
        return None

    value = value.strip()

    # Already a timestamp
    if value.isdigit() and len(value) >= 10:
        ts = int(value)
        if ts < 10_000_000_000:  # seconds, convert to ms
            ts *= 1000
        return ts

    now = datetime.now()

    # Relative shortcuts
    lower = value.lower()
    if lower == "today":
        return _to_ms(now.replace(hour=23, minute=59, second=59))
    if lower == "tomorrow":
        return _to_ms((now + timedelta(days=1)).replace(hour=23, minute=59, second=59))
    if lower == "yesterday":
        return _to_ms((now - timedelta(days=1)).replace(hour=23, minute=59, second=59))
    if lower == "end of month":
        next_month = now + relativedelta(months=1)
        end = next_month.replace(day=1) - timedelta(days=1)
        return _to_ms(end.replace(hour=23, minute=59, second=59))
    if lower == "start of today":
        return _to_ms(now.replace(hour=0, minute=0, second=0))
    if lower == "end of today":
        return _to_ms(now.replace(hour=23, minute=59, second=59))
    if lower == "end of week":
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour >= 17:
            days_until_friday = 7
        end = now + timedelta(days=days_until_friday)
        return _to_ms(end.replace(hour=23, minute=59, second=59))

    # "in X days/hours/weeks"
    in_match = re.match(r"in\s+(\d+)\s+(day|hour|week|month)s?", lower)
    if in_match:
        amount = int(in_match.group(1))
        unit = in_match.group(2)
        if unit == "day":
            dt = now + timedelta(days=amount)
        elif unit == "hour":
            dt = now + timedelta(hours=amount)
        elif unit == "week":
            dt = now + timedelta(weeks=amount)
        elif unit == "month":
            dt = now + relativedelta(months=amount)
        return _to_ms(dt)

    # "X days/hours ago"
    ago_match = re.match(r"(\d+)\s+(day|hour|week|month)s?\s+ago", lower)
    if ago_match:
        amount = int(ago_match.group(1))
        unit = ago_match.group(2)
        if unit == "day":
            dt = now - timedelta(days=amount)
        elif unit == "hour":
            dt = now - timedelta(hours=amount)
        elif unit == "week":
            dt = now - timedelta(weeks=amount)
        elif unit == "month":
            dt = now - relativedelta(months=amount)
        return _to_ms(dt)

    # Fallback to dateutil parser
    try:
        dt = dateutil_parser.parse(value, fuzzy=True)
        return _to_ms(dt)
    except (ValueError, OverflowError):
        return None


def _to_ms(dt: datetime) -> int:
    """Convert datetime to Unix milliseconds."""
    return int(dt.timestamp() * 1000)


def ms_to_iso(ms: int) -> str:
    """Convert Unix milliseconds to ISO 8601 string."""
    return datetime.fromtimestamp(ms / 1000).isoformat()
