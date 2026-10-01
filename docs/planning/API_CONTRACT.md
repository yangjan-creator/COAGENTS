# COAGENTS API／MCP 詳細契約 v1（設計候選）

作者／責任歸屬：滴。2026-10-01。
這是未實作的新契約，不是目前 v0.2 的 OpenAPI。現行操作仍以 [API 教學](../API.md) 和服役 `/openapi.json` 為準。
本文件與 [SQL 模型](SQL_MODEL.md)、[權限矩陣](AUTHORIZATION_MATRIX.md)、[狀態流程](STATE_MACHINES.md) 同版對帳。
完整需求分母 B01–B10／R01–R10／X01–X08 不變；沒有把規劃完成當成產品完成。

## 1. 共通 HTTP 契約

新契約前綴 `/api/v1`；下表路徑省略此前綴。UUID 是資源識別，不是存取憑證。
Agent 用 `Authorization: Bearer …`；Dashboard 用服務端 session。兩者走相同 Principal／ACL。
cookie 身分的所有 mutation 必須驗 CSRF；API key 不得放 query、瀏覽器持久儲存或報告。
路由表以外沒有 generic SQL、shell、任意模型呼叫、遠端讀檔、部署、migration 或備份執行入口。

| 欄位／行為 | 精確約定 |
|---|---|
| Content-Type | JSON mutation 為 application/json；provider ingress 保留原 bytes 驗簽後再解析 |
| X-Request-ID | 可選 UUID；缺時 server 產生；只作追蹤，不授權或去重 |
| Idempotency-Key | 所有業務 mutation 必填，1–128 ASCII；在 principal＋action 範圍唯一；相同 payload 回同 operation／receipt |
| If-Match | 對既有 target mutation 必填：`"r:<resource UUID>:<revision>"`；不接受萬用 `*`；錯版 409；缺少 428 |
| 新資源 | 不用既有 target 的 If-Match；payload 內 parent_revision 必填並锁父；creation target_revision=0 |
| 一次性授權 | header `X-COAGENTS-Authorization-Request` UUID ＋ `X-COAGENTS-Authorization-Code`；並保留 executor 自己的 Bearer |
| Canonical payload | typed validation 後保留原文；UTF-8、物件 key 排序、無額外空白、拒 NaN／重複 key；array 順序保留；decimal用schema定義的十進位字串，不容許任意float；hash 算法與版本入 receipt |
| 正文 | 不自動 strip、重寫語句或改 Markdown；key／enum 可用明訂正規化；原檔 bytes hash 與 JSON payload hash 是不同欄位 |
| Extra fields | 全部 write schema `additionalProperties=false`；nested 同樣；不能用自由 metadata 偷填 role／state／owner |
| 大小上限 | 預設 JSON body 1 MiB、正文每欄 128 KiB、一般 array 100、context 選取200塊；超限413；部署可降低但不得靜默截斷 |
| Secret output | token／code 僅指定一次回應；no-store、不可記 log；read API 永不回 token_digest 或 signing secret |
| Sync／async | 同 SQL tx 完成用 200／新建201；需 worker 用202＋operation ID；HTTP成功不等於外部效果已成功 |
| 批次 | 本版不提供隱式跨案 bulk mutation；明示單案展開為一個原子 command，非部分成功 |
| Retry | 相同 key 仍驗當次身分／可見性；相同 key 不同 typed payload409；未提交可同 key 有限重試 |

授權、epoch、revision 和獨立性要在同一 transaction 再驗；先驗後撤權不能留下無權更新。
成功記錄 Principal、action、target、payload hash、before/after revision、event／receipt；不信任 body actor。
單次碼 header 不進 payload hash，碼仍綁固定 operation intent。receipt 可返回原成功，不再消耗碼。
operation intent的hash涵蓋action、workspace/project、target_id、expected_revision與typed payload；
canonicalization v1會顯式補schema既定default，optional缺值與null僅按schema分辨，不能任意當相同。
身份、Idempotency-Key、secret headers不進本文hash，但獨立binding照驗；不可跨principal借receipt。

### 1.1 共通回應形狀

`Mutation<T>`：`{data:T, receipt:CommitReceipt, operation:OperationView}`。
`CommitReceipt`：`{id, operation_id, action, target_id, principal_id, execution_identity_id,
before_revision, after_revision, payload_sha256, canonicalization_version, event_ids[], committed_at}`。
`OperationView`：`{id, action, target_id, status, domain_committed, external_effect,
receipt_id?, error_code?, created_at, finished_at?}`；domain 與 external_effect 分層。
`ResourceView`：`{id, workspace_id, project_id?, kind, revision, lifecycle_state,
data_classification, created_by, created_at, updated_at, current_revision_id?}`＋該 kind 的 allowlisted `data`。
`RevisionView`：`{id, resource_id, ordinal, schema_id, schema_version, body, body_sha256,
author_id, source_refs[], classification, created_at}`；正文仍受當次 ACL。
`Page<T>`：`{items:T[], next_cursor?, snapshot_id, measured_at, count_scope}`；不輸出無權總數。
`EventView`：`{id, event_type, aggregate_id, aggregate_revision, operation_id, occurred_at,
principal_id, payload_revision_id}`；payload 另外經 ACL 讀，非 unfiltered audit dump。
`Error`：`{error:{code,message,request_id,action?,retryable,field_errors[]?,operation_id?}}`。
不可見 target 的 Error 不含 target 名稱、現行revision、別案 membership 或密鑰。
表內 `M` 是 Mutation<ResourceView>，`A` 是202 OperationView，`R` 是 ResourceView。
`P` 是 Page<ResourceView>。同路由可以因 effect 種類回 M／A，但必須以已記 operation 分辨。

### 1.2 錯誤分母

