"""Adaptive response sizing for query tools."""
from typing import Any

CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_LIMIT = 50_000

SUMMARY_FIELDS = {
    "id", "name", "status", "priority", "assignees", "due_date",
    "start_date", "tags", "list", "folder", "space", "url",
}

NAMES_FIELDS = {
    "id", "name", "status", "list",
}


def size_response(
    tasks: list[dict],
    detail_level: str = "summary",
    token_limit: int = DEFAULT_TOKEN_LIMIT,
) -> list[dict]:
    """
    Filter task fields based on detail level.

    Levels:
    - "names": id, name, status, list only
    - "summary": core fields (assignees, dates, priority, tags)
    - "detailed": full API response, no filtering

    Auto-downgrades to a lighter level if response would exceed token_limit.
    """
    if detail_level == "detailed":
        estimated = _estimate_tokens(tasks)
        if estimated > token_limit:
            detail_level = "summary"

    if detail_level == "summary":
        estimated = _estimate_tokens([_filter_fields(t, SUMMARY_FIELDS) for t in tasks])
        if estimated > token_limit:
            detail_level = "names"

    if detail_level == "names":
        return [_filter_fields(t, NAMES_FIELDS) for t in tasks]
    elif detail_level == "summary":
        return [_filter_fields(t, SUMMARY_FIELDS) for t in tasks]
    else:
        return tasks


def _filter_fields(task: dict, fields: set[str]) -> dict:
    """Keep only specified fields from a task dict."""
    result = {}
    for key in fields:
        if key in task:
            val = task[key]
            if key == "assignees" and isinstance(val, list):
                val = [a.get("username", a.get("email", str(a.get("id", "")))) if isinstance(a, dict) else a for a in val]
            if key == "status" and isinstance(val, dict):
                val = val.get("status", val)
            if key in ("list", "folder", "space") and isinstance(val, dict):
                val = val.get("name", val)
            result[key] = val
    return result


def _estimate_tokens(data: Any) -> int:
    """Rough token count estimate from data size."""
    import json
    chars = len(json.dumps(data, default=str))
    return chars // CHARS_PER_TOKEN
