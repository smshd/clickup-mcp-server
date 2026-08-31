"""Comment management tools - CRUD and threaded replies."""
import json
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from config import TEAM_ID
from utils import format_error


_COMMENT_NODES_DESC = (
    "Rich text comment as a JSON array of node objects. Each node has 'text' and optional 'attributes'. "
    "Supported attributes: bold (true), italic (true), code (true), link ('url'). "
    "For @mentions use {\"type\": \"tag\", \"user\": {\"id\": USER_ID}} or provide a name/email "
    "in place of USER_ID and it will be resolved automatically. "
    "Line breaks: {\"text\": \"\\n\"}. "
    "Example: [{\"text\": \"Hello \"}, {\"text\": \"world\", \"attributes\": {\"bold\": true}}]. "
    "When provided, this overrides comment_text."
)


PIP_COMMENT_PREFIX_PLAIN = "🥑 Pip: "
PIP_COMMENT_PREFIX_NODES = [
    {"text": "🥑 "},
    {"text": "Pip:", "attributes": {"bold": True}},
    {"text": " "},
]


def _node_text(node: dict) -> str:
    """Return visible text for simple ClickUp comment nodes."""
    if "text" in node:
        return str(node.get("text") or "")
    if node.get("type") == "tag":
        user = node.get("user", {})
        return f"@{user.get('username') or user.get('email') or user.get('id') or ''}"
    return ""


def _has_pip_prefix(nodes: list[dict]) -> bool:
    """Detect Pip's visible prefix to avoid double-prefixing retries."""
    visible = "".join(_node_text(node) for node in nodes[:4])
    return visible.startswith(PIP_COMMENT_PREFIX_PLAIN)


def _with_pip_comment_prefix(nodes: list[dict]) -> list[dict]:
    """Prefix task comments with avocado + bold Pip label, idempotently."""
    if _has_pip_prefix(nodes):
        return nodes
    return [dict(node) for node in PIP_COMMENT_PREFIX_NODES] + nodes


async def _parse_comment_nodes(nodes_json: str) -> list[dict]:
    """Parse a JSON string of comment nodes, resolving @mention names to user IDs."""
    from cache import cache
    nodes = json.loads(nodes_json)
    resolved = []
    for node in nodes:
        if node.get("type") == "tag":
            user_ref = node.get("user", {})
            user_id = user_ref.get("id")
            # If the ID is a string (name/email), resolve it
            if isinstance(user_id, str) and not user_id.isdigit():
                member = await cache.resolve_member(user_id)
                if member:
                    node = {"type": "tag", "user": {"id": int(member["id"])}}
                else:
                    # Fall back to plain text if user not found
                    node = {"text": f"@{user_id}"}
            elif isinstance(user_id, str) and user_id.isdigit():
                node["user"]["id"] = int(user_id)
        resolved.append(node)
    return resolved


