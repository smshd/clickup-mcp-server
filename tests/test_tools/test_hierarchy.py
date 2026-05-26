"""Tests for workspace hierarchy tools (spaces, folders, lists CRUD)."""
import pytest
from unittest.mock import AsyncMock, patch

from fastmcp import FastMCP
from tools.hierarchy import register_hierarchy_tools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_hierarchy_tools(mcp)
    return mcp


async def _call(mcp: FastMCP, tool_name: str, args: dict) -> dict:
    result = await mcp.call_tool(tool_name, args)
    return result.structured_content


SAMPLE_SPACE = {
    "id": "space1",
    "name": "Client Space",
    "private": False,
    "_space_id": "space1",
}

SAMPLE_FOLDER = {
    "id": "folder1",
    "name": "Acme Corp",
    "_space_id": "space1",
    "_space_name": "Client Space",
}

SAMPLE_LIST = {
    "id": "list1",
    "name": "Website Build",
    "_folder_id": "folder1",
    "_folder_name": "Acme Corp",
    "_space_id": "space1",
    "_space_name": "Client Space",
}

HIERARCHY_RESULT = {
    "spaces": [
        {
            "id": "space1",
            "name": "Client Space",
            "folders": [
                {
                    "id": "folder1",
                    "name": "Acme Corp",
                    "lists": [{"id": "list1", "name": "Website Build"}],
                }
            ],
            "lists": [{"id": "list4", "name": "General Tasks"}],
        }
    ]
}


# ---------------------------------------------------------------------------
# get_workspace_hierarchy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_workspace_hierarchy():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.get_hierarchy", new=AsyncMock(return_value=HIERARCHY_RESULT)):
        result = await _call(mcp, "get_workspace_hierarchy", {})

    assert "spaces" in result
    assert len(result["spaces"]) == 1
    assert result["spaces"][0]["id"] == "space1"


# ---------------------------------------------------------------------------
# get_spaces
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_spaces():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"spaces": [SAMPLE_SPACE]})
    with patch("tools.hierarchy.api_client.get", new=mock_get):
        result = await _call(mcp, "get_spaces", {})

    call_path = mock_get.call_args.args[0]
    assert "/space" in call_path
    assert "spaces" in result


# ---------------------------------------------------------------------------
# create_space
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_space():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value={"id": "space_new", "name": "New Space"})
    mock_refresh = AsyncMock()
    with (
        patch("tools.hierarchy.api_client.post", new=mock_post),
        patch("tools.hierarchy.cache.refresh", new=mock_refresh),
    ):
        result = await _call(mcp, "create_space", {"name": "New Space"})

    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["name"] == "New Space"
    assert body["multiple_assignees"] is True
    mock_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# get_space (name resolution)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_space_resolves_name():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_SPACE)
    with (
        patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=SAMPLE_SPACE)),
        patch("tools.hierarchy.api_client.get", new=mock_get),
    ):
        result = await _call(mcp, "get_space", {"space_name": "Client Space"})

    call_path = mock_get.call_args.args[0]
    assert "space1" in call_path


@pytest.mark.asyncio
async def test_get_space_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "get_space", {"space_name": "Nonexistent"})

    assert result["success"] is False
    assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# update_space
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_space_name():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "space1", "name": "Renamed Space"})
    with (
        patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=SAMPLE_SPACE)),
        patch("tools.hierarchy.api_client.put", new=mock_put),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        await _call(mcp, "update_space", {"space_name": "Client Space", "name": "Renamed Space"})

    body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert body["name"] == "Renamed Space"


@pytest.mark.asyncio
async def test_update_space_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "update_space", {"space_name": "Ghost Space", "name": "New Name"})

    assert result["success"] is False


# ---------------------------------------------------------------------------
# delete_space
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_space():
    mcp = _build_mcp()
    mock_delete = AsyncMock(return_value={"success": True})
    with (
        patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=SAMPLE_SPACE)),
        patch("tools.hierarchy.api_client.delete", new=mock_delete),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        result = await _call(mcp, "delete_space", {"space_name": "Client Space"})

    call_path = mock_delete.call_args.args[0]
    assert "space1" in call_path
    assert result["success"] is True


