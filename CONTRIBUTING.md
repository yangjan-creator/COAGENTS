# Contributing to COAGENTS

1. Do not add an adapter that reads or writes an upstream product's database directly.
2. New agent write actions must create an append-only `AuditEvent`.
3. New work states must specify whether they can lead to `VERIFIED`, and which gate closes them.
4. New artifact behavior must preserve the no-copy registry model and a deletion check.
5. New Dashboard widgets require a declared data query and a fail-closed unknown-widget behavior.
6. Run the API smoke tests and preserve API compatibility unless the change is versioned.

Use Apache-2.0-compatible contributions. Do not copy source code from AGPL upstream tools into this
repository; API adapters are intentionally separate from upstream implementations.
