# Install and use COAGENTS

## Service

```bash
cp .env.example .env
# Put a private random token in COAGENTS_ADMIN_TOKEN.
docker compose up --build -d
curl http://localhost:8310/healthz
```

Open http://localhost:8310/dashboard. Select **連線與身分**, enter the administrator token,
then create teams and a shared project. In **團隊與 Agent**, register members and issue their
own keys. The one-time displayed keys are stored only as SHA-256 hashes in SQL.

An empty admin token enables local development mode: the caller chooses a registered actor.
Compose binds localhost. For remote use, set a token and put TLS in front of the service.
If the subnet conflicts with a local network, choose a free `COAGENTS_SUBNET` in `.env`.

## Optional example

```bash
pip install -e .
export COAGENTS_API_TOKEN='<administrator token>'
coagents-demo --url http://localhost:8310
```

The sample contains synthetic teams, tasks, a validation gate, summary and a fictitious 2 GB
artifact registry entry. It creates no 2 GB file or real database copy. It is opt-in.

## Agent setup

Install the package in the agent's Python environment and add this MCP configuration:

```json
{
  "mcpServers": {
    "coagents": {
      "command": "coagents-mcp",
      "env": {
        "COAGENTS_API_URL": "http://127.0.0.1:8310",
        "COAGENTS_ACTOR": "yu-agent",
        "COAGENTS_API_TOKEN": "<yu-agent key>"
      }
    }
  }
}
```

If the agent is in another container, use the service's reachable hostname instead of loopback.
COAGENTS MCP runs with the agent; it calls the single service. Agents do not need PostgreSQL
credentials. Read [the Skill](../skills/coagents-api/SKILL.md) for the workflow and
[API tutorial](API.md) for complete endpoint coverage.

## Development and persistence

```bash
pip install -e '.[dev]'
pytest -q
```

Docker installs the pinned `requirements.lock`; `uv.lock` is the dependency graph used to
generate it. Dependency updates should regenerate both and rerun the tests.

Optional UI check against the local service (creates only synthetic DEMO records):

```bash
pip install playwright==1.58.0
playwright install chromium
PYTHONPATH=src python scripts/browser_smoke.py
```

The script checks actual PostgreSQL-backed creation, claims, progress, PM summaries,
template rendering, all seven views and mobile overflow. Screenshots use synthetic data only.

PostgreSQL lives in the `coagents_apc-postgres` volume. `docker compose down` keeps it.
No source/rollback database copies belong in the application repo. Register their original paths.

The v0.2 schema is additive to v0.1. Before future schema upgrades, follow the release's migration
instructions; startup table creation does not migrate arbitrary column changes.
