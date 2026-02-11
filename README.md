# Odoo MCP Server

An MCP (Model Context Protocol) server that connects Claude in Cursor to your Odoo instance. Tell Claude to "turn this PRD into tasks in Odoo" and it will create a full hierarchy of epics, tasks, and subtasks with tags, priorities, and assignments.

## Quick Start

### 1. Install

```bash
cd odoo-mcp
pip install -e .
```

Or with a virtual environment:

```bash
cd odoo-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Get Your Odoo API Key

1. Log into your Odoo instance
2. Go to **Settings → Users & Companies → Users**
3. Click your user → **Preferences** tab
4. Under **Account Security**, click **New API Key**
5. Name it "Cursor MCP" and copy the key

### 3. Configure Cursor

Add this to your `.cursor/mcp.json` (create it if it doesn't exist):

```json
{
  "mcpServers": {
    "odoo": {
      "command": "odoo-mcp",
      "env": {
        "ODOO_URL": "https://mycompany.odoo.com",
        "ODOO_DB": "mycompany-main",
        "ODOO_USERNAME": "admin@mycompany.com",
        "ODOO_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

> **Using a venv?** Point the command to the venv's Python:
> ```json
> {
>   "command": "/path/to/odoo-mcp/.venv/bin/odoo-mcp"
> }
> ```

### 4. Use It

Restart Cursor, then try prompts like:

- *"List my Odoo projects"*
- *"Read @specs/bright-blue-rewards-prd.md and create tasks in the 'Mobile App' project in Odoo. Break it into epics with subtasks, tag by feature area, and set priorities."*
- *"Show me the current tasks in the Backend project and update the auth task to urgent priority"*

## Available Tools

| Tool | Description |
|------|-------------|
| `odoo_test_connection` | Verify credentials and connectivity |
| `odoo_list_projects` | List all projects with metadata |
| `odoo_get_project_stages` | Get kanban stages for a project |
| `odoo_create_task` | Create a single task (supports subtasks via `parent_id`) |
| `odoo_create_tasks_batch` | Create multiple tasks at once |
| `odoo_list_tasks` | List tasks in a project |
| `odoo_update_task` | Update any field on an existing task |
| `odoo_search_users` | Find users by name/email for assignment |
| `odoo_list_tags` | List existing project tags |
| `odoo_create_milestone` | Create project milestones for phasing |
| `odoo_list_milestones` | List milestones in a project |
| `odoo_search_records` | Generic search on any Odoo model |
| `odoo_create_record` | Generic create on any Odoo model |

## How PRD → Tasks Works

When you ask Claude to turn a PRD into Odoo tasks, here's the flow:

1. **Claude reads the PRD** from a file or pasted text
2. **Calls `odoo_list_projects`** to find (or confirm) the target project
3. **Calls `odoo_get_project_stages`** to understand the workflow
4. **Decomposes the PRD** into a task hierarchy using its reasoning:
   - Top-level tasks = epics / feature areas
   - Subtasks = individual work items
5. **Calls `odoo_create_task`** for each epic, getting back IDs
6. **Calls `odoo_create_tasks_batch`** for subtasks, using `parent_id` to link them
7. Tags are auto-created if they don't exist

## Architecture

```
Cursor (Claude) ──MCP stdio──► odoo-mcp server ──XML-RPC──► Odoo
                                    │
                               odoo_mcp/
                               ├── server.py   (MCP tools)
                               ├── client.py   (Odoo API wrapper)
                               └── __main__.py  (entrypoint)
```

The server uses Odoo's standard XML-RPC API (`/xmlrpc/2/common` and `/xmlrpc/2/object`), which is stable across Odoo versions 12+. No special Odoo modules or plugins needed.

## Supported Odoo Versions

Works with any Odoo version that supports XML-RPC (12.0+), including:
- Odoo Community
- Odoo Enterprise
- Odoo.sh
- Odoo Online (SaaS)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ODOO_URL` | Yes | Your Odoo instance URL |
| `ODOO_DB` | Yes | Database name |
| `ODOO_USERNAME` | Yes | Login email |
| `ODOO_API_KEY` | Yes | API key (not password) |
| `LOG_LEVEL` | No | `DEBUG`, `INFO` (default), `WARNING`, `ERROR` |

## Development

```bash
# Install in dev mode
pip install -e .

# Run directly
python -m odoo_mcp

# Test connection
ODOO_URL=... ODOO_DB=... ODOO_USERNAME=... ODOO_API_KEY=... python -c "
from odoo_mcp.client import OdooClient
c = OdooClient()
print(c.version())
print('uid:', c.uid)
print('projects:', c.list_projects())
"
```

## License

MIT
