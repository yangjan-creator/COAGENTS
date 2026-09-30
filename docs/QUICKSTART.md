# COAGENTS quick start

## 1. Start locally

```bash
cp .env.example .env
docker compose up --build
open http://localhost:8080/dashboard
```

The first start creates PostgreSQL tables automatically. Production migrations and authenticated
actors are planned before any public-network deployment; do not expose this v0.1 development API.

## 2. Create the two teams and one shared initiative

```bash
curl -X POST http://localhost:8080/teams -H 'content-type: application/json' \
  -d '{"slug":"yu","name":"羽","actor":"pm"}'
curl -X POST http://localhost:8080/teams -H 'content-type: application/json' \
  -d '{"slug":"si","name":"思","actor":"pm"}'

# Use the returned yu team id here.
curl -X POST http://localhost:8080/projects -H 'content-type: application/json' \
  -d '{"team_id":"<yu-team-id>","key":"BAD","name":"羽球資料整合","actor":"pm"}'
```

Create a `SUBPROJECT` under `BAD`, then its `FEATURE` and `TASK` children. Each becomes separately
claimable and has its own version chain and gates.

## 3. Create a PM view template

```bash
curl -X POST http://localhost:8080/dashboard-templates -H 'content-type: application/json' \
  -d @- <<'JSON'
{
  "name":"PM 交付總覽",
  "description":"版本、驗證、阻塞與資料保留風險",
  "team_id":"<yu-team-id>",
  "actor":"pm",
  "layout":{
    "title":"羽：交付總覽",
    "widgets":[
      {"type":"metric","query":"versions.required_gates_pending"},
      {"type":"table","query":"work_items.blocked","columns":["key","title","current_version","owner_actor"]},
      {"type":"timeline","query":"audit_events.recent"}
    ]
  }
}
JSON
```

See [DASHBOARD_TEMPLATES.md](DASHBOARD_TEMPLATES.md) for the stable JSON contract.

## 4. Let an agent use MCP

Example local configuration:

```json
{
  "mcpServers": {
    "coagents": {
      "command": "python3",
      "args": ["-m", "apc.mcp.server"],
      "env": {"PYTHONPATH": "/path/to/coagents/src", "COAGENTS_API_URL": "http://127.0.0.1:8080"}
    }
  }
}
```

The agent then uses the `coagents-api` skill in this repository. MCP has no SQL tool and cannot
mark work verified by itself; required gates still enforce the version lifecycle.
