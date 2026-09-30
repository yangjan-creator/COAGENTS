# COAGENTS architecture

## Agent-first route

```text
Agent (MCP) -> guarded REST API -> PostgreSQL control plane
                              -> append-only events / versions / gates / artifacts
                              -> optional outbound adapter or webhook
```

The primary route is MCP to the COAGENTS API. The API owns claims, versions, gate state, and
artifact retention. It’s a Plan, Plane, and Vikunja are secondary integrations; they may mirror
status but cannot independently mark a version verified.

## Truth boundaries

| Concern | Truth source |
|---|---|
| Code version | Git commit/tag/PR, linked by `source_ref` |
| Work ownership, status, version, gate | COAGENTS PostgreSQL |
| Validation evidence | immutable artifact reference + gate result |
| PM interpretation | append-only PM Summary Log |
| External board display | adapter cache only |

## Two-team operation

Teams such as `yu` and `si` receive separate Team records. A project belongs to one owning team.
A shared initiative becomes a coordination project with work items owned by either team.

## Version and verification invariant

1. A new delivery creates `WorkVersion(ordinal=n+1)`; prior rows remain immutable.
2. Gates belong to one version, never an unversioned task.
3. Required gates must be `PASSED` or reasoned `WAIVED` before that version becomes `VERIFIED`.
4. A `FAILED` gate blocks the version; a repair becomes a new version.
5. All state transitions emit an `AuditEvent`.
