# Custom Dashboard templates

The same service renders templates, stores their revisions, and exposes them through API/MCP.
A template is global, team-scoped or project-scoped. Open **Dashboard 模板** to create one, then
select it on **專案總覽**. Editing saves a new version; earlier layouts remain visible.

## Layout v1

```json
{
  "title": "羽 / 思：共同交付",
  "statuses": [],
  "widgets": [
    {"type": "metric", "title": "待驗證格", "query": "pending_gates"},
    {"type": "board", "title": "共同工作", "query": "items"},
    {"type": "table", "title": "阻塞項目", "query": "blocked",
     "columns": ["key", "title", "team", "owner_actor", "version", "validation"]},
    {"type": "summary", "title": "PM 決策", "query": "summaries"},
    {"type": "artifacts", "title": "資料路徑與保留狀態", "query": "artifacts"},
    {"type": "timeline", "title": "最新動作", "query": "events"}
  ]
}
```

| Widget | Allowed queries |
|---|---|
| metric | items, blocked, verified, pending_gates |
| table | items, blocked, verified |
| board | items |
| summary | summaries |
| artifacts | artifacts |
| timeline | events |

Table columns: `key, title, kind, owner_actor, status, version, progress, team, priority, validation`.
Order controls widget order. Metrics are grouped into the top strip. `statuses` filters work-item
widgets; the toolbar adds project/team/search filters. Timeline and summary widgets follow the
selected project. They remain project-wide when a team/search filter is applied.

Unknown widgets, unknown columns and incompatible type/query pairs fail validation (HTTP 422).
Templates contain data bindings, never executable JavaScript or SQL. The open static renderer in
`src/apc/static/app.js` can be extended alongside the API's Widget schema.

## API

```text
GET  /dashboard-templates
POST /dashboard-templates
POST /dashboard-templates/{id}/revisions
```

Create body: `actor, name, description?, team_id? OR project_id?, layout`.
Revision body: `actor, layout`. GET returns every revision and the current revision ID.
