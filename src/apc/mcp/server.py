"""COAGENTS MCP: the same commands and permissions as the human workspace."""

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("COAGENTS")
BASE_URL = os.environ.get("COAGENTS_API_URL", "http://127.0.0.1:8310").rstrip("/")
ACTOR = os.environ.get("COAGENTS_ACTOR", "pm")


def request(method, path, payload=None):
    token = os.environ.get("COAGENTS_API_TOKEN", "")
    headers = {"Authorization": "Bearer " + token} if token else {}
    response = httpx.request(method, BASE_URL + path, json=payload, headers=headers, timeout=30)
    if response.is_error:
        raise ValueError(f"COAGENTS {response.status_code}: {response.json().get('detail')}")
    return response.json()


def command(path, payload):
    return request("POST", path, {"actor": ACTOR, **payload})


@mcp.tool()
def list_projects() -> list:
    """List projects visible to your authenticated identity."""
    return request("GET", "/projects")


@mcp.tool()
def workspace(project_id: str = "") -> dict:
    """Read tasks, current versions, gates, summaries, artifacts, teams and recent events."""
    return request("GET", "/workspace" + ("?project_id=" + project_id if project_id else ""))


@mcp.tool()
def create_team(slug: str, name: str) -> dict:
    """PM: create a team."""
    return command("/teams", {"slug": slug, "name": name})


@mcp.tool()
def register_member(member_actor: str, name: str, team_id: str, kind: str = "AGENT",
                    role: str = "CONTRIBUTOR") -> dict:
    """PM: register a human or agent with CONTRIBUTOR, REVIEWER or PM role."""
    return command("/members", dict(member_actor=member_actor, name=name, team_id=team_id,
                                    kind=kind, role=role))


@mcp.tool()
def create_project(team_id: str, key: str, name: str, team_ids: list[str] | None = None) -> dict:
    """PM: create a project shared by one or more teams."""
    return command("/projects", dict(team_id=team_id, key=key, name=name, team_ids=team_ids or []))


@mcp.tool()
def create_work_item(project_id: str, key: str, title: str, kind: str = "TASK",
                     description: str = "", parent_id: str = "", team_id: str = "") -> dict:
    """Expand a project into SUBPROJECT, FEATURE or TASK, optionally under a parent."""
    return command("/projects/" + project_id + "/items",
                   dict(key=key, title=title, kind=kind, description=description,
                        parent_id=parent_id or None, team_id=team_id or None))


@mcp.tool()
def claim_work_item(item_id: str) -> dict:
    """Claim an unowned item. Another member's claim is never overwritten."""
    return command("/items/" + item_id + "/claim", {})


@mcp.tool()
def report_progress(item_id: str, message: str, status: str = "WORKING",
                    progress_percent: int = 0) -> dict:
    """Owner: append progress or a BLOCKED/HOLD reason. Cannot set VERIFIED/CLOSED."""
    return command("/items/" + item_id + "/progress",
                   dict(message=message, status=status, progress_percent=progress_percent))


@mcp.tool()
def create_delivery_version(item_id: str, change_note: str, source_ref: str = "",
                            source_sha256: str = "") -> dict:
    """Owner/PM: create vN and link Git commit/PR/artifact identity; retains all older versions."""
    return command("/items/" + item_id + "/versions",
                   dict(change_note=change_note, source_ref=source_ref or None,
                        source_sha256=source_sha256 or None))


@mcp.tool()
def declare_validation_gate(version_id: str, name: str, required: bool = True) -> dict:
    """Reviewer/PM: declare what must be proved for this version."""
    return command("/versions/" + version_id + "/gates", dict(name=name, required=required))


@mcp.tool()
def record_validation_result(gate_id: str, status: str, message: str, evidence_uri: str,
                             evidence_sha256: str) -> dict:
    """Reviewer: PASSED/FAILED with evidence path and full SHA; PM may WAIVE with a reason."""
    return command("/gates/" + gate_id + "/result",
                   dict(status=status, message=message, evidence_uri=evidence_uri,
                        evidence_sha256=evidence_sha256))


@mcp.tool()
def add_dependency(item_id: str, depends_on_id: str) -> dict:
    """Declare a dependency between two items in this shared project. Cycles are rejected."""
    return command("/items/" + item_id + "/dependencies", {"depends_on_id": depends_on_id})


@mcp.tool()
def close_work_item(item_id: str) -> dict:
    """PM: close only an item with its current version and dependencies verified."""
    return command("/items/" + item_id + "/close", {})


@mcp.tool()
def update_project_overview(project_id: str, body_markdown: str) -> dict:
    """PM: save a new overview revision. Previous text remains in history."""
    return command("/projects/" + project_id + "/overview", {"body_markdown": body_markdown})


@mcp.tool()
def append_pm_summary(project_id: str, body_markdown: str, evidence_refs: list[str]) -> dict:
    """PM: append an integrated decision, blockers and next steps, citing evidence."""
    return command("/projects/" + project_id + "/pm-summaries",
                   dict(body_markdown=body_markdown, evidence_refs=evidence_refs))


@mcp.tool()
def register_artifact(project_id: str, path: str, sha256: str, bytes: int,
                      media_type: str, purpose: str, source_ref: str = "") -> dict:
    """Register a file locator, full SHA and size. No file upload, copying or deletion occurs."""
    return command("/projects/" + project_id + "/artifacts",
                   dict(path=path, sha256=sha256, bytes=bytes, media_type=media_type,
                        purpose=purpose, source_ref=source_ref or None))


@mcp.tool()
def link_artifact(artifact_id: str, ref_kind: str, ref_id: str) -> dict:
    """Link a registered artifact to a VERSION, GATE or SUMMARY in the same project."""
    return command("/artifacts/" + artifact_id + "/references",
                   dict(ref_kind=ref_kind, ref_id=ref_id))


@mcp.tool()
def artifact_deletion_check(artifact_id: str) -> dict:
    """Read registry protection/references. This does not inspect processes or delete files."""
    return request("GET", "/artifacts/" + artifact_id + "/deletion-check")


@mcp.tool()
def project_history(project_id: str) -> list:
    """Read all project events in chronological order."""
    return request("GET", "/projects/" + project_id + "/history")


@mcp.tool()
def item_history(item_id: str) -> dict:
    """Read every delivery version, gate and event for a work item."""
    return request("GET", "/items/" + item_id + "/history")


@mcp.tool()
def list_dashboard_templates() -> list:
    """Read saved templates and their complete revision history."""
    return request("GET", "/dashboard-templates")


@mcp.tool()
def save_dashboard_template(name: str, layout: dict, project_id: str = "") -> dict:
    """PM: create a template using validated metric/table/board/timeline/summary/artifacts widgets."""
    return command("/dashboard-templates", dict(name=name, layout=layout, project_id=project_id or None))


@mcp.tool()
def revise_dashboard_template(template_id: str, layout: dict) -> dict:
    """PM: save the next template revision; does not overwrite older layouts."""
    return command("/dashboard-templates/" + template_id + "/revisions", {"layout": layout})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