@pytest.mark.asyncio
async def test_delete_space_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "delete_space", {"space_name": "Ghost"})

    assert result["success"] is False


# ---------------------------------------------------------------------------
# get_folders
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_folders_resolves_space():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"folders": [SAMPLE_FOLDER]})
    with (
        patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=SAMPLE_SPACE)),
        patch("tools.hierarchy.api_client.get", new=mock_get),
    ):
        result = await _call(mcp, "get_folders", {"space_name": "Client Space"})

    call_path = mock_get.call_args.args[0]
    assert "space1" in call_path
    assert "/folder" in call_path


@pytest.mark.asyncio
async def test_get_folders_space_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "get_folders", {"space_name": "Ghost"})

    assert result["success"] is False


# ---------------------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_folder():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value={"id": "folder_new", "name": "New Client"})
    with (
        patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=SAMPLE_SPACE)),
        patch("tools.hierarchy.api_client.post", new=mock_post),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        await _call(mcp, "create_folder", {"space_name": "Client Space", "name": "New Client"})

    call_path = mock_post.call_args.args[0]
    assert "space1" in call_path
    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["name"] == "New Client"


# ---------------------------------------------------------------------------
# get_folder (name resolution)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_folder_resolves_name():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value=SAMPLE_FOLDER)
    with (
        patch("tools.hierarchy.cache.resolve_folder", new=AsyncMock(return_value=SAMPLE_FOLDER)),
        patch("tools.hierarchy.api_client.get", new=mock_get),
    ):
        result = await _call(mcp, "get_folder", {"folder_name": "Acme Corp"})

    call_path = mock_get.call_args.args[0]
    assert "folder1" in call_path


@pytest.mark.asyncio
async def test_get_folder_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_folder", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "get_folder", {"folder_name": "Ghost Folder"})

    assert result["success"] is False
    assert "not found" in result["error"]


# ---------------------------------------------------------------------------
# update_folder
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_folder():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "folder1", "name": "Renamed"})
    with (
        patch("tools.hierarchy.cache.resolve_folder", new=AsyncMock(return_value=SAMPLE_FOLDER)),
        patch("tools.hierarchy.api_client.put", new=mock_put),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        await _call(mcp, "update_folder", {"folder_name": "Acme Corp", "name": "Renamed"})

    call_path = mock_put.call_args.args[0]
    assert "folder1" in call_path
    body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert body["name"] == "Renamed"


@pytest.mark.asyncio
async def test_update_folder_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_folder", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "update_folder", {"folder_name": "Ghost", "name": "New Name"})

    assert result["success"] is False


# ---------------------------------------------------------------------------
# delete_folder
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_folder():
    mcp = _build_mcp()
    mock_delete = AsyncMock(return_value={"success": True})
    with (
        patch("tools.hierarchy.cache.resolve_folder", new=AsyncMock(return_value=SAMPLE_FOLDER)),
        patch("tools.hierarchy.api_client.delete", new=mock_delete),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        result = await _call(mcp, "delete_folder", {"folder_name": "Acme Corp"})

    call_path = mock_delete.call_args.args[0]
    assert "folder1" in call_path
    assert result["success"] is True


# ---------------------------------------------------------------------------
# get_lists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_lists_by_folder():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"lists": [SAMPLE_LIST]})
    with (
        patch("tools.hierarchy.cache.resolve_folder", new=AsyncMock(return_value=SAMPLE_FOLDER)),
        patch("tools.hierarchy.api_client.get", new=mock_get),
    ):
        result = await _call(mcp, "get_lists", {"folder_name": "Acme Corp"})

    call_path = mock_get.call_args.args[0]
    assert "folder1" in call_path
    assert "/list" in call_path


@pytest.mark.asyncio
async def test_get_lists_by_space():
    mcp = _build_mcp()
    mock_get = AsyncMock(return_value={"lists": [SAMPLE_LIST]})
    with (
        patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=SAMPLE_SPACE)),
        patch("tools.hierarchy.api_client.get", new=mock_get),
    ):
        result = await _call(mcp, "get_lists", {"space_name": "Client Space"})

    call_path = mock_get.call_args.args[0]
    assert "space1" in call_path
    assert "/list" in call_path


