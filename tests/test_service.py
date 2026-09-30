import pytest
from fastapi.testclient import TestClient

from apc.api import DEFAULT_LAYOUT, create_app


@pytest.fixture
def client():
    # Every test gets its own database; no filesystem copies or import-time globals.
    with TestClient(create_app("sqlite:///:memory:", admin_token="")) as client:
        yield client


def post(client, path, body=None, actor="pm"):
    response = client.post(path, json={"actor": actor, **(body or {})})
    assert response.status_code < 300, response.text
    return response.json()


def setup(client, claim=True):
    yu = post(client, "/teams", {"slug": "yu", "name": "羽"})
    si = post(client, "/teams", {"slug": "si", "name": "思"})
    for actor, role, team in [("yu", "CONTRIBUTOR", yu), ("si", "CONTRIBUTOR", si),
                               ("review", "REVIEWER", yu)]:
        post(client, "/members", dict(member_actor=actor, name=actor, team_id=team["id"],
                                      kind="AGENT", role=role))
    project = post(client, "/projects", dict(team_id=yu["id"], team_ids=[si["id"]],
                                            key="APP", name="Shared"))
    item = post(client, f"/projects/{project['id']}/items",
                {"key": "APP-1", "title": "First feature", "kind": "FEATURE"})
    if claim:
        post(client, f"/items/{item['id']}/claim", actor="yu")
    return yu, si, project, item


def gate(client, item, actor="yu"):
    version = post(client, f"/items/{item['id']}/versions", {"change_note": "Delivery"}, actor)
    gate = post(client, f"/versions/{version['id']}/gates", {"name": "Source alignment"})
    return version, gate


def result(client, gate, status="PASSED", actor="review"):
    return client.post(f"/gates/{gate['id']}/result", json={
        "actor": actor, "status": status, "evidence_uri": "/evidence/check.json",
        "evidence_sha256": "a" * 64, "message": "Independently checked",
    })


def test_new_version_keeps_old_gate_results_out_of_current_state(client):
    _, _, _, item = setup(client)
    v1, g1 = gate(client, item)
    v2, g2 = gate(client, item)
    assert result(client, g1).status_code == 200
    history = client.get(f"/items/{item['id']}/history").json()
    assert history["item"]["current_version_id"] == v2["id"]
    assert history["item"]["status"] == "WORKING"
    assert history["versions"][0]["state"] == "VERIFIED"
    assert result(client, g2).status_code == 200
    assert result(client, g1, "FAILED").status_code == 409
    history = client.get(f"/items/{item['id']}/history").json()
    assert history["item"]["status"] == "VERIFIED"
    assert {row["ordinal"] for row in history["versions"]} == {1, 2}


def test_failed_required_gate_is_not_erased_by_later_pass(client):
    _, _, _, item = setup(client)
    version, first = gate(client, item)
    second = post(client, f"/versions/{version['id']}/gates", {"name": "Additional check"})
    assert result(client, first, "FAILED").status_code == 200
    assert result(client, second).status_code == 200
    assert client.get(f"/items/{item['id']}").json()["status"] == "BLOCKED"


def test_claim_cannot_be_stolen_and_progress_cannot_self_verify(client):
    _, _, _, item = setup(client)
    assert client.post(f"/items/{item['id']}/claim", json={"actor": "si"}).status_code in {403, 409}
    assert client.post(f"/items/{item['id']}/progress", json={
        "actor": "yu", "message": "done", "status": "VERIFIED",
    }).status_code == 422
    version, first = gate(client, item, actor="pm")
    assert result(client, first, actor="pm").status_code == 403
    assert client.post(f"/gates/{first['id']}/result", json={
        "actor": "review", "status": "PASSED", "message": "no evidence",
    }).status_code == 422
    assert client.post(f"/items/{item['id']}/close", json={"actor": "pm"}).status_code == 409


def test_dependencies_are_acyclic_and_required_for_closure(client):
    _, _, project, item = setup(client)
    other = post(client, f"/projects/{project['id']}/items",
                 {"key": "APP-2", "title": "Blocking task"})
    post(client, f"/items/{item['id']}/dependencies", {"depends_on_id": other["id"]})
    assert client.post(f"/items/{other['id']}/dependencies", json={
        "actor": "pm", "depends_on_id": item["id"],
    }).status_code == 409
    _, check = gate(client, item)
    assert result(client, check).status_code == 200
    assert client.post(f"/items/{item['id']}/close", json={"actor": "pm"}).status_code == 409
    _, check2 = gate(client, other, "pm")
    assert result(client, check2).status_code == 200
    assert post(client, f"/items/{item['id']}/close")["status"] == "CLOSED"


