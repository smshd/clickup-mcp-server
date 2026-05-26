"""Tests for task management tools (create, update, move, query, delete)."""
import pytest
from unittest.mock import AsyncMock, patch

from fastmcp import FastMCP
from tools.tasks import register_task_tools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_LIST = {
    "id": "list1",
    "name": "Website Build",
    "_folder_id": "folder1",
    "_folder_name": "Acme Corp",
    "_space_id": "space1",
    "_space_name": "Client Space",
}

SAMPLE_TASK_RESPONSE = {
    "id": "task_abc",
    "name": "Build homepage",
    "url": "https://app.clickup.com/t/task_abc",
    "status": {"status": "open", "type": "open"},
    "assignees": [],
    "priority": {"id": "3", "priority": "normal"},
    "due_date": None,
}

SAMPLE_TASKS_LIST = {
    "tasks": [
        {
            "id": "task1",
            "name": "Build homepage",
            "status": {"status": "in progress", "type": "open"},
            "priority": {"id": "2", "priority": "high"},
            "assignees": [{"id": 200, "username": "Alice", "email": "alice@example.com"}],
            "due_date": "1740000000000",
            "start_date": None,
            "tags": [],
            "list": {"id": "list1", "name": "Website Build"},
            "folder": {"id": "folder1", "name": "Acme Corp"},
            "space": {"id": "space1"},
            "url": "https://app.clickup.com/t/task1",
        }
    ]
}


def _build_mcp() -> FastMCP:
    """Create a fresh MCP instance with task tools registered."""
    mcp = FastMCP("test")
    register_task_tools(mcp)
    return mcp


async def _call(mcp: FastMCP, tool_name: str, args: dict) -> dict:
    """Call a tool via mcp.call_tool and return structured_content."""
    result = await mcp.call_tool(tool_name, args)
    return result.structured_content


# ---------------------------------------------------------------------------
# Test: create_task — list name resolution + API call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_resolves_list_name():
    mcp = _build_mcp()
    with (
        patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=SAMPLE_LIST)),
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.post", new=AsyncMock(return_value=SAMPLE_TASK_RESPONSE)),
    ):
        result = await _call(mcp, "create_task", {"list_name": "Website Build", "name": "Build homepage"})

    assert result["success"] is True
    assert result["task_id"] == "task_abc"
    assert result["name"] == "Build homepage"
    assert "url" in result


@pytest.mark.asyncio
async def test_create_task_list_not_found():
    mcp = _build_mcp()
    with patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "create_task", {"list_name": "Nonexistent List", "name": "My task"})

    assert result["success"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_create_task_with_assignees():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_TASK_RESPONSE)
    with (
        patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=SAMPLE_LIST)),
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[200, 100])),
        patch("tools.tasks.api_client.post", new=mock_post),
    ):
        result = await _call(mcp, "create_task", {
            "list_name": "Website Build",
            "name": "Build homepage",
            "assignees": ["Alice", "John"],
        })

    assert result["success"] is True
    # Verify the POST body included resolved assignee IDs
    call_args = mock_post.call_args
    posted_body = call_args.kwargs.get("json_body") or call_args.args[1]
    assert posted_body["assignees"] == [200, 100]


@pytest.mark.asyncio
async def test_create_task_with_priority():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_TASK_RESPONSE)
    with (
        patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=SAMPLE_LIST)),
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.post", new=mock_post),
    ):
        await _call(mcp, "create_task", {
            "list_name": "Website Build",
            "name": "Urgent task",
            "priority": "urgent",
        })

    posted_body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert posted_body["priority"] == 1  # "urgent" maps to 1


@pytest.mark.asyncio
async def test_create_task_with_due_date():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_TASK_RESPONSE)
    with (
        patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=SAMPLE_LIST)),
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.post", new=mock_post),
    ):
        await _call(mcp, "create_task", {
            "list_name": "Website Build",
            "name": "Timed task",
            "due_date": "2026-03-15",
        })

    posted_body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert "due_date" in posted_body
    assert isinstance(posted_body["due_date"], int)  # parsed to ms timestamp


# ---------------------------------------------------------------------------
# Test: update_task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_task_status():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "task_abc", "status": {"status": "in progress"}})
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.put", new=mock_put),
    ):
        await _call(mcp, "update_task", {"task_id": "task_abc", "status": "in progress"})

    put_body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert put_body["status"] == "in progress"


@pytest.mark.asyncio
async def test_update_task_no_fields_returns_error():
    mcp = _build_mcp()
    with patch("tools.tasks.api_client.put", new=AsyncMock()):
        result = await _call(mcp, "update_task", {"task_id": "task_abc"})

    assert result["success"] is False
    assert "No fields" in result["error"]


@pytest.mark.asyncio
async def test_update_task_clear_due_date():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "task_abc"})
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.put", new=mock_put),
    ):
        await _call(mcp, "update_task", {"task_id": "task_abc", "due_date": "null"})

    put_body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert put_body["due_date"] is None


@pytest.mark.asyncio
async def test_update_task_add_assignees():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "task_abc"})
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[200])),
        patch("tools.tasks.api_client.put", new=mock_put),
    ):
        await _call(mcp, "update_task", {"task_id": "task_abc", "add_assignees": ["Alice"]})

    put_body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert "assignees" in put_body
    assert put_body["assignees"]["add"] == [200]


@pytest.mark.asyncio
async def test_update_task_remove_assignees():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "task_abc"})
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[100])),
        patch("tools.tasks.api_client.put", new=mock_put),
    ):
        await _call(mcp, "update_task", {"task_id": "task_abc", "remove_assignees": ["John"]})

    put_body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert put_body["assignees"]["rem"] == [100]


