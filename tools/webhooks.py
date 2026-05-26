"""Webhooks tools for ClickUp — manage workspace webhooks."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from config import TEAM_ID
from utils import format_error


def register_webhook_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_webhooks(
    ) -> dict:
        """Get all webhooks configured for the workspace.

        Returns all active webhooks including their endpoints, event subscriptions,
        and optional scope (task/list/folder/space). Useful for auditing integrations.
        """
        try:
            return await api_client.get(f"/team/{TEAM_ID}/webhook")
        except Exception as e:
            return format_error("get_webhooks", e)

    @mcp.tool()
    async def create_webhook(
        endpoint: str = Field(description="URL to receive webhook POST requests."),
        events: list[str] = Field(description="List of event names to subscribe to, or ['*'] for all events. Examples: ['taskCreated', 'taskUpdated', 'taskStatusUpdated', 'taskDeleted', 'taskCommentPosted']."),
        space_id: Optional[str] = Field(default=None, description="Scope the webhook to a specific space ID."),
        folder_id: Optional[str] = Field(default=None, description="Scope the webhook to a specific folder ID."),
        list_id: Optional[str] = Field(default=None, description="Scope the webhook to a specific list ID."),
        task_id: Optional[str] = Field(default=None, description="Scope the webhook to a specific task ID."),
    ) -> dict:
        """Create a webhook to receive ClickUp event notifications.

        Webhooks send POST requests to your endpoint when events occur.
        Use events=['*'] to subscribe to all events, or specify individual event names.
        Optionally scope the webhook to a specific space, folder, list, or task.

        Common events: taskCreated, taskUpdated, taskDeleted, taskStatusUpdated,
        taskCommentPosted, taskAssigneeUpdated, taskDueDateUpdated, listCreated,
        folderCreated, spaceCreated.
        """
        try:
            body: dict = {
                "endpoint": endpoint,
                "events": events,
            }
            if space_id:
                body["space_id"] = space_id
            if folder_id:
                body["folder_id"] = folder_id
            if list_id:
                body["list_id"] = list_id
            if task_id:
                body["task_id"] = task_id

            return await api_client.post(f"/team/{TEAM_ID}/webhook", json_body=body)
        except Exception as e:
            return format_error("create_webhook", e)

    @mcp.tool()
    async def update_webhook(
        webhook_id: str = Field(description="Webhook ID to update."),
        endpoint: Optional[str] = Field(default=None, description="New endpoint URL."),
        events: Optional[list[str]] = Field(default=None, description="New event list (replaces existing subscriptions)."),
        status: Optional[str] = Field(default=None, description="Webhook status: 'active' or 'inactive'."),
    ) -> dict:
        """Update a webhook's endpoint, events, or status.

        Modify an existing webhook. Set status='inactive' to pause delivery without deleting.
        Providing events replaces all existing event subscriptions.
        """
        try:
            body: dict = {}
            if endpoint:
                body["endpoint"] = endpoint
            if events is not None:
                body["events"] = events
            if status:
                body["status"] = status

            return await api_client.put(f"/webhook/{webhook_id}", json_body=body)
        except Exception as e:
            return format_error("update_webhook", e)

    @mcp.tool()
    async def delete_webhook(
        webhook_id: str = Field(description="Webhook ID to delete."),
    ) -> dict:
        """Delete a webhook.

        Permanently removes the webhook. ClickUp will stop sending events to its endpoint.
        """
        try:
            return await api_client.delete(f"/webhook/{webhook_id}")
        except Exception as e:
            return format_error("delete_webhook", e)
