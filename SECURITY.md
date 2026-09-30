# Security policy

COAGENTS v0.1 is a local-development foundation. Do not expose its API to a network until the
v0.2 authenticated-actor and RBAC release is available.

The API must never store upstream API keys in progress payloads, PM summaries, or audit events.
Adapters use separately configured secrets and interact with It’s a Plan, Plane, and Vikunja only
through documented APIs/webhooks. They must never access an upstream database directly.

Report vulnerabilities privately to the repository maintainers once the public repository exists.