@pytest.mark.asyncio
async def test_update_task_priority_string():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "task_abc"})
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.put", new=mock_put),
    ):
        await _call(mcp, "update_task", {"task_id": "task_abc", "priority": "high"})

    put_body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert put_body["priority"] == 2  # "high" maps to 2


# ---------------------------------------------------------------------------
# Test: move_task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_move_task_resolves_list():
    mcp = _build_mcp()
    dest_list = {**SAMPLE_LIST, "id": "list2", "name": "SEO Tasks"}
    mock_put = AsyncMock(return_value={"id": "task_abc", "list": {"id": "list2"}})
    with (
        patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=dest_list)),
        patch("tools.tasks.api_client.put", new=mock_put),
    ):
        await _call(mcp, "move_task", {"task_id": "task_abc", "list_name": "SEO Tasks"})

    put_body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert put_body["list"] == "list2"


@pytest.mark.asyncio
async def test_move_task_list_not_found():
    mcp = _build_mcp()
    with patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "move_task", {"task_id": "task_abc", "list_name": "Nonexistent"})

    assert result["success"] is False
    assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# Test: get_workspace_tasks — filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_workspace_tasks_basic():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_TASKS_LIST)
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.get", new=mock_get),
    ):
        result = await _call(mcp, "get_workspace_tasks", {})

    assert result["success"] is True
    assert result["count"] == 1
    assert isinstance(result["tasks"], list)


@pytest.mark.asyncio
async def test_get_workspace_tasks_status_filter():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_TASKS_LIST)
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.get", new=mock_get),
    ):
        await _call(mcp, "get_workspace_tasks", {"statuses": ["in progress", "open"]})

    call_args = mock_get.call_args
    params = call_args.kwargs.get("params") or call_args.args[1]
    assert params["statuses[]"] == ["in progress", "open"]


@pytest.mark.asyncio
async def test_get_workspace_tasks_assignee_filter():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_TASKS_LIST)
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[200])),
        patch("tools.tasks.api_client.get", new=mock_get),
    ):
        await _call(mcp, "get_workspace_tasks", {"assignees": ["Alice"]})

    call_args = mock_get.call_args
    params = call_args.kwargs.get("params") or call_args.args[1]
    assert params["assignees[]"] == [200]


@pytest.mark.asyncio
async def test_get_workspace_tasks_date_filter():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_TASKS_LIST)
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.get", new=mock_get),
    ):
        await _call(mcp, "get_workspace_tasks", {
            "due_date_gt": "2026-01-01",
            "due_date_lt": "2026-12-31",
        })

    call_args = mock_get.call_args
    params = call_args.kwargs.get("params") or call_args.args[1]
    assert "due_date_gt" in params
    assert "due_date_lt" in params
    assert isinstance(params["due_date_gt"], int)
    assert isinstance(params["due_date_lt"], int)


@pytest.mark.asyncio
async def test_get_workspace_tasks_tag_filter():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_TASKS_LIST)
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.get", new=mock_get),
    ):
        await _call(mcp, "get_workspace_tasks", {"tags": ["website", "priority"]})

    call_args = mock_get.call_args
    params = call_args.kwargs.get("params") or call_args.args[1]
    assert params["tags[]"] == ["website", "priority"]


@pytest.mark.asyncio
async def test_get_workspace_tasks_detail_level_names():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_TASKS_LIST)
    with (
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.get", new=mock_get),
    ):
        result = await _call(mcp, "get_workspace_tasks", {"detail_level": "names"})

    assert result["success"] is True
    task = result["tasks"][0]
    # names level: only id, name, status, list — not assignees or priority
    assert "id" in task
    assert "name" in task
    assert "assignees" not in task
    assert "priority" not in task


# ---------------------------------------------------------------------------
# Test: delete_task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_task_calls_api():
    mcp = _build_mcp()
    mock_delete = AsyncMock(return_value={"success": True})
    with patch("tools.tasks.api_client.delete", new=mock_delete):
        await _call(mcp, "delete_task", {"task_id": "task_abc"})

    mock_delete.assert_called_once()
    call_path = mock_delete.call_args.args[0]
    assert "task_abc" in call_path


@pytest.mark.asyncio
async def test_delete_task_returns_api_response():
    mcp = _build_mcp()
    mock_delete = AsyncMock(return_value={"success": True})
    with patch("tools.tasks.api_client.delete", new=mock_delete):
        result = await _call(mcp, "delete_task", {"task_id": "task_xyz"})

    assert result["success"] is True


# ---------------------------------------------------------------------------
# Test: get_tasks (list-scoped)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_tasks_resolves_list():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_TASKS_LIST)
    with (
        patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=SAMPLE_LIST)),
        patch("tools.tasks.cache.resolve_members", new=AsyncMock(return_value=[])),
        patch("tools.tasks.api_client.get", new=mock_get),
    ):
        result = await _call(mcp, "get_tasks", {"list_name": "Website Build"})

    assert result["success"] is True
    assert result["count"] == 1
    # Verify the API was called with the resolved list ID
    call_path = mock_get.call_args.args[0]
    assert "list1" in call_path


@pytest.mark.asyncio
async def test_get_tasks_list_not_found():
    mcp = _build_mcp()
    with patch("tools.tasks.cache.resolve_list", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "get_tasks", {"list_name": "No Such List"})

    assert result["success"] is False
    assert "not found" in result["error"]
