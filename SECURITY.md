# Security

Set COAGENTS_ADMIN_TOKEN to enable authentication. Blank token is local development mode, in
which registered actor names are caller-supplied. Compose binds to 127.0.0.1 by default.

The administrator is `pm`. Member keys are shown once, hashed in SQL and revocable. All nonpublic
API calls require a token when authentication is enabled. Dashboard shell/static files, health
and API schema are public; project data is fetched through the authenticated API.
Use TLS for remote access. This release uses one administrator token; SSO is future work.

Do not put API keys into progress payloads, summaries or artifact source references.
Dashboard tokens stay in browser session storage. MCP reads keys from its process environment.

Artifact entries are locator/hash attestations. The server does not read or delete arbitrary
files or run deployment commands. The registry's cleanup check does not inspect real processes,
cron jobs or filesystem mounts.

Report security issues privately through GitHub Security Advisories in this repository.
