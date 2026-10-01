# COAGENTS control records and development authority

Author and responsibility: 滴.

COAGENTS uses its authenticated SQL service to control project work. Git stores code and
reviewable design documents; it is not a second live progress database. This page explains
how humans and agents should distinguish those records and read the evidence behind a status.
It does not grant development, deployment, or data access by itself.

## Where each kind of information belongs

| Information | Authority | How to inspect it |
|---|---|---|
| Current owner, progress, blocker and next action | The project work item and its recorded events | Dashboard, `GET /workspace`, item history |
| A proposed implementation or changed requirement | A fixed plan revision and its review decision | The referenced plan body and review evidence |
| Code and public documentation | The exact Git commit and blob | Repository history and the delivery source reference |
| Delivery acceptance | That delivery version and its applicable gate results | `GET /items/{id}/history` and evidence references |
| PM decisions and consolidated project context | Append-only PM Summary and Overview revisions | Project workspace and project history |
| File content and location | Registered locator, measured hash, size and owner | Artifact registry and the cited measurement evidence |
| Deployment or runtime behavior | A receipt for the named environment and served version | The deployment or runtime evidence referenced by the project |

In v0.2, Summary and Overview can hold planning text and lessons. Typed Rule, Memory, code
registries and automatic Context Packs are future contracts, not capabilities created by
putting those headings in a Summary. Likewise, an artifact registration is an attestation;
it does not mean the server read the file or verified its bytes.

## Read the current state before acting

Use your own member credential. Follow the [API tutorial](../API.md) and
[Agent Skill](../../skills/coagents-api/SKILL.md); do not borrow a PM identity to bypass a 403.

1. Read the selected project workspace, including its latest Overview and relevant PM decisions.
2. Read the specific item history. Identify the owner, current delivery version, source commit
   or content hash, declared gates and terminal results. Older passed versions are historical
   evidence, not acceptance of a newer delivery.
3. Read the decision that authorizes the requested phase and its write set. A plan review may
   authorize only a small implementation increment, not every feature described by the plan.
4. Check dependencies and the intended environment. A candidate tested on an isolated service
   does not replace the running service or authorize production deployment.
5. Report an unresolved scope, identity, dependency or unknown write outcome before retrying.
   If the response was lost, inspect history first; do not interpret a timeout as proof of no write.

The existing Dashboard is a view of these API records. The current API tutorial documents
implemented routes; the future [API contract](../planning/API_CONTRACT.md) must not be treated
as a list of callable endpoints. The eventual context-query service will preserve this same
distinction between accepted records, drafts and historical evidence.

## Status terms do not substitute for one another

| English term | 中文判讀 | What it does not establish |
|---|---|---|
| ACK or CLAIMED | 收到或認領 | Work started, tests passed, or acceptance |
| WORKING | 執行者回報正在進行 | Completion or reviewer verification |
| READY_FOR_REVIEW | 作者交付待驗 | Acceptance |
| VERIFIED plan | 指定計畫版本已驗 | Implemented functionality or permission to deploy |
| VERIFIED delivery | 指定交付與必要格已驗 | Another version, another environment, or the whole project |
| Deployed | 指定環境已套用變更 | Successful user behavior or completion of runtime gates |
| Runtime verified | 指定入口與分母的行為已驗 | Unmeasured routes, all accessibility checks, or indefinite reliability |
| CLOSED | 核定完成條件和依賴已满足 | Physical deletion of files, Git history, or external databases |

These are interpretation rules, not new v0.2 status enums. Consult the current OpenAPI for
the actual accepted values. In particular, `progress=100` cannot grant `VERIFIED`.

## Review and repair

The project operating policy uses one independent reviewer. The delivery author cannot approve
their own work; developer joint testing remains development evidence. Declare the required gates
before recording results. A required failure is retained and corrections receive a successor
version. Do not amend a failed historical delivery to make it look as though it originally passed.

A source change invalidates only the evidence whose bindings and claims are affected. Reuse a
result only when its exact inputs and tested behavior remain applicable, and state that scope.
Review of a documentation-only change cannot silently expand into a full product regression claim.

## Historical plans and current authorization

The original [product plan](../PROJECT_PLAN.md), [completion matrix](../planning/COMPLETION_MATRIX.md)
and [execution blueprint](../planning/EXECUTION_BLUEPRINT.md) retain the approval state they had
when recorded. Development was later authorized in phases. Their historical “not authorized”
wording does not cancel a later explicit decision, and a broad design does not override a later
restricted write set.

Current progress, phase permissions and handoffs belong in the SQL project records. Git documents
describe the stable architecture and process; they should link to the appropriate record type
rather than grow a second manually maintained status table. Production access, real-team onboarding,
external credentials and destructive operations still require their own authority and evidence.
