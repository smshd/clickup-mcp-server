"""Task management tools - CRUD, move, query, merge."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import BaseModel, Field
import api_client
from cache import cache
from config import TEAM_ID
from utils import parse_date, size_response, format_error


PRIORITY_MAP = {"urgent": 1, "high": 2, "normal": 3, "low": 4}


def _resolve_priority(p) -> Optional[int]:
    if p is None:
        return None
    if isinstance(p, int):
        return p
    return PRIORITY_MAP.get(str(p).lower())


def register_task_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def create_task(
        list_name: str = Field(description="List name or ID to create the task in."),
        name: str = Field(description="Task title."),
        description: Optional[str] = Field(None, description="Task description (plain text)."),
        markdown_description: Optional[str] = Field(None, description="Task description (markdown). Overrides description if both provided."),
        assignees: Optional[list[str]] = Field(None, description="List of assignee names, emails, or IDs."),
        tags: Optional[list[str]] = Field(None, description="List of tag names to apply."),
        status: Optional[str] = Field(None, description="Task status name (e.g. 'open', 'in progress')."),
        priority: Optional[str] = Field(None, description="Priority: 'urgent', 'high', 'normal', 'low' or 1-4."),
        due_date: Optional[str] = Field(None, description="Due date. Natural language ('tomorrow', 'next Monday') or ISO 8601."),
        start_date: Optional[str] = Field(None, description="Start date. Natural language or ISO 8601."),
        time_estimate: Optional[int] = Field(None, description="Time estimate in milliseconds."),
        parent: Optional[str] = Field(None, description="Parent task ID to create as subtask."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope list lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope list lookup."),
    ) -> dict:
        """
        Creates a new task in a ClickUp list.

        Accepts list names (resolved automatically) or list IDs.
        Assignees can be names or emails - resolved to user IDs.
        Dates accept natural language like 'tomorrow at 9am'.

        Returns the created task record with ID, URL, and status.
        """
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found.", "hint": "Check the list name or provide folder_name/space_name to narrow the search."}

            body = {"name": name}
            if markdown_description:
                body["markdown_content"] = markdown_description
            elif description:
                body["description"] = description
            if assignees:
                body["assignees"] = await cache.resolve_members(assignees)
            if tags:
                body["tags"] = tags
            if status:
                body["status"] = status
            if priority is not None:
                body["priority"] = _resolve_priority(priority)
            if due_date:
                body["due_date"] = parse_date(due_date)
            if start_date:
                body["start_date"] = parse_date(start_date)
            if time_estimate:
                body["time_estimate"] = time_estimate
            if parent:
                body["parent"] = parent

            result = await api_client.post(f"/list/{lst['id']}/task", json_body=body)
            if isinstance(result, dict) and "id" in result:
                return {"success": True, "task_id": result["id"], "name": result.get("name"), "url": result.get("url"), "status": result.get("status", {}).get("status")}
            return result
        except Exception as e:
            return format_error("create_task", e)

    @mcp.tool()
    async def get_task(
        task_id: str = Field(description="Task ID (e.g. 'abc123') or custom task ID (e.g. 'DEV-123')."),
        custom_task_ids: bool = Field(False, description="Set true if using a custom task ID format."),
    ) -> dict:
        """
        Fetches a single task by ID.

        Returns the full task record including status, assignees, due date, and custom fields.
        Use custom_task_ids=true for custom ID formats like 'DEV-123'.
        """
        try:
            params = {}
            if custom_task_ids:
                params["custom_task_ids"] = "true"
                params["team_id"] = TEAM_ID
            return await api_client.get(f"/task/{task_id}", params=params or None)
        except Exception as e:
            return format_error("get_task", e)

    @mcp.tool()
    async def update_task(
        task_id: str = Field(description="Task ID to update."),
        name: Optional[str] = Field(None, description="New task name."),
        description: Optional[str] = Field(None, description="New description (plain text)."),
        markdown_description: Optional[str] = Field(None, description="New description (markdown)."),
        status: Optional[str] = Field(None, description="New status name."),
        priority: Optional[str] = Field(None, description="New priority: 'urgent', 'high', 'normal', 'low' or 1-4."),
        due_date: Optional[str] = Field(None, description="New due date. Natural language or ISO 8601. Use 'null' to clear."),
        start_date: Optional[str] = Field(None, description="New start date. Natural language or ISO 8601. Use 'null' to clear."),
        add_assignees: Optional[list[str]] = Field(None, description="Assignee names/emails to add."),
        remove_assignees: Optional[list[str]] = Field(None, description="Assignee names/emails to remove."),
        parent: Optional[str] = Field(None, description="Parent task ID (converts to subtask). Use 'null' to make top-level."),
        archived: Optional[bool] = Field(None, description="Set true to archive the task."),
    ) -> dict:
        """
        Updates properties of an existing task.

        Only include the fields you want to change. Unspecified fields are not modified.
        Use 'null' string for due_date/start_date to clear them.
        Assignees are additive/subtractive - use add_assignees and remove_assignees.
        """
        try:
            body = {}
            if name is not None:
                body["name"] = name
            if markdown_description is not None:
                body["markdown_content"] = markdown_description
            elif description is not None:
                body["description"] = description
            if status is not None:
                body["status"] = status
            if priority is not None:
                body["priority"] = _resolve_priority(priority)
            if due_date is not None:
                body["due_date"] = None if due_date == "null" else parse_date(due_date)
            if start_date is not None:
                body["start_date"] = None if start_date == "null" else parse_date(start_date)
            if add_assignees or remove_assignees:
                body["assignees"] = {}
                if add_assignees:
                    body["assignees"]["add"] = await cache.resolve_members(add_assignees)
                if remove_assignees:
                    body["assignees"]["rem"] = await cache.resolve_members(remove_assignees)
            if parent is not None:
                body["parent"] = None if parent == "null" else parent
            if archived is not None:
                body["archived"] = archived

            if not body:
                return {"success": False, "error": "No fields to update.", "hint": "Provide at least one field to change."}

            return await api_client.put(f"/task/{task_id}", json_body=body)
        except Exception as e:
            return format_error("update_task", e)

    @mcp.tool()
    async def delete_task(
        task_id: str = Field(description="Task ID to delete."),
    ) -> dict:
        """
        Permanently deletes a task. This cannot be undone.

        Only use after explicit user confirmation.
        Consider archiving (update_task with archived=true) as a safer alternative.
        """
        try:
            return await api_client.delete(f"/task/{task_id}")
        except Exception as e:
            return format_error("delete_task", e)

    @mcp.tool()
    async def move_task(
        task_id: str = Field(description="Task ID to move."),
        list_name: str = Field(description="Destination list name or ID."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope list lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope list lookup."),
    ) -> dict:
        """
        Moves a task to a different list (changes its home list).

        The task's status may change if the destination list has different statuses.
        Accepts list names - resolved automatically.
        """
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found."}
            return await api_client.put(f"/task/{task_id}", json_body={"list": lst["id"]})
        except Exception as e:
            return format_error("move_task", e)

    @mcp.tool()
    async def get_tasks(
        list_name: str = Field(description="List name or ID to get tasks from."),
        archived: bool = Field(False, description="Include archived tasks."),
        page: int = Field(0, description="Page number (0-indexed, 100 tasks per page)."),
        order_by: Optional[str] = Field(None, description="Sort field: 'created', 'updated', 'due_date'."),
        reverse: bool = Field(False, description="Reverse sort order."),
        statuses: Optional[list[str]] = Field(None, description="Filter by status names."),
        assignees: Optional[list[str]] = Field(None, description="Filter by assignee names/emails."),
        include_closed: bool = Field(False, description="Include tasks with closed status."),
        subtasks: bool = Field(False, description="Include subtasks."),
        detail_level: str = Field("summary", description="Response detail: 'names', 'summary', or 'detailed'."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope list lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope list lookup."),
    ) -> dict:
        """
        Gets tasks from a specific list with filtering and pagination.

        Returns 100 tasks per page. Use page parameter for pagination.
        Response size is controlled by detail_level (auto-downgrades if too large).
        """
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found."}

            params = {"archived": str(archived).lower(), "page": page, "include_closed": str(include_closed).lower(), "subtasks": str(subtasks).lower()}
            if order_by:
                params["order_by"] = order_by
            if reverse:
                params["reverse"] = "true"
            if statuses:
                params["statuses[]"] = statuses
            if assignees:
                member_ids = await cache.resolve_members(assignees)
                params["assignees[]"] = member_ids

            result = await api_client.get(f"/list/{lst['id']}/task", params=params)
            if isinstance(result, dict) and "tasks" in result:
                tasks = size_response(result["tasks"], detail_level)
                return {"success": True, "tasks": tasks, "count": len(tasks)}
            return result
        except Exception as e:
            return format_error("get_tasks", e)

    @mcp.tool()
    async def get_workspace_tasks(
        page: int = Field(0, description="Page number (0-indexed)."),
        statuses: Optional[list[str]] = Field(None, description="Filter by status names."),
        assignees: Optional[list[str]] = Field(None, description="Filter by assignee names/emails."),
        tags: Optional[list[str]] = Field(None, description="Filter by tag names."),
        space_ids: Optional[list[str]] = Field(None, description="Filter by space IDs."),
        list_ids: Optional[list[str]] = Field(None, description="Filter by list IDs."),
        due_date_gt: Optional[str] = Field(None, description="Due date after this. Natural language or ISO 8601."),
        due_date_lt: Optional[str] = Field(None, description="Due date before this. Natural language or ISO 8601."),
        date_created_gt: Optional[str] = Field(None, description="Created after this date."),
        date_created_lt: Optional[str] = Field(None, description="Created before this date."),
        date_updated_gt: Optional[str] = Field(None, description="Updated after this date."),
        date_updated_lt: Optional[str] = Field(None, description="Updated before this date."),
        order_by: Optional[str] = Field(None, description="Sort: 'created', 'updated', 'due_date'."),
        reverse: bool = Field(False, description="Reverse sort order."),
        include_closed: bool = Field(False, description="Include closed tasks."),
        subtasks: bool = Field(False, description="Include subtasks."),
        detail_level: str = Field("summary", description="Response detail: 'names', 'summary', or 'detailed'."),
    ) -> dict:
        """
        Searches tasks across the entire workspace with filtering.

        Powerful cross-workspace query. Supports date ranges, status, assignee, and tag filters.
        Dates accept natural language. Assignees accept names/emails.
        Response size controlled by detail_level.
        """
        try:
            params = {"page": page, "include_closed": str(include_closed).lower(), "subtasks": str(subtasks).lower()}
            if statuses:
                params["statuses[]"] = statuses
            if assignees:
                member_ids = await cache.resolve_members(assignees)
                params["assignees[]"] = member_ids
            if tags:
                params["tags[]"] = tags
            if space_ids:
                params["space_ids[]"] = space_ids
            if list_ids:
                params["list_ids[]"] = list_ids
            if due_date_gt:
                params["due_date_gt"] = parse_date(due_date_gt)
            if due_date_lt:
                params["due_date_lt"] = parse_date(due_date_lt)
            if date_created_gt:
                params["date_created_gt"] = parse_date(date_created_gt)
            if date_created_lt:
                params["date_created_lt"] = parse_date(date_created_lt)
            if date_updated_gt:
                params["date_updated_gt"] = parse_date(date_updated_gt)
            if date_updated_lt:
                params["date_updated_lt"] = parse_date(date_updated_lt)
            if order_by:
                params["order_by"] = order_by
            if reverse:
                params["reverse"] = "true"

            result = await api_client.get(f"/team/{TEAM_ID}/task", params=params)
            if isinstance(result, dict) and "tasks" in result:
                tasks = size_response(result["tasks"], detail_level)
                return {"success": True, "tasks": tasks, "count": len(tasks)}
            return result
        except Exception as e:
            return format_error("get_workspace_tasks", e)

    @mcp.tool()
    async def merge_tasks(
        target_task_id: str = Field(description="Task ID to merge INTO (this task survives)."),
        source_task_ids: list[str] = Field(description="Task IDs to merge FROM (these get merged into target)."),
    ) -> dict:
        """
        Merges multiple source tasks into a target task.

        Source tasks are combined into the target. Source tasks are removed after merge.
        Use this to consolidate duplicate tasks.
        """
        try:
            return await api_client.post(f"/task/{target_task_id}/merge", json_body={"task_ids": source_task_ids})
        except Exception as e:
            return format_error("merge_tasks", e)

    @mcp.tool()
    async def create_task_from_template(
        list_name: str = Field(description="List name or ID."),
        template_id: str = Field(description="Template ID to create from."),
        name: str = Field(description="Task name for the new task."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope list lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope list lookup."),
    ) -> dict:
        """
        Creates a new task from a ClickUp task template.

        The template must exist in the workspace. Provide the template ID.
        """
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found."}
            return await api_client.post(f"/list/{lst['id']}/taskTemplate/{template_id}", json_body={"name": name})
        except Exception as e:
            return format_error("create_task_from_template", e)

    @mcp.tool()
    async def get_task_members(
        task_id: str = Field(description="Task ID."),
    ) -> dict:
        """
        Lists all members assigned to or watching a task.

        Returns member details including name, email, and role.
        """
        try:
            return await api_client.get(f"/task/{task_id}/member")
        except Exception as e:
            return format_error("get_task_members", e)

    @mcp.tool()
    async def get_time_in_status(
        task_id: str = Field(description="Task ID."),
    ) -> dict:
        """
        Gets how long a task has spent in each status.

        Returns time in milliseconds per status, useful for bottleneck analysis.
        """
        try:
            return await api_client.get(f"/task/{task_id}/time_in_status")
        except Exception as e:
            return format_error("get_time_in_status", e)

    @mcp.tool()
    async def get_bulk_time_in_status(
        task_ids: list[str] = Field(description="List of task IDs (max 100)."),
    ) -> dict:
        """
        Gets time-in-status for multiple tasks at once (max 100).

        More efficient than calling get_time_in_status per task.
        """
        try:
            params = {"task_ids": ",".join(task_ids[:100])}
            return await api_client.get("/task/bulk_time_in_status/task_ids", params=params)
        except Exception as e:
            return format_error("get_bulk_time_in_status", e)

    @mcp.tool()
    async def add_task_to_list(
        task_id: str = Field(description="Task ID."),
        list_name: str = Field(description="List name or ID to add the task to."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope list lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope list lookup."),
    ) -> dict:
        """
        Adds a task to an additional list (Tasks in Multiple Lists / TIML).

        The task remains in its home list. This creates a secondary association.
        Requires the Tasks in Multiple Lists ClickApp to be enabled.
        """
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found."}
            return await api_client.post(f"/list/{lst['id']}/task/{task_id}")
        except Exception as e:
            return format_error("add_task_to_list", e)

    @mcp.tool()
    async def remove_task_from_list(
        task_id: str = Field(description="Task ID."),
        list_name: str = Field(description="List name or ID to remove the task from."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope list lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope list lookup."),
    ) -> dict:
        """
        Removes a task from a secondary list (TIML).

        Cannot remove a task from its home list. Only works for additional list associations.
        """
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found."}
            return await api_client.delete(f"/list/{lst['id']}/task/{task_id}")
        except Exception as e:
            return format_error("remove_task_from_list", e)
