---
name: coagents-api
description: Use the standalone COAGENTS service to create and expand projects, claim tasks, report progress, deliver versions, validate evidence, read histories, register file paths, and maintain PM summaries or Dashboard templates through REST or MCP.
---

# COAGENTS

One service provides SQL-backed project control, a human Dashboard and Agent MCP.
Use MCP when configured. Use REST when integrating scripts. Never edit the control database.

Read the repository's [API tutorial](../../docs/API.md) for request fields, permissions and errors.
Read [Template contract](../../docs/DASHBOARD_TEMPLATES.md) when making or editing a view.
If installed independently of the repository, use the published
[API tutorial](https://github.com/yangjan-creator/COAGENTS/blob/main/docs/API.md) and
[Template contract](https://github.com/yangjan-creator/COAGENTS/blob/main/docs/DASHBOARD_TEMPLATES.md).

## Identity and permissions

Use the configured `COAGENTS_ACTOR` and its `COAGENTS_API_TOKEN`. Token and actor must match.
CONTRIBUTOR owns work; REVIEWER records independent gates; PM manages decisions and closure.
For a new actor, a PM must register the member and issue its own key first.

## Work lifecycle

1. Read `workspace` or `item_history`.
2. Create a SUBPROJECT/FEATURE/TASK under a project or parent, then claim it.
3. Report progress with the concrete result, next step and blocker. Another member's claim cannot
   be overwritten; progress cannot grant VERIFIED.
4. Deliver a new vN with change note and Git commit/PR/artifact reference. Never reuse an old version.
5. A separate reviewer declares and runs gates for that version, citing evidence path + full SHA.
   No declared gates is not a pass. FAILED is preserved; repairs receive a new version.
6. A PM may close a verified version only when its dependencies are verified.
7. Append a PM Summary when integrating facts into a decision; save overview revisions for the
   current overall plan. All older records remain readable.

## File registry

Register `path, sha256, bytes, owner, purpose`; the service stores metadata, never large copies.
Link assets to versions/gates/summaries for reverse traceability. A path is a locator, not identity.
Protected input/rollback or referenced files cannot receive a deletion attestation.
`artifact_deletion_check` examines registry references only: inspect processes, mounts and retention
requirements separately before touching the real file. The server never physically deletes it.

## Templates

Templates render directly in the Dashboard. Use the typed widget/query pairs from the contract.
Editing creates a new template revision; don't imply that a stored JSON layout is verified
until its actual view has been opened.

## Boundaries

No external PM installation or Connector is required. COAGENTS records Git identities and
evidence attestations, but does not prove runtime facts, host Git or execute deployments.
Report a 401/403/409/422 with its actual reason; don't retry as another actor or claim success.
