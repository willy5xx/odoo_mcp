# Team Rollout Guide

Use this guide to onboard teammates to Odoo MCP in 5-10 minutes.

## 1) Install

```bash
git clone <your-repo-url>
cd odoo-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2) Configure Env Vars

Create a local `.env` file from `.env.example` and fill in:

- `ODOO_URL` (base host like `https://company.odoo.com`)
- `ODOO_DB` (database name, not URL)
- `ODOO_USERNAME` (Odoo login email)
- `ODOO_API_KEY` (Odoo API key)

## 3) Validate Credentials Locally

```bash
set -a
source .env
set +a
odoo-mcp-doctor
```

Expected: `status: connected` and a valid `uid`.

## 4) Configure Cursor

In `~/.cursor/mcp.json`, add:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "/absolute/path/to/odoo-mcp/.venv/bin/odoo-mcp",
      "env": {
        "ODOO_URL": "https://company.odoo.com",
        "ODOO_DB": "company",
        "ODOO_USERNAME": "name@company.com",
        "ODOO_API_KEY": "your-key-here",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Then restart Cursor.

## 5) Smoke Test in Cursor Chat

Run:

1. `odoo_test_connection`
2. `odoo_list_projects`
3. `odoo_list_tasks` for a known project
4. `odoo_create_task` in a non-production project
5. `odoo_update_task` and `odoo_post_task_message`

## 6) Team Usage Pattern

- Start with `odoo_test_connection` once per day/session
- Use `odoo_list_projects` to discover project IDs
- Use `odoo_get_project_stages` before task automation
- Use `odoo_create_tasks_batch` for PRD decomposition
- Use `odoo_post_task_message` for progress updates

## Troubleshooting

- Auth failures: verify API key and user has project permissions
- `ODOO_DB` errors: ensure DB name, not URL
- URL errors: remove `/odoo` path from `ODOO_URL`
- Tool mismatch after updates: restart Cursor