| HTTP／code | 情況 | 有沒有業務寫入 |
|---|---|---|
| 400 MALFORMED | 不合法 JSON、重複 key、無法解析 query | 無 |
| 401 AUTH_REQUIRED | 缺／失效 credential | 無 |
| 403 ACTION_DENIED | target 可見但缺 action、capability 或有效分級 | 無 |
| 404 NOT_FOUND | 不存在或不可見；兩者不可由回應推知 | 無 |
| 409 REVISION_CONFLICT | expected revision／epoch 改變、搶認領／重複 key 不同 payload | 無新 effect；既有 operation 可讀 |
| 409 INVALID_TRANSITION | state、依賴／保留、獨立性、必要 Gate 不允許 | 無 |
| 413 TOO_LARGE | 超過 schema／transport 上限 | 無，不截斷 |
| 422 SCHEMA_INVALID | unknown field／enum、少欄、歧義、unsupported action/schema | 無；field errors 不回私人原值 |
| 428 PRECONDITION_REQUIRED | 缺 target／parent revision | 無 |
| 429 RATE_LIMITED | principal/action 和全域費用限制 | 無新 operation；Retry-After |
| 503 DEPENDENCY_UNAVAILABLE | DB、secret store、核定依賴不可用 | commit 狀態以 operation 讀回；不聲稱沒發生 |

not_found／ambiguous／missing_slot／wrong_target 都不改叫另一案的工具。
對 domain invalid 明示要求 client 修正 typed command；没有自然語言續句猜意思的 continuation。

## 2. 查詢、歷程與有效版本

所有 list 用 `limit=1..100`（預設50）、opaque cursor、固定順序 `(created_at,id)`。
cursor 綁 query hash、principal visibility epoch、scope、high-watermark；改 query／撤權後回409 CURSOR_STALE。
不承諾動態任務狀態的所有欄位永遠同時點：Page 明示 snapshot_id／measured_at；完整稽核用固定 revisions manifest。
filter/sort 僅下表預定欄：key/kind/lifecycle、work status/owner/team、record kind/state、artifact purpose、operation state。
history 在 high-watermark 下分頁至末頁；舊版正文仍查當次 ACL；返回 RETRACTED/STALE 不刪原PASS。
有效版要返回 `effective_state, policy_revision_id, source_revision_ids, invalidation_event_ids[]`。
搜尋只在可見資料內做，title、snippet、facet、count、suggestion 不得洩漏別案。

## 3. Request schema 詞典

記號：`?` optional；未標必填；`null` 只在明訂 nullable 欄可用。
UUID／RevisionRef／SHA 等型別見 SQL_MODEL；`reason` 1..2000字、`key` 1..80字（ASCII大小寫字母數字與 ._-，不默默改寫）、`title/name` 1..200字。
所有 mutation schema 有 `reason`；除純 self inbox ack 外也保留 command intent。
`RevisionRef={resource_id,revision_id,body_sha256}`；必須指相同 resource，不只湊三個合法值。
`SourceRef={revision:RevisionRef,locator,evidence_kind}`；locator 非空；kind=DECLARED/STATIC/SYNTHETIC/INTERCEPTED/RUNTIME/HISTORICAL。
`Scope={kind:WORKSPACE|PROJECT|SUBTREE|RESOURCE,id:uuid}`；額外 scope 必須 object ACL，不能自由字串。
`Disposition={reason, evidence_refs:SourceRef[]}`；至少一 evidence；state command 的 target 由 path 決定。

