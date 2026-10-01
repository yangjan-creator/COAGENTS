# Product state

## v0.2: available

One native service: human dashboard, Agent MCP, shared-team projects, hierarchy, claims,
progress, dependencies, delivery versions, independent validation, full history, PM decisions,
file registry and real JSON dashboard-template rendering. API-key identity and role/team
checks are included. Synthetic demo is opt-in.

## Next

- Versioned SQL migrations and upgrade/rollback commands.
- Notifications, scheduled check-ins, assignment handoff and richer dependency visualization.
- Typed custom task fields, template visual editor and saved historical views.
- Git-host evidence attachment and CI check ingestion.
- SSO and more granular project permissions.

These are future features. COAGENTS never requires external project-management products.

## Full objective and acceptance

See the [complete project plan](PROJECT_PLAN.md), [completion matrix](planning/COMPLETION_MATRIX.md)
and [execution blueprint](planning/EXECUTION_BLUEPRINT.md). The matrix preserves all remaining requirements:
scheduling, notifications, webhooks, SSO, SQL upgrade/rollback, automatic Git history synchronization,
real 羽/思 onboarding, production deployment, restore and long-term operation. Project controllers,
single-use authorization and typed knowledge/code registries are also retained.

The [framework detail index](planning/FRAMEWORK_SPEC.md) links the candidate API, SQL, permission
and state-machine contracts. Its static self-check is not runtime acceptance or permission to start DEV.

Planning has been dogfooded in the running v0.2. Development was authorized in phases; current
phase permissions and progress are recorded in the SQL-backed project, not inferred from this
roadmap or the approval state of an older planning snapshot. Unfinished drafts and accepted
isolated candidates are not automatically part of the public release or the running service.
See [control records and development authority](architecture/CONTROL_AUTHORITY.md).
