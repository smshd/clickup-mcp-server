"""Tags tools for ClickUp — space-level tags and task tag assignment."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from cache import cache
from utils import format_error, resolve_color


def register_tag_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_space_tags(
        space: str = Field(description="Space name or ID to fetch tags for."),
    ) -> dict:
        """Get all tags defined in a space.

        Returns all tag objects with their name and color. Tags are defined at the space level
        and can be applied to any task within that space.
        """
        try:
            space_obj = await cache.resolve_space(space)
            if not space_obj:
                return {"success": False, "error": f"Space not found: {space}", "error_type": "ValueError"}
            return await api_client.get(f"/space/{space_obj['id']}/tag")
        except Exception as e:
            return format_error("get_space_tags", e)

    @mcp.tool()
    async def create_tag(
        space: str = Field(description="Space name or ID where the tag will be created."),
        name: str = Field(description="Tag name."),
        color: Optional[str] = Field(default=None, description="Tag color as hex (#FF5722) or name ('red', 'dark blue', 'green', etc.)."),
    ) -> dict:
        """Create a new tag in a space.

        Tags are created at the space level and can then be applied to tasks.
        Use resolve_color-compatible color names or hex codes.
        """
        try:
            space_obj = await cache.resolve_space(space)
            if not space_obj:
                return {"success": False, "error": f"Space not found: {space}", "error_type": "ValueError"}

            body: dict = {"tag": {"name": name}}
            if color:
                body["tag"]["tag_fg"] = resolve_color(color)
                body["tag"]["tag_bg"] = resolve_color(color)

            return await api_client.post(f"/space/{space_obj['id']}/tag", json_body=body)
        except Exception as e:
            return format_error("create_tag", e)

    @mcp.tool()
    async def update_tag(
        space: str = Field(description="Space name or ID containing the tag."),
        tag_name: str = Field(description="Current tag name to update."),
        new_name: Optional[str] = Field(default=None, description="New name for the tag."),
        color: Optional[str] = Field(default=None, description="New color as hex or name."),
    ) -> dict:
        """Update a tag's name or color.

        Modifies an existing tag in a space. You can rename it, change its color, or both.
        """
        try:
            space_obj = await cache.resolve_space(space)
            if not space_obj:
                return {"success": False, "error": f"Space not found: {space}", "error_type": "ValueError"}

            tag_data: dict = {}
            if new_name:
                tag_data["name"] = new_name
            if color:
                tag_data["tag_fg"] = resolve_color(color)
                tag_data["tag_bg"] = resolve_color(color)

            return await api_client.put(
                f"/space/{space_obj['id']}/tag/{tag_name}",
                json_body={"tag": tag_data},
            )
        except Exception as e:
            return format_error("update_tag", e)

    @mcp.tool()
    async def delete_tag(
        space: str = Field(description="Space name or ID containing the tag."),
        tag_name: str = Field(description="Name of the tag to delete."),
    ) -> dict:
        """Delete a tag from a space.

        Permanently removes a tag from the space. This also removes it from all tasks
        it was applied to. This action cannot be undone.
        """
        try:
            space_obj = await cache.resolve_space(space)
            if not space_obj:
                return {"success": False, "error": f"Space not found: {space}", "error_type": "ValueError"}

            return await api_client.delete(f"/space/{space_obj['id']}/tag/{tag_name}")
        except Exception as e:
            return format_error("delete_tag", e)

    @mcp.tool()
    async def add_tag_to_task(
        task_id: str = Field(description="Task ID to apply the tag to."),
        tag_name: str = Field(description="Name of the tag to apply."),
    ) -> dict:
        """Apply a tag to a task.

        Adds an existing space tag to a task. The tag must already exist in the task's space.
        Use get_space_tags to see available tags.
        """
        try:
            return await api_client.post(f"/task/{task_id}/tag/{tag_name}")
        except Exception as e:
            return format_error("add_tag_to_task", e)

    @mcp.tool()
    async def remove_tag_from_task(
        task_id: str = Field(description="Task ID to remove the tag from."),
        tag_name: str = Field(description="Name of the tag to remove."),
    ) -> dict:
        """Remove a tag from a task.

        Strips a tag from a task without deleting the tag from the space.
        """
        try:
            return await api_client.delete(f"/task/{task_id}/tag/{tag_name}")
        except Exception as e:
            return format_error("remove_tag_from_task", e)