| Schema | allowlisted 欄位與限制 |
|---|---|
| WorkspaceEdit | name?,reason；至少一變更，不改 key／epoch |
| TeamCreate | key,name,parent_revision,reason |
| MemberCreate | key,name,kind HUMAN/AGENT,execution_identity_id,parent_revision,reason |
| MembershipChange | member_id,role CONTRIBUTOR/REVIEWER/READER/CONTROLLER,classification_ceiling,valid_until?,reason；最後controller保護 |
| TeamMembershipChange | team_id,role CONTRIBUTOR/REVIEWER/READER,classification_ceiling,valid_until?,reason；team不等於project controller |
| ExecutionIdentityCreate | authority_ref,organization_ref?,parent_revision,reason；只能由trusted global controller建立，普通Agent不能自證獨立 |
| CredentialIssue | expires_at,label,reason；subject=self 或另發權；scope不超原principal；server code只回一次 |
| CredentialRevoke | reason；path key 必須屬指定member |
| IdentityLink | issuer_ref,subject,proof_operation_id,reason；email不可代替subject；只連已驗人帳戶 |
| ProjectProposal | workspace_id,parent_revision,key,name,purpose,team_ids[],controller_id?,initial_plan:RecordBody,reason；server配新UUID及immutable proposal revision |
| ProjectCreate | proposal_revision:RevisionRef,reason；body不得換proposal參數；批准hash即此intent；target由proposal給定 |
| ProjectEdit | name?,purpose?,reason；controller／team另命令 |
| PlanRevise | record_revision:RevisionRef,change_note,reason；kind必為PROJECT_DOCUMENT，提交先待核定 |
| TransferRequest | to_member_id,handoff:RevisionRef,expires_at,reason |
| TransferAccept | transfer_revision:RevisionRef,reason；仅 to principal；G緊急恢復另receipt不能偽ACK |
| GrantCreate | subject_id,action,scope,expires_at?,delegable,classification_ceiling,record_kinds[]?,write_scopes[]?,reason；enum action且不能擴 grantor |
| GrantRevoke | reason；增加適用policy epoch |
| AuthorizationRequest | action,target_id,target_kind,scope,typed_payload,expected_revision,expires_at,reason；typed_payload按action對應schema，不是任意JSON |
| AuthorizationDecision | decision APPROVE/DENY,request_revision,proof_code?,reason；APPROVE必有碼，回應不含碼 |
| ItemCreate | parent_id?,parent_revision,key,kind SUBPROJECT/FEATURE/TASK,title,description:RecordBody,execution_team_id,completion_policy_revision:RevisionRef,reason |
| ItemExpand | parent_revision,children:ItemCreate[]（1..100）,dependency_edges[]?,reason；同案、全原子；children 不可暗移父 |
| ItemEdit | title?,description_revision:RevisionRef?,execution_team_id?,reason；已認領換team须handoff |
| WriteSetCreate | scope:FILE（repo_id,path,expected_blob_sha256）/SCHEMA（namespace,reservation_key）/COMPONENT（registry_id）,lease_generation,parent_revision,reason；scope閉集合、file按實際repo path，不能靠功能label避同檔碰撞 |
| DependencyChange | prerequisite_id,requirement_kind REQUIRED/INFORMATIONAL,reason；增刪均驗cycle／scope |
| Claim | intended_generation?,lease_seconds（60..1800）,reason；owner由principal給定 |
| Heartbeat | lease_id,generation,lease_seconds；僅有效owner；server timestamp；無任意state |
| Progress | reported_percent（0..100）,operational_intent WORKING/BLOCKED/HOLD/PARKED,message,next_step?,blocker_refs[]?,reason；不准提交quality／complete=true |
| HandoffRequest | to_member_id,expected_lease_generation,handoff_revision:RevisionRef,expires_at,reason |
| HandoffDecision | decision APPROVE/DENY,reason；controller scope |
| HandoffAccept | handoff_revision:RevisionRef,reason；recipient真ACK；兩方receipt |
| DeliveryCreate | change_note,source_manifest_revision:RevisionRef,source_manifest_sha256,requirement_refs:RevisionRef[],selftest_revision:RevisionRef,limitations_revision:RevisionRef,reason；manifest非空 |
| DeliverySubmit | draft_revision:RevisionRef,reason；鎖source／分母；authors immutable |
| RequirementCreate | key,applicability_kind,body:RecordBody,parent_revision,reason |
| RequirementRevise | applicability_kind,body:RecordBody,change_note,reason；旧delivery requirement binding固定 |
| GateDeclare | requirement_binding_id,name,required,risk_class P0/NORMAL,method_revision:RevisionRef,expected_revision:RevisionRef,waive_policy_revision:RevisionRef?,reason；必要格分母非空 |
| GateRun | checker_execution_identity_id（server核對principal）,input_manifest_revision:RevisionRef,environment_revision:RevisionRef,method_sha256,reason |
| GateResult | outcome PASSED/FAILED/NOT_RUN/ERROR,expected_revision:RevisionRef,actual_revision:RevisionRef,evidence_refs:SourceRef[],limitations_revision:RevisionRef,reason；至少一實際結果，獨立性再驗 |
| GateWaiver | policy_revision:RevisionRef,risk_revision:RevisionRef,expires_at,reason；P0禁止，不刪原結果 |
| Acceptance | policy_revision:RevisionRef,gate_set_sha256,requirement_set_sha256,exception_set_sha256,reason；server重新計集合，不採caller hash自證 |
| ItemClose | policy_revision:RevisionRef,accepted_delivery_id,child_set_sha256,dependency_set_sha256,runtime_evidence_refs:SourceRef[],reason；server自己重算，無需runtime的型別明示 |
| ItemReopen | change_request_revision:RevisionRef,reason |
| RecordCreate | key,kind,body:RecordBody,classification,source_refs:SourceRef[],parent_revision,reason |
| RecordRevise | body:RecordBody,classification,source_refs:SourceRef[],change_note,reason；accepted原版不覆寫 |
| RecordReview | revision:RevisionRef,outcome ACCEPT/REJECT,assessment_revision:RevisionRef,reason |
| RecordAccept | revision:RevisionRef,review_ids[],reason；author不能替自己必要審查 |
| RecordBinding | revision:RevisionRef,consumer_revision:RevisionRef,binding_kind,valid_until?,reason；未知consumer不得假活 |
| ConflictCreate | left_revision:RevisionRef,right_revision:RevisionRef,assessment_revision:RevisionRef,parent_revision,reason |
| ConflictResolve | resolution_revision:RevisionRef,disposition KEEP_LEFT/KEEP_RIGHT/SUCCESSOR/UNRESOLVED,successor_revision:RevisionRef?,reason；不LWW |
| ContextQuery | scope,purpose,record_kinds[],registry_kinds[],max_tokens（1..32000）,input_revision_refs[]?；只讀、ACL後截预算，不把截斷當完整 |
| RepoCreate | canonical_url,provider GITHUB/LOCAL_GIT,external_repo_id?,credential_reference?,allowed_refs[],parent_revision,reason；不傳secret值、不執行hook |
| RepoSync | range_ref,expected_cursor?,reason；有界／有限額；worker action固定 |
| RegistryCreate | key,kind MODULE/SYMBOL/INTERFACE/FIELD/DB_SCHEMA/PROMPT/DATA_LINEAGE,body:RegistryBody,source_refs:SourceRef[],parent_revision,reason |
| RegistryRevise | body:RegistryBody,source_refs:SourceRef[],change_note,reason |
| RegistryAccept | revision:RevisionRef,impact_review_revision:RevisionRef,reason |
| RegistryRetire | revision:RevisionRef,consumer_set_sha256,replacement_bindings[],impact_review_revision:RevisionRef,reason；server對帳，不靠檔名grep |
| Reservation | namespace MIGRATION/FIELD/FUNCTION/INTERFACE,reservation_key,owner_id,expires_at?,parent_revision,reason；同案有效UQ |
| ImpactCreate | change_revision:RevisionRef,affected_refs:RevisionRef[],assessment:RecordBody,parent_revision,reason |
| ArtifactCreate | logical_key,purpose SOURCE/EVIDENCE/CANDIDATE/ROLLBACK/BACKUP,classification,description,source_refs:SourceRef[],parent_revision,reason |
| ArtifactRevise | content_sha256,bytes,media_type,source_code_revision:RevisionRef?,protected_state_ref:RevisionRef?,change_note,reason；單個path不當identity |
| ArtifactLocation | host_ref,path_or_uri,measured_sha256,measured_bytes,measured_at,verification_kind REGISTERED_ATTESTATION/VERIFIED_BYTES,verification_evidence:RevisionRef?,reason；VERIFIED_BYTES需可核receipt |
| ArtifactReference | artifact_revision:RevisionRef,target_revision:RevisionRef,role INPUT/OUTPUT/EVIDENCE/ROLLBACK,reason |
| RetentionHold | kind SOLE_INPUT/ROLLBACK/LEGAL/ACTIVE_USE,reason_revision:RevisionRef,expires_at?,reason |
| CleanupAttestation | artifact_revision:RevisionRef,process_check:RevisionRef,mount_check:RevisionRef,replacement_evidence:RevisionRef?,released_bytes?,outcome DELETED/MOVED/RETAINED,performed_at,reason；只是實際執行者證明，不讓server直接unlink |
| TemplateCreate | key,scope,layout:TemplateBody,parent_revision,reason；scope不可擴ACL |
| TemplateRevise | layout:TemplateBody,change_note,reason |
| SavedViewCreate | key,template_revision:RevisionRef,filter:ViewFilter,historical_revision:RevisionRef?,parent_revision,reason |
| CustomFieldCreate | key,value_type STRING/INTEGER/DECIMAL/BOOLEAN/DATE/ENUM/RESOURCE_REF,nullable,enum_values[]?,classification,write_action,parent_revision,reason；不得叫owner/status/grant等保留鍵 |
| CustomFieldSet | definition_revision:RevisionRef,value,reason；value依definition具型，不接受任意object |
| ScheduleCreate | rule:ScheduleRule,timezone,misfire_policy SKIP/COALESCE/BOUNDED_CATCHUP,max_catchup（0..10）,recipient_ids[],parent_revision,reason |
| ScheduleEdit | rule:ScheduleRule?,timezone?,misfire_policy?,max_catchup?,recipient_ids[]?,reason；改rule新revision |
| NotificationAck | reason；只能self，不更改原event |
| WebhookCreate | url,secret_reference,event_types[],delivery_policy:WebhookPolicy,parent_revision,reason；正式receiver先核定 |
| WebhookEdit | url?,secret_reference?,event_types[]?,delivery_policy:WebhookPolicy?,reason；worker用exact endpoint revision |
| RetryRequest | last_attempt_id,reconciliation_revision:RevisionRef?,reason；UNKNOWN_EFFECT必有reconcile，不改delivery ID |
| PolicyBind | accepted_rule_revision:RevisionRef,compiled_kind COMPLETION/AUTHORIZATION/RETENTION/WAIVER,compiled_body:PolicyBody,parent_revision,reason；編譯結果和獨立typed schema一致；正文仍唯一在Rule |
| OIDCStart | issuer_ref,return_path；只same-origin路徑；state/nonce/PKCE由server產生 |
| OIDCCallback | code,state（provider query）；參數不進公開log；核驗後server session，不回provider token |

