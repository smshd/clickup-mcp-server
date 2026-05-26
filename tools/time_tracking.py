"""Time tracking tools for ClickUp — timers, entries, and tags."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from cache import cache
from config import TEAM_ID
from utils import parse_date, format_error


def register_time_tracking_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_time_entries(
        start_date: Optional[str] = Field(default=None, description="Start of date range. Accepts ISO dates, 'today', 'yesterday', 'X days ago', etc."),
        end_date: Optional[str] = Field(default=None, description="End of date range. Accepts ISO dates, 'today', 'tomorrow', etc."),
        assignee: Optional[str] = Field(default=None, description="Filter by member name, email, or user ID."),
        include_task_tags: bool = Field(default=False, description="Include task tags in the response."),
        include_location_names: bool = Field(default=False, description="Include space/folder/list names in the response."),
    ) -> dict:
        """Fetch time entries for the workspace within a date range.

        Returns a list of time entries with task, duration, description, and billable status.
        Filter by date range and/or assignee. Useful for generating time reports and invoices.
        """
        try:
            params = {}
            if start_date:
                parsed = parse_date(start_date)
                if parsed:
                    params["start_date"] = parsed
            if end_date:
                parsed = parse_date(end_date)
                if parsed:
                    params["end_date"] = parsed
            if assignee:
                member = await cache.resolve_member(assignee)
                if member:
                    params["assignee"] = member["id"]
            if include_task_tags:
                params["include_task_tags"] = "true"
            if include_location_names:
                params["include_location_names"] = "true"

            return await api_client.get(f"/team/{TEAM_ID}/time_entries", params=params)
        except Exception as e:
            return format_error("get_time_entries", e)

    @mcp.tool()
    async def create_time_entry(
        task_id: str = Field(description="Task ID to log time against."),
        duration: int = Field(description="Duration in milliseconds (e.g., 3600000 for 1 hour)."),
        start: Optional[str] = Field(default=None, description="Start time. Accepts ISO dates, 'today', 'X hours ago', etc. Defaults to now minus duration."),
        description: Optional[str] = Field(default=None, description="Description or note for this time entry."),
        billable: bool = Field(default=False, description="Whether this time entry is billable."),
        tags: Optional[list[str]] = Field(default=None, description="List of tag names to apply to this time entry."),
    ) -> dict:
        """Log a time entry against a task.

        Creates a manual time entry with a specified duration. Use start to set when the
        work began. Duration is in milliseconds (3600000 = 1 hour, 1800000 = 30 minutes).
        """
        try:
            body: dict = {
                "tid": task_id,
                "duration": duration,
                "billable": billable,
            }
            if start:
                parsed = parse_date(start)
                if parsed:
                    body["start"] = parsed
            if description:
                body["description"] = description
            if tags:
                body["tags"] = [{"name": t} for t in tags]

            return await api_client.post(f"/team/{TEAM_ID}/time_entries", json_body=body)
        except Exception as e:
            return format_error("create_time_entry", e)

    @mcp.tool()
    async def update_time_entry(
        timer_id: str = Field(description="Time entry ID to update."),
        duration: Optional[int] = Field(default=None, description="New duration in milliseconds."),
        start: Optional[str] = Field(default=None, description="New start time."),
        description: Optional[str] = Field(default=None, description="New description."),
        billable: Optional[bool] = Field(default=None, description="Whether this time entry is billable."),
        tags: Optional[list[str]] = Field(default=None, description="New list of tag names (replaces existing tags)."),
        task_id: Optional[str] = Field(default=None, description="Move this entry to a different task ID."),
    ) -> dict:
        """Update an existing time entry.

        Modify the duration, description, billable status, tags, or task assignment
        for a previously logged time entry.
        """
        try:
            body: dict = {}
            if duration is not None:
                body["duration"] = duration
            if start:
                parsed = parse_date(start)
                if parsed:
                    body["start"] = parsed
            if description is not None:
                body["description"] = description
            if billable is not None:
                body["billable"] = billable
            if tags is not None:
                body["tags"] = [{"name": t} for t in tags]
            if task_id:
                body["tid"] = task_id

            return await api_client.put(f"/team/{TEAM_ID}/time_entries/{timer_id}", json_body=body)
        except Exception as e:
            return format_error("update_time_entry", e)

    @mcp.tool()
    async def delete_time_entry(
        timer_id: str = Field(description="Time entry ID to delete."),
    ) -> dict:
        """Delete a time entry permanently.

        This action cannot be undone. Returns success: true on completion.
        """
        try:
            return await api_client.delete(f"/team/{TEAM_ID}/time_entries/{timer_id}")
        except Exception as e:
            return format_error("delete_time_entry", e)

    @mcp.tool()
    async def start_timer(
        task_id: str = Field(description="Task ID to start tracking time against."),
        description: Optional[str] = Field(default=None, description="Description of what you're working on."),
        billable: bool = Field(default=False, description="Whether this time is billable."),
        tags: Optional[list[str]] = Field(default=None, description="List of tag names to apply."),
    ) -> dict:
        """Start a running timer for a task.

        Begins tracking time from now. Only one timer can run at a time per user.
        Use stop_timer to end it and create a time entry. Returns the running timer details.
        """
        try:
            body: dict = {
                "tid": task_id,
                "billable": billable,
            }
            if description:
                body["description"] = description
            if tags:
                body["tags"] = [{"name": t} for t in tags]

            return await api_client.post(f"/team/{TEAM_ID}/time_entries/start", json_body=body)
        except Exception as e:
            return format_error("start_timer", e)

    @mcp.tool()
    async def stop_timer(
    ) -> dict:
        """Stop the currently running timer.

        Stops the active timer for the authenticated user and creates a time entry.
        Returns the completed time entry details including duration elapsed.
        """
        try:
            return await api_client.post(f"/team/{TEAM_ID}/time_entries/stop")
        except Exception as e:
            return format_error("stop_timer", e)

    @mcp.tool()
    async def get_running_timer(
        assignee: Optional[str] = Field(default=None, description="Check timer for a specific member (name, email, or ID). Defaults to authenticated user."),
    ) -> dict:
        """Get the currently running timer.

        Returns the active timer details if one is running, or an empty response if none.
        Useful to check whether time tracking is active before starting a new timer.
        """
        try:
            params = {}
            if assignee:
                member = await cache.resolve_member(assignee)
                if member:
                    params["assignee"] = member["id"]

            return await api_client.get(f"/team/{TEAM_ID}/time_entries/running", params=params)
        except Exception as e:
            return format_error("get_running_timer", e)

    @mcp.tool()
    async def get_time_entry_history(
        timer_id: str = Field(description="Time entry ID to fetch history for."),
    ) -> dict:
        """Get the edit history for a time entry.

        Returns a log of all changes made to a time entry, including who changed it and when.
        Useful for auditing time records.
        """
        try:
            return await api_client.get(f"/team/{TEAM_ID}/time_entries/{timer_id}/history")
        except Exception as e:
            return format_error("get_time_entry_history", e)

    @mcp.tool()
    async def get_time_tags(
    ) -> dict:
        """Get all time tracking tags for the workspace.

        Returns all tags that can be applied to time entries. These are separate from
        task tags and are used for categorising time records (e.g., 'billable', 'internal', 'support').
        """
        try:
            return await api_client.get(f"/team/{TEAM_ID}/time_entries/tags")
        except Exception as e:
            return format_error("get_time_tags", e)

    @mcp.tool()
    async def manage_time_tags(
        time_entry_ids: list[str] = Field(description="List of time entry IDs to apply tag changes to."),
        tags: list[str] = Field(description="List of tag names to add or remove."),
        action: str = Field(description="Action to perform: 'add' to add tags, 'remove' to remove tags."),
    ) -> dict:
        """Add or remove tags on one or more time entries.

        Apply or strip tags from multiple time entries in a single call.
        Use get_time_tags to see available tag names.
        Action must be 'add' or 'remove'.
        """
        try:
            if action not in ("add", "remove"):
                return {"success": False, "error": "action must be 'add' or 'remove'", "error_type": "ValueError"}

            body = {
                "time_entry_ids": time_entry_ids,
                "tags": [{"name": t} for t in tags],
                "action": action,
            }
            return await api_client.post(f"/team/{TEAM_ID}/time_entries/tags", json_body=body)
        except Exception as e:
            return format_error("manage_time_tags", e)
