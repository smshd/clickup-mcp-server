"""Member and group management tools."""
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field
import api_client
from cache import cache
from config import TEAM_ID
from utils import format_error


def register_member_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_workspace_members() -> dict:
        """
        Lists all members in the workspace.

        Returns name, email, role, and last active date for each member.
        """
        try:
            return await api_client.get(f"/team/{TEAM_ID}/member")
        except Exception as e:
            return format_error("get_workspace_members", e)

    @mcp.tool()
    async def find_member(
        name_or_email: str = Field(description="Member name, username, or email to search for."),
    ) -> dict:
        """
        Finds a workspace member by name or email.

        Uses fuzzy matching. Returns the best match with ID, name, and email.
        """
        try:
            member = await cache.resolve_member(name_or_email)
            if member:
                return {"success": True, "member": member}
            return {"success": False, "error": f"No member matching '{name_or_email}' found."}
        except Exception as e:
            return format_error("find_member", e)

    @mcp.tool()
    async def invite_user(
        email: str = Field(description="Email address to invite."),
        admin: bool = Field(False, description="Invite as admin (default: member)."),
    ) -> dict:
        """
        Invites a user to the workspace by email.

        The user receives an email invitation to join.
        Set admin=true to invite as a workspace admin.
        """
        try:
            body = {"email": email, "admin": admin}
            return await api_client.post(f"/team/{TEAM_ID}/user", json_body=body)
        except Exception as e:
            return format_error("invite_user", e)

    @mcp.tool()
    async def update_user(
        user_name: str = Field(description="User name, email, or ID."),
        admin: Optional[bool] = Field(None, description="Set admin status."),
        custom_role_id: Optional[int] = Field(None, description="Custom role ID to assign."),
    ) -> dict:
        """Updates a user's role in the workspace."""
        try:
            member = await cache.resolve_member(user_name)
            if not member:
                return {"success": False, "error": f"User '{user_name}' not found."}
            body = {}
            if admin is not None:
                body["admin"] = admin
            if custom_role_id is not None:
                body["custom_role_id"] = custom_role_id
            return await api_client.put(f"/team/{TEAM_ID}/user/{member['id']}", json_body=body)
        except Exception as e:
            return format_error("update_user", e)

    @mcp.tool()
    async def remove_user(
        user_name: str = Field(description="User name, email, or ID to remove."),
    ) -> dict:
        """
        Removes a user from the workspace. Cannot be undone easily.

        Only use after explicit user confirmation.
        """
        try:
            member = await cache.resolve_member(user_name)
            if not member:
                return {"success": False, "error": f"User '{user_name}' not found."}
            return await api_client.delete(f"/team/{TEAM_ID}/user/{member['id']}")
        except Exception as e:
            return format_error("remove_user", e)

    @mcp.tool()
    async def get_groups() -> dict:
        """Lists all user groups (teams) in the workspace."""
        try:
            return await api_client.get(f"/group", params={"team_id": TEAM_ID})
        except Exception as e:
            return format_error("get_groups", e)

    @mcp.tool()
    async def create_group(
        name: str = Field(description="Group name."),
        member_ids: Optional[list[int]] = Field(None, description="User IDs to add to the group."),
    ) -> dict:
        """Creates a new user group in the workspace."""
        try:
            body = {"name": name}
            if member_ids:
                body["members"] = member_ids
            return await api_client.post(f"/team/{TEAM_ID}/group", json_body=body)
        except Exception as e:
            return format_error("create_group", e)

    @mcp.tool()
    async def update_group(
        group_id: str = Field(description="Group ID."),
        name: Optional[str] = Field(None, description="New group name."),
        add_members: Optional[list[int]] = Field(None, description="User IDs to add."),
        remove_members: Optional[list[int]] = Field(None, description="User IDs to remove."),
    ) -> dict:
        """Updates a user group's name or membership."""
        try:
            body = {"handle": {}}
            if name:
                body["name"] = name
            if add_members:
                body["members"] = {"add": add_members}
            if remove_members:
                body["members"] = body.get("members", {})
                body["members"]["rem"] = remove_members
            return await api_client.put(f"/group/{group_id}", json_body=body)
        except Exception as e:
            return format_error("update_group", e)

    @mcp.tool()
    async def delete_group(
        group_id: str = Field(description="Group ID to delete."),
    ) -> dict:
        """Deletes a user group. Members are not removed from the workspace."""
        try:
            return await api_client.delete(f"/group/{group_id}")
        except Exception as e:
            return format_error("delete_group", e)

    @mcp.tool()
    async def get_list_members(
        list_name: str = Field(description="List name or ID."),
        folder_name: Optional[str] = Field(None, description="Folder name to scope lookup."),
        space_name: Optional[str] = Field(None, description="Space name to scope lookup."),
    ) -> dict:
        """Lists all members who have access to a specific list."""
        try:
            lst = await cache.resolve_list(list_name, folder_name, space_name)
            if not lst:
                return {"success": False, "error": f"List '{list_name}' not found."}
            return await api_client.get(f"/list/{lst['id']}/member")
        except Exception as e:
            return format_error("get_list_members", e)
