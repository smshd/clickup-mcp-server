"""Relationships tools for ClickUp — task dependencies and task links."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from utils import format_error


def register_relationship_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def add_dependency(
        task_id: str = Field(description="Task ID to add the dependency to."),
        depends_on: Optional[str] = Field(default=None, description="Task ID that this task is waiting on (must be completed before task_id can start)."),
        dependency_of: Optional[str] = Field(default=None, description="Task ID that is waiting on this task (task_id must complete before dependency_of can start)."),
    ) -> dict:
        """Add a dependency between two tasks.

        Use depends_on when this task is blocked by another (task_id waits for depends_on).
        Use dependency_of when this task blocks another (dependency_of waits for task_id).
        Provide exactly one of depends_on or dependency_of.
        """
        try:
            if not depends_on and not dependency_of:
                return {
                    "success": False,
                    "error": "Provide either depends_on or dependency_of.",
                    "error_type": "ValueError",
                }

            body: dict = {}
            if depends_on:
                body["depends_on"] = depends_on
            if dependency_of:
                body["dependency_of"] = dependency_of

            return await api_client.post(f"/task/{task_id}/dependency", json_body=body)
        except Exception as e:
            return format_error("add_dependency", e)

    @mcp.tool()
    async def remove_dependency(
        task_id: str = Field(description="Task ID to remove the dependency from."),
        depends_on: Optional[str] = Field(default=None, description="Task ID that was blocking this task."),
        dependency_of: Optional[str] = Field(default=None, description="Task ID that this task was blocking."),
    ) -> dict:
        """Remove a dependency between two tasks.

        Provide the same depends_on or dependency_of value that was used when the
        dependency was added. Provide exactly one of the two parameters.
        """
        try:
            if not depends_on and not dependency_of:
                return {
                    "success": False,
                    "error": "Provide either depends_on or dependency_of.",
                    "error_type": "ValueError",
                }

            params: dict = {}
            if depends_on:
                params["depends_on"] = depends_on
            if dependency_of:
                params["dependency_of"] = dependency_of

            return await api_client.delete(f"/task/{task_id}/dependency", params=params)
        except Exception as e:
            return format_error("remove_dependency", e)

    @mcp.tool()
    async def add_task_link(
        task_id: str = Field(description="Task ID to link from."),
        links_to: str = Field(description="Task ID to link to."),
    ) -> dict:
        """Create a link between two tasks.

        Task links create a loose association between tasks (as opposed to dependencies,
        which have directional blocking semantics). Both tasks will show the link.
        """
        try:
            return await api_client.post(f"/task/{task_id}/link/{links_to}")
        except Exception as e:
            return format_error("add_task_link", e)

    @mcp.tool()
    async def remove_task_link(
        task_id: str = Field(description="Task ID to remove the link from."),
        links_to: str = Field(description="Task ID that was linked to."),
    ) -> dict:
        """Remove a link between two tasks.

        Removes the association created by add_task_link. The link is removed from both tasks.
        """
        try:
            return await api_client.delete(f"/task/{task_id}/link/{links_to}")
        except Exception as e:
            return format_error("remove_task_link", e)
