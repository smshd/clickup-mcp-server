# clickup-mcp-server

A Python MCP (Model Context Protocol) server for ClickUp. Built and used internally by Smashed Avo. Published publicly so our other systems and the community can use or fork it.

## Why this one?

Three things this server does that other open-source ClickUp MCPs don't (as of May 2026):

- **Accepts names, not IDs.** Pass "Acme Corp / Backlog" instead of hunting workspace/space/folder/list IDs. Works for spaces, folders, lists, members, and tags.
- **Rich-text comments.** Posts and edits comments with formatting (bold, links, mentions). The official ClickUp cloud MCP is plain-text only.
- **Around 140 tools covering full CRUD** across tasks, comments, time tracking, custom fields, dependencies, attachments, webhooks, goals, docs, and the full workspace hierarchy.

Also: natural-language dates ("tomorrow at 9am"), structured error responses with hint fields, and a hierarchy cache to avoid hammering the ClickUp API.

## Comparison

| Server | Tools | Name lookups | Rich comments | Licence |
|---|---|---|---|---|
| **This one** | ~140 | Yes | Yes | MIT |
| taazkareem (free) | ~15 | Partial | Partial | MIT |
| taazkareem (premium) | ~150 | Yes | Yes | Proprietary, paid |
| hauptsacheNet | 13 | Partial | Unconfirmed | MIT |
| Nazruden | 30+ | No | No | MIT |
| Official ClickUp cloud | varies | ? | Yes | OAuth, 50 calls/day free |

## Install — Claude Code (Windows / macOS / Linux)

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/), a ClickUp personal API token.

```bash
# 1. Clone the repo
git clone https://github.com/smshd/clickup-mcp-server.git
cd clickup-mcp-server

# 2. Install dependencies
uv sync

# 3. Create your .env
cp .env.example .env
# Edit .env: add your CLICKUP_API_TOKEN and CLICKUP_TEAM_ID
```

**Get your API token:** ClickUp settings (gear icon) > Apps > ClickUp API > Generate or Regenerate.

**Get your team ID:** Open any ClickUp URL. The number after `app.clickup.com/` is your team/workspace ID.

**Wire into Claude Code** by adding to your project `.mcp.json` (or `~/.claude/claude_desktop_config.json` for global):

```json
{
  "mcpServers": {
    "clickup": {
      "command": "uv",
      "args": ["run", "--project", "/absolute/path/to/clickup-mcp-server", "python", "server.py"],
      "env": {
        "CLICKUP_API_TOKEN": "pk_your_token_here",
        "CLICKUP_TEAM_ID": "12345678"
      }
    }
  }
}
```

Restart Claude Code after editing the config. Run `/mcp` in Claude Code to confirm the server is connected and list available tools.

## Install — Hermes / server-resident agents (Linux)

This section is for anyone running this MCP on a Linux server as part of a long-running agent (Hermes, OpenClaw, a custom MCP gateway, etc).

```bash
# Install uv if not already present
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env  # or restart shell

# Clone and install
git clone https://github.com/smshd/clickup-mcp-server.git /opt/clickup-mcp-server
cd /opt/clickup-mcp-server
uv sync

# Set env vars (or use a .env file)
export CLICKUP_API_TOKEN=pk_your_token_here
export CLICKUP_TEAM_ID=12345678

# Test the server starts
uv run python server.py
# Should print startup output and wait for MCP input on stdin
```

**Wiring into an MCP-compatible client via stdio transport:**

The server uses stdio transport (stdin/stdout). Your MCP client should launch it as a subprocess. The launch command is:

```
uv run --project /opt/clickup-mcp-server python /opt/clickup-mcp-server/server.py
```

**Systemd unit example** (keeps the server available as a managed process; useful if your agent framework expects a long-running MCP process):

```ini
[Unit]
Description=ClickUp MCP Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/clickup-mcp-server
Environment=CLICKUP_API_TOKEN=pk_your_token_here
Environment=CLICKUP_TEAM_ID=12345678
ExecStart=/root/.cargo/bin/uv run python server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable clickup-mcp
sudo systemctl start clickup-mcp
```

**Where to look in the source:**

- `server.py` — entry point; tool registration
- `tools/` — one file per tool group (tasks, comments, hierarchy, time_tracking, etc.)
- `cache.py` — workspace hierarchy cache; refresh interval set by `CACHE_TTL_SECONDS`
- `api_client.py` — thin wrapper around httpx for ClickUp REST API calls

## Configuration

Required env vars:

- `CLICKUP_API_TOKEN` — generate at: ClickUp > Workspace Settings > Apps > ClickUp API > Regenerate
- `CLICKUP_TEAM_ID` — your workspace ID; visible in any ClickUp URL: `app.clickup.com/<TEAM_ID>/...`

Optional:

- `CACHE_TTL_SECONDS` (default 300) — how long before the workspace hierarchy cache is refreshed

## Status

Internal Smashed Avo tool. Maintained as needed for our own use. Pull requests are welcome but not guaranteed to be reviewed promptly. See DISCLAIMER.md.
