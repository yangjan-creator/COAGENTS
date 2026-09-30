# Dashboard templates

Templates describe a human view of COAGENTS data. They do not alter work-item, version, or gate
state. Each saved edit creates a new immutable template revision.

## Template scope

- **Global**: a standard operating view for every team.
- **Team**: for example, 羽's data-ingestion view or 思's release queue.
- **Project**: one project-specific PM overview.

At most one of `team_id` and `project_id` should normally be set. The API leaves global templates
with both empty.

## Layout JSON v1

```json
{
  "title": "羽：入庫控制",
  "filters": [{"field": "status", "operator": "in", "value": ["WORKING", "BLOCKED", "HOLD"]}],
  "widgets": [
    {"type": "metric", "title": "待驗證版本", "query": "versions.required_gates_pending"},
    {"type": "table", "title": "阻塞項目", "query": "work_items.blocked", "columns": ["key", "title", "owner_actor", "current_version", "blocker"]},
    {"type": "timeline", "title": "近 24 小時", "query": "audit_events.recent"},
    {"type": "artifact-risk", "title": "受保護資料資產", "query": "artifacts.protected"}
  ]
}
```

The initial API stores this contract and revisions it. The interactive renderer is intentionally
small in v0.1; it must reject unknown widget types rather than silently rendering an incomplete
dashboard.

## Required human views

Every production project should provide at least:

1. **PM overview** — active version, gate state, blockers, latest summary, next owner.
2. **Validation queue** — each version's required gates, evidence URI/SHA, and last checker.
3. **History** — append-only claim/progress/version/gate/summary events.
4. **Retention** — large artifacts, paths, size, owner, purpose, live references, deletion status.

This is where a PM reads the whole project without reconstructing it from scattered RD reports.
