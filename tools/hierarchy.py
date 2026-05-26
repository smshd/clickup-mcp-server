"""Workspace hierarchy tools - Spaces, Folders, Lists CRUD."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from cache import cache
from config import TEAM_ID
from utils import format_error


def register_hierarchy_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_workspace_hierarchy() -> dict:
        """
        Returns the full workspace tree: spaces > folders > lists.

        Useful for understanding the workspace structure.
        Results are cached for 5 minutes.
        """
        try:
            return await cache.get_hierarchy()
        except Exception as e:
            return format_error("get_workspace_hierarchy", e)

    @mcp.tool()
    async def get_spaces(
        archived: bool = Field(False, description="Include archived spaces."),
    ) -> dict:
        """Lists all spaces in the workspace."""
        try:
            return await api_client.get(f"/team/{TEAM_ID}/space", params={"archived": str(archived).lower()})
        except Exception as e:
            return format_error("get_spaces", e)

    @mcp.tool()
    async def create_space(
        name: str = Field(description="Space name."),
        multiple_assignees: bool = Field(True, description="Allow multiple assignees on tasks."),
        features: Optional[dict] = Field(None, description="Space features to enable (e.g. time_tracking, tags)."),
    ) -> dict:
        """
        Creates a new space in the workspace.

        Spaces are the top-level organizational unit in ClickUp.
        """
        try:
            body = {"name": name, "multiple_assignees": multiple_assignees}
            if features:
                body["features"] = features
            result = await api_client.post(f"/team/{TEAM_ID}/space", json_body=body)
            await cache.refresh()  # Invalidate cache
            return result
        except Exception as e:
            return format_error("create_space", e)

    @mcp.tool()
    async def get_space(
        space_name: str = Field(description="Space name or ID."),
    ) -> dict:
        """Gets details of a specific space."""
        try:
            space = await cache.resolve_space(space_name)
            if not space:
                return {"success": False, "error": f"Space '{space_name}' not found."}
            return await api_client.get(f"/space/{space['id']}")
        except Exception as e:
            return format_error("get_space", e)

    @mcp.tool()
    async def update_space(
        space_name: str = Field(description="Space name or ID."),
        name: Optional[str] = Field(None, description="New space name."),
        color: Optional[str] = Field(None, description="Space color (hex or name like 'dark blue')."),
        private: Optional[bool] = Field(None, description="Make space private."),
        multiple_assignees: Optional[bool] = Field(None, description="Allow multiple assignees."),
    ) -> dict:
        """Updates space properties. Only include fields you want to change."""
        try:
            space = await cache.resolve_space(space_name)
            if not space:
                return {"success": False, "error": f"Space '{space_name}' not found."}
            from utils import resolve_color
            body = {}
            if name is not None:
                body["name"] = name
            if color is not None:
                body["color"] = resolve_color(color)
            if private is not None:
                body["private"] = private
            if multiple_assignees is not None:
                body["multiple_assignees"] = multiple_assignees
            result = await api_client.put(f"/space/{space['id']}", json_body=body)
            await cache.refresh()
            return result
        except Exception as e:
            return format_error("update_space", e)

    @mcp.tool()
    async def delete_space(
        space_name: str = Field(description="Space name or ID."),
    ) -> dict:
        """
        Permanently deletes a space and ALL its contents. Cannot be undone.

        This deletes all folders, lists, and tasks within the space.
        Only use after explicit user confirmation.
        """
        try:
            space = await cache.resolve_space(space_name)
            if not space:
                return {"success": False, "error": f"Space '{space_name}' not found."}
            result = await api_client.delete(f"/space/{space['id']}")
            await cache.refresh()
            return result
        except Exception as e:
            return format_error("delete_space", e)

    @mcp.tool()
    async def get_folders(
        space_name: str = Field(description="Space name or ID."),
        archived: bool = Field(False, description="Include archived folders."),
    ) -> dict:
        """Lists all folders in a space."""
        try:
            space = await cache.resolve_space(space_name)
            if not space:
                return {"success": False, "error": f"Space '{space_name}' not found."}
            return await api_client.get(f"/space/{space['id']}/folder", params={"archived": str(archived).lower()})
        except Exception as e:
            return format_error("get_folders", e)

    @mcp.tool()
    async def create_folder(
        space_name: str = Field(description="Space name or ID."),
        name: str = Field(description="Folder name."),
    ) -> dict:
        """Creates a new folder in a space."""
        try:
            space = await cache.resolve_space(space_name)
            if not space:
                return {"success": False, "error": f"Space '{space_name}' not found."}
            result = await api_client.post(f"/space/{space['id']}/folder", json_body={"name": name})
            await cache.refresh()
            return result
        except Exception as e:
            return format_error("create_folder", e)

    @mcp.tool()
    async def get_folder(
        folder_name: str = Field(description="Folder name or ID."),
        space_name: Optional[str] = Field(None, description="Space name to narrow search."),
    ) -> dict:
        """Gets details of a specific folder including its lists."""
        try:
            folder = await cache.resolve_folder(folder_name, space_name)
            if not folder:
                return {"success": False, "error": f"Folder '{folder_name}' not found."}
            return await api_client.get(f"/folder/{folder['id']}")
        except Exception as e:
            return format_error("get_folder", e)

    @mcp.tool()
    async def update_folder(
        folder_name: str = Field(description="Folder name or ID."),
        name: str = Field(description="New folder name."),
        space_name: Optional[str] = Field(None, description="Space name to narrow search."),
    ) -> dict:
        """Renames a folder."""
        try:
            folder = await cache.resolve_folder(folder_name, space_name)
            if not folder:
                return {"success": False, "error": f"Folder '{folder_name}' not found."}
            result = await api_client.put(f"/folder/{folder['id']}", json_body={"name": name})
            await cache.refresh()
            return result
        except Exception as e:
            return format_error("update_folder", e)

    @mcp.tool()
    async def delete_folder(
        folder_name: str = Field(description="Folder name or ID."),
        space_name: Optional[str] = Field(None, description="Space name to narrow search."),
    ) -> dict:
        """
        Permanently deletes a folder and all its lists and tasks. Cannot be undone.

        Only use after explicit user confirmation.
        """
        try:
            folder = await cache.resolve_folder(folder_name, space_name)
            if not folder:
                return {"success": False, "error": f"Folder '{folder_name}' not found."}
            result = await api_client.delete(f"/folder/{folder['id']}")
            await cache.refresh()
            return result
        except Exception as e:
            return format_error("delete_folder", e)

    @mcp.tool()
    async def get_lists(
        folder_name: Optional[str] = Field(None, description="Folder name or ID. If omitted, returns folderless lists from space."),
        space_name: Optional[str] = Field(None, description="Space name or ID (required if no folder_name)."),
        archived: bool = Field(False, description="Include archived lists."),
    ) -> dict:
        """
        Lists all lists in a folder, or folderless lists in a space.

        Provide folder_name for folder lists, or space_name for folderless lists.
        """
        try:
            if folder_name:
                folder = await cache.resolve_folder(folder_name, space_name)
                if not folder:
                    return {"success": False, "error": f"Folder '{folder_name}' not found."}
                return await api_client.get(f"/folder/{folder['id']}/list", params={"archived": str(archived).lower()})
            elif space_name:
                space = await cache.resolve_space(space_name)
                if not space:
                    return {"success": False, "error": f"Space '{space_name}' not found."}
                return await api_client.get(f"/space/{space['id']}/list", params={"archived": str(archived).lower()})
            else:
                return {"success": False, "error": "Provide either folder_name or space_name."}
        except Exception as e:
            return format_error("get_lists", e)

    @mcp.tool()
    async def create_list(
        name: str = Field(description="List name."),
        folder_name: Optional[str] = Field(None, description="Folder name or ID. If omitted, creates folderless list in space."),
        space_name: Optional[str] = Field(None, description="Space name or ID (required if no folder_name)."),
        status: Optional[str] = Field(None, description="Default status for new tasks."),
    ) -> dict:
        """
        Creates a new list in a folder or as a folderless list in a space.

        Provide folder_name to create inside a folder, or space_name for a folderless list.
        """
        try:
            body = {"name": name}
            if status:
                body["status"] = status

            if folder_name:
                folder = await cache.resolve_folder(folder_name, space_name)
                if not folder:
                    return {"success": False, "error": f"Folder '{folder_name}' not found."}
                result = await api_client.post(f"/folder/{folder['id']}/list", json_body=body)
            elif space_name:
                space = await cache.resolve_space(space_name)
                if not space:
                    return {"success": False, "error": f"Space '{space_name}' not found."}
                result = await api_client.post(f"/space/{space['id']}/list", json_body=body)
            else:
                return {"success": False, "error": "Provide either folder_name or space_name."}
            await cache.refresh()
            return result
        except Exception as e:
            return format_error("create_list", e)

    @mcp.tool()
    async def update_list(
        list_name: str = Field(description="List name or ID."),
        name: Optional[str] = Field(None, description="New list name."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope lookup."),
    ) -> dict:
        """Renames a list."""
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found."}
            body = {}
            if name is not None:
                body["name"] = name
            result = await api_client.put(f"/list/{lst['id']}", json_body=body)
            await cache.refresh()
            return result
        except Exception as e:
            return format_error("update_list", e)

    @mcp.tool()
    async def delete_list(
        list_name: str = Field(description="List name or ID."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope lookup."),
    ) -> dict:
        """
        Permanently deletes a list and all its tasks. Cannot be undone.

        Only use after explicit user confirmation.
        """
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found."}
            result = await api_client.delete(f"/list/{lst['id']}")
            await cache.refresh()
            return result
        except Exception as e:
            return format_error("delete_list", e)
