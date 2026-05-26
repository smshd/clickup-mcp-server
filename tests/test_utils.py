"""Tests for shared utilities: dates, responses, colors, errors."""
import time
import pytest
from datetime import datetime, timedelta

from utils.dates import parse_date
from utils.responses import size_response
from utils.colors import resolve_color
from utils.errors import format_error


# ===========================================================================
# Date parsing (parse_date)
# ===========================================================================

def test_parse_tomorrow():
    result = parse_date("tomorrow")
    assert result is not None
    tomorrow = datetime.now() + timedelta(days=1)
    # Should be tomorrow, end of day (23:59:59)
    result_dt = datetime.fromtimestamp(result / 1000)
    assert result_dt.date() == tomorrow.date()
    assert result_dt.hour == 23
    assert result_dt.minute == 59


def test_parse_in_3_days():
    result = parse_date("in 3 days")
    assert result is not None
    now_ms = int(time.time() * 1000)
    three_days_ms = 3 * 24 * 60 * 60 * 1000
    # Should be approximately 3 days from now (within a minute tolerance)
    diff = abs(result - (now_ms + three_days_ms))
    assert diff < 60_000  # within 1 minute


def test_parse_iso_date():
    result = parse_date("2026-03-15")
    assert result is not None
    result_dt = datetime.fromtimestamp(result / 1000)
    assert result_dt.year == 2026
    assert result_dt.month == 3
    assert result_dt.day == 15


def test_parse_unix_timestamp_ms():
    ts_ms = 1740000000000
    result = parse_date(str(ts_ms))
    assert result == ts_ms


def test_parse_unix_timestamp_seconds():
    ts_s = 1740000000
    result = parse_date(str(ts_s))
    assert result == ts_s * 1000


def test_parse_end_of_month():
    result = parse_date("end of month")
    assert result is not None
    result_dt = datetime.fromtimestamp(result / 1000)
    now = datetime.now()
    # The result should be in the current or next month boundary
    # It's the last day of the current month
    import calendar
    last_day = calendar.monthrange(now.year, now.month)[1]
    assert result_dt.day == last_day
    assert result_dt.hour == 23
    assert result_dt.minute == 59


def test_parse_invalid():
    result = parse_date("not a date")
    assert result is None


def test_parse_today():
    result = parse_date("today")
    assert result is not None
    result_dt = datetime.fromtimestamp(result / 1000)
    assert result_dt.date() == datetime.now().date()
    assert result_dt.hour == 23
    assert result_dt.minute == 59


def test_parse_days_ago():
    result = parse_date("3 days ago")
    assert result is not None
    now_ms = int(time.time() * 1000)
    three_days_ms = 3 * 24 * 60 * 60 * 1000
    expected_approx = now_ms - three_days_ms
    diff = abs(result - expected_approx)
    assert diff < 60_000  # within 1 minute


# ===========================================================================
# Response sizing (size_response)
# ===========================================================================

FULL_TASK = {
    "id": "task1",
    "name": "Build homepage",
    "status": {"status": "in progress", "type": "open"},
    "priority": {"id": "2", "priority": "high"},
    "assignees": [{"id": 200, "username": "Alice", "email": "alice@example.com"}],
    "due_date": "1740000000000",
    "start_date": "1739000000000",
    "tags": [{"name": "website"}],
    "list": {"id": "list1", "name": "Website Build"},
    "folder": {"id": "folder1", "name": "Acme Corp"},
    "space": {"id": "space1"},
    "url": "https://app.clickup.com/t/task1",
    "description": "Build the homepage for Acme Corp",
    "custom_fields": [],
    "creator": {"id": 100, "username": "John"},
    "watchers": [],
    "date_created": "1738000000000",
    "date_updated": "1739500000000",
}


def test_names_level():
    result = size_response([FULL_TASK], detail_level="names")
    assert len(result) == 1
    task = result[0]
    assert "id" in task
    assert "name" in task
    assert "status" in task
    assert "list" in task
    # names level should NOT include assignees, priority, due_date, etc.
    assert "assignees" not in task
    assert "priority" not in task
    assert "due_date" not in task
    assert "description" not in task


def test_summary_level():
    result = size_response([FULL_TASK], detail_level="summary")
    assert len(result) == 1
    task = result[0]
    # Summary includes core fields
    assert "id" in task
    assert "name" in task
    assert "status" in task
    assert "assignees" in task
    assert "due_date" in task
    assert "priority" in task
    assert "tags" in task
    # But not full description or custom fields
    assert "description" not in task
    assert "custom_fields" not in task


def test_detailed_level():
    result = size_response([FULL_TASK], detail_level="detailed")
    assert len(result) == 1
    task = result[0]
    # Detailed returns everything
    assert "description" in task
    assert "custom_fields" in task
    assert "creator" in task
    assert "date_created" in task


def test_auto_downgrade():
    # With a very tiny token limit, detailed should downgrade
    # Create a large task payload so it will definitely exceed limit
    big_task = {**FULL_TASK, "description": "x" * 10000}
    # With token_limit=1, even summary should downgrade to names
    result = size_response([big_task], detail_level="detailed", token_limit=1)
    assert len(result) == 1
    task = result[0]
    # Should have been downgraded — description should not be present
    assert "description" not in task


def test_assignee_flattening():
    result = size_response([FULL_TASK], detail_level="summary")
    task = result[0]
    # Assignees should be flattened to usernames
    assert isinstance(task["assignees"], list)
    assert task["assignees"] == ["Alice"]


def test_status_flattening():
    result = size_response([FULL_TASK], detail_level="summary")
    task = result[0]
    # Status should be flattened to string
    assert isinstance(task["status"], str)
    assert task["status"] == "in progress"


# ===========================================================================
# Color resolution (resolve_color)
# ===========================================================================

def test_hex_passthrough():
    result = resolve_color("#FF5722")
    assert result == "#FF5722"


def test_named_color():
    result = resolve_color("dark blue")
    assert result == "#04A9F4"


def test_unknown_color():
    result = resolve_color("rainbow")
    assert result == "rainbow"


def test_empty_color():
    result = resolve_color("")
    assert result == ""


# ===========================================================================
# Error formatting (format_error)
# ===========================================================================

def test_format_error_structure():
    error = Exception("something went wrong")
    result = format_error("my_tool", error)
    assert result["success"] is False
    assert "error" in result
    assert "error_type" in result
    assert result["tool"] == "my_tool"
    assert "hint" in result
    assert result["error"] == "something went wrong"
    assert result["error_type"] == "Exception"


def test_format_error_known_type():
    error = ValueError("invalid parameter")
    result = format_error("create_task", error)
    assert result["success"] is False
    assert result["error_type"] == "ValueError"
    assert result["tool"] == "create_task"
    # ValueError should get a specific hint (not the generic fallback)
    assert result["hint"] == "Check parameter format and types."
