"""Odoo XML-RPC client wrapper.

Provides a clean interface over Odoo's XML-RPC API for common operations
on projects, tasks, users, tags, and generic records.
"""

from __future__ import annotations

import logging
import os
import xmlrpc.client
from typing import Any

logger = logging.getLogger(__name__)


class OdooClient:
    """Stateful wrapper around Odoo's XML-RPC endpoints."""

    def __init__(
        self,
        url: str | None = None,
        db: str | None = None,
        username: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.url = (url or os.environ.get("ODOO_URL", "")).rstrip("/")
        self.db = db or os.environ.get("ODOO_DB", "")
        self.username = username or os.environ.get("ODOO_USERNAME", "")
        self.api_key = api_key or os.environ.get("ODOO_API_KEY", "")

        if not all([self.url, self.db, self.username, self.api_key]):
            raise ValueError(
                "Missing Odoo connection details. Set ODOO_URL, ODOO_DB, "
                "ODOO_USERNAME, and ODOO_API_KEY environment variables."
            )

        self._common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common", allow_none=True
        )
        self._models = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object", allow_none=True
        )
        self._uid: int | None = None

    # ── Authentication ──────────────────────────────────────────────

    @property
    def uid(self) -> int:
        """Authenticate lazily and cache the uid."""
        if self._uid is None:
            self._uid = self._common.authenticate(
                self.db, self.username, self.api_key, {}
            )
            if not self._uid:
                raise ConnectionError(
                    f"Odoo authentication failed for {self.username}@{self.url}"
                )
            logger.info("Authenticated as uid=%s on %s", self._uid, self.url)
        return self._uid

    def version(self) -> dict:
        """Return the Odoo server version info."""
        return self._common.version()

    # ── Low-level execute_kw wrapper ────────────────────────────────

    def execute(
        self,
        model: str,
        method: str,
        args: list | None = None,
        kwargs: dict | None = None,
    ) -> Any:
        """Call execute_kw on the Odoo object endpoint."""
        return self._models.execute_kw(
            self.db,
            self.uid,
            self.api_key,
            model,
            method,
            args or [],
            kwargs or {},
        )

    # ── Generic CRUD helpers ────────────────────────────────────────

    def search_read(
        self,
        model: str,
        domain: list | None = None,
        fields: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict]:
        """Search and read records in one call."""
        kw: dict[str, Any] = {"limit": limit, "offset": offset}
        if fields:
            kw["fields"] = fields
        if order:
            kw["order"] = order
        return self.execute(model, "search_read", [domain or []], kw)

    def create(self, model: str, values: dict) -> int:
        """Create a single record, returning its ID."""
        return self.execute(model, "create", [values])

    def write(self, model: str, record_ids: list[int], values: dict) -> bool:
        """Update one or more records."""
        return self.execute(model, "write", [record_ids, values])

    def unlink(self, model: str, record_ids: list[int]) -> bool:
        """Delete one or more records."""
        return self.execute(model, "unlink", [record_ids])

    def read(
        self, model: str, record_ids: list[int], fields: list[str] | None = None
    ) -> list[dict]:
        """Read specific records by ID."""
        kw = {}
        if fields:
            kw["fields"] = fields
        return self.execute(model, "read", [record_ids], kw)

    # ── Project helpers ─────────────────────────────────────────────

    def list_projects(self, active_only: bool = True) -> list[dict]:
        """List projects with key metadata."""
        domain: list = []
        if active_only:
            domain.append(["active", "=", True])
        return self.search_read(
            "project.project",
            domain=domain,
            fields=["id", "name", "user_id", "partner_id", "tag_ids", "task_count"],
            order="name asc",
        )

    def get_project_stages(self, project_id: int) -> list[dict]:
        """Return the task stages (kanban columns) for a project."""
        return self.search_read(
            "project.task.type",
            domain=[["project_ids", "in", [project_id]]],
            fields=["id", "name", "sequence", "fold"],
            order="sequence asc",
        )

    # ── Task helpers ────────────────────────────────────────────────

    def create_task(
        self,
        project_id: int,
        name: str,
        description: str = "",
        priority: str = "0",
        stage_id: int | None = None,
        tag_ids: list[int] | None = None,
        user_ids: list[int] | None = None,
        parent_id: int | None = None,
        planned_hours: float | None = None,
    ) -> int:
        """Create a project task and return its ID."""
        vals: dict[str, Any] = {
            "name": name,
            "project_id": project_id,
            "priority": priority,
        }
        if description:
            vals["description"] = description
        if stage_id:
            vals["stage_id"] = stage_id
        if parent_id:
            vals["parent_id"] = parent_id
        if planned_hours is not None:
            vals["planned_hours"] = planned_hours
        if tag_ids:
            vals["tag_ids"] = [(6, 0, tag_ids)]
        if user_ids:
            vals["user_ids"] = [(6, 0, user_ids)]
        return self.create("project.task", vals)

    def list_tasks(
        self,
        project_id: int,
        stage_id: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List tasks in a project, optionally filtered by stage."""
        domain: list = [["project_id", "=", project_id]]
        if stage_id:
            domain.append(["stage_id", "=", stage_id])
        return self.search_read(
            "project.task",
            domain=domain,
            fields=[
                "id",
                "name",
                "stage_id",
                "priority",
                "user_ids",
                "tag_ids",
                "parent_id",
                "child_ids",
                "planned_hours",
                "date_deadline",
            ],
            limit=limit,
            order="sequence asc, id asc",
        )

    def update_task(self, task_id: int, values: dict) -> bool:
        """Update a task by ID."""
        return self.write("project.task", [task_id], values)

    # ── Tag helpers ─────────────────────────────────────────────────

    def find_or_create_tags(self, tag_names: list[str]) -> list[int]:
        """Resolve tag names to IDs, creating any that don't exist."""
        if not tag_names:
            return []

        existing = self.search_read(
            "project.tags",
            domain=[["name", "in", tag_names]],
            fields=["id", "name"],
        )
        existing_map = {t["name"].lower(): t["id"] for t in existing}

        tag_ids = []
        for name in tag_names:
            tid = existing_map.get(name.lower())
            if tid:
                tag_ids.append(tid)
            else:
                tid = self.create("project.tags", {"name": name})
                tag_ids.append(tid)
        return tag_ids

    # ── User helpers ────────────────────────────────────────────────

    def search_users(self, query: str = "", limit: int = 20) -> list[dict]:
        """Search internal users by name or email."""
        domain: list = [["share", "=", False]]
        if query:
            domain = [
                "&",
                ["share", "=", False],
                "|",
                ["name", "ilike", query],
                ["email", "ilike", query],
            ]
        return self.search_read(
            "res.users",
            domain=domain,
            fields=["id", "name", "email"],
            limit=limit,
            order="name asc",
        )