def test_artifact_protection_and_reference_ownership(client):
    _, _, project, item = setup(client)
    def artifact(purpose, path):
        return post(client, f"/projects/{project['id']}/artifacts", {
            "path": path, "sha256": "b" * 64, "bytes": 5_000_000_000,
            "media_type": "application/x-sqlite3", "purpose": purpose,
        })
    protected = artifact("ROLLBACK_POINT", "/mnt/d/rollback.sqlite3")
    assert not client.get(f"/artifacts/{protected['id']}/deletion-check").json()["allowed"]
    ephemeral = artifact("VERIFIED_EPHEMERAL", "/mnt/d/temp.sqlite3")
    assert client.get(f"/artifacts/{ephemeral['id']}/deletion-check").json()["allowed"]
    version, _ = gate(client, item)
    post(client, f"/artifacts/{ephemeral['id']}/references",
         {"ref_kind": "VERSION", "ref_id": version["id"]})
    assert not client.get(f"/artifacts/{ephemeral['id']}/deletion-check").json()["allowed"]
    assert client.post(f"/artifacts/{ephemeral['id']}/deleted",
                       json={"actor": "pm", "message": "removed"}).status_code == 409
    assert client.post(f"/projects/{project['id']}/artifacts", json={
        "actor": "pm", "path": "/reports/frozen/input.sqlite3", "sha256": "b" * 64,
        "bytes": 10, "media_type": "application/x-sqlite3", "purpose": "EVIDENCE",
    }).status_code == 422
    assert client.post(f"/artifacts/{ephemeral['id']}/references", json={
        "actor": "pm", "ref_kind": "VERSION", "ref_id": "nonexistent",
    }).status_code == 404
    removed = artifact("VERIFIED_EPHEMERAL", "/mnt/d/removed.sqlite3")
    post(client, f"/artifacts/{removed['id']}/deleted", {"message": "Synthetic deletion attestation"})
    assert client.post(f"/artifacts/{removed['id']}/references", json={
        "actor": "pm", "ref_kind": "VERSION", "ref_id": version["id"],
    }).status_code == 409


def test_summary_overview_template_history_and_fail_closed_layout(client):
    _, _, project, _ = setup(client)
    for text in ("old overview", "new overview"):
        post(client, f"/projects/{project['id']}/overview", {"body_markdown": text})
    for text in ("decision one", "decision two"):
        post(client, f"/projects/{project['id']}/pm-summaries",
             {"body_markdown": text, "evidence_refs": []})
    template = post(client, "/dashboard-templates", {"name": "PM", "layout": DEFAULT_LAYOUT})
    layout = {"title": "Only history", "widgets": [
        {"type": "timeline", "title": "History", "query": "events"},
    ]}
    post(client, f"/dashboard-templates/{template['id']}/revisions", {"layout": layout})
    assert len(client.get("/dashboard-templates").json()[0]["revisions"]) == 2
    assert client.post("/dashboard-templates", json={
        "actor": "pm", "name": "bad",
        "layout": {"title": "Bad", "widgets": [{"type": "metric", "title": "Wrong", "query": "events"}]},
    }).status_code == 422
    workspace = client.get("/workspace").json()
    assert len(workspace["overviews"]) == len(workspace["summaries"]) == 2
    assert client.get("/dashboard").status_code == client.get("/static/app.js").status_code == 200


def test_agent_token_has_identity_and_team_boundaries():
    with TestClient(create_app("sqlite:///:memory:", admin_token="admin-test-token")) as client:
        assert client.get("/workspace").status_code == 401
        client.headers["Authorization"] = "Bearer admin-test-token"
        yu, si, project, item = setup(client, claim=False)
        isolated = post(client, "/projects", {"team_id": si["id"], "key": "PRIVATE", "name": "Private"})
        member = next(row for row in client.get("/members").json() if row["actor"] == "yu")
        key = post(client, f"/members/{member['id']}/keys")
        client.headers["Authorization"] = "Bearer " + key["token"]
        post(client, f"/items/{item['id']}/claim", actor="yu")
        assert client.get("/session").json()["principal"]["actor"] == "yu"
        assert len(client.get("/projects").json()) == 1
        assert client.get("/workspace?project_id=" + isolated["id"]).status_code == 403
        assert client.post(f"/items/{item['id']}/progress", json={
            "actor": "pm", "message": "spoofed identity",
        }).status_code == 403
        assert client.post("/teams", json={"actor": "yu", "name": "Escalation", "slug": "x"}).status_code == 403


def test_demo_is_synthetic_repeatable_and_mcp_uses_the_same_api(client):
    from apc.demo import seed
    data = seed(client)
    assert data["status"] == "seeded"
    assert seed(client)["status"] == "already seeded"
    workspace = client.get("/workspace").json()
    assert len(workspace["items"]) == 5
    assert all(row["source_ref"] == "demo:synthetic-no-file" for row in workspace["artifacts"])
    assert not workspace["artifacts"][0]["deletion_check"]["allowed"]


def test_mcp_transport_preserves_api_identity_and_errors(monkeypatch):
    import httpx
    from apc.mcp import server

    calls = []
    def capture(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return httpx.Response(200, json={"ok": True})
    monkeypatch.setenv("COAGENTS_API_TOKEN", "synthetic-token")
    monkeypatch.setattr(server, "ACTOR", "yu")
    monkeypatch.setattr(server.httpx, "request", capture)
    assert server.report_progress("item", "Started", "WORKING", 30) == {"ok": True}
    assert calls[0][2]["json"]["actor"] == "yu"
    assert calls[0][2]["headers"]["Authorization"] == "Bearer synthetic-token"
    assert calls[0][1].endswith("/items/item/progress")