### 3.1 有型別的擴充本文

RecordBody 是由 kind 作 discriminator 的閉集合，不使用自由「什麼都行的報告」取代系統權限。
文字保留原文，最多128 KiB；source／counterevidence refs 各≤100；未知 schema version422。

| kind／Body | required fields；optional 以 ? 標 |
|---|---|
| REPORT | title,scope,findings[]（key,claim,evidence_refs[],limitation）,conclusion,not_measured[] |
| SUMMARY | period_start,period_end,input_revision_refs[],accomplished[],blocked[],next_steps[],limitations[] |
| RULE | title,rule_text,applies_to:Scope[],consumer_refs[],source_refs[],supersedes_refs[],effective_from?,expires_at? |
| PROJECT_DOCUMENT | title,purpose,scope_in[],scope_out[],requirement_keys[],success_definition,sections[]（key,title,markdown） |
| MEMORY | claim,evidence_refs[],counterevidence_refs[],confidence DECLARED/OBSERVED/VERIFIED,valid_until?,consumer_refs[] |
| DECISION | question,options[]（key,benefits[],losses[]）,chosen_key,authority_ref,impact_refs[],rationale |
| RISK | scenario,likelihood UNKNOWN/LOW/MEDIUM/HIGH,impact,signals[],mitigation,owner_id,next_check_at? |
| ISSUE | observed,expected,reproduction,evidence_refs[],severity P0/P1/P2/P3,owner_id?,next_step |

RegistryBody 分種；所有種都具 `description, evidence_level, limitations[]`，其餘如下。
UNRESOLVED 必須具名缺欄；可作ISSUE／提案，沒有必填producer/consumer時不造有效INTERFACE；不宣稱runtime VERIFIED。

| kind | 專用 required fields |
|---|---|
| MODULE | repo_id,commit_oid,git_algorithm,path,blob_sha256,owner_id,producer_refs[],consumer_refs[] |
| SYMBOL | repo_id,commit_oid,git_algorithm,path,blob_sha256,qualified_name,symbol_kind,signature,producer_refs[],consumer_refs[] |
| INTERFACE | producer_ref,consumer_ref,payload_schema_revision,error_contract_revision,condition_revision,transform_revision? |
| FIELD | field_path,data_type,nullable,unit?,unit_state KNOWN/NOT_APPLICABLE/UNKNOWN,grain,direction_state KNOWN/UNORIENTED/NOT_APPLICABLE/UNKNOWN,null_semantics,privacy,producer_refs[],consumer_refs[] |
| DB_SCHEMA | db_ref,namespace,table,columns[]（field_revision_ref）,migration_reservation_ref,producer_refs[],consumer_refs[] |
| PROMPT | authoritative_record_revision,renderer_symbol_ref,producer_refs[],consumer_refs[],input_schema_revision,output_contract_revision |
| DATA_LINEAGE | sources[]（RevisionRef,locator）,target_ref,transform_ref,record_ownership,grain,direction_state,coverage_revision,unresolved_keys[] |

