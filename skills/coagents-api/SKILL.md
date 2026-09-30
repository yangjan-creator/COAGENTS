---
name: coagents-api
description: Manage COAGENTS projects, subprojects, delivery versions, validation gates, progress, artifacts, and PM summaries through its guarded API or MCP. Use when an agent needs to claim work, report progress, hand off a delivery, or inspect project history; do not use it to execute product deployments.
---

# COAGENTS API Skill

COAGENTS is the project-control source of truth. Use MCP when available; use REST only when MCP
is not configured. Never write directly to its PostgreSQL database.

## Model

- `WorkItem`: a subproject, feature, or task.
- `WorkVersion`: immutable delivery revision (`v1`, `v2`, ...), not a Git branch.
- Git SHA, PR, or frozen manifest: linked through `source_ref` and `source_sha256`.
- `ValidationGate`: only gates can make a version `VERIFIED`.
- Audit events, overview revisions, and PM summaries are append-only history.

## Normal agent flow

1. Read item history and current version.
2. Claim before work.
3. Append progress or `BLOCKED` with a concrete reason.
4. Make a new delivery version; never overwrite vN.
5. Declare gates, then record results with evidence URI plus full SHA-256.
6. Register large artifacts by locator/SHA/bytes; never copy databases into reports.
7. Use PM Summary only for decisions that integrate several facts.

## MCP examples

```text
claim_work_item(item_id="…", actor="yu-agent")
report_progress(item_id="…", actor="yu-agent", status="WORKING", message="Started v2 extraction")
create_delivery_version(item_id="…", actor="yu-agent", change_note="Fix source binding", source_ref="git:…", source_sha256="<64 hex>")
project_history(project_id="…")
```

## REST examples

```bash
curl -X POST "$COAGENTS_URL/items/$ITEM_ID/claim" \
  -H 'content-type: application/json' -d '{"actor":"yu-agent"}'

curl -X POST "$COAGENTS_URL/gates/$GATE_ID/result" \
  -H 'content-type: application/json' \
  -d '{"actor":"review-agent","status":"PASSED","message":"replay passed","evidence_uri":"/mnt/d/evidence/run.json","evidence_sha256":"<64-hex>"}'
```

## Artifact safety

Call `GET /artifacts/{id}/deletion-check` before cleanup. `UNIQUE_INPUT` and `ROLLBACK_POINT`
are never removable. A path is not identity: record full SHA-256 and bytes. The first release
records deletion permission but does not physically delete files.

## Boundaries

COAGENTS does not prove runtime behavior, deploy code, or replace Git review. It records who
claims work, what version is under review, evidence that exists, and whether declared gates close.
