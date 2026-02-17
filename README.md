# Odoo MCP Server

An MCP (Model Context Protocol) server that connects AI agents in Cursor to your Odoo instance. Tell your AI to "turn this PRD into tasks in Odoo" and it will create a full hierarchy of epics, tasks, and subtasks with tags, priorities, and assignments.

**No cloning required** — just configure and go.

## Quick Start

### 1. Install uv

[uv](https://github.com/astral-sh/uv) is a fast Python package manager that includes `uvx` for running tools directly from git repos.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Get Your Odoo API Key

1. Log into your Odoo instance
2. Go to **My Profile** (click your avatar → My Profile)
3. Navigate to **Preferences** → **Account Security**
4. Click **New API Key**, name it "Cursor MCP", and copy the key

### 3. Configure Cursor

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "/Users/YOUR_USERNAME/.local/bin/uvx",
      "args": [
        "--from",
        "git+https://github.com/willy5xx/odoo_mcp.git",
        "odoo-mcp"
      ],
      "env": {
        "ODOO_URL": "https://your-instance.odoo.com",
        "ODOO_DB": "your-database-name",
        "ODOO_USERNAME": "your-email@example.com",
        "ODOO_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Replace the placeholder values:**
- `YOUR_USERNAME` — your macOS username (run `whoami` to check)
- `ODOO_URL` — your Odoo instance URL (e.g., `https://mycompany.odoo.com`)
- `ODOO_DB` — your database name (often the subdomain, e.g., `mycompany`)
- `ODOO_USERNAME` — your Odoo login email
- `ODOO_API_KEY` — the API key you created in step 2

### 4. Restart Cursor

Quit and reopen Cursor for the MCP server to load.

### 6. Test It

In Cursor, ask your AI:

- *"Test the Odoo connection"*
- *"List my Odoo projects"*

If it works, you're all set!

---

## Important Notes

| Issue | Solution |
|-------|----------|
| **uvx not found** | Cursor can't find `uvx` via PATH. Always use the full absolute path: `/Users/YOUR_USERNAME/.local/bin/uvx` |
| **SSL certificate errors** | Usually handled automatically. If you're behind a corporate proxy, see [Troubleshooting](#ssl-errors) |
| **ODOO_URL format** | Use the base URL only (e.g., `https://mycompany.odoo.com`). Do NOT include `/odoo` or other paths |
| **Changes not taking effect** | Restart Cursor after editing `~/.cursor/mcp.json` |

---

## Usage Examples

Once configured, you can use natural language to manage Odoo:

```
"List my Odoo projects"

"Read @specs/feature-prd.md and create tasks in the 'Mobile App' project. 
 Break it into epics with subtasks, tag by feature area, and set priorities."

"Show me tasks in the Backend project and update the auth task to urgent priority"

"Create a new task in the API project: implement rate limiting for the /users endpoint"

"Add a subtask to task #123: write unit tests for the validation logic"
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `odoo_test_connection` | Verify credentials and connectivity |
| `odoo_list_projects` | List all projects with metadata |
| `odoo_create_project` | Create a new project |
| `odoo_update_project` | Update project fields (name, manager, active status) |
| `odoo_get_project_stages` | Get kanban stages for a project |
| `odoo_create_task` | Create a single task (supports subtasks via `parent_id`) |
| `odoo_create_tasks_batch` | Create multiple tasks at once |
| `odoo_list_tasks` | List tasks in a project |
| `odoo_update_task` | Update any field on an existing task |
| `odoo_post_task_message` | Post progress updates to task chatter |
| `odoo_search_users` | Find users by name/email for assignment |
| `odoo_list_tags` | List existing project tags |
| `odoo_create_milestone` | Create project milestones |
| `odoo_list_milestones` | List milestones in a project |
| `odoo_search_records` | Generic search on any Odoo model |
| `odoo_create_record` | Generic create on any Odoo model |
| `odoo_update_record` | Generic update for any Odoo model |
| `odoo_delete_record` | Generic delete for any Odoo model |

---

## How PRD → Tasks Works

When you ask your AI to turn a PRD into Odoo tasks:

1. **AI reads the PRD** from a file or pasted text
2. **Calls `odoo_list_projects`** to find the target project
3. **Calls `odoo_get_project_stages`** to understand the workflow
4. **Decomposes the PRD** into a task hierarchy:
   - Top-level tasks = epics / feature areas
   - Subtasks = individual work items
5. **Creates epics** via `odoo_create_task`, getting back IDs
6. **Creates subtasks** via `odoo_create_tasks_batch` with `parent_id` linking
7. **Tags are auto-created** if they don't exist

---

## Supported Odoo Versions

Works with any Odoo version that supports XML-RPC (12.0+):
- Odoo Community
- Odoo Enterprise
- Odoo.sh
- Odoo Online (SaaS)

---

## Troubleshooting

### Connection fails

1. Verify your credentials by logging into Odoo manually
2. Check that your API key is valid (regenerate if needed)
3. Ensure `ODOO_URL` doesn't have a trailing slash or `/odoo` path
4. Verify the database name matches exactly

### SSL errors

SSL certificates are handled automatically via the bundled `certifi` package. If you're behind a corporate proxy or firewall that intercepts SSL, add these environment variables to your config:

```json
"env": {
  "ODOO_URL": "...",
  "ODOO_DB": "...",
  "ODOO_USERNAME": "...",
  "ODOO_API_KEY": "...",
  "SSL_CERT_FILE": "/path/to/your/corporate-ca-bundle.pem",
  "REQUESTS_CA_BUNDLE": "/path/to/your/corporate-ca-bundle.pem"
}
```

To find your system's certificate bundle:

```bash
python3 -c "import certifi; print(certifi.where())"
```

### uvx errors

Verify uvx is installed and get the correct path:

```bash
which uvx
```

Use that exact path in your config.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ODOO_URL` | Yes | Your Odoo instance URL (base URL only) |
| `ODOO_DB` | Yes | Database name |
| `ODOO_USERNAME` | Yes | Login email |
| `ODOO_API_KEY` | Yes | API key (not password) |
| `SSL_CERT_FILE` | No | Path to CA certificate bundle (only for corporate proxies) |
| `REQUESTS_CA_BUNDLE` | No | Path to CA certificate bundle (only for corporate proxies) |
| `LOG_LEVEL` | No | `DEBUG`, `INFO` (default), `WARNING`, `ERROR` |

---

## License

MIT
