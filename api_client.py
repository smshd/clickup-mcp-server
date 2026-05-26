"""HTTP client for ClickUp API v2 with auth, rate limiting, and retries."""
import asyncio
import httpx
from typing import Any, Optional
from config import API_TOKEN, BASE_URL

_client: Optional[httpx.AsyncClient] = None


def _get_headers() -> dict[str, str]:
    return {
        "Authorization": API_TOKEN,
        "Content-Type": "application/json",
    }


async def get_client() -> httpx.AsyncClient:
    """Get or create the shared async HTTP client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=_get_headers(),
            timeout=30.0,
        )
    return _client


async def api_request(
    method: str,
    path: str,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    Make an authenticated request to the ClickUp API.

    Handles:
    - Authentication via API token header
    - Rate limiting (429) with exponential backoff
    - Retries on 5xx server errors
    - Structured error responses

    Returns the parsed JSON response or an error dict.
    """
    client = await get_client()
    last_error = None

    for attempt in range(max_retries):
        try:
            response = await client.request(
                method=method,
                url=path,
                params=params,
                json=json_body,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", str(2 ** attempt)))
                await asyncio.sleep(retry_after)
                continue

            if response.status_code >= 500:
                await asyncio.sleep(2 ** attempt)
                continue

            if response.status_code >= 400:
                # Defensive: error responses may be plain text (e.g. "404 page not found")
                # rather than JSON. Don't crash the whole tool on a non-JSON error body.
                error_body: dict = {}
                if response.content:
                    try:
                        parsed = response.json()
                        if isinstance(parsed, dict):
                            error_body = parsed
                    except Exception:
                        error_body = {"err": response.text[:200].strip()}
                return {
                    "success": False,
                    "error": error_body.get("err", f"HTTP {response.status_code}"),
                    "error_type": "APIError",
                    "status_code": response.status_code,
                    "hint": _get_api_hint(response.status_code),
                }

            if response.status_code == 204:
                return {"success": True}

            return response.json()

        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue

        except httpx.ConnectError as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "ConnectionError",
                "hint": "Cannot reach ClickUp API. Check network connection.",
            }

    return {
        "success": False,
        "error": str(last_error) if last_error else "Max retries exceeded",
        "error_type": "RetryExhausted",
        "hint": "ClickUp API is not responding. Try again in a few minutes.",
    }


def _get_api_hint(status_code: int) -> str:
    hints = {
        400: "Bad request. Check parameter names and values.",
        401: "Unauthorized. Check CLICKUP_API_TOKEN in .env.",
        403: "Forbidden. The API token may lack permission for this operation.",
        404: "Resource not found. Verify the ID or name.",
        422: "Validation error. Check required fields and value formats.",
    }
    return hints.get(status_code, f"HTTP error {status_code}.")


async def get(path: str, params: Optional[dict] = None) -> dict[str, Any]:
    """GET request shorthand."""
    return await api_request("GET", path, params=params)


async def post(path: str, json_body: Optional[dict] = None) -> dict[str, Any]:
    """POST request shorthand."""
    return await api_request("POST", path, json_body=json_body)


async def put(path: str, json_body: Optional[dict] = None) -> dict[str, Any]:
    """PUT request shorthand."""
    return await api_request("PUT", path, json_body=json_body)


async def delete(path: str, params: Optional[dict] = None) -> dict[str, Any]:
    """DELETE request shorthand."""
    return await api_request("DELETE", path, params=params)
