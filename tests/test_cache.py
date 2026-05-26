"""Tests for WorkspaceCache — hierarchy loading and name resolution."""
import time
import pytest
from unittest.mock import AsyncMock, patch

from cache import WorkspaceCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cache() -> WorkspaceCache:
    """Return a fresh, uninitialized cache instance."""
    return WorkspaceCache()


def make_api_mock(spaces_data, folders_by_space, lists_by_space, members_data):
    """
    Build an AsyncMock for api_client.get that returns different data
    based on the URL path.

    - /team/.../space  -> spaces_data
    - /space/<id>/list -> lists_by_space[id]
    - /space/<id>/folder -> folders_by_space[id]
    - /team/.../member -> members_data
    """
    async def fake_get(path, params=None):
        if path.endswith("/space") and "/team/" in path:
            return spaces_data
        if path.endswith("/member"):
            return members_data
        for space_id in lists_by_space:
            if f"/space/{space_id}/list" in path:
                return lists_by_space[space_id]
        for space_id in folders_by_space:
            if f"/space/{space_id}/folder" in path:
                return folders_by_space[space_id]
        return {}

    mock = AsyncMock(side_effect=fake_get)
    return mock


# ---------------------------------------------------------------------------
# Fixtures (extend shared ones with per-test convenience)
# ---------------------------------------------------------------------------

SPACES = {
    "spaces": [
        {"id": "space1", "name": "Client Space", "private": False, "statuses": []},
        {"id": "space2", "name": "Internal", "private": True, "statuses": []},
    ]
}

FOLDERS_SPACE1 = {
    "folders": [
        {
            "id": "folder1",
            "name": "Acme Corp",
            "lists": [
                {"id": "list1", "name": "Website Build"},
                {"id": "list2", "name": "SEO Tasks"},
            ],
        },
        {
            "id": "folder2",
            "name": "Beta Client",
            "lists": [
                {"id": "list3", "name": "Maintenance"},
            ],
        },
    ]
}

FOLDERS_SPACE2 = {"folders": []}

LISTS_SPACE1 = {"lists": [{"id": "list4", "name": "General Tasks"}]}
LISTS_SPACE2 = {"lists": []}

MEMBERS = {
    "members": [
        {"user": {"id": 100, "username": "John", "email": "john@example.com", "role": 1}},
        {"user": {"id": 200, "username": "Alice", "email": "alice@example.com", "role": 2}},
        {"user": {"id": 300, "username": "Sarah", "email": "sarah@example.com", "role": 2}},
    ]
}


def _make_mock():
    return make_api_mock(
        spaces_data=SPACES,
        folders_by_space={"space1": FOLDERS_SPACE1, "space2": FOLDERS_SPACE2},
        lists_by_space={"space1": LISTS_SPACE1, "space2": LISTS_SPACE2},
        members_data=MEMBERS,
    )


# ---------------------------------------------------------------------------
# Test 1: refresh populates hierarchy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_populates_hierarchy():
    cache = make_cache()
    mock_get = _make_mock()

    with patch("cache.api_client.get", mock_get):
        await cache.refresh()

    assert len(cache._spaces) == 2
    assert any(s["id"] == "space1" for s in cache._spaces)

    # Folders: 2 from space1, 0 from space2
    assert len(cache._folders) == 2
    folder_ids = {f["id"] for f in cache._folders}
    assert "folder1" in folder_ids
    assert "folder2" in folder_ids

    # Lists: 1 folderless (list4) + 2 from folder1 (list1, list2) + 1 from folder2 (list3)
    list_ids = {l["id"] for l in cache._lists}
    assert "list1" in list_ids
    assert "list2" in list_ids
    assert "list3" in list_ids
    assert "list4" in list_ids

    assert len(cache._members) == 3
    assert cache._initialized is True


# ---------------------------------------------------------------------------
# Test 2: resolve_space exact match
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_space_exact_match():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_space("Client Space")
    assert result is not None
    assert result["id"] == "space1"


# ---------------------------------------------------------------------------
# Test 3: resolve_space prefix match
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_space_prefix_match():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_space("Client")
    assert result is not None
    assert result["id"] == "space1"


# ---------------------------------------------------------------------------
# Test 4: resolve_space fuzzy match (typo)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_space_fuzzy_match():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_space("Clinet Space")  # typo
    assert result is not None
    assert result["id"] == "space1"


# ---------------------------------------------------------------------------
# Test 5: resolve_space by ID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_space_by_id():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_space("space1")
    assert result is not None
    assert result["id"] == "space1"


# ---------------------------------------------------------------------------
# Test 6: resolve_folder exact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_folder_exact():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_folder("Acme Corp")
    assert result is not None
    assert result["id"] == "folder1"


# ---------------------------------------------------------------------------
# Test 7: resolve_folder scoped to space
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_folder_scoped_to_space():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_folder("Acme Corp", space_name="Client Space")
    assert result is not None
    assert result["id"] == "folder1"
    assert result["_space_id"] == "space1"


# ---------------------------------------------------------------------------
# Test 8: resolve_list exact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_list_exact():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_list("Website Build")
    assert result is not None
    assert result["id"] == "list1"


# ---------------------------------------------------------------------------
# Test 9: resolve_list scoped to folder
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_list_scoped_to_folder():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_list("Website Build", folder_name="Acme Corp")
    assert result is not None
    assert result["id"] == "list1"
    assert result["_folder_id"] == "folder1"


# ---------------------------------------------------------------------------
# Test 10: resolve_member by name
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_member_by_name():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_member("Alice")
    assert result is not None
    assert result["id"] == 200


# ---------------------------------------------------------------------------
# Test 11: resolve_member by email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_member_by_email():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_member("alice@example.com")
    assert result is not None
    assert result["id"] == 200


# ---------------------------------------------------------------------------
# Test 12: resolve_members multiple names
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_members_multiple():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        result = await cache.resolve_members(["John", "Alice"])
    assert sorted(result) == [100, 200]


# ---------------------------------------------------------------------------
# Test 13: cache staleness triggers refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_staleness():
    cache = make_cache()
    mock_get = _make_mock()

    with patch("cache.api_client.get", mock_get):
        # First load
        await cache.ensure_loaded()
        first_call_count = mock_get.call_count

        # Simulate stale cache (last_refresh very old)
        cache._last_refresh = time.time() - 99999

        # Second load — should trigger refresh
        await cache.ensure_loaded()
        second_call_count = mock_get.call_count

    assert second_call_count > first_call_count, "Stale cache should trigger a refresh"


# ---------------------------------------------------------------------------
# Test 14: get_hierarchy returns correct structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_hierarchy_structure():
    cache = make_cache()
    with patch("cache.api_client.get", _make_mock()):
        hierarchy = await cache.get_hierarchy()

    assert "spaces" in hierarchy
    spaces = hierarchy["spaces"]
    assert len(spaces) == 2

    client_space = next(s for s in spaces if s["id"] == "space1")
    assert "folders" in client_space
    assert "lists" in client_space

    folder_ids = {f["id"] for f in client_space["folders"]}
    assert "folder1" in folder_ids
    assert "folder2" in folder_ids

    # Folderless list (list4) should be in top-level lists
    list_ids = {l["id"] for l in client_space["lists"]}
    assert "list4" in list_ids

    # Folder lists should be nested inside folders, not top-level
    assert "list1" not in list_ids

    acme_folder = next(f for f in client_space["folders"] if f["id"] == "folder1")
    acme_list_ids = {l["id"] for l in acme_folder["lists"]}
    assert "list1" in acme_list_ids
    assert "list2" in acme_list_ids