TemplateBody：`{schema_version:1, name, sections[]}`；section為 discriminator
`METRICS(binding_keys[]) | TABLE(binding_key,columns[],filter) | BOARD(binding_key,group_by) |
TIMELINE(binding_key) | SUMMARY(record_revision_ref) | MARKDOWN(record_revision_ref)`。
binding key只指server已註冊read projection；filter為ViewFilter；column只allowlisted field path。
ViewFilter：`{project_id,kind[]?,status[]?,owner_ids[]?,team_ids[]?,since?,until?,sort:CREATED_ASC|CREATED_DESC}`。
ScheduleRule：`CHECK_IN(interval_seconds:300..86400)` 或 `DEADLINE_REMINDER(item_id,offset_seconds)`；不包含shell/LLM。
WebhookPolicy：`{max_attempts:1..10,expires_seconds:60..86400,timeout_seconds:1..30,
allowed_host_policy_revision,signature_key_version,include_body:false|true}`；include body仍逐field ACL。
PolicyBody 是schema版本化閉集合：COMPLETION（工作類型／required gate keys／runtime kinds／notes policy）、
AUTHORIZATION（delegable action allowlist／classification ceiling／capability期限）、
RETENTION（purpose／minimum保留／sole-input和rollback不得清）、WAIVER（non-P0 kinds／max期限）。
Policy不能注入SQL、Python、JS或含「放行所有」的自由expression；改schema需review/新release。

## 4. 路由及 action 清單

每行 operation_id 唯一；Action 是權限registry的 exact token，不允許request自己換名。
`—` Request 指沒有 body，仍驗path/query和ACL。純 read 不用Idempotency-Key。
公開例外只有 /healthz（最小訊號）、OIDC callback（state flow）和具簽名provider ingress。
table列舉實際要讀寫的主table，revision/event/operation共同表由§1統一負責。
mutation 的既有 target revision 由If-Match核對；nested path要對帳父/子所有權。
SQL表的工作表／enum是跨文件對帳分母，未編譯成OpenAPI與DDL；不能拿路由表當既有端點。

