"""ClickUp MCP Server - comprehensive ClickUp API v2 coverage."""
from fastmcp import FastMCP

mcp = FastMCP(
    name="ClickUp MCP Server",
    instructions=(
        "This server provides tools for managing ClickUp workspaces. "
        "All tools accept names (spaces, folders, lists, members) instead of IDs. "
        "Dates accept natural language like 'tomorrow at 9am'. "
        "Tools returning 'success: false' have failed - read the error and hint fields."
    ),
)

from tools import register_all_tools
register_all_tools(mcp)

if __name__ == "__main__":
    mcp.run()
