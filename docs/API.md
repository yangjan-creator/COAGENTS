# REST API v0.1

The running service publishes OpenAPI at `/openapi.json` and Swagger UI at `/docs`.

| Intent | Method and path | Guard |
|---|---|---|
| Create a team | `POST /teams` | team slug unique |
| Create project | `POST /projects` | team must exist |
| Expand into subproject/feature/task | `POST /projects/{id}/items` | parent must share project |
| Claim work | `POST /items/{id}/claim` | state transition guarded |
| Report progress/block | `POST /items/{id}/progress` | owner-only when claimed |
| Create `vN` | `POST /items/{id}/versions` | ordinal assigned by server |
| Declare a validation gate | `POST /versions/{id}/gates` | gate attaches to exactly one version |
| Record pass/fail/waiver | `POST /gates/{id}/result` | PASS/WAIVED require evidence URI |
| Update current overview | `POST /projects/{id}/overview` | creates a revision, no overwrite |
| Append PM interpretation | `POST /projects/{id}/pm-summaries` | append-only |
| Register an artifact locator | `POST /projects/{id}/artifacts` | rejects database copies in reports/frozen dirs |
| Check safe cleanup | `GET /artifacts/{id}/deletion-check` | returns references and permission |
| Read history | `GET /projects/{id}/history` | append-only timeline |
| Configure dashboard | `POST /dashboard-templates` | template starts at revision 1 |

## Version state machine

```text
DRAFT --delivery--> WORKING --all required gates pass--> VERIFIED --> CLOSED
                     |                 |
                     |                 +-- failed gate --> BLOCKED
                     +-- new delivery creates a new vN; v(N-1) stays readable
```

The API must never infer verification from a text progress update.
