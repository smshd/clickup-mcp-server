"""Tests for comment management tools (CRUD and threaded replies)."""
import pytest
from unittest.mock import AsyncMock, patch

from fastmcp import FastMCP
from tools.comments import register_comment_tools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_comment_tools(mcp)
    return mcp


async def _call(mcp: FastMCP, tool_name: str, args: dict) -> dict:
    result = await mcp.call_tool(tool_name, args)
    return result.structured_content


SAMPLE_COMMENT = {
    "id": "comment_abc",
    "comment_text": "Looks good!",
    "user": {"id": 100, "username": "John"},
    "resolved": False,
    "date": "1740000000000",
}

SAMPLE_COMMENTS_LIST = {
    "comments": [SAMPLE_COMMENT]
}

SAMPLE_MEMBER = {"id": 200, "username": "Alice", "email": "alice@example.com"}


# ---------------------------------------------------------------------------
# get_task_comments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_task_comments_basic():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_COMMENTS_LIST)
    with patch("tools.comments.api_client.get", new=mock_get):
        result = await _call(mcp, "get_task_comments", {"task_id": "task_abc"})

    mock_get.assert_called_once()
    call_path = mock_get.call_args.args[0]
    assert "task_abc" in call_path
    assert "/comment" in call_path
    assert result == SAMPLE_COMMENTS_LIST


@pytest.mark.asyncio
async def test_get_task_comments_with_pagination():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_COMMENTS_LIST)
    with patch("tools.comments.api_client.get", new=mock_get):
        await _call(mcp, "get_task_comments", {
            "task_id": "task_abc",
            "start": 1740000000000,
            "start_id": "comment_abc",
        })

    params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
    assert params["start"] == 1740000000000
    assert params["start_id"] == "comment_abc"


# ---------------------------------------------------------------------------
# create_task_comment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_comment_basic():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_COMMENT)
    with patch("tools.comments.api_client.post", new=mock_post):
        result = await _call(mcp, "create_task_comment", {
            "task_id": "task_abc",
            "comment_text": "Looks good!",
        })

    call_path = mock_post.call_args.args[0]
    assert "task_abc" in call_path
    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["comment_text"] == "Looks good!"
    assert body["notify_all"] is False


@pytest.mark.asyncio
async def test_create_task_comment_with_assignee():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_COMMENT)
    with (
        patch("tools.comments.api_client.post", new=mock_post),
        patch("cache.cache.resolve_member", new=AsyncMock(return_value=SAMPLE_MEMBER)),
    ):
        result = await _call(mcp, "create_task_comment", {
            "task_id": "task_abc",
            "comment_text": "Please review",
            "assignee": "Alice",
        })

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["assignee"] == 200


@pytest.mark.asyncio
async def test_create_task_comment_notify_all():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_COMMENT)
    with patch("tools.comments.api_client.post", new=mock_post):
        await _call(mcp, "create_task_comment", {
            "task_id": "task_abc",
            "comment_text": "FYI all",
            "notify_all": True,
        })

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["notify_all"] is True


# ---------------------------------------------------------------------------
# get_list_comments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_list_comments_basic():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_COMMENTS_LIST)
    with patch("tools.comments.api_client.get", new=mock_get):
        await _call(mcp, "get_list_comments", {"list_id": "list1"})

    call_path = mock_get.call_args.args[0]
    assert "list1" in call_path
    assert "/comment" in call_path


# ---------------------------------------------------------------------------
# create_list_comment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_list_comment_basic():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_COMMENT)
    with patch("tools.comments.api_client.post", new=mock_post):
        await _call(mcp, "create_list_comment", {
            "list_id": "list1",
            "comment_text": "List-level note",
        })

    call_path = mock_post.call_args.args[0]
    assert "list1" in call_path
    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["comment_text"] == "List-level note"


# ---------------------------------------------------------------------------
# get_threaded_comments
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_threaded_comments():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"comments": []})
    with patch("tools.comments.api_client.get", new=mock_get):
        await _call(mcp, "get_threaded_comments", {"comment_id": "comment_abc"})

    call_path = mock_get.call_args.args[0]
    assert "comment_abc" in call_path
    assert "/reply" in call_path


# ---------------------------------------------------------------------------
# create_threaded_comment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_threaded_comment_basic():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_COMMENT)
    with patch("tools.comments.api_client.post", new=mock_post):
        await _call(mcp, "create_threaded_comment", {
            "comment_id": "comment_abc",
            "comment_text": "Good point!",
        })

    call_path = mock_post.call_args.args[0]
    assert "comment_abc" in call_path
    assert "/reply" in call_path
    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["comment_text"] == "Good point!"


@pytest.mark.asyncio
async def test_create_threaded_comment_with_assignee():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value=SAMPLE_COMMENT)
    with (
        patch("tools.comments.api_client.post", new=mock_post),
        patch("cache.cache.resolve_member", new=AsyncMock(return_value=SAMPLE_MEMBER)),
    ):
        await _call(mcp, "create_threaded_comment", {
            "comment_id": "comment_abc",
            "comment_text": "Assigned for follow-up",
            "assignee": "Alice",
        })

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["assignee"] == 200


# ---------------------------------------------------------------------------
# update_comment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_comment_text():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "comment_abc"})
    with patch("tools.comments.api_client.put", new=mock_put):
        await _call(mcp, "update_comment", {
            "comment_id": "comment_abc",
            "comment_text": "Updated text",
        })

    call_path = mock_put.call_args.args[0]
    assert "comment_abc" in call_path
    body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert body["comment_text"] == "Updated text"


@pytest.mark.asyncio
async def test_update_comment_resolved():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "comment_abc"})
    with patch("tools.comments.api_client.put", new=mock_put):
        await _call(mcp, "update_comment", {
            "comment_id": "comment_abc",
            "resolved": True,
        })

    body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert body["resolved"] is True


@pytest.mark.asyncio
async def test_update_comment_no_fields():
    mcp = _build_mcp()
    with patch("tools.comments.api_client.put", new=AsyncMock()):
        result = await _call(mcp, "update_comment", {"comment_id": "comment_abc"})

    assert result["success"] is False
    assert "No fields" in result["error"]


# ---------------------------------------------------------------------------
# delete_comment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_comment():
    mcp = _build_mcp()
    mock_delete = AsyncMock(return_value={"success": True})
    with patch("tools.comments.api_client.delete", new=mock_delete):
        result = await _call(mcp, "delete_comment", {"comment_id": "comment_abc"})

    mock_delete.assert_called_once()
    call_path = mock_delete.call_args.args[0]
    assert "comment_abc" in call_path
    assert result["success"] is True
