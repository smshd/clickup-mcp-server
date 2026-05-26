"""Views tools for ClickUp — list, create, update, and delete views at any scope."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from cache import cache
from config import TEAM_ID
from utils import format_error


def register_view_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_views(
        scope: str = Field(description="Level to fetch views for: 'team', 'space', 'folder', or 'list'."),
        name: Optional[str] = Field(default=None, description="Space/folder/list name or ID (required for scopes other than 'team')."),
        parent_space: Optional[str] = Field(default=None, description="Optional space name to narrow folder/list lookup."),
        parent_folder: Optional[str] = Field(default=None, description="Optional folder name to narrow list lookup."),
    ) -> dict:
        """Get views at the team, space, folder, or list level.

        Views define how tasks are displayed (Board, List, Calendar, etc.).
        Use scope='team' for workspace-level views, or provide a name for
        space/folder/list-scoped views. Returns view IDs, names, and types.
        """
        try:
            scope = scope.lower()
            if scope == "team":
                return await api_client.get(f"/team/{TEAM_ID}/view")

            if not name:
                return {"success": False, "error": "name is required for scopes other than 'team'", "error_type": "ValueError"}

            if scope == "space":
                space_obj = await cache.resolve_space(name)
                if not space_obj:
                    return {"success": False, "error": f"Space not found: {name}", "error_type": "ValueError"}
                return await api_client.get(f"/space/{space_obj['id']}/view")

            elif scope == "folder":
                folder_obj = await cache.resolve_folder(name, space_name=parent_space)
                if not folder_obj:
                    return {"success": False, "error": f"Folder not found: {name}", "error_type": "ValueError"}
                return await api_client.get(f"/folder/{folder_obj['id']}/view")

            elif scope == "list":
                list_obj = await cache.resolve_list(name, folder_name=parent_folder, space_name=parent_space)
                if not list_obj:
                    return {"success": False, "error": f"List not found: {name}", "error_type": "ValueError"}
                return await api_client.get(f"/list/{list_obj['id']}/view")

            else:
                return {"success": False, "error": f"Invalid scope '{scope}'. Must be 'team', 'space', 'folder', or 'list'.", "error_type": "ValueError"}
        except Exception as e:
            return format_error("get_views", e)

    @mcp.tool()
    async def create_view(
        name: str = Field(description="Name for the new view."),
        view_type: str = Field(description="View type: 'list', 'board', 'calendar', 'table', 'timeline', 'workload', 'activity', 'map', 'chat', 'gantt'."),
        scope: str = Field(description="Scope to create the view at: 'team', 'space', 'folder', or 'list'."),
        scope_name: Optional[str] = Field(default=None, description="Space/folder/list name or ID (required for scopes other than 'team')."),
        parent_space: Optional[str] = Field(default=None, description="Optional space name to narrow folder/list lookup."),
        parent_folder: Optional[str] = Field(default=None, description="Optional folder name to narrow list lookup."),
    ) -> dict:
        """Create a new view at the specified scope.

        Creates a view (e.g., Board, Calendar, Gantt) at the team, space, folder, or list level.
        The view_type determines how tasks are visualized. Returns the created view details.
        """
        try:
            scope = scope.lower()
            body = {"name": name, "type": view_type}

            if scope == "team":
                return await api_client.post(f"/team/{TEAM_ID}/view", json_body=body)

            if not scope_name:
                return {"success": False, "error": "scope_name is required for scopes other than 'team'", "error_type": "ValueError"}

            if scope == "space":
                space_obj = await cache.resolve_space(scope_name)
                if not space_obj:
                    return {"success": False, "error": f"Space not found: {scope_name}", "error_type": "ValueError"}
                return await api_client.post(f"/space/{space_obj['id']}/view", json_body=body)

            elif scope == "folder":
                folder_obj = await cache.resolve_folder(scope_name, space_name=parent_space)
                if not folder_obj:
                    return {"success": False, "error": f"Folder not found: {scope_name}", "error_type": "ValueError"}
                return await api_client.post(f"/folder/{folder_obj['id']}/view", json_body=body)

            elif scope == "list":
                list_obj = await cache.resolve_list(scope_name, folder_name=parent_folder, space_name=parent_space)
                if not list_obj:
                    return {"success": False, "error": f"List not found: {scope_name}", "error_type": "ValueError"}
                return await api_client.post(f"/list/{list_obj['id']}/view", json_body=body)

            else:
                return {"success": False, "error": f"Invalid scope '{scope}'.", "error_type": "ValueError"}
        except Exception as e:
            return format_error("create_view", e)

    @mcp.tool()
    async def update_view(
        view_id: str = Field(description="View ID to update."),
        name: Optional[str] = Field(default=None, description="New name for the view."),
        view_type: Optional[str] = Field(default=None, description="New view type."),
    ) -> dict:
        """Update a view's name or type.

        Modifies an existing view. Use get_views to find view IDs.
        """
        try:
            body: dict = {}
            if name:
                body["name"] = name
            if view_type:
                body["type"] = view_type

            return await api_client.put(f"/view/{view_id}", json_body=body)
        except Exception as e:
            return format_error("update_view", e)

    @mcp.tool()
    async def delete_view(
        view_id: str = Field(description="View ID to delete."),
    ) -> dict:
        """Delete a view.

        Permanently removes a view. This does not delete any tasks, only the view configuration.
        """
        try:
            return await api_client.delete(f"/view/{view_id}")
        except Exception as e:
            return format_error("delete_view", e)
