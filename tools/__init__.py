"""Tool registration hub. Each domain module registers its tools."""
from fastmcp import FastMCP

from .tasks import register_task_tools
from .comments import register_comment_tools
from .hierarchy import register_hierarchy_tools
from .members import register_member_tools
from .time_tracking import register_time_tracking_tools
from .tags import register_tag_tools
from .custom_fields import register_custom_field_tools
from .views import register_view_tools
from .goals import register_goal_tools
from .checklists import register_checklist_tools
from .relationships import register_relationship_tools
from .webhooks import register_webhook_tools
from .attachments import register_attachment_tools


def register_all_tools(mcp: FastMCP) -> None:
    """Register all 13 tool domains (89 tools total). Called from server.py."""
    register_task_tools(mcp)
    register_comment_tools(mcp)
    register_hierarchy_tools(mcp)
    register_member_tools(mcp)
    register_time_tracking_tools(mcp)
    register_tag_tools(mcp)
    register_custom_field_tools(mcp)
    register_view_tools(mcp)
    register_goal_tools(mcp)
    register_checklist_tools(mcp)
    register_relationship_tools(mcp)
    register_webhook_tools(mcp)
    register_attachment_tools(mcp)
