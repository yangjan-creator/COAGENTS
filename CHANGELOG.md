# Changelog

## 0.2.0 — 2026-09-30

COAGENTS becomes a standalone workspace, not an external-PM connector scaffold.

- PostgreSQL-backed shared projects, human/agent members and member-key authentication.
- Working human Dashboard: hierarchy, claims, progress, editing, versions, validation,
  assets, complete selected-project history, PM summaries and custom template rendering.
- Independent gates are version-bound; old results cannot change the current delivery.
- Claims cannot be stolen; required failures persist; progress cannot self-verify work.
- Conservative file registry with reverse references; no physical files copied or deleted.
- 23 native MCP tools, API tutorial, reusable Agent Skill and synthetic demo.
- Locked runtime dependencies and local-only Docker Compose defaults.
- Removed external adapters; no It's a Plan, Plane or Vikunja service is required.

Verification: nine isolated API regression tests, PostgreSQL-backed browser workflow,
seven Dashboard views, mobile overflow check, real MCP stdio workspace read, and a
PostgreSQL concurrent-gate result test. Reproduction steps: [Verification](docs/VERIFICATION.md).
Source/rollback artifact metadata remains an attestation, not a runtime verification.
Versioned SQL migrations, scheduling, notifications and SSO remain future work.