| operation_id | Method path | Request | Result | Action | SQL tables |
|---|---|---|---|---|---|
| workspace_edit | PATCH /workspaces/{id} | WorkspaceEdit | M | workspace.edit | workspaces |
| workspace_list | GET /workspaces | — | P | workspace.read | workspaces |
| team_create | POST /workspaces/{id}/teams | TeamCreate | M | workspace.teams.manage | teams |
| member_create | POST /workspaces/{id}/members | MemberCreate | M | workspace.members.manage | members |
| execution_identity_create | POST /workspaces/{id}/execution-identities | ExecutionIdentityCreate | M | workspace.identities.manage | execution_identities |
| team_membership_set | PUT /teams/{id}/memberships/{member_id} | MembershipChange | M | workspace.teams.manage | team_memberships |
| member_disable | POST /members/{id}/disable | Disposition | M | workspace.members.manage | members,credentials,sessions |
| credential_issue | POST /members/{id}/credentials | CredentialIssue | M＋secret_once | credential.issue.self/other | credentials |
| credential_revoke | POST /members/{id}/credentials/{credential_id}/revoke | CredentialRevoke | M | credential.revoke.self/other | credentials |
| identity_link | POST /members/{id}/identity-links | IdentityLink | M | workspace.members.manage | identity_links |
| project_propose | POST /project-proposals | ProjectProposal | M | capability.request | project_proposals |
| project_create | POST /projects | ProjectCreate | M | project.create | projects,project_memberships,project_teams |
| project_list | GET /projects | — | P | project.read | projects |
| project_edit | PATCH /projects/{id} | ProjectEdit | M | project.plan.revise | projects |
| project_plan_revise | POST /projects/{id}/plan-revisions | PlanRevise | M | project.plan.revise | projects,project_records |
| project_membership_set | PUT /projects/{id}/memberships/{member_id} | MembershipChange | M | project.membership.manage | project_memberships |
| project_team_set | PUT /projects/{id}/teams/{team_id} | TeamMembershipChange | M | project.membership.manage | project_teams |
| project_transfer_request | POST /projects/{id}/control-transfers | TransferRequest | M | project.control.transfer | control_transfers |
| project_transfer_accept | POST /control-transfers/{id}/accept | TransferAccept | M | project.control.accept | projects,control_transfers |
| project_archive | POST /projects/{id}/archive | Disposition | M | project.archive | projects,schedules |
| project_restore | POST /projects/{id}/restore | Disposition | M | project.restore | projects |
| project_delete | DELETE /projects/{id} | Disposition | M | project.delete | projects |
| project_purge | POST /projects/{id}/purge | Disposition | A | project.purge | projects,artifact_retention_holds |
| grant_create | POST /projects/{id}/grants | GrantCreate | M | permission.grant | permission_grants |
| workspace_grant_create | POST /workspaces/{id}/grants | GrantCreate | M | permission.grant | permission_grants |
| grant_revoke | POST /grants/{id}/revoke | GrantRevoke | M | permission.revoke | permission_grants |
| capability_request | POST /authorization-requests | AuthorizationRequest | M＋secret_once | capability.request | authorization_requests |
| capability_decide | POST /authorization-requests/{id}/decision | AuthorizationDecision | M | capability.approve/deny | authorization_decisions |
| capability_revoke | POST /authorization-requests/{id}/revoke | GrantRevoke | M | capability.revoke | authorization_requests |
| item_create | POST /projects/{id}/items | ItemCreate | M | item.expand | work_items |
| item_expand | POST /items/{id}/expand | ItemExpand | M | item.expand | work_items,work_dependencies |
| item_list | GET /projects/{id}/items | — | P | project.read | work_items |
| item_edit | PATCH /items/{id} | ItemEdit | M | item.edit | work_items |
| write_set_create | POST /items/{id}/write-sets | WriteSetCreate | M | item.write_set.manage | work_write_sets,write_scope_locks |
| write_set_release | POST /write-sets/{id}/release | Disposition | M | item.write_set.manage | work_write_sets,write_scope_locks |
| dependency_add | POST /items/{id}/dependencies | DependencyChange | M | item.dependencies.manage | work_dependencies |
| dependency_remove | DELETE /items/{id}/dependencies/{prerequisite_id} | DependencyChange | M | item.dependencies.manage | work_dependencies |
| item_queue | POST /items/{id}/queue | Disposition | M | item.queue | work_items |
| item_claim | POST /items/{id}/claim | Claim | M | item.claim | work_items,work_leases |
| item_heartbeat | POST /items/{id}/heartbeat | Heartbeat | M | item.heartbeat | work_leases |
| item_progress | POST /items/{id}/progress | Progress | M | item.progress | work_items |
| handoff_request | POST /items/{id}/handoffs | HandoffRequest | M | item.handoff.request | handoffs |
| handoff_decide | POST /handoffs/{id}/decision | HandoffDecision | M | item.handoff.approve | handoffs |
| handoff_accept | POST /handoffs/{id}/accept | HandoffAccept | M | item.handoff.accept | handoffs,work_leases |
| delivery_create | POST /items/{id}/deliveries | DeliveryCreate | M | item.deliver | deliveries,requirement_bindings |
| delivery_submit | POST /deliveries/{id}/submit | DeliverySubmit | M | delivery.submit | deliveries |
| delivery_retract | POST /deliveries/{id}/retract | Disposition | M | delivery.retract | deliveries |
| requirement_create | POST /projects/{id}/requirements | RequirementCreate | M | requirement.manage | requirements |
| requirement_revise | POST /requirements/{id}/revisions | RequirementRevise | M | requirement.manage | requirements,resource_revisions |
| gate_declare | POST /deliveries/{id}/gates | GateDeclare | M | gate.declare | gates |
| gate_run | POST /gates/{id}/runs | GateRun | M | gate.run | gate_runs |
| gate_result | POST /gate-runs/{id}/result | GateResult | M | gate.result.submit | gate_results,evidence_bindings |
| gate_waive | POST /gates/{id}/waivers | GateWaiver | M | gate.waive | gate_waivers |
| delivery_accept | POST /deliveries/{id}/accept | Acceptance | M | delivery.accept | acceptance_receipts |
| item_close | POST /items/{id}/close | ItemClose | M | item.close | completion_receipts,work_items |
| item_reopen | POST /items/{id}/reopen | ItemReopen | M | item.reopen | work_items |
| item_cancel | POST /items/{id}/cancel | Disposition | M | item.cancel | work_items |
| record_create | POST /projects/{id}/records | RecordCreate | M | record.draft | project_records |
| record_revise | POST /records/{id}/revisions | RecordRevise | M | record.revision.create | project_records,resource_revisions |
| record_list | GET /projects/{id}/records | — | P | project.read | project_records |
| record_review | POST /records/{id}/reviews | RecordReview | M | record.review | record_reviews |
| record_accept | POST /records/{id}/accept | RecordAccept | M | record.accept | project_records |
| record_retire | POST /records/{id}/retire | Disposition | M | record.retire | project_records,record_bindings |
| record_bind | POST /records/{id}/bindings | RecordBinding | M | record.bind | record_bindings |
| conflict_create | POST /projects/{id}/conflicts | ConflictCreate | M | record.conflict.manage | record_conflicts |
| conflict_resolve | POST /conflicts/{id}/resolution | ConflictResolve | M | record.conflict.manage | record_conflicts |
| context_get | POST /context-query | ContextQuery | ContextPack | context.read | project_records,registry_entries |
| repo_create | POST /projects/{id}/repositories | RepoCreate | M | repo.manage | source_repositories |
| repo_sync | POST /repositories/{id}/sync | RepoSync | A | repo.sync | git_sync_cursors,git_objects |
| repo_history | GET /repositories/{id}/history | — | Page<GitObjectView> | project.read | git_objects,git_parent_edges |
| git_ingress | POST /repositories/{id}/provider-events | RawProviderEvent | M | provider.ingress | git_provider_events |
| registry_create | POST /projects/{id}/registry | RegistryCreate | M | registry.propose | registry_entries |
| registry_revise | POST /registry/{id}/revisions | RegistryRevise | M | registry.propose | registry_entries,resource_revisions |
| registry_list | GET /projects/{id}/registry | — | P | project.read | registry_entries |
| registry_accept | POST /registry/{id}/accept | RegistryAccept | M | registry.accept | registry_entries |
| registry_retire | POST /registry/{id}/retire | RegistryRetire | M | registry.retire | registry_entries,impact_reviews |
| reservation_create | POST /projects/{id}/reservations | Reservation | M | registry.reserve | schema_reservations |
| reservation_release | POST /reservations/{id}/release | Disposition | M | registry.reserve | schema_reservations |
| impact_create | POST /projects/{id}/impact-reviews | ImpactCreate | M | registry.impact | impact_reviews |
| artifact_create | POST /projects/{id}/artifacts | ArtifactCreate | M | artifact.register | artifacts |
| artifact_revise | POST /artifacts/{id}/revisions | ArtifactRevise | M | artifact.register | artifacts,resource_revisions |
| artifact_location | POST /artifacts/{id}/locations | ArtifactLocation | M | artifact.register | artifact_locations |
| artifact_reference | POST /artifacts/{id}/references | ArtifactReference | M | artifact.register | artifact_references |
| artifact_hold | POST /artifacts/{id}/retention-holds | RetentionHold | M | artifact.retention.manage | artifact_retention_holds |
| artifact_hold_release | POST /retention-holds/{id}/release | Disposition | M | artifact.retention.manage | artifact_retention_holds |
| artifact_cleanup | POST /artifacts/{id}/cleanup-receipts | CleanupAttestation | M | artifact.deletion.attest | cleanup_receipts |
| template_create | POST /templates | TemplateCreate | M | template.edit | dashboard_templates |
| template_revise | POST /templates/{id}/revisions | TemplateRevise | M | template.edit | dashboard_templates,resource_revisions |
| saved_view_create | POST /projects/{id}/views | SavedViewCreate | M | template.edit | saved_views |
| custom_field_create | POST /projects/{id}/field-definitions | CustomFieldCreate | M | custom_field.manage | custom_field_definitions |
| custom_field_set | PUT /resources/{id}/custom-fields/{definition_id} | CustomFieldSet | M | custom_field.write | custom_field_values |
| schedule_create | POST /projects/{id}/schedules | ScheduleCreate | M | schedule.manage | schedules |
| schedule_edit | PATCH /schedules/{id} | ScheduleEdit | M | schedule.manage | schedules |
| schedule_pause | POST /schedules/{id}/pause | Disposition | M | schedule.manage | schedules |
| schedule_resume | POST /schedules/{id}/resume | Disposition | M | schedule.manage | schedules |
| notification_list | GET /me/notifications | — | Page<NotificationView> | notification.read | notifications |
| notification_mark_read | POST /me/notifications/{id}/read | NotificationAck | M | notification.mark_read | notifications |
| notification_ack | POST /me/notifications/{id}/ack | NotificationAck | M | notification.ack | notifications |
| webhook_create | POST /projects/{id}/webhooks | WebhookCreate | M | webhook.manage | webhook_endpoints |
| webhook_edit | PATCH /webhooks/{id} | WebhookEdit | M | webhook.manage | webhook_endpoints |
| webhook_disable | POST /webhooks/{id}/disable | Disposition | M | webhook.manage | webhook_endpoints |
| webhook_retry | POST /webhook-deliveries/{id}/retry | RetryRequest | A | webhook.retry | webhook_deliveries,webhook_attempts |
| policy_bind | POST /projects/{id}/policy-bindings | PolicyBind | M | policy.manage | policy_bindings |
| resource_get | GET /resources/{id} | — | R | resource.read | resources |
| resource_revisions | GET /resources/{id}/revisions | — | Page<RevisionView> | history.read | resource_revisions |
| resource_history | GET /resources/{id}/history | — | Page<EventView> | history.read | domain_events |
| project_history | GET /projects/{id}/history | — | Page<EventView> | history.read | domain_events |
| project_summary | GET /projects/{id}/overview | — | ProjectOverview | project.read | project_records,work_items,deliveries |
| operation_get | GET /operations/{id} | — | OperationView | operation.read | operations,operation_receipts |
| operation_reconcile | POST /operations/{id}/reconcile | Disposition | M | operation.reconcile | operations,operation_receipts |
| oidc_start | POST /auth/oidc/start | OIDCStart | LoginStart | auth.login | oidc_flows |
| oidc_callback | GET /auth/oidc/callback | OIDCCallback | 303 same-origin | auth.callback | oidc_flows,identity_links,sessions |
| session_get | GET /auth/session | — | PrincipalView | auth.session.read | sessions,members |
| session_logout | POST /auth/logout | Disposition | M | auth.logout | sessions |

