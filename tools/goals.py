"""Goals tools for ClickUp — OKRs and goal tracking."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from cache import cache
from config import TEAM_ID
from utils import parse_date, format_error, resolve_color


def register_goal_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_goals(
        include_completed: bool = Field(default=False, description="Include completed goals in the response."),
    ) -> dict:
        """Get all goals for the workspace.

        Returns all goals (OKRs) with their targets, owners, and progress.
        Useful for tracking high-level objectives across the team.
        """
        try:
            params = {}
            if include_completed:
                params["include_completed"] = "true"
            return await api_client.get(f"/team/{TEAM_ID}/goal", params=params)
        except Exception as e:
            return format_error("get_goals", e)

    @mcp.tool()
    async def create_goal(
        name: str = Field(description="Goal name."),
        due_date: Optional[str] = Field(default=None, description="Due date. Accepts ISO dates, 'end of month', 'next quarter', etc."),
        description: Optional[str] = Field(default=None, description="Goal description or context."),
        owners: Optional[list[str]] = Field(default=None, description="List of owner names, emails, or user IDs."),
        color: Optional[str] = Field(default=None, description="Goal color as hex or name ('blue', 'green', 'red', etc.)."),
    ) -> dict:
        """Create a new goal (OKR) for the workspace.

        Goals represent high-level objectives. You can set targets (key results) on them
        after creation. Returns the created goal with its ID.
        """
        try:
            body: dict = {"name": name}
            if due_date:
                parsed = parse_date(due_date)
                if parsed:
                    body["due_date"] = parsed
            if description:
                body["description"] = description
            if owners:
                owner_ids = await cache.resolve_members(owners)
                body["owners"] = owner_ids
            if color:
                body["color"] = resolve_color(color)

            return await api_client.post(f"/team/{TEAM_ID}/goal", json_body=body)
        except Exception as e:
            return format_error("create_goal", e)

    @mcp.tool()
    async def get_goal(
        goal_id: str = Field(description="Goal ID to fetch."),
    ) -> dict:
        """Get a single goal with its targets and progress.

        Returns full goal details including key results (targets), current progress,
        and owner information.
        """
        try:
            return await api_client.get(f"/goal/{goal_id}")
        except Exception as e:
            return format_error("get_goal", e)

    @mcp.tool()
    async def update_goal(
        goal_id: str = Field(description="Goal ID to update."),
        name: Optional[str] = Field(default=None, description="New goal name."),
        due_date: Optional[str] = Field(default=None, description="New due date."),
        description: Optional[str] = Field(default=None, description="New description."),
        owners: Optional[list[str]] = Field(default=None, description="New list of owner names, emails, or IDs (replaces existing owners)."),
        color: Optional[str] = Field(default=None, description="New color as hex or name."),
    ) -> dict:
        """Update a goal's details.

        Modify the name, due date, description, owners, or color of an existing goal.
        """
        try:
            body: dict = {}
            if name:
                body["name"] = name
            if due_date:
                parsed = parse_date(due_date)
                if parsed:
                    body["due_date"] = parsed
            if description is not None:
                body["description"] = description
            if owners is not None:
                owner_ids = await cache.resolve_members(owners)
                body["owners"] = owner_ids
            if color:
                body["color"] = resolve_color(color)

            return await api_client.put(f"/goal/{goal_id}", json_body=body)
        except Exception as e:
            return format_error("update_goal", e)
