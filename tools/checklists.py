"""Checklists tools for ClickUp — create and manage task checklists and items."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from cache import cache
from utils import format_error


def register_checklist_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def create_checklist(
        task_id: str = Field(description="Task ID to add the checklist to."),
        name: str = Field(description="Checklist name (e.g., 'Launch Steps', 'QA Checklist')."),
    ) -> dict:
        """Create a new checklist on a task.

        Checklists are sub-lists of items within a task. Use create_checklist_item to
        add individual items after creating the checklist. Returns the created checklist
        with its ID for subsequent item additions.
        """
        try:
            return await api_client.post(
                f"/task/{task_id}/checklist",
                json_body={"name": name},
            )
        except Exception as e:
            return format_error("create_checklist", e)

    @mcp.tool()
    async def update_checklist(
        checklist_id: str = Field(description="Checklist ID to update."),
        name: Optional[str] = Field(default=None, description="New name for the checklist."),
        position: Optional[int] = Field(default=None, description="New position (0-indexed) among checklists on the task."),
    ) -> dict:
        """Update a checklist's name or position.

        Rename a checklist or reorder it among the other checklists on the task.
        """
        try:
            body: dict = {}
            if name:
                body["name"] = name
            if position is not None:
                body["position"] = position

            return await api_client.put(f"/checklist/{checklist_id}", json_body=body)
        except Exception as e:
            return format_error("update_checklist", e)

    @mcp.tool()
    async def delete_checklist(
        checklist_id: str = Field(description="Checklist ID to delete."),
    ) -> dict:
        """Delete a checklist and all its items from a task.

        Permanently removes the checklist. This cannot be undone.
        """
        try:
            return await api_client.delete(f"/checklist/{checklist_id}")
        except Exception as e:
            return format_error("delete_checklist", e)

    @mcp.tool()
    async def create_checklist_item(
        checklist_id: str = Field(description="Checklist ID to add the item to."),
        name: str = Field(description="Checklist item text."),
        assignee: Optional[str] = Field(default=None, description="Member name, email, or ID to assign this item to."),
    ) -> dict:
        """Add an item to a checklist.

        Creates a new unchecked item in the checklist. Optionally assign it to a team member.
        Items can be nested under other items using update_checklist_item with a parent.
        """
        try:
            body: dict = {"name": name}
            if assignee:
                member = await cache.resolve_member(assignee)
                if member:
                    body["assignee"] = member["id"]

            return await api_client.post(f"/checklist/{checklist_id}/checklist_item", json_body=body)
        except Exception as e:
            return format_error("create_checklist_item", e)

    @mcp.tool()
    async def update_checklist_item(
        checklist_id: str = Field(description="Checklist ID containing the item."),
        checklist_item_id: str = Field(description="Checklist item ID to update."),
        name: Optional[str] = Field(default=None, description="New text for the item."),
        resolved: Optional[bool] = Field(default=None, description="True to check (complete) the item, False to uncheck it."),
        assignee: Optional[str] = Field(default=None, description="New assignee name, email, or ID. Set to empty string to remove."),
        parent: Optional[str] = Field(default=None, description="Parent checklist item ID to nest this item under."),
    ) -> dict:
        """Update a checklist item's text, completion status, assignee, or nesting.

        Use resolved=true to mark an item complete, resolved=false to reopen it.
        Set parent to a checklist item ID to nest this item as a sub-item.
        """
        try:
            body: dict = {}
            if name is not None:
                body["name"] = name
            if resolved is not None:
                body["resolved"] = resolved
            if assignee is not None:
                if assignee == "":
                    body["assignee"] = None
                else:
                    member = await cache.resolve_member(assignee)
                    if member:
                        body["assignee"] = member["id"]
            if parent is not None:
                body["parent"] = parent

            return await api_client.put(
                f"/checklist/{checklist_id}/checklist_item/{checklist_item_id}",
                json_body=body,
            )
        except Exception as e:
            return format_error("update_checklist_item", e)

    @mcp.tool()
    async def delete_checklist_item(
        checklist_id: str = Field(description="Checklist ID containing the item."),
        checklist_item_id: str = Field(description="Checklist item ID to delete."),
    ) -> dict:
        """Delete a checklist item.

        Permanently removes an item from a checklist. Cannot be undone.
        """
        try:
            return await api_client.delete(
                f"/checklist/{checklist_id}/checklist_item/{checklist_item_id}"
            )
        except Exception as e:
            return format_error("delete_checklist_item", e)