credential.issue/revoke self/other 按已驗 path subject 決定action；request不能選低權的self操作另一人。
capability.decide APPROVE/DENY discriminator 同理；JSON判定結果要明示 actual action。
workspace建立在安裝時的獨立bootstrap流程，bootstrap收據與固定第一位owner由operator核定。
API不開無身分「建立全域主控」捷徑；workspace_edit不能提升role。
DELETE dependencies path必須等於payload prerequisite_id，否則422；沒有無body偷偷刪除。
context_query是純讀、不寫稽核業務狀態，不用Idempotency-Key；可選存context receipt為另受權command，這一版不暴露。
尚未成熟的跨案共享先不提供建立路由；普通操作遇跨案引用422。SQL不可因此去掉同案約束。

### 4.1 專用 read result 與入口

ContextPack：`{scope,purpose,blocks[]:{source_revision:RevisionRef,kind,classification,
content,content_sha256,evidence_kind,limitations[]},selected_set_sha256,coverage,truncated,
requested_budget,estimated_tokens,token_estimator_version,policy_epoch,measured_at}`。
ProjectOverview：`{project:ResourceView,current_plan_revision,controller,teams[],
work_state_counts,quality_state_counts,runtime_state_counts,summary_revision_ids[],
pending_gate_refs[],blocked_refs[],coverage,measured_at}`；各counts只算當次可見scope。
GitObjectView：`{repo_id,oid,algorithm,type,parents[],metadata_revision,coverage,fetched_at}`。
NotificationView：`{id,event_id,project_id,redacted_content,read_at?,ack_at?,state}`；撤權後隱正文。
PrincipalView：`{member_id,workspace_id,execution_identity_id,authentication_method,
visible_project_ids[],effective_action_summary,expires_at?}`；不回角色秘密／token。
LoginStart：`{redirect_url,flow_id,expires_at}`；issuer由server registry選，非任意URL。
RawProviderEvent：完整原body＋provider簽名、delivery ID；各provider adapter明訂大小/事件enum；
只經registered repository credential驗簽，映射受限system principal；不能當未認證任意mutation。
auth.login/auth.callback只有SSO登入效果；不允許client給role或自動取得project membership。

### 4.2 ResourceView.data 的輸出 allowlist

相同kind透過list/detail/history不返回額外未授權欄；當次role/action可以進一步減少下列欄位。
write schema不可用來序列化DB ORM全欄。類似title/name只有其實體適用者返回，不造佔位。

