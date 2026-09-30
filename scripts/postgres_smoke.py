"""Opt-in test inside the local API container; creates only synthetic DEMO evidence."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text


def main():
    admin = os.environ["COAGENTS_ADMIN_TOKEN"]
    headers = {"Authorization": "Bearer " + admin}
    url = "http://127.0.0.1:8080"
    with httpx.Client(base_url=url, headers=headers) as client:
        def post(path, **body):
            response = client.post(path, json={"actor": "pm", **body})
            response.raise_for_status()
            return response.json()

        project = next(p for p in client.get("/projects").json() if p["key"] == "DEMO")
        member = next(p for p in client.get("/members").json() if p["actor"] == "review-demo")
        key = post(f"/members/{member['id']}/keys")
        try:
            item = post(f"/projects/{project['id']}/items", key="PG-" + uuid4().hex[:8],
                        title="Synthetic concurrent validation test")
            version = post(f"/items/{item['id']}/versions", change_note="Synthetic concurrency proof")
            gate = post(f"/versions/{version['id']}/gates", name="Cannot overwrite final result")
            engine = create_engine(os.environ["DATABASE_URL"])
            reviewer_headers = {"Authorization": "Bearer " + key["token"]}

            def submit(status):
                return httpx.post(url + f"/gates/{gate['id']}/result", headers=reviewer_headers,
                                  json={"actor": "review-demo", "status": status,
                                        "message": "Synthetic concurrent gate result",
                                        "evidence_uri": "/demo/synthetic/concurrent.json",
                                        "evidence_sha256": "d" * 64}, timeout=15).status_code

            # Hold the item lock until both handlers have read the previous gate state.
            with engine.connect() as lock, ThreadPoolExecutor(max_workers=2) as pool:
                transaction = lock.begin()
                lock.execute(text("SELECT id FROM work_items WHERE id=:id FOR UPDATE"), {"id": item["id"]})
                first, second = pool.submit(submit, "PASSED"), pool.submit(submit, "FAILED")
                deadline = time.monotonic() + 10
                ready = False
                with engine.connect() as probe:
                    while time.monotonic() < deadline:
                        blocked = probe.execute(text("SELECT count(*) FROM pg_stat_activity "
                            "WHERE wait_event_type='Lock' AND query LIKE '%work_items%'")).scalar()
                        probe.rollback()
                        if blocked >= 2:
                            ready = True
                            break
                        time.sleep(0.02)
                transaction.commit()
                statuses = sorted([first.result(), second.result()])
            engine.dispose()
            assert ready, "did not exercise the competing handlers at the same lock"
            assert statuses == [200, 409], statuses
            print("PASS: PostgreSQL two concurrent gate results => exactly one 200, one 409")
        finally:
            response = client.request("DELETE", f"/members/{member['id']}/keys/{key['id']}",
                                      json={"actor": "pm"})
            response.raise_for_status()


if __name__ == "__main__":
    main()
