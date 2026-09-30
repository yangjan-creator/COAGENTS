# COAGENTS

An API-first, self-hosted control plane for humans and coding agents working on the same projects.

It is **not** another issue board. Its source of truth is a PostgreSQL database that records:

- projects, subprojects, features, and tasks;
- immutable delivery versions (`v1`, `v2`, ...);
- required validation gates and their evidence;
- agent claims, progress events, blockers, and handoffs;
- a mutable project overview plus an append-only PM summary log.

Git is the source of truth for code. Agent Project Control links a delivery version to a Git commit, tag, PR, or frozen artifact; it does not replace Git.

## Why adapters, not a merger

It’s a Plan, Plane, and Vikunja remain independent systems. This project offers adapters for importing or publishing bounded work-item state through their APIs/webhooks. No adapter writes directly to a vendor database, and no external board can silently close a required validation gate.

## Core lifecycle

```text
DRAFT -> CLAIMED -> WORKING -> READY_FOR_REVIEW
      -> VALIDATING -> VERIFIED -> CLOSED
                    -> FAILED / BLOCKED / HOLD
```

`VERIFIED` requires every required gate on the active delivery version to be `PASSED` (or explicitly `WAIVED` with a reason). A new version never overwrites a prior version's gates or evidence.

## Quick start

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8080/healthz
```

OpenAPI is served at `http://localhost:8080/docs`.

For agent usage, read [skills/coagents-api/SKILL.md](skills/coagents-api/SKILL.md), then configure the MCP server from `src/apc/mcp/server.py`.

## MVP scope

The first runnable release provides the canonical model, guarded REST API, PostgreSQL schema, append-only progress/summary evidence, and MCP-facing commands. Adapter execution and a human dashboard are deliberately secondary: agents must be able to run the system without clicking a UI.

## License

Apache-2.0. This repository communicates with external systems only through their documented APIs. Verify each upstream product's license before embedding or modifying its code.