| 實體kind | data欄位（含nullable pointer，皆經ACL） |
|---|---|
| WORKSPACE/TEAM/MEMBER | key,name,status；MEMBER另kind,execution_identity_id；無provider tokens／secret |
| CREDENTIAL/SESSION | subject_member_id,label?,expires_at,revoked_at?；不回token/code/digest；issue只一次secret_once |
| EXECUTION_IDENTITY/IDENTITY_LINK | authority_ref,organization_ref?,issuer_ref?,subject_ref?；只manage grant可見identity detail |
| PROJECT/PROJECT_PROPOSAL | key,name,purpose,creator_id,controller_id,team_ids[],current_plan_revision_id?,policy_epoch；proposal另proposed_project_id,state,expires_at |
| GRANT/AUTHORIZATION_REQUEST | subject_id,action,scope,expires_at,revoked_at?,decision?,request_revision,payload_sha256,expected_revision,status；request正文另受ACLrevision，無原碼 |
| CONTROL_TRANSFER/HANDOFF | from_id,to_id,state,expires_at,handoff_revision_id,accepted_at? |
| ITEM | key,parent_id?,kind,title,description_revision_id,owner_id?,execution_team_id,current_delivery_id?,operational_status,reported_progress,quality_projection,completion_receipt_id? |
| WORK_LEASE/WRITE_SET | owner_id,generation,expires_at,status,scope?,expected_source_sha?；不是任意local path讀權 |
| DELIVERY | item_id,ordinal,state,source_manifest_revision_id,source_manifest_sha256,submitted_at?,gate_ids[],requirement_binding_ids[],acceptance_receipt_id?,effective_validity |
| REQUIREMENT/GATE/GATE_RUN/GATE_WAIVER | stable_key?,delivery_id?,requirement_binding_id?,name?,required?,risk_class?,method_revision_id?,expected_revision_id?,input_manifest_revision_id?,environment_revision_id?,checker_id?,status?,result_revision_id?,expires_at?,effective_validity |
| RECORD/REGISTRY/CONFLICT | key?,kind?,state,current_revision_id?,accepted_revision_id?,owner_id?,left_revision_id?,right_revision_id?,resolution_revision_id?,effective_validity |
| REPOSITORY/RESERVATION/IMPACT | canonical_url?,provider?,allowed_refs[]?,coverage_revision_id?,namespace?,reservation_key?,owner_id?,state,affected_set_sha256?；secret_reference僅manage grant可讀，無secret值 |
| ARTIFACT/LOCATION/RETENTION_HOLD/CLEANUP_RECEIPT | logical_key?,purpose?,retention_state?,content_sha256?,bytes?,media_type?,host_ref?,path_or_uri?,measured_at?,verification_kind?,target_revision_refs[]?,outcome?,released_bytes?,performed_at?；locator也須source ACL |
| TEMPLATE/SAVED_VIEW/CUSTOM_FIELD | key,owner_id?,scope?,schema_version?,layout_revision_id?,template_revision_id?,filter_revision_id?,value_type?,definition_revision_id?,value?；不返回已無权binding正文 |
| SCHEDULE/OCCURRENCE/NOTIFICATION | rule_revision_id?,timezone?,next_run_at?,misfire_policy?,state,event_id?,recipient_id?,scheduled_at?,read_at?,ack_at? |
| WEBHOOK/DELIVERY/ATTEMPT/DEAD_LETTER | canonical_url?,event_types[]?,state,delivery_id?,attempt_ordinal?,http_status?,error_code?,outcome?,expires_at?,resolution_revision_id?；secret_ref僅manage grant且不回值，response只有去敏digest |
| POLICY_BINDING | accepted_rule_revision_id,compiled_kind,compiled_schema_version,compiled_sha256,state；compiled_body按同Rule資料分級 |

各kind的正式response schema在DEV必須拆成有discriminator的具型模型，不能把上表合成自由dict。
state/quality/effective_validity由服務推導，輸入裡同名欄位一律422。
receipt中不可見artifact只顯示去敏reference，不能以path/bytes推知另一案資料。

## 5. API／MCP／Dashboard 共用與相容

REST是唯一domain command adapter；MCP與Dashboard不另寫權限／SQL策略。
MCP tool identity對上述operation_id，dynamic discovery只列當次可見action/schema；不回全域秘密。
MCP error具 `isError=true`、Error.code／request_id／operation_id；不將403/409變成成功自然語句。
async MCP回pending operation，不文字聲稱已部署/已送達；Agent可用operation_get追同ID。
人Dashboard按effective actions顯示控制；隱按鈕只是UX，後端仍拒絕直接API越權。
人批准頁先顯示subject/action/target/完整diff/影響/版本/expiry，點批准和實際consume分兩個時刻。

v0.2 23tools／34API是歷史基線，不能用它們的數量背書本表新操作已接線。
v0.2未前綴API保留為legacy adapter期間，須逐操作跑相容或明示破壞性升版。
legacy actor若仍帶body，必須等於authenticated principal；不能保留舊全域PM繞project ACL。
舊狀態／receipt不改寫；legacy無法表示新有效性時加明示讀取連結，不偽造VERIFIED。
新錯誤enum加值、限制變更、必填欄、permission模型變動均是契約release，不默默換版。
SQL migration、OpenAPI schema、MCP、Skill教材、Dashboard模板schema同release manifest釘SHA。

## 6. 完整教學的固定流程與驗收

未實作功能不提前塞進現行API Skill。本節是release時需交付的教學分母。

| 教學角色 | 必須能照步驟完成 | 必須看見的失敗 |
|---|---|---|
| Global controller | 建兩隊→註冊trusted identities→單次批准開案→授權scope→查receipt | 自批／過廣grant／最後controller刪除被拒 |
| Project controller | 核計畫→開子案/功能→write-set→分派→交接→Overview/Summary→關案 | 子項未結、未驗Gate、跨案target不能關案 |
| Contributor Agent | 自己key→讀context→claim/heartbeat→回報HOLD→交v1→successor v2→查歷程 | 冒actor、自審、progress100、錯revision、多consume被拒 |
| Reviewer Agent | 固定input/method→跑正負控→上傳evidence→FAIL→檢successor | 無實測／同identity／空分母／STALE input不能PASS |
| Human reader | SSO→Dashboard各層點歷程→看version/Gate/source/path→套Template | 別案history/context/template不漏資料 |
| Ops | schema status→受控upgrade/DOWN→備份/restore→outbox停發/重啟 | 不相容schema、破壞DOWN、未知效果不能盲重送 |

每篇同一組合成專案，標 release／OpenAPI SHA／身分／前置條件、可複製命令與request/receipt ID。
token 以environment/secret store取得，不貼真值；教材錯碼是合成值。
REST與MCP各跑同一條完整鏈，expected/actual分開；手冊不能以endpoint存在充當可用證據。
API Skill更新時再使用skill-creator；本輪不把設計候選安裝成已可用Skill。

## 7. 定版／驗收界線

設計自檢：operation ID/Method+path不重複、Request schema皆具名、Action矩陣皆有規則、SQL table皆定義。
DEV驗收：同版OpenAPI schema編譯、request正反controls、真Postgres transaction/鎖與rollback、REST/MCP parity、browser ACL。
真環境：SSO／Webhook receiver／Git增量／羽思接入／部署restore／長期運作仍按完成矩陣逐格驗。
本文件沒有執行新API、migration或真模型呼叫；沒有把上述設計結果當成產品已PASS。
