"""Custom fields tools for ClickUp — read and set task custom field values."""
from typing import Any, Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from cache import cache
from utils import format_error


def register_custom_field_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_custom_fields(
        list_name: str = Field(description="List name or ID to fetch custom field definitions for."),
        folder: Optional[str] = Field(default=None, description="Optional folder name to narrow the list search."),
        space: Optional[str] = Field(default=None, description="Optional space name to narrow the list search."),
    ) -> dict:
        """Get all custom field definitions for a list.

        Returns all custom fields configured on a list, including their IDs, names,
        types, and configuration. Use the field IDs to set or clear values with
        set_custom_field and clear_custom_field.
        """
        try:
            lst = await cache.resolve_list(list_name, folder_name=folder, space_name=space)
            if not lst:
                return {"success": False, "error": f"List not found: {list_name}", "error_type": "ValueError"}

            return await api_client.get(f"/list/{lst['id']}/field")
        except Exception as e:
            return format_error("get_custom_fields", e)

    @mcp.tool()
    async def set_custom_field(
        task_id: str = Field(description="Task ID to set the custom field value on."),
        field_id: str = Field(description="Custom field ID (from get_custom_fields)."),
        value: Any = Field(description="Value to set. Type depends on the field: string for text/url/email, number for numeric fields, list of user IDs for people fields, unix ms timestamp for date fields, option ID for dropdown fields."),
    ) -> dict:
        """Set a custom field value on a task.

        The value format depends on the field type. Use get_custom_fields to check
        the field type before setting. Common types:
        - text/url/email: plain string
        - number: numeric value
        - date: unix milliseconds timestamp
        - dropdown: option ID string
        - people: list of user ID integers
        """
        try:
            return await api_client.post(
                f"/task/{task_id}/field/{field_id}",
                json_body={"value": value},
            )
        except Exception as e:
            return format_error("set_custom_field", e)

    @mcp.tool()
    async def clear_custom_field(
        task_id: str = Field(description="Task ID to clear the custom field value on."),
        field_id: str = Field(description="Custom field ID to clear."),
    ) -> dict:
        """Clear a custom field value from a task.

        Removes the value set on a custom field, resetting it to empty.
        The field definition remains; only the value on this task is cleared.
        """
        try:
            return await api_client.delete(f"/task/{task_id}/field/{field_id}")
        except Exception as e:
            return format_error("clear_custom_field", e)
