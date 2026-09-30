# Contributing

COAGENTS is one native service. Keep the dashboard, REST API and MCP on the same data model.
Do not add a dependency on installing another project manager.

- Add history events for every work-state change.
- Attach verification to a delivery version and preserve old versions and results.
- Test invalid actions as well as a successful workflow.
- Preserve actor/team boundaries and full evidence hashes.
- Keep file storage as an artifact registry; never copy large data into reports.
- Extend Widget schema and renderer together; unknown layouts must be rejected.
- Keep browser content escaped; template JSON must never execute code.

Run `pytest -q` and `node --check src/apc/static/app.js`.
Use Apache-2.0-compatible contributions; do not copy code from other projects without resolving
their license requirements.
