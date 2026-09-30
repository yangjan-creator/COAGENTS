"""Explicit synthetic example data. Never imports real team documents or databases."""

import argparse
import os

import httpx


def seed(client):
    tokens = {}
    auth_enabled = client.get("/session").json()["auth_enabled"]

    def post(path, body, actor="pm"):
        headers = {"Authorization": "Bearer " + tokens[actor]} if actor in tokens else {}
        response = client.post(path, json={"actor": actor, **body}, headers=headers)
        response.raise_for_status()
        return response.json()

    if any(row["key"] == "DEMO" for row in client.get("/projects").json()):
        return {"status": "already seeded"}
    yu = post("/teams", {"slug": "yu-demo", "name": "羽團隊 · 範例"})
    si = post("/teams", {"slug": "si-demo", "name": "思團隊 · 範例"})
    for actor, name, role, team in [
        ("yu-demo", "羽 Agent", "CONTRIBUTOR", yu),
        ("si-demo", "思 Agent", "CONTRIBUTOR", si),
        ("review-demo", "內容驗證 Agent", "REVIEWER", yu),
    ]:
        member = post("/members", {"member_actor": actor, "name": name, "kind": "AGENT",
                                   "role": role, "team_id": team["id"]})
        if auth_enabled:
            tokens[actor] = post(f"/members/{member['id']}/keys", {})["token"]
    project = post("/projects", {"team_id": yu["id"], "team_ids": [si["id"]],
                                "key": "DEMO", "name": "雙團隊交付 · 示範專案"})
    pid = project["id"]
    root = post(f"/projects/{pid}/items", {"key": "DEMO-001", "kind": "SUBPROJECT",
                "title": "來源到交付的完整歷程", "description": "純合成示範，展示團隊協作與版本驗證。"})
    verified = None
    for n, title, team, actor, state in [
        (2, "核對来源與欄位", yu, "yu-demo", "VERIFIED"),
        (3, "產生交付版本", yu, "yu-demo", "WORKING"),
        (4, "檢查入口格式", si, "si-demo", "HOLD"),
        (5, "整理 PM 整合摘要", si, "si-demo", "READY_FOR_REVIEW"),
    ]:
        item = post(f"/projects/{pid}/items", {
            "key": f"DEMO-{n:03d}", "kind": "TASK", "title": title, "parent_id": root["id"],
            "team_id": team["id"], "description": "示範資料；沒有執行任何產品操作。",
        })
        post(f"/items/{item['id']}/claim", {}, actor)
        version = post(f"/items/{item['id']}/versions",
                       {"change_note": "第一版合成交付", "source_ref": "demo:synthetic",
                        "source_sha256": "a" * 64}, actor)
        gate = post(f"/versions/{version['id']}/gates", {"name": "來源與交付逐欄比對"})
        if state == "VERIFIED":
            post(f"/gates/{gate['id']}/result", {
                "status": "PASSED", "evidence_uri": "/demo/evidence/synthetic-check.json",
                "evidence_sha256": "b" * 64, "message": "合成驗證通過；示範用途。",
            })
            verified = version
        else:
            post(f"/items/{item['id']}/progress", {
                "status": state, "progress_percent": 65 if state == "WORKING" else 30,
                "message": "等待獨立內容證據。" if state == "HOLD" else "已核欄位，下一步整理交付。",
            }, actor)
    artifact = post(f"/projects/{pid}/artifacts", {
        "path": "/demo/scratch/workcopy.sqlite3", "sha256": "c" * 64, "bytes": 2147483648,
        "media_type": "application/x-sqlite3", "purpose": "ROLLBACK_POINT",
        "source_ref": "demo:synthetic-no-file",
    })
    post(f"/artifacts/{artifact['id']}/references",
         {"ref_kind": "VERSION", "ref_id": verified["id"]})
    post(f"/projects/{pid}/overview",
         {"body_markdown": "此專案展示羽、思雙團隊共同工作。所有內容是合成範例。\n完成條件：版本綁定、獨立驗證、證據可追溯。"})
    post(f"/projects/{pid}/pm-summaries", {
        "body_markdown": "來源核對已驗證；交付版正在整理，入口格式仍 HOLD。\n下一步：補齊獨立證據後再開啟驗證。",
        "evidence_refs": ["demo:synthetic-check"],
    })
    return {"status": "seeded", "project_id": pid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8310")
    args = parser.parse_args()
    token = os.environ.get("COAGENTS_API_TOKEN", "")
    with httpx.Client(base_url=args.url,
                      headers={"Authorization": "Bearer " + token} if token else {}) as client:
        print(seed(client))


if __name__ == "__main__":
    main()
