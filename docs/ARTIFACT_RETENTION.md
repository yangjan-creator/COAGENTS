# Artifact registry and retention

The control plane stores artifact metadata, not artifact copies. A database copy is never placed
inside `reports/`, a frozen package, or the Project Control database merely to make it auditable.

## Required registry fields

`path`, full SHA-256, byte size, media type, creator, purpose, retention state, and source reference.
Paths are authoritative only together with their SHA-256: a path is a locator, not identity.

## Retention states

| State | Meaning | Deletion rule |
|---|---|---|
| `UNIQUE_INPUT` | Only known input for a pending derivation | API must refuse deletion |
| `ROLLBACK_POINT` | Required to undo a live/pending change | API must refuse deletion |
| `VERIFIED_EPHEMERAL` | Regenerable work copy after evidence is recorded | delete after zero live references |
| `EVIDENCE` | Small receipt, manifest, JSON result, or log | retain by project policy |
| `DELETED` | A historical registry entry whose physical file is gone | immutable tombstone |

Before deletion, call `GET /artifacts/{id}/deletion-check`. It returns every live reference and
whether the retention state permits cleanup. Physical deletion is intentionally outside the first
API release. `allowed=true` means only that the registry has no protection or references;
the agent must independently inspect actual process handles, jobs, mount points and rollback
needs before deleting anything. After deletion, a PM records the tombstone with
`POST /artifacts/{id}/deleted`. The server never deletes a file.

## Path policy

- Large files (>500 MB): `/mnt/d/...` or a configured scratch volume.
- Reports/frozen packages: manifests, receipts, JSON results, and logs only.
- The registry rejects database-looking paths below `/reports/` or a `frozen_` directory.
