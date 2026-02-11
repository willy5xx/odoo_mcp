"""Team-friendly diagnostics for Odoo MCP configuration."""

from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlparse

from odoo_mcp.client import OdooClient


def _mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _validate_url(url: str) -> list[str]:
    warnings: list[str] = []
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        warnings.append("ODOO_URL should be a full URL like https://company.odoo.com")
    if "/odoo" in parsed.path:
        warnings.append("ODOO_URL should be the base host; remove '/odoo' from the URL")
    return warnings


def main() -> None:
    required = ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_API_KEY"]
    env = {k: os.environ.get(k, "") for k in required}
    missing = [k for k, v in env.items() if not v]

    print("Odoo MCP Doctor")
    print("=" * 60)
    print(
        json.dumps(
            {
                "ODOO_URL": env["ODOO_URL"],
                "ODOO_DB": env["ODOO_DB"],
                "ODOO_USERNAME": env["ODOO_USERNAME"],
                "ODOO_API_KEY": _mask_secret(env["ODOO_API_KEY"])
                if env["ODOO_API_KEY"]
                else "",
            },
            indent=2,
        )
    )

    if missing:
        print(f"\nERROR: Missing required env vars: {', '.join(missing)}")
        sys.exit(1)

    url_warnings = _validate_url(env["ODOO_URL"])
    if url_warnings:
        print("\nURL Warnings:")
        for warning in url_warnings:
            print(f"- {warning}")

    try:
        client = OdooClient()
        version = client.version()
        projects = client.list_projects(active_only=True)
        output = {
            "status": "connected",
            "uid": client.uid,
            "server_version": version.get("server_version"),
            "active_projects": len(projects),
        }
        print("\nConnection Check:")
        print(json.dumps(output, indent=2))
    except Exception as exc:  # noqa: BLE001 - doctor should catch and explain all failures
        print("\nERROR: Connection check failed")
        print(f"{type(exc).__name__}: {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()
