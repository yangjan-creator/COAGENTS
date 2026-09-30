# v0.2 implementation checks

These checks were run locally against COAGENTS, using synthetic data only. They do not
authorize real deployments, import real team data, or attest external artifact contents.

| Check | Actual result |
|---|---|
| `PYTHONPATH=src pytest -q` | 9 passed |
| `ruff check src tests scripts` | all checks passed |
| Skill `quick_validate.py skills/coagents-api` | valid |
| `docker compose up --build -d` | API and PostgreSQL started; health 200 |
| `PYTHONPATH=src python scripts/browser_smoke.py` | create/claim/progress/edit/summary/template round trips; 7 views; mobile no overflow; zero JS errors |
| Real MCP stdio `initialize`, `list_tools`, `call_tool(workspace)` | 23 tools; workspace read from PostgreSQL passed |
| `scripts/postgres_smoke.py` inside local API container | two concurrently waiting gate submissions: exactly one HTTP 200 and one HTTP 409 |

The concurrent-gate test holds a PostgreSQL row lock until both handlers are waiting, then
releases them. This exercises the stale-read boundary, rather than relying on two requests
accidentally running sequentially. Gate/version state is refreshed after the item lock.
Dependency graph edits serialize per project so disjoint edges cannot jointly form a cycle.

The Dashboard browser test is opt-in and creates labeled synthetic DEMO records. It requires
Playwright 1.58.0 and its Chromium installation. See [Quickstart](QUICKSTART.md).
To repeat the PostgreSQL gate test after seeding DEMO, run:

```bash
docker cp scripts/postgres_smoke.py coagents-api-1:/tmp/coagents_postgres_smoke.py
docker compose exec -T api python /tmp/coagents_postgres_smoke.py
docker compose exec -T api python -c 'from pathlib import Path; Path("/tmp/coagents_postgres_smoke.py").unlink()'
```

It creates one synthetic work item/version/gate and revokes its temporary reviewer key.
It makes no database copies. The project data and audit event are retained as synthetic evidence.
The service's private `.env` is ignored by Git and excluded from the Docker context.

Not tested or not implemented: multi-host deployment, SSO, scheduling, arbitrary future
SQL schema migrations, external file/process verification, and automatic Git/deploy execution.
No external PM product is contacted. No provider LLM calls are made by these checks.
