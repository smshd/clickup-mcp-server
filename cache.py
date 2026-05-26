"""
Workspace hierarchy cache and name resolver.

Fetches the full workspace tree (spaces > folders > lists) on first use,
caches it in memory, and resolves names to IDs with fuzzy matching.
Also caches workspace members for assignee resolution.
"""
import time
from typing import Optional
from difflib import SequenceMatcher
from config import TEAM_ID, CACHE_TTL
import api_client


class WorkspaceCache:
    """Singleton cache for workspace hierarchy and members."""

    def __init__(self):
        self._spaces: list[dict] = []
        self._folders: list[dict] = []
        self._lists: list[dict] = []
        self._members: list[dict] = []
        self._last_refresh: float = 0
        self._initialized: bool = False

    def _is_stale(self) -> bool:
        return time.time() - self._last_refresh > CACHE_TTL

    async def ensure_loaded(self) -> None:
        """Load hierarchy if not yet loaded or stale."""
        if self._initialized and not self._is_stale():
            return
        await self.refresh()

    async def refresh(self) -> None:
        """Fetch full workspace hierarchy from ClickUp."""
        spaces_resp = await api_client.get(f"/team/{TEAM_ID}/space", params={"archived": "false"})
        if isinstance(spaces_resp, dict) and "spaces" not in spaces_resp:
            return  # API error, keep stale cache

        self._spaces = spaces_resp.get("spaces", [])
        self._folders = []
        self._lists = []

        for space in self._spaces:
            space_id = space["id"]

            # Folderless lists
            lists_resp = await api_client.get(f"/space/{space_id}/list", params={"archived": "false"})
            if isinstance(lists_resp, dict) and "lists" in lists_resp:
                for lst in lists_resp["lists"]:
                    lst["_space_id"] = space_id
                    lst["_space_name"] = space["name"]
                    lst["_folder_id"] = None
                    lst["_folder_name"] = None
                self._lists.extend(lists_resp["lists"])

            # Folders and their lists
            folders_resp = await api_client.get(f"/space/{space_id}/folder", params={"archived": "false"})
            if isinstance(folders_resp, dict) and "folders" in folders_resp:
                for folder in folders_resp["folders"]:
                    folder["_space_id"] = space_id
                    folder["_space_name"] = space["name"]
                    self._folders.append(folder)

                    for lst in folder.get("lists", []):
                        lst["_space_id"] = space_id
                        lst["_space_name"] = space["name"]
                        lst["_folder_id"] = folder["id"]
                        lst["_folder_name"] = folder["name"]
                        self._lists.append(lst)

        # Members
        # ClickUp API v2: /team/{id}/member returns 404 (endpoint doesn't exist).
        # Workspace members come back embedded in GET /team alongside each workspace.
        members_resp = await api_client.get("/team")
        if isinstance(members_resp, dict):
            members: list[dict] = []
            for team in members_resp.get("teams", []) or []:
                if str(team.get("id")) == str(TEAM_ID):
                    members = team.get("members", []) or []
                    break
            # Fallbacks for older/alternative response shapes
            if not members:
                members = (
                    members_resp.get("members", [])
                    or members_resp.get("team", {}).get("members", [])
                )
            self._members = members

        self._last_refresh = time.time()
        self._initialized = True

    def _fuzzy_match(self, query: str, candidates: list[dict], name_key: str = "name") -> list[dict]:
        """Find candidates matching query by exact, prefix, contains, or fuzzy similarity."""
        query_lower = query.strip().lower()
        exact = [c for c in candidates if c.get(name_key, "").strip().lower() == query_lower]
        if exact:
            return exact

        prefix = [c for c in candidates if c.get(name_key, "").strip().lower().startswith(query_lower)]
        if prefix:
            return prefix

        contains = [c for c in candidates if query_lower in c.get(name_key, "").strip().lower()]
        if contains:
            return contains

        # Fuzzy fallback
        scored = []
        for c in candidates:
            ratio = SequenceMatcher(None, query_lower, c.get(name_key, "").strip().lower()).ratio()
            if ratio > 0.6:
                scored.append((ratio, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:5]]

    async def resolve_space(self, name_or_id: str) -> Optional[dict]:
        """Resolve a space by name or ID. Returns the space dict or None."""
        await self.ensure_loaded()
        for s in self._spaces:
            if s["id"] == name_or_id:
                return s
        matches = self._fuzzy_match(name_or_id, self._spaces)
        return matches[0] if len(matches) == 1 else (matches[0] if matches else None)

    async def resolve_folder(self, name_or_id: str, space_name: Optional[str] = None) -> Optional[dict]:
        """Resolve a folder by name or ID, optionally scoped to a space."""
        await self.ensure_loaded()
        for f in self._folders:
            if f["id"] == name_or_id:
                return f
        candidates = self._folders
        if space_name:
            space = await self.resolve_space(space_name)
            if space:
                candidates = [f for f in candidates if f.get("_space_id") == space["id"]]
        matches = self._fuzzy_match(name_or_id, candidates)
        return matches[0] if len(matches) == 1 else (matches[0] if matches else None)

    async def resolve_list(self, name_or_id: str, folder_name: Optional[str] = None, space_name: Optional[str] = None) -> Optional[dict]:
        """Resolve a list by name or ID, optionally scoped to folder/space."""
        await self.ensure_loaded()
        for lst in self._lists:
            if lst["id"] == name_or_id:
                return lst
        candidates = self._lists
        if space_name:
            space = await self.resolve_space(space_name)
            if space:
                candidates = [l for l in candidates if l.get("_space_id") == space["id"]]
        if folder_name:
            folder = await self.resolve_folder(folder_name, space_name)
            if folder:
                candidates = [l for l in candidates if l.get("_folder_id") == folder["id"]]
        matches = self._fuzzy_match(name_or_id, candidates)
        return matches[0] if len(matches) == 1 else (matches[0] if matches else None)

    async def resolve_member(self, name_or_id: str) -> Optional[dict]:
        """Resolve a member by name, email, or ID."""
        await self.ensure_loaded()
        query_lower = name_or_id.strip().lower()
        for m in self._members:
            user = m.get("user", m)
            if str(user.get("id", "")) == name_or_id:
                return user
            if user.get("email", "").lower() == query_lower:
                return user
            if user.get("username", "").lower() == query_lower:
                return user
        # Fuzzy on name
        users = [m.get("user", m) for m in self._members]
        matches = self._fuzzy_match(name_or_id, users, name_key="username")
        return matches[0] if matches else None

    async def resolve_members(self, names_or_ids: list[str]) -> list[int]:
        """Resolve multiple member names/IDs to a list of user IDs."""
        result = []
        for name in names_or_ids:
            member = await self.resolve_member(name)
            if member:
                result.append(int(member["id"]))
        return result

    async def get_hierarchy(self) -> dict:
        """Return the full workspace hierarchy as a structured dict."""
        await self.ensure_loaded()
        return {
            "spaces": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "folders": [
                        {
                            "id": f["id"],
                            "name": f["name"],
                            "lists": [
                                {"id": l["id"], "name": l["name"]}
                                for l in self._lists
                                if l.get("_folder_id") == f["id"]
                            ],
                        }
                        for f in self._folders
                        if f.get("_space_id") == s["id"]
                    ],
                    "lists": [
                        {"id": l["id"], "name": l["name"]}
                        for l in self._lists
                        if l.get("_space_id") == s["id"] and l.get("_folder_id") is None
                    ],
                }
                for s in self._spaces
            ],
        }


# Singleton instance
cache = WorkspaceCache()
