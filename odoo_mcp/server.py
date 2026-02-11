"""Odoo MCP Server.

Exposes Odoo project management operations as MCP tools so that an AI
assistant (Claude in Cursor) can read PRDs and turn them into actionable
Odoo tasks, epics, and subtasks.

Run directly:  python -m odoo_mcp.server
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from odoo_mcp.client import OdooClient

# ── Logging ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("odoo_mcp")

# ── MCP app ─────────────────────────────────────────────────────────

mcp = FastMCP(
    "odoo",
    instructions=(
        "Odoo Project Management MCP server. Use these tools to create and "
        "manage tasks in Odoo. A typical workflow: list_projects → "
        "get_project_stages → create tasks (with parent_id for subtasks). "
        "When turning a PRD into tasks, create parent tasks as epics first, "
        "then create subtasks under them using parent_id."
    ),
)

# Lazy-initialized client (created on first tool call)
_client: OdooClient | None = None


def get_client() -> OdooClient:
    """Return (and lazily create) the Odoo client singleton."""
    global _client
    if _client is None:
        _client = OdooClient()
    return _client


# ── Helper ──────────────────────────────────────────────────────────


def _fmt(obj: Any) -> str:
    """Pretty-format a result for the LLM."""
    return json.dumps(obj, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════


# ── Connection ──────────────────────────────────────────────────────


@mcp.tool()
def odoo_test_connection() -> str:
    """Test the Odoo connection and return server version info.

    Call this first to verify credentials are working.
    """
    client = get_client()
    version = client.version()
    # Also trigger auth to validate credentials
    uid = client.uid
    return _fmt(
        {
            "status": "connected",
            "uid": uid,
            "server_version": version.get("server_version"),
            "url": client.url,
        }
    )


# ── Projects ────────────────────────────────────────────────────────


@mcp.tool()
def odoo_list_projects(active_only: bool = True) -> str:
    """List all projects in Odoo.

    Returns project id, name, manager, and task count.
    Use this to find the right project_id before creating tasks.

    Args:
        active_only: Only return active (non-archived) projects. Default True.
    """
    projects = get_client().list_projects(active_only=active_only)
    return _fmt(projects)


@mcp.tool()
def odoo_get_project_stages(project_id: int) -> str:
    """Get the kanban stages (columns) for a project.

    Returns stage id, name, and sequence order.
    Use this to understand the workflow and set the right stage_id on tasks.

    Args:
        project_id: The Odoo project ID.
    """
    stages = get_client().get_project_stages(project_id)
    return _fmt(stages)


# ── Tasks ───────────────────────────────────────────────────────────


@mcp.tool()
def odoo_create_task(
    project_id: int,
    name: str,
    description: str = "",
    priority: str = "0",
    stage_id: int | None = None,
    tag_names: list[str] | None = None,
    user_ids: list[int] | None = None,
    parent_id: int | None = None,
    planned_hours: float | None = None,
) -> str:
    """Create a single task in an Odoo project.

    For subtasks, set parent_id to the ID of the parent task.
    For epics, create a task first, then create subtasks under it.

    Args:
        project_id: The project to create the task in.
        name: Task title / summary.
        description: Detailed description. Supports HTML for rich formatting.
        priority: '0' = Normal, '1' = Important, '2' = Urgent.
        stage_id: Stage/column ID. If omitted, uses the project's default stage.
        tag_names: List of tag names (e.g. ["backend", "auth"]). Tags are
                   created automatically if they don't exist.
        user_ids: List of user IDs to assign. Use odoo_search_users to find IDs.
        parent_id: Parent task ID to create this as a subtask.
        planned_hours: Estimated hours for the task.
    """
    client = get_client()

    # Resolve tag names to IDs
    tag_ids = None
    if tag_names:
        tag_ids = client.find_or_create_tags(tag_names)

    task_id = client.create_task(
        project_id=project_id,
        name=name,
        description=description,
        priority=priority,
        stage_id=stage_id,
        tag_ids=tag_ids,
        user_ids=user_ids,
        parent_id=parent_id,
        planned_hours=planned_hours,
    )

    return _fmt({"id": task_id, "name": name, "project_id": project_id})


@mcp.tool()
def odoo_create_tasks_batch(
    project_id: int,
    tasks: list[dict],
) -> str:
    """Create multiple tasks in a project at once.

    This is the primary tool for turning a PRD into actionable items. Pass a
    list of task definitions. To create a hierarchy, first create parent tasks,
    note their returned IDs, then create subtasks referencing parent_id.

    Each task dict supports these keys:
        - name (required): Task title
        - description: Detailed description (HTML ok)
        - priority: '0'=Normal, '1'=Important, '2'=Urgent
        - stage_id: Kanban stage ID
        - tag_names: List of tag name strings
        - user_ids: List of assignee user IDs
        - parent_id: Parent task ID for subtasks
        - planned_hours: Estimated hours

    Args:
        project_id: The project to create all tasks in.
        tasks: List of task definition dicts.

    Returns:
        List of created task objects with their IDs.
    """
    client = get_client()
    results = []

    for task_def in tasks:
        tag_names = task_def.pop("tag_names", None)
        tag_ids = None
        if tag_names:
            tag_ids = client.find_or_create_tags(tag_names)

        task_id = client.create_task(
            project_id=project_id,
            tag_ids=tag_ids,
            **task_def,
        )
        results.append({"id": task_id, "name": task_def["name"]})

    return _fmt({"created": len(results), "tasks": results})


@mcp.tool()
def odoo_list_tasks(
    project_id: int,
    stage_id: int | None = None,
    limit: int = 100,
) -> str:
    """List tasks in a project, optionally filtered by stage.

    Args:
        project_id: The project ID.
        stage_id: Optional stage ID to filter by.
        limit: Max tasks to return (default 100).
    """
    tasks = get_client().list_tasks(
        project_id=project_id, stage_id=stage_id, limit=limit
    )
    return _fmt(tasks)


@mcp.tool()
def odoo_update_task(
    task_id: int,
    name: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    stage_id: int | None = None,
    tag_names: list[str] | None = None,
    user_ids: list[int] | None = None,
    parent_id: int | None = None,
    planned_hours: float | None = None,
    date_deadline: str | None = None,
) -> str:
    """Update an existing task.

    Only the fields you provide will be changed; others are left untouched.

    Args:
        task_id: The task ID to update.
        name: New task title.
        description: New description (HTML ok).
        priority: '0'=Normal, '1'=Important, '2'=Urgent.
        stage_id: Move to this stage.
        tag_names: Replace tags with these (creates if needed).
        user_ids: Replace assignees with these user IDs.
        parent_id: Set or change parent task.
        planned_hours: Update estimated hours.
        date_deadline: Deadline in 'YYYY-MM-DD' format.
    """
    client = get_client()
    vals: dict[str, Any] = {}

    if name is not None:
        vals["name"] = name
    if description is not None:
        vals["description"] = description
    if priority is not None:
        vals["priority"] = priority
    if stage_id is not None:
        vals["stage_id"] = stage_id
    if parent_id is not None:
        vals["parent_id"] = parent_id
    if planned_hours is not None:
        vals["planned_hours"] = planned_hours
    if date_deadline is not None:
        vals["date_deadline"] = date_deadline
    if tag_names is not None:
        tag_ids = client.find_or_create_tags(tag_names)
        vals["tag_ids"] = [(6, 0, tag_ids)]
    if user_ids is not None:
        vals["user_ids"] = [(6, 0, user_ids)]

    if not vals:
        return _fmt({"error": "No fields provided to update"})

    client.update_task(task_id, vals)
    return _fmt({"updated": True, "task_id": task_id, "fields_changed": list(vals.keys())})


# ── Users ───────────────────────────────────────────────────────────


@mcp.tool()
def odoo_search_users(query: str = "") -> str:
    """Search for internal Odoo users by name or email.

    Use this to find user IDs before assigning tasks.

    Args:
        query: Search term to match against name or email. Leave empty
               to list all internal users.
    """
    users = get_client().search_users(query=query)
    return _fmt(users)


# ── Tags ────────────────────────────────────────────────────────────


@mcp.tool()
def odoo_list_tags() -> str:
    """List all existing project tags.

    Useful to see what tags already exist before creating tasks.
    """
    tags = get_client().search_read(
        "project.tags",
        fields=["id", "name", "color"],
        order="name asc",
    )
    return _fmt(tags)


# ── Generic record access ──────────────────────────────────────────


@mcp.tool()
def odoo_search_records(
    model: str,
    domain: list | None = None,
    fields: list[str] | None = None,
    limit: int = 50,
    order: str | None = None,
) -> str:
    """Search any Odoo model. For advanced use cases beyond projects/tasks.

    Common models:
        - project.project: Projects
        - project.task: Tasks
        - project.task.type: Task stages
        - project.tags: Project tags
        - res.users: Users
        - res.partner: Contacts
        - project.milestone: Milestones

    Args:
        model: The Odoo model name (e.g. 'project.task').
        domain: Odoo domain filter list (e.g. [['name', 'ilike', 'auth']]).
                Defaults to [] (all records).
        fields: List of field names to return. Defaults to all fields.
        limit: Max records to return (default 50).
        order: Sort order (e.g. 'name asc', 'create_date desc').
    """
    records = get_client().search_read(
        model, domain=domain, fields=fields, limit=limit, order=order
    )
    return _fmt(records)


@mcp.tool()
def odoo_create_record(model: str, values: dict) -> str:
    """Create a record in any Odoo model. For advanced use cases.

    Args:
        model: The Odoo model name.
        values: Dict of field values to set.
    """
    record_id = get_client().create(model, values)
    return _fmt({"id": record_id, "model": model})


# ── Milestones ──────────────────────────────────────────────────────


@mcp.tool()
def odoo_create_milestone(
    project_id: int,
    name: str,
    deadline: str | None = None,
) -> str:
    """Create a project milestone.

    Milestones can be assigned to tasks to group them into phases/releases.

    Args:
        project_id: The project ID.
        name: Milestone name (e.g. "Phase 1 - MVP").
        deadline: Optional deadline in 'YYYY-MM-DD' format.
    """
    vals: dict[str, Any] = {"name": name, "project_id": project_id}
    if deadline:
        vals["deadline"] = deadline

    mid = get_client().create("project.milestone", vals)
    return _fmt({"id": mid, "name": name, "project_id": project_id})


@mcp.tool()
def odoo_list_milestones(project_id: int) -> str:
    """List milestones for a project.

    Args:
        project_id: The project ID.
    """
    milestones = get_client().search_read(
        "project.milestone",
        domain=[["project_id", "=", project_id]],
        fields=["id", "name", "deadline", "is_reached"],
        order="deadline asc, id asc",
    )
    return _fmt(milestones)


# ═══════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════


def main() -> None:
    """Run the MCP server over stdio."""
    logger.info("Starting Odoo MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