def register_comment_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_task_comments(
        task_id: str = Field(description="Task ID."),
        start: Optional[int] = Field(None, description="Pagination start (Unix ms timestamp). Use with start_id."),
        start_id: Optional[str] = Field(None, description="Comment ID to start pagination from."),
    ) -> dict:
        """
        Gets all top-level comments on a task.

        Paginated - use start and start_id for subsequent pages.
        Does NOT include threaded replies. Use get_threaded_comments for those.
        """
        try:
            params = {}
            if start is not None:
                params["start"] = start
            if start_id:
                params["start_id"] = start_id
            return await api_client.get(f"/task/{task_id}/comment", params=params or None)
        except Exception as e:
            return format_error("get_task_comments", e)

    @mcp.tool()
    async def create_task_comment(
        task_id: str = Field(description="Task ID."),
        comment_text: str = Field("", description="Plain text comment content. Ignored if comment_nodes is provided."),
        comment_nodes: Optional[str] = Field(None, description=_COMMENT_NODES_DESC),
        notify_all: bool = Field(False, description="Notify all assignees and watchers."),
        assignee: Optional[str] = Field(None, description="Assign the comment to a member (name, email, or ID)."),
    ) -> dict:
        """
        Adds a comment to a task.

        For plain text, use comment_text. For rich text (bold, links, @mentions),
        use comment_nodes with a JSON array of formatted nodes.
        """
        try:
            from cache import cache
            body: dict[str, object] = {"notify_all": notify_all}
            if comment_nodes:
                body["comment"] = _with_pip_comment_prefix(
                    await _parse_comment_nodes(comment_nodes)
                )
            else:
                body["comment"] = _with_pip_comment_prefix([{"text": comment_text}])
            if assignee:
                member = await cache.resolve_member(assignee)
                if member:
                    body["assignee"] = int(member["id"])
            return await api_client.post(f"/task/{task_id}/comment", json_body=body)
        except Exception as e:
            return format_error("create_task_comment", e)

    @mcp.tool()
    async def get_list_comments(
        list_id: str = Field(description="List ID."),
        start: Optional[int] = Field(None, description="Pagination start (Unix ms timestamp)."),
        start_id: Optional[str] = Field(None, description="Comment ID to start from."),
    ) -> dict:
        """
        Gets comments on a list (not on individual tasks within the list).

        Use get_task_comments for task-level comments.
        """
        try:
            params = {}
            if start is not None:
                params["start"] = start
            if start_id:
                params["start_id"] = start_id
            return await api_client.get(f"/list/{list_id}/comment", params=params or None)
        except Exception as e:
            return format_error("get_list_comments", e)

    @mcp.tool()
    async def create_list_comment(
        list_id: str = Field(description="List ID."),
        comment_text: str = Field("", description="Plain text comment content. Ignored if comment_nodes is provided."),
        comment_nodes: Optional[str] = Field(None, description=_COMMENT_NODES_DESC),
        notify_all: bool = Field(False, description="Notify all list followers."),
        assignee: Optional[str] = Field(None, description="Assign comment to a member (name, email, or ID)."),
    ) -> dict:
        """
        Adds a comment to a list.

        This is a list-level comment, not attached to any specific task.
        For rich text formatting, use comment_nodes instead of comment_text.
        """
        try:
            from cache import cache
            body: dict[str, object] = {"notify_all": notify_all}
            if comment_nodes:
                body["comment"] = await _parse_comment_nodes(comment_nodes)
            else:
                body["comment_text"] = comment_text
            if assignee:
                member = await cache.resolve_member(assignee)
                if member:
                    body["assignee"] = int(member["id"])
            return await api_client.post(f"/list/{list_id}/comment", json_body=body)
        except Exception as e:
            return format_error("create_list_comment", e)

    @mcp.tool()
    async def get_threaded_comments(
        comment_id: str = Field(description="Parent comment ID to get replies for."),
    ) -> dict:
        """
        Gets threaded replies to a specific comment.

        Returns child comments only (the parent comment is NOT included).
        Use get_task_comments first to find the parent comment ID.
        """
        try:
            return await api_client.get(f"/comment/{comment_id}/reply")
        except Exception as e:
            return format_error("get_threaded_comments", e)

    @mcp.tool()
    async def create_threaded_comment(
        comment_id: str = Field(description="Parent comment ID to reply to."),
        comment_text: str = Field("", description="Plain text reply content. Ignored if comment_nodes is provided."),
        comment_nodes: Optional[str] = Field(None, description=_COMMENT_NODES_DESC),
        notify_all: bool = Field(False, description="Notify all followers."),
        assignee: Optional[str] = Field(None, description="Assign reply to a member (name, email, or ID)."),
    ) -> dict:
        """
        Creates a threaded reply to an existing comment.

        The reply appears nested under the parent comment in ClickUp.
        For rich text formatting, use comment_nodes instead of comment_text.
        """
        try:
            from cache import cache
            body: dict[str, object] = {"notify_all": notify_all}
            if comment_nodes:
                body["comment"] = await _parse_comment_nodes(comment_nodes)
            else:
                body["comment_text"] = comment_text
            if assignee:
                member = await cache.resolve_member(assignee)
                if member:
                    body["assignee"] = int(member["id"])
            return await api_client.post(f"/comment/{comment_id}/reply", json_body=body)
        except Exception as e:
            return format_error("create_threaded_comment", e)

    @mcp.tool()
    async def update_comment(
        comment_id: str = Field(description="Comment ID to update."),
        comment_text: Optional[str] = Field(None, description="New plain text. Ignored if comment_nodes is provided."),
        comment_nodes: Optional[str] = Field(None, description=_COMMENT_NODES_DESC),
        assignee: Optional[str] = Field(None, description="New assignee (name, email, or ID)."),
        resolved: Optional[bool] = Field(None, description="Set true to resolve, false to unresolve."),
    ) -> dict:
        """
        Updates an existing comment's text, assignee, or resolved status.

        Provide only the fields you want to change.
        For rich text formatting, use comment_nodes instead of comment_text.
        """
        try:
            from cache import cache
            body = {}
            if comment_nodes is not None:
                body["comment"] = await _parse_comment_nodes(comment_nodes)
            elif comment_text is not None:
                body["comment_text"] = comment_text
            if assignee is not None:
                member = await cache.resolve_member(assignee)
                if member:
                    body["assignee"] = int(member["id"])
            if resolved is not None:
                body["resolved"] = resolved
            if not body:
                return {"success": False, "error": "No fields to update."}
            return await api_client.put(f"/comment/{comment_id}", json_body=body)
        except Exception as e:
            return format_error("update_comment", e)

    @mcp.tool()
    async def delete_comment(
        comment_id: str = Field(description="Comment ID to delete."),
    ) -> dict:
        """
        Permanently deletes a comment. This cannot be undone.

        Only use after explicit user confirmation.
        """
        try:
            return await api_client.delete(f"/comment/{comment_id}")
        except Exception as e:
            return format_error("delete_comment", e)
