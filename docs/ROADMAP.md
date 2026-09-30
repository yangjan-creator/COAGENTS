# Roadmap

## v0.1 — control-plane foundation (this commit)

- PostgreSQL-first project/subproject/feature/task model.
- Immutable delivery versions and validation gates.
- Append-only history, PM summaries, and artifact retention registry.
- REST/OpenAPI, minimal MCP commands, and read-only human dashboard shell.
- It’s a Plan, Plane, and Vikunja adapter boundaries with no upstream database access.

## v0.2 — safe multi-agent operation

- API keys/OIDC and actor-to-team RBAC.
- Alembic migrations, authenticated webhooks, adapter mapping UI.
- Dependency graph and cross-team work ownership.
- Dashboard-template renderer and role-specific views.

## v0.3 — integration and governance

- Version-pinned It’s a Plan connector pilot.
- Plane/Vikunja connectors behind explicit outbound-sync policy.
- Gate policies, evidence verification jobs, and release-readiness dashboard.
- Artifact cleanup receipt/tombstone workflow.

No production integration is enabled until v0.2 authentication/RBAC and v0.3 connector tests pass.
