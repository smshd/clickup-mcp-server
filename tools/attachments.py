"""Attachments tools for ClickUp — upload files to tasks."""
import os
from fastmcp import FastMCP
from pydantic import Field
import api_client
from utils import format_error


def register_attachment_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def upload_attachment(
        task_id: str = Field(description="Task ID to attach the file to."),
        file_path: str = Field(description="Absolute path to the file to upload."),
    ) -> dict:
        """Upload a file attachment to a task.

        Uploads a local file to a task as an attachment. The file will appear in the
        task's attachments section. Returns the attachment details including its URL.

        Note: Uses multipart form upload, not JSON. File size limits apply per ClickUp plan.
        """
        try:
            client = await api_client.get_client()
            with open(file_path, "rb") as f:
                files = {"attachment": (os.path.basename(file_path), f)}
                response = await client.post(f"/task/{task_id}/attachment", files=files)
                if response.status_code >= 400:
                    error_body = response.json() if response.content else {}
                    return {
                        "success": False,
                        "error": error_body.get("err", f"HTTP {response.status_code}"),
                        "error_type": "APIError",
                        "status_code": response.status_code,
                    }
                return response.json()
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "error_type": "FileNotFoundError",
                "hint": "Provide an absolute path to an existing file.",
            }
        except Exception as e:
            return format_error("upload_attachment", e)
