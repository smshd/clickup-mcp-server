"""Standardized error responses for all tools."""


def format_error(tool_name: str, error: Exception) -> dict:
    """Standard error response structure for LLM consumption."""
    error_type = type(error).__name__
    return {
        "success": False,
        "error": str(error),
        "error_type": error_type,
        "tool": tool_name,
        "hint": _get_hint(error),
    }


def _get_hint(error: Exception) -> str:
    hints = {
        "ValueError": "Check parameter format and types.",
        "TimeoutException": "ClickUp API is slow. Retry in 30 seconds.",
        "ConnectError": "Cannot reach ClickUp API. Check network.",
        "KeyError": "Resource not found. Verify the ID or name.",
    }
    return hints.get(type(error).__name__, "An unexpected error occurred.")