@pytest.mark.asyncio
async def test_get_lists_no_args():
    mcp = _build_mcp()
    result = await _call(mcp, "get_lists", {})

    assert result["success"] is False
    assert "folder_name or space_name" in result["error"]


@pytest.mark.asyncio
async def test_get_lists_folder_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_folder", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "get_lists", {"folder_name": "Ghost Folder"})

    assert result["success"] is False


# ---------------------------------------------------------------------------
# create_list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_list_in_folder():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value={"id": "list_new", "name": "New List"})
    with (
        patch("tools.hierarchy.cache.resolve_folder", new=AsyncMock(return_value=SAMPLE_FOLDER)),
        patch("tools.hierarchy.api_client.post", new=mock_post),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        await _call(mcp, "create_list", {"name": "New List", "folder_name": "Acme Corp"})

    call_path = mock_post.call_args.args[0]
    assert "folder1" in call_path
    body = mock_post.call_args.kwargs.get("json_body") or mock_post.call_args.args[1]
    assert body["name"] == "New List"


@pytest.mark.asyncio
async def test_create_list_in_space():
    mcp = _build_mcp()
    mock_post = AsyncMock(return_value={"id": "list_new", "name": "Folderless List"})
    with (
        patch("tools.hierarchy.cache.resolve_space", new=AsyncMock(return_value=SAMPLE_SPACE)),
        patch("tools.hierarchy.api_client.post", new=mock_post),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        await _call(mcp, "create_list", {"name": "Folderless List", "space_name": "Client Space"})

    call_path = mock_post.call_args.args[0]
    assert "space1" in call_path


@pytest.mark.asyncio
async def test_create_list_no_args():
    mcp = _build_mcp()
    result = await _call(mcp, "create_list", {"name": "Orphan List"})

    assert result["success"] is False
    assert "folder_name or space_name" in result["error"]


# ---------------------------------------------------------------------------
# update_list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_list():
    mcp = _build_mcp()
    mock_put = AsyncMock(return_value={"id": "list1", "name": "Renamed List"})
    with (
        patch("tools.hierarchy.cache.resolve_list", new=AsyncMock(return_value=SAMPLE_LIST)),
        patch("tools.hierarchy.api_client.put", new=mock_put),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        await _call(mcp, "update_list", {"list_name": "Website Build", "name": "Renamed List"})

    call_path = mock_put.call_args.args[0]
    assert "list1" in call_path
    body = mock_put.call_args.kwargs.get("json_body") or mock_put.call_args.args[1]
    assert body["name"] == "Renamed List"


@pytest.mark.asyncio
async def test_update_list_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_list", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "update_list", {"list_name": "Ghost List", "name": "New Name"})

    assert result["success"] is False


# ---------------------------------------------------------------------------
# delete_list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_list():
    mcp = _build_mcp()
    mock_delete = AsyncMock(return_value={"success": True})
    with (
        patch("tools.hierarchy.cache.resolve_list", new=AsyncMock(return_value=SAMPLE_LIST)),
        patch("tools.hierarchy.api_client.delete", new=mock_delete),
        patch("tools.hierarchy.cache.refresh", new=AsyncMock()),
    ):
        result = await _call(mcp, "delete_list", {"list_name": "Website Build"})

    call_path = mock_delete.call_args.args[0]
    assert "list1" in call_path
    assert result["success"] is True


@pytest.mark.asyncio
async def test_delete_list_not_found():
    mcp = _build_mcp()
    with patch("tools.hierarchy.cache.resolve_list", new=AsyncMock(return_value=None)):
        result = await _call(mcp, "delete_list", {"list_name": "Ghost List"})

    assert result["success"] is False
