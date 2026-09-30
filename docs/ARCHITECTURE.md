# COAGENTS architecture

```text
Human Dashboard ─┐
                 ├─ COAGENTS REST API ─ PostgreSQL
Agent MCP ───────┘                     ├─ teams / members / project_teams
                                      ├─ work_items / details / dependencies
                                      ├─ versions / validation_gates
                                      ├─ audit_events / overviews / pm_summaries
                                      ├─ artifacts / references
                                      └─ dashboard_templates / revisions
```

One deployable service implements planning, task management, agent collaboration and reporting.
It's a Plan, Plane and Vikunja informed the capability selection; no external instance or vendor
database is used.

## Authority

Git owns code history; a WorkVersion links to its commit, PR or delivery path and full SHA.
COAGENTS owns task claims, active delivery, validation state, decisions and file references.
It stores artifact locators and attestations, not artifact bytes.

## Collaboration and permissions

A project has an owning team plus participating teams. Each work item has an execution team.
Members have HUMAN/AGENT kind and CONTRIBUTOR/REVIEWER/PM role. An API key resolves to one member;
the body actor must match. Contributors can read participating projects and claim their team's
work. Reviewers declare gates and record results. PMs manage teams, overviews, summaries and closure.
No member can validate its own delivery. The administrator uses the reserved actor `pm`.

## Invariants

- A work-item row lock serializes claims and delivery ordinals on PostgreSQL.
- vN remains readable when v(N+1) becomes active.
- Each gate records one terminal result, evidence URI, full SHA and checker identity.
- All required gates must pass or receive a reasoned PM waiver. Zero gates never verify.
- A result for an older version changes only that version.
- Closing requires the active version and declared dependencies to be verified.
- Dashboard templates are validated layouts, and each edit creates a new revision.
- File deletion checks are conservative registry checks, never physical deletion authorization
  based on filesystem/process inspection.

## Schema compatibility

v0.2 adds separate tables rather than changing v0.1 columns. Startup uses SQLAlchemy create_all
for a new database or those additive tables. Existing v0.1 records remain available, but owners
must register their actor identities before issuing new commands. SQL migration versioning is
still future work; create_all is not a general migration engine.
