from pathlib import Path

from fastapi.testclient import TestClient


def test_required_gate_controls_verification(tmp_path, monkeypatch):
    db = tmp_path / "coagents-test.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    # Settings are process-global, so import only after setting this isolated test database.
    from apc.api import app

    with TestClient(app) as client:
        team = client.post("/teams", json={"slug": "yu", "name": "羽", "actor": "seed"}).json()
        project = client.post("/projects", json={"team_id": team["id"], "key": "COA", "name": "Test", "actor": "seed"}).json()
        item = client.post(f"/projects/{project['id']}/items", json={"key": "COA-1", "kind": "TASK", "title": "Gate", "actor": "yu-agent"}).json()
        version = client.post(f"/items/{item['id']}/versions", json={"actor": "yu-agent", "change_note": "first"}).json()
        required = client.post(f"/versions/{version['id']}/gates", json={"name": "review", "required": True, "actor": "yu-agent"}).json()
        optional = client.post(f"/versions/{version['id']}/gates", json={"name": "note", "required": False, "actor": "yu-agent"}).json()
        assert client.post(f"/gates/{optional['id']}/result", json={"status": "PASSED", "evidence_uri": "/mnt/d/optional.json", "actor": "review", "message": "optional"}).status_code == 200
        assert client.get(f"/items/{item['id']}/history").json()["item"]["status"] != "VERIFIED"
        assert client.post(f"/gates/{required['id']}/result", json={"status": "PASSED", "evidence_uri": "/mnt/d/required.json", "actor": "review", "message": "required"}).status_code == 200
        assert client.get(f"/items/{item['id']}/history").json()["item"]["status"] == "VERIFIED"


def test_database_artifact_path_is_rejected_under_reports(tmp_path, monkeypatch):
    db = tmp_path / "coagents-artifact-test.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    from apc.api import app

    with TestClient(app) as client:
        team = client.post("/teams", json={"slug": "si", "name": "思", "actor": "seed"}).json()
        project = client.post("/projects", json={"team_id": team["id"], "key": "COB", "name": "Test", "actor": "seed"}).json()
        response = client.post(f"/projects/{project['id']}/artifacts", json={"path": "/home/sky/reports/packet/workcopy.sqlite3", "sha256": "0" * 64, "bytes": 1024, "media_type": "application/x-sqlite3", "purpose": "VERIFIED_EPHEMERAL", "actor": "si-agent"})
        assert response.status_code == 422
