"""Tests for time tracking tools (timers, entries, tags)."""
import pytest
from unittest.mock import AsyncMock, patch

from fastmcp import FastMCP
from tools.time_tracking import register_time_tracking_tools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_time_tracking_tools(mcp)
    return mcp


async def _call(mcp: FastMCP, tool_name: str, args: dict) -> dict:
    result = await mcp.call_tool(tool_name, args)
    return result.structured_content


SAMPLE_ENTRY = {
    "id": "timer_abc",
    "task": {"id": "task1", "name": "Build homepage"},
    "duration": 3600000,
    "billable": False,
    "description": "Frontend work",
    "start": 1740000000000,
}

SAMPLE_MEMBER = {"id": 200, "username": "Alice", "email": "alice@example.com"}


# ---------------------------------------------------------------------------
# get_time_entries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_time_entries_basic():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"data": [SAMPLE_ENTRY]})
    with patch("tools.time_tracking.api_client.get", new=mock_get):
        result = await _call(mcp, "get_time_entries", {})

    call_path = mock_get.call_args.args[0]
    assert "time_entries" in call_path
    assert "data" in result


@pytest.mark.asyncio
async def test_get_time_entries_date_range():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"data": []})
    with patch("tools.time_tracking.api_client.get", new=mock_get):
        await _call(mcp, "get_time_entries", {
            "start_date": "2026-02-01",
            "end_date": "2026-02-28",
        })

    params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
    assert "start_date" in params
    assert "end_date" in params
    assert isinstance(params["start_date"], int)
    assert isinstance(params["end_date"], int)


@pytest.mark.asyncio
async def test_get_time_entries_assignee_filter():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"data": []})
    with (
        patch("tools.time_tracking.cache.resolve_member", new=AsyncMock(return_value=SAMPLE_MEMBER)),
        patch("tools.time_tracking.api_client.get", new=mock_get),
    ):
        await _call(mcp, "get_time_entries", {"assignee": "Alice"})

    params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
    assert params["assignee"] == 200


@pytest.mark.asyncio
async def test_get_time_entries_include_flags():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"data": []})
    with patch("tools.time_tracking.api_client.get", new=mock_get):
        await _call(mcp, "get_time_entries", {
            "include_task_tags": True,
            "include_location_names": True,
        })

    params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
    assert params["include_task_tags"] == "true"
    assert params["include_location_names"] == "true"


# ---------------------------------------------------------------------------
# create_time_entry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_time_entry_basic():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_ENTRY)
    with patch("tools.time_tracking.api_client.post", new=mock_post):
        result = await _call(mcp, "create_time_entry", {
            "task_id": "task1",
            "duration": 3600000,
        })

    call_path = mock_post.call_args.args[0]
    assert "time_entries" in call_path
    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["tid"] == "task1"
    assert body["duration"] == 3600000
    assert body["billable"] is False


@pytest.mark.asyncio
async def test_create_time_entry_with_start_date():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_ENTRY)
    with patch("tools.time_tracking.api_client.post", new=mock_post):
        await _call(mcp, "create_time_entry", {
            "task_id": "task1",
            "duration": 1800000,
            "start": "2026-02-20",
        })

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert "start" in body
    assert isinstance(body["start"], int)


@pytest.mark.asyncio
async def test_create_time_entry_billable_with_tags():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_ENTRY)
    with patch("tools.time_tracking.api_client.post", new=mock_post):
        await _call(mcp, "create_time_entry", {
            "task_id": "task1",
            "duration": 3600000,
            "billable": True,
            "tags": ["client", "design"],
        })

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["billable"] is True
    assert body["tags"] == [{"name": "client"}, {"name": "design"}]


# ---------------------------------------------------------------------------
# update_time_entry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_time_entry_duration():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "timer_abc"})
    with patch("tools.time_tracking.api_client.put", new=mock_put):
        await _call(mcp, "update_time_entry", {
            "timer_id": "timer_abc",
            "duration": 7200000,
        })

    call_path = mock_put.call_args.args[0]
    assert "timer_abc" in call_path
    body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert body["duration"] == 7200000


@pytest.mark.asyncio
async def test_update_time_entry_billable_and_description():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "timer_abc"})
    with patch("tools.time_tracking.api_client.put", new=mock_put):
        await _call(mcp, "update_time_entry", {
            "timer_id": "timer_abc",
            "billable": True,
            "description": "Client call",
        })

    body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert body["billable"] is True
    assert body["description"] == "Client call"


