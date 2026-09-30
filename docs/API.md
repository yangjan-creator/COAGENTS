# COAGENTS API / Agent tutorial

OpenAPI: `GET /openapi.json`; interactive reference: `/docs`.
Dashboard and MCP use these same endpoints. Production API identity is determined by the token.

## Connect

```bash
export COAGENTS_URL=http://127.0.0.1:8310
export COAGENTS_API_TOKEN='<member or administrator token>'
curl "$COAGENTS_URL/session" -H "Authorization: Bearer $COAGENTS_API_TOKEN"
```

Every command includes `actor`. Administrator token means actor=`pm`; member token means its
registered actor. A mismatched body actor receives 403. Missing/invalid keys receive 401.
Member keys can be issued and revoked by a PM, and their plaintext is never listed again.

## Start one shared project (PM)

1. `POST /teams`: `{"actor":"pm","slug":"yu","name":"羽"}`.
2. Create 思 the same way.
3. `POST /members`: `actor, member_actor, name, kind=HUMAN|AGENT, role=CONTRIBUTOR|REVIEWER|PM, team_id`.
4. `POST /members/{id}/keys`: `{"actor":"pm"}`. Save the one-time token in a secret store.
5. `POST /projects`: `{"actor":"pm","team_id":"<yu>","team_ids":["<si>"],"key":"APP","name":"共同專案"}`.

## Expand and claim work

```bash
curl -X POST "$COAGENTS_URL/projects/$PROJECT_ID/items" \
  -H "Authorization: Bearer $COAGENTS_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"actor":"yu-agent","key":"APP-1","kind":"FEATURE","title":"來源核對",
       "description":"逐欄可重播","team_id":"<yu-id>"}'

curl -X POST "$COAGENTS_URL/items/$ITEM_ID/claim" \
  -H "Authorization: Bearer $COAGENTS_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"actor":"yu-agent"}'
```

Types: SUBPROJECT, FEATURE, TASK. Use `parent_id` to build the hierarchy.
`PATCH /items/{id}` updates title, description, labels and priority, preserving the before/after
values in history. Claims cannot overwrite another owner.

## Report progress and blockers

```json
{
  "actor":"yu-agent",
  "status":"BLOCKED",
  "progress_percent":65,
  "message":"缺來源學校欄；等官方資料。",
  "payload":{"next_owner":"source-owner","next_check":"tomorrow"}
}
```

Send to `POST /items/{id}/progress`. Requires ownership.
Progress states: QUEUED, WORKING, READY_FOR_REVIEW, VALIDATING, BLOCKED, HOLD, PARKED.
VERIFIED and CLOSED cannot be set here.

## Deliver a version

`POST /items/{id}/versions`:

```json
{
  "actor":"yu-agent",
  "change_note":"修正來源綁定",
  "source_ref":"git:<repository>@<commit>",
  "source_sha256":"<64 lowercase hex>"
}
```

The server chooses vN under a work-item lock. Previous versions, evidence and results stay readable.
Git references are recorded, not fetched or executed.

## Validate independently

A REVIEWER/PM declares gates via `POST /versions/{id}/gates`:

```json
{"actor":"review-agent","name":"逐列來源守恆","required":true}
```

Then `POST /gates/{id}/result`:

```json
{
  "actor":"review-agent",
  "status":"PASSED",
  "message":"獨立重播後符合；負控有紅。",
  "evidence_uri":"/mnt/d/evidence/check.json",
  "evidence_sha256":"<64 lowercase hex>"
}
```

All results require a path/URI, full SHA and message. A delivery's creator cannot validate it.
Each result is terminal: corrections require a successor version. WAIVED requires a PM.
No gates means NOT_DECLARED, not a vacuous pass. One failed required gate prevents verification.
Results on an older version cannot alter the current item.

## Dependencies and closure

- `POST /items/{id}/dependencies`: `actor, depends_on_id`; cycles and cross-project edges rejected.
- `POST /items/{id}/close`: PM-only; active version and dependencies must be verified.

## PM records

- `POST /projects/{id}/overview`: `actor, body_markdown`. New revision on each save.
- `POST /projects/{id}/pm-summaries`: `actor, body_markdown, evidence_refs[]`. Append-only decision log.
- `GET /projects/{id}/history`: full event history.
- `GET /items/{id}/history`: every version, gate and event.
- `GET /workspace?project_id=<id>`: current overview, tasks, versions, gates, summaries,
  assets, roster and latest 200 events. This endpoint powers the Dashboard.

## Files and database copies

`POST /projects/{id}/artifacts`:

```json
{
  "actor":"yu-agent",
  "path":"/mnt/d/scratch/workcopy.sqlite3",
  "sha256":"<64 lowercase hex>",
  "bytes":5000000000,
  "media_type":"application/x-sqlite3",
  "purpose":"ROLLBACK_POINT",
  "source_ref":"derived-from:<source>"
}
```

Purposes: UNIQUE_INPUT, ROLLBACK_POINT, VERIFIED_EPHEMERAL, EVIDENCE.
This registers a locator; it never copies file bytes.
`POST /artifacts/{id}/references` links `ref_kind=VERSION|GATE|SUMMARY, ref_id` within the same project.
`GET /artifacts/{id}/deletion-check` reports protection and references.
`POST /artifacts/{id}/deleted` (PM) records a deletion attestation only for unprotected,
unreferenced entries. The server does not delete files or verify absence.
Database files below reports/frozen paths are rejected.

## Templates and open extension points

- `GET /dashboard-templates`: saved templates, all revisions and current ID.
- `POST /dashboard-templates`: `actor, name, layout, project_id? OR team_id?`.
- `POST /dashboard-templates/{id}/revisions`: `actor, layout`.

See [Template schema](DASHBOARD_TEMPLATES.md). Typed bindings can be extended in
`schemas.Widget` and the static renderer together; unknown binding combinations receive 422.

## Error handling

| Code | Action |
|---|---|
| 401 | fix token; do not retry anonymously |
| 403 | actor, role, team or independence violation; preserve the blocker |
| 404 | reference is missing; locate the actual ID |
| 409 | state/claim/result/duplicate conflict; read history before making a new version |
| 422 | contract validation failure; correct the payload, never relabel a failure as success |

## MCP tools

The 23 tools cover projects, teams, members, workspace, task creation/claims/progress,
versions, gates/results, dependencies/closure, overviews/summaries, artifacts/links/checks,
histories and templates. Each uses the API and the process's configured actor/key.
The MCP server has no SQL access, shell-execution or deployment tool.
