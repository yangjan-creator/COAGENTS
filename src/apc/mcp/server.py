"""MCP surface. Agents call the guarded COAGENTS API; they never receive SQL access."""

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("COAGENTS")
BASE_URL = os.environ.get("COAGENTS_API_URL", "http://127.0.0.1:8080")


def request(method: str, path: str, payload: dict | None = None) -> dict:
    response = httpx.request(method, f"{BASE_URL}{path}", json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def claim_work_item(item_id: str, actor: str) -> dict:
    """Claim one item. The claim becomes part of immutable history."""
    return request("POST", f"/items/{item_id}/claim", {"actor": actor})


@mcp.tool()
def report_progress(item_id: str, actor: str, message: str, status: str | None = None) -> dict:
    """Append progress. Gate completion, not this call, grants VERIFIED."""
    payload = {"actor": actor, "message": message}
    if status:
        payload["status"] = status
    return request("POST", f"/items/{item_id}/progress", payload)


@mcp.tool()
def create_delivery_version(item_id: str, actor: str, change_note: str, source_ref: str = "", source_sha256: str = "") -> dict:
    """Create immutable vN delivery linked to a code/artifact reference."""
    payload = {"actor": actor, "change_note": change_note, "source_ref": source_ref or None, "source_sha256": source_sha256 or None}
    return request("POST", f"/items/{item_id}/versions", payload)


@mcp.tool()
def project_history(project_id: str) -> list[dict]:
    """Read the append-only timeline used for PM integration and handoff."""
    return request("GET", f"/projects/{project_id}/history")


if __name__ == "__main__":
    mcp.run()