@pytest.mark.asyncio
async def test_update_time_entry_tags():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "timer_abc"})
    with patch("tools.time_tracking.api_client.put", new=mock_put):
        await _call(mcp, "update_time_entry", {
            "timer_id": "timer_abc",
            "tags": ["support"],
        })

    body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert body["tags"] == [{"name": "support"}]


# ---------------------------------------------------------------------------
# delete_time_entry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_time_entry():
    mcp = _build_mcp()
    mock_delete = AsyncMock(return_value={"success": True})
    with patch("tools.time_tracking.api_client.delete", new=mock_delete):
        result = await _call(mcp, "delete_time_entry", {"timer_id": "timer_abc"})

    call_path = mock_delete.call_args.args[0]
    assert "timer_abc" in call_path
    assert result["success"] is True


# ---------------------------------------------------------------------------
# start_timer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_timer_basic():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value={"id": "timer_running", "task": {"id": "task1"}})
    with patch("tools.time_tracking.api_client.post", new=mock_post):
        result = await _call(mcp, "start_timer", {"task_id": "task1"})

    call_path = mock_post.call_args.args[0]
    assert "start" in call_path
    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["tid"] == "task1"
    assert body["billable"] is False


@pytest.mark.asyncio
async def test_start_timer_with_tags_and_description():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value={"id": "timer_running"})
    with patch("tools.time_tracking.api_client.post", new=mock_post):
        await _call(mcp, "start_timer", {
            "task_id": "task1",
            "description": "Working on nav",
            "billable": True,
            "tags": ["dev"],
        })

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["description"] == "Working on nav"
    assert body["billable"] is True
    assert body["tags"] == [{"name": "dev"}]


# ---------------------------------------------------------------------------
# stop_timer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stop_timer():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_ENTRY)
    with patch("tools.time_tracking.api_client.post", new=mock_post):
        result = await _call(mcp, "stop_timer", {})

    call_path = mock_post.call_args.args[0]
    assert "stop" in call_path


# ---------------------------------------------------------------------------
# get_running_timer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_running_timer_no_assignee():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"data": {}})
    with patch("tools.time_tracking.api_client.get", new=mock_get):
        await _call(mcp, "get_running_timer", {})

    call_path = mock_get.call_args.args[0]
    assert "running" in call_path


@pytest.mark.asyncio
async def test_get_running_timer_with_assignee():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"data": {}})
    with (
        patch("tools.time_tracking.cache.resolve_member", new=AsyncMock(return_value=SAMPLE_MEMBER)),
        patch("tools.time_tracking.api_client.get", new=mock_get),
    ):
        await _call(mcp, "get_running_timer", {"assignee": "Alice"})

    params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
    assert params["assignee"] == 200


# ---------------------------------------------------------------------------
# get_time_entry_history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_time_entry_history():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"history": []})
    with patch("tools.time_tracking.api_client.get", new=mock_get):
        await _call(mcp, "get_time_entry_history", {"timer_id": "timer_abc"})

    call_path = mock_get.call_args.args[0]
    assert "timer_abc" in call_path
    assert "history" in call_path


# ---------------------------------------------------------------------------
# get_time_tags
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_time_tags():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"data": [{"name": "billable"}, {"name": "internal"}]})
    with patch("tools.time_tracking.api_client.get", new=mock_get):
        result = await _call(mcp, "get_time_tags", {})

    call_path = mock_get.call_args.args[0]
    assert "tags" in call_path
    assert "data" in result


# ---------------------------------------------------------------------------
# manage_time_tags
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manage_time_tags_add():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value={"success": True})
    with patch("tools.time_tracking.api_client.post", new=mock_post):
        await _call(mcp, "manage_time_tags", {
            "time_entry_ids": ["timer_abc", "timer_xyz"],
            "tags": ["billable"],
            "action": "add",
        })

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["time_entry_ids"] == ["timer_abc", "timer_xyz"]
    assert body["tags"] == [{"name": "billable"}]
    assert body["action"] == "add"


@pytest.mark.asyncio
async def test_manage_time_tags_remove():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value={"success": True})
    with patch("tools.time_tracking.api_client.post", new=mock_post):
        await _call(mcp, "manage_time_tags", {
            "time_entry_ids": ["timer_abc"],
            "tags": ["internal"],
            "action": "remove",
        })

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["action"] == "remove"


@pytest.mark.asyncio
async def test_manage_time_tags_invalid_action():
    mcp = _build_mcp()
    result = await _call(mcp, "manage_time_tags", {
        "time_entry_ids": ["timer_abc"],
        "tags": ["billable"],
        "action": "update",  # invalid
    })

    assert result["success"] is False
    assert "add" in result["error"] or "remove" in result["error"]
