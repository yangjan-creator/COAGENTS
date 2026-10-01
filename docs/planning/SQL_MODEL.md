# COAGENTS SQL 模型與升降版詳細規格 v1

作者／責任歸屬：滴。2026-10-01。
候選邏輯／物理模型；本文件不含可執行migration，不建立任何表。
正式DB為PostgreSQL；基線是v0.2，不把工作樹尚未接入的models當現有DDL。

## 1. 通用型別、權威與引用

- 公共ID為 `uuid`；公開key為 `varchar(80)`，同workspace下唯一，不當授權憑證。
- 時刻為 `timestamptz`；timezone為獨立IANA字串；bytes/序位/revision為 `bigint` 且非負。
- SHA-256為 `char(64)`、小寫hex CHECK；git object ID為 `varchar(64)`＋algorithm，不將短SHA當身份。
- 狀態為受CHECK限制的 `varchar(32)`；已定枚舉見 [STATE_MACHINES](STATE_MACHINES.md)。
- 下表 `?` 是nullable、`[]` 是有schema的JSONB array；沒標 `?` 是NOT NULL。
- `id` PK、`created_at`、`created_by`每個實體必有；member tombstone不刪歷史creator FK。
- immutable revision/result/event/receipt只INSERT；current head/cache可UPDATE但帶revision guard和audit。
- 不用 `ON DELETE CASCADE` 把歷史證據一起刪掉；預設FK RESTRICT。Purge是獨立policy/作業。

資源共同頭 `resources`：
`id uuid PK, workspace_id uuid FK, project_id uuid? FK, kind varchar(32), revision bigint,
lifecycle_state varchar(32), data_classification varchar(16), created_by uuid FK,
created_at timestamptz, updated_at timestamptz, tombstoned_at timestamptz?, tombstone_reason text?`。
`UNIQUE(id,workspace_id)`、`UNIQUE(id,project_id)`與`UNIQUE(id,kind)`供複合FK；kind不變。
`resources(project_id,workspace_id)`複合FK指`projects(id,workspace_id)`，後者有同型UNIQUE；
nullable project_id只限已列workspace kinds，不得把A workspace資源掛B workspace專案。
同project引用使用 `(ref_id,project_id)`複合FK；不靠只有UUID的FK默許跨案。
domain表PK=id FK resources，附constant `resource_kind` CHECK＋`(id,resource_kind)` FK，禁止型別错接。
PROJECT資源的project_id等於自己的id；初始化cycle用同tx與DEFERRABLE FK，不分兩次提交孤頭。
workspace級資源project_id=NULL，只允許指定kinds，需服務／DB CHECK，不能靠NULL绕ACL。

`resource_revisions`：
`id uuid PK, resource_id uuid FK, ordinal bigint, schema_id varchar(80), schema_version int,
body_json jsonb, body_sha256 char(64), author_id uuid FK, source_refs jsonb[],
classification varchar(16), created_at timestamptz`；`UNIQUE(resource_id,ordinal)`。
另有`UNIQUE(id,resource_id)`供current/accepted revision pointer的同resource複合FK。
body須通過typed schema；安全／scope／grant／recipient等查權欄位不塞入任意body_json。
每個current revision有FK回同resource；accepted引用精確revision，不只current pointer。

## 2. 身分與權限表

| 表 | 主要欄位（不含通用id/時間/作者） | 約束／索引 |
|---|---|---|
| workspaces | key, name, status, policy_epoch bigint | UQ key；epoch≥1 |
| teams | workspace_id, key, name, status | UQ(workspace_id,key) |
| members | workspace_id, key, name, kind HUMAN/AGENT, status, execution_identity_id | UQ(workspace_id,key)；同workspace identity FK |
| execution_identities | workspace_id, authority_ref, organization_ref?, registered_by | UQ(workspace_id,authority_ref)；普通Agent不可自建 |
| team_memberships | team_id, member_id, role, valid_from, valid_until?, revoked_at? | 同workspace複合FK；有效membership UQ(team_id,member_id) partial |
| identity_links | member_id, issuer, subject, linked_by, linked_at, revoked_at? | UQ(issuer,subject)；不以email作合帳key |
| credentials | member_id, kind, token_digest, key_version, expires_at?, revoked_at? | UQ token_digest；讀API永不出digest |
| sessions | member_id, session_digest, csrf_digest, auth_time, expires_at, revoked_at? | UQ session_digest；refresh/provider tokens若必要只存外部secret reference |
| oidc_flows | flow_digest, issuer_ref, state_digest, nonce_digest, pkce_verifier_secret_ref, return_path, expires_at, consumed_at? | UQ flow_digest/state_digest；same-origin return_path；one-use flow不因重播callback建新session |
| projects | workspace_id, key, name, purpose, creator_id, controller_id, policy_epoch, current_plan_revision_id? | UQ(workspace_id,key)；creator immutable；controller ACTIVE且scope受控 |
| project_proposals | workspace_id, proposed_project_id, proposer_id, proposal_revision_id, expected_workspace_revision, expires_at, state | UQ proposed_project_id；提案不可換內容；author及new UUID由server釘定；非已建project |
| project_memberships | project_id, member_id, role, classification_ceiling, grant_source, revoked_at? | 有效UQ(project_id,member_id) partial；不能把team membership當永久案權 |
| project_teams | project_id, team_id, role, revoked_at? | 同workspace；有效UQ(project_id,team_id) partial |
| control_transfers | project_id, from_id, to_id, expected_epoch, status, accepted_at?, expires_at, reason | 同案lock；有效pending UQ(project_id) partial；最後controller不可刪 |
| permission_grants | workspace_id, project_id?, subject_id, action, scope_kind, scope_resource_id?, expires_at?, delegable bool, classification_ceiling, issued_epoch, revoked_at? | CHECK scope結構；index(subject_id,action,revoked_at)；不可自由SQL条件 |
| authorization_requests | workspace_id, project_id?, requester_id, action, target_id, target_kind, payload_sha256, payload_revision_id, expected_revision, code_digest, expires_at, workspace_epoch, project_epoch?, status | UQ code_digest；所有binding immutable；status index |
| authorization_decisions | request_id, approver_id, decision, reason, request_revision, decided_at | 一request一terminal decision；拒自批/同execution identity |
| capability_uses | request_id, operation_id, executor_id, consumed_at | UQ request_id；UQ operation_id；與domain改動同tx |
| policy_bindings | project_id, accepted_rule_revision_id, compiled_kind, compiled_schema_version, compiled_body_json, compiled_sha256, state | 原文權威只在RULE；編譯投影受閉schema、exact source revision；改原Rule後STALE，不能偷偷換policy |

code/token/session均高熵隨機值，不用此digest方法儲存人密碼；本版不提供自建密碼庫。
Grant的 typed conditions另有 `grant_record_kinds(grant_id,kind)`、`grant_write_scopes(grant_id,resource_id)`，
需要新condition時改schema，不塞未校驗expression。

## 3. 工作、交付與驗收表

| 表 | 欄位 | 約束／索引 |
|---|---|---|
| work_items | project_id, key, parent_id?, kind, title, description_revision_id, execution_team_id?, owner_id?, current_delivery_id?, completion_policy_revision_id, operational_status, reported_progress smallint | UQ(project_id,key)；progress0..100；parent同案、kind階層與cycle檢查；policy exact binding revision；index(project_id,parent_id) |
| work_dependencies | project_id, item_id, prerequisite_id, requirement_kind | UQ(item_id,prerequisite_id)；不可自己依賴、跨案/cycle拒絕；index(prerequisite_id) |
| work_leases | item_id, owner_id, generation bigint, issued_at, heartbeat_at, expires_at, status | 有效lease UQ(item_id) partial；stale不自動换owner |
| work_write_sets | delivery_id或item_id, repo_id?, file_path?, schema_key?, component_id?, expected_source_sha? | exact file/scope單位；排他lease用owner/generation，不以label避衝突 |
| write_scope_locks | workspace_id,canonical_source_id,scope_kind,scope_key,item_id,owner_id,lease_generation,status,expires_at | 有效UQ(workspace_id,canonical_source_id,scope_kind,scope_key) partial；同repo被兩案綁定仍共用canonical source身份；過期不自動搶占 |
| handoffs | item_id, from_id, to_id, expected_lease_generation, status, handoff_revision_id, expires_at | 有效pending UQ(item_id) partial；原owner不可偷換target |
| deliveries | item_id, ordinal, author_id, source_manifest_revision_id, source_manifest_sha256, state, submitted_at?, accepted_receipt_id? | UQ(item_id,ordinal)；submitted後source固定；index(item_id,ordinal) |
| requirements | project_id, stable_key, current_revision_id, applicability_kind, retired_at? | UQ(project_id,stable_key)；requirement變更不回寫舊gate |
| requirement_bindings | delivery_id, requirement_revision_id, scope_id?, applicable bool, exclusion_reason? | UQ(delivery_id,requirement_revision_id,scope_id)；NULL粒度以顯式scope ID表示避免NULL UQ漏 |
| gates | delivery_id, requirement_binding_id, name, required bool, waive_policy, method_revision_id, expected_revision_id | UQ(delivery_id,requirement_binding_id,name)；分母凍後不得刪必要格 |
| gate_runs | gate_id, checker_id, checker_execution_identity_id, method_sha256, input_manifest_revision_id, environment_revision_id, started_at, finished_at?, status | index(gate_id,started_at)；作者獨立性在開始與提交兩次驗 |
| gate_results | gate_run_id, outcome, expected_sha256, actual_sha256, evidence_revision_id, limitation_revision_id, submitted_at | UQ gate_run_id；immutable結果；run NULL/空分母不能PASS |
| gate_waivers | gate_id, policy_revision_id, risk_revision_id, approver_id, expires_at, reason_revision_id | P0 CHECK/validator拒絕；保持原FAIL/NOT_RUN；到期失效而非改原result |
| evidence_bindings | project_id, result_id, artifact_revision_id?, source_resource_revision_id?, binding_kind, observed_at, valid_until? | exact revision與scope；至少一source；校驗kind与可見性 |
| acceptance_receipts | delivery_id, policy_revision_id, accepted_by, gate_set_sha256, requirement_set_sha256, exception_set_sha256, accepted_at | UQ(delivery_id,policy_revision_id)；保存有效分母，不只bool |
| environment_observations | project_id, delivery_id, environment_revision_id, code_commit, image_digest?, marker_evidence_revision_id, observation_kind, observed_at | 舊環境票與現況分開；index(project_id,environment_revision_id) |
| completion_receipts | item_id, accepted_delivery_id, child_set_sha256, dependency_set_sha256, runtime_evidence_set_sha256, policy_revision_id, approved_by, closed_at | current completion不可自述覆寫；新任務/版本須重開或change request |

依賴圖的變更鎖同project；子項完工／新增／刪除與root結案須同序列鎖，防新增子項被結案漏掉。
結果的STALE是有效性投影，不改舊PASSED；source revisions、policy與環境變更產impact event。
gate結果追加新run，FAILED不刪；「新run修正」是否適用由policy和input revision决定，不能刷到綠覆蓋不同版本。
既有v0.2 terminal gate仍只讀，migration不得把它改成可重寫的當前結果。

## 4. 知識、程式、欄位與資料流

| 表 | 欄位 | 約束／索引 |
|---|---|---|
| project_records | project_id, key, kind, current_revision_id, accepted_revision_id?, state, owner_id | kind=REPORT/SUMMARY/RULE/PROJECT_DOCUMENT/MEMORY/DECISION/RISK/ISSUE；UQ(project_id,key) |
| record_reviews | record_revision_id, reviewer_id, outcome, reason_revision_id | immutable；獨立審/來源條件由policy決定 |
| record_bindings | record_revision_id, consumer_resource_id, consumer_revision_id?, binding_kind, valid_from, valid_to? | consumer具名；index(consumer_resource_id,valid_to) |
| record_conflicts | project_id, left_revision_id, right_revision_id, reason_revision_id, resolution_revision_id?, state | 不按last-write-wins自解；same/supersedes需receipt |
| source_repositories | project_id, canonical_url, provider, external_repo_id?, secret_ref?, allowed_range, state | UQ(project_id,canonical_url)；URL/userinfo/redirect受validator |
| git_sync_cursors | repo_id, cursor_kind, cursor_value, last_success_at?, coverage_revision_id, state | UQ(repo_id,cursor_kind)；force-push記新coverage，不刪舊object |
| git_objects | repo_id, object_id, algorithm, type, metadata_revision_id, fetched_at | UQ(repo_id,algorithm,object_id)；metadata有source事件 |
| git_parent_edges | repo_id, child_object_id, parent_object_id, parent_ordinal | UQ(child,parent_ordinal)；object引用同repo |
| git_provider_events | repo_id, provider_event_id, payload_sha256, validated_at, state | UQ(repo_id,provider_event_id)；重送不同sha必紅 |
| registry_entries | project_id, key, kind, owner_id, current_revision_id, accepted_revision_id?, state | UQ(project_id,key)；kind=MODULE/SYMBOL/INTERFACE/FIELD/DB_SCHEMA/PROMPT/DATA_LINEAGE |
| code_symbols | entry_id, repo_id, commit_object_id, path, blob_sha256, qualified_name, symbol_kind, signature_revision_id, confidence_kind | UQ(repo,commit,path,qualified_name)；DECLARED/STATIC/RUNTIME分層 |
| interface_edges | entry_id, producer_id, consumer_id, payload_schema_revision_id, transform_revision_id, error_contract_revision_id, condition_revision_id | 同案或明示shared binding；producer/consumer不可NULL寫「未知」混過 |
| field_definitions | entry_id, field_path, data_type, nullable bool, unit?, unit_state, grain, direction_state, privacy, null_semantics_revision_id | side/grain必填；UNKNOWN不能宣稱ACTIVE_VERIFIED |
| schema_reservations | project_id, namespace, reservation_key, owner_id, state, expires_at?, applied_source_revision_id? | 有效UQ(project_id,namespace,reservation_key) partial |
| registry_source_bindings | entry_revision_id, source_resource_revision_id, locator, transform_revision_id?, evidence_level | 非空locator/sha由source revision提供；未驗原件不能RUNTIME |
| impact_reviews | project_id, change_revision_id, affected_set_sha256, status, reviewed_by?, assessment_revision_id | UNASSESSED不可當無影響；差集保留逐成員 |
| context_pack_receipts | project_id, consumer_member_id, purpose, input_revision_set_sha256, policy_epoch, budget_tokens?, created_at | index(project,consumer,created_at)；收到的是逐塊source，不只一段長prompt |

Rule與Memory不是另建各一套文字表；project_records＋typed revisions維持唯一內容權威。
向量/全文是derived index；撤權/過期/刪除先filter，不因索引命中泄露已無權正文。
如需跨案sharing先建shared resource binding＋兩案批准；不直接移除same-project FK。
本版未提供cross-project sharing command，跨案source引用一律拒絕；「可另案設計共享」不構成本版FK例外。

## 5. Artifact與模板

| 表 | 欄位 | 約束／索引 |
|---|---|---|
| artifacts | project_id, logical_key, owner_id, current_revision_id, purpose, retention_state | UQ(project_id,logical_key)；不再全系統path唯一 |
| artifact_locations | artifact_revision_id, host_ref, normalized_path或object_uri, measured_sha256, measured_bytes, measured_at?, verification_kind | path是位置非身份；REGISTERED_ATTESTATION/VERIFIED_BYTES分層；no arbitrary file-serving |
| artifact_references | project_id, artifact_revision_id, target_resource_revision_id, role | UQ(artifact_revision,target_revision,role)；與exact revision绑定 |
| artifact_retention_holds | artifact_id, kind, reason_revision_id, issued_by, expires_at?, released_at? | 未release不可purge；唯一input/rollback保護 |
| cleanup_receipts | artifact_revision_id, executor_id, process_check_revision_id, mount_check_revision_id, replacement_evidence_revision_id?, released_bytes?, outcome, performed_at | 服務只記實檔檢查/attestation；不以API讀路徑刪檔 |
| dashboard_templates | workspace_id, project_id?, team_id?, owner_id, current_revision_id, accepted_revision_id? | 明示scope XOR；模板不擴權 |
| saved_views | project_id, owner_id, template_revision_id, filter_revision_id, historical_revision_id? | query參數typed；不能存任意SQL |
| custom_field_definitions | project_id, key, value_type, schema_revision_id, owner_id, state, write_action | UQ(project_id,key)；改type需impact和資料遷移 |
| custom_field_values | resource_id, definition_revision_id, typed_value jsonb | UQ(resource,definition_revision)；validator+分類/ACL；安全欄不能自定替代 |

同path改內容要新artifact revision／measurement；不能覆蓋以前sha或被迫造另一path當現行身份。
不儲存多GB副本；host_ref/path能讓人知道內容在哪、誰建、何時清，不給任意shell權。

## 6. Operations、排程、通知、Webhook

| 表 | 欄位 | 約束／索引 |
|---|---|---|
| operations | project_id?, requester_id, action, target_id, payload_revision_id, payload_sha256, idempotency_key, status, policy_epoch, current_receipt_id?, created_at, finished_at? | UQ(requester_id,action,idempotency_key)；same key不同payload拒絕；receipt pointer同operation複合FK |
| operation_receipts | operation_id, ordinal, outcome, domain_revision_id?, result_revision_id, external_effect_kind, supersedes_receipt_id?, finished_at | UQ(operation_id,ordinal)；append-only；operation指一effective head；UNKNOWN_EFFECT→reconcile新增receipt，不改原未知效果證據 |
| domain_events | project_id?, operation_id, event_type, aggregate_id, aggregate_revision, payload_revision_id, sequence bigint, occurred_at | UQ(aggregate_id,aggregate_revision,event_type)；append-only |
| outbox_entries | event_id, destination_kind, destination_id, payload_revision_id, due_at, state | UQ(event_id,destination_kind,destination_id)；index(state,due_at) |
| worker_leases | outbox_id或occurrence_id, owner, generation, expires_at, heartbeat_at | target XOR；有效UQ(target) partial；fencing generation |
| notifications | project_id, event_id, recipient_id, redacted_revision_id, read_at?, ack_at?, revoked_at? | UQ(event_id,recipient_id)；index(recipient_id,read_at,created_at) |
| schedules | project_id, owner_id, rule_kind, rule_revision_id, timezone, next_run_at, misfire_policy, state | bounded catch-up；index(state,next_run_at) |
| schedule_occurrences | schedule_id, schedule_revision_id, scheduled_at, operation_id, state | UQ(schedule_id,scheduled_at)；rule更新不重送已產時點 |
| webhook_endpoints | project_id, canonical_url, secret_ref, allowed_event_types, policy_revision_id, state | endpoint配置有revision，code/key不存值 |
| webhook_deliveries | outbox_id, endpoint_id, endpoint_revision_id, delivery_id, state, expires_at, next_attempt_at? | UQ(outbox_id,endpoint_id)；deliveryID跨retry固定 |
| webhook_attempts | delivery_id, attempt_ordinal, lease_generation, started_at, ended_at?, http_status?, error_code?, response_digest?, outcome | UQ(delivery_id,attempt_ordinal)；有限byte摘要，无secret |
| dead_letters | source_operation_id, source_delivery_id?, reason_code, last_attempt_id?, acknowledged_by?, resolution_revision_id? | 不刪原attempt；人工retry回同delivery |

外送snapshot與recipient/endpoint policy撤權需協調：出站前重驗epoch；送出途中撤權不得虛稱追回。
未知外部效果走reconciliation，不以回滾SQL掩蓋已發出的網路請求。

## 7. Migration／備份／鎖與保留

Migration ledger：`migration_id PK, predecessor_id?, ddl_sha256, applied_at, applied_by, code_commit,
schema_before_sha256, schema_after_sha256, data_validation_revision_id`；DDL/ID不可原地改。
另一張migration_attempts記開始/停止/失敗；失敗不冒稱applied。runtime role無DDL/ledger寫權。
PG單一migration advisory lock；DDL不得默默忽略已存在但不同的column/index。

鎖順序固定：workspace→project→item/resource→operation→authorization request→outbox/lease。
批次resource按UUID排序，避免不同order死鎖；遇可重試DB衝突有限retry，外部effect不重做。
所有新增mutable row帶revision；更新WHERE id＋expected revision，rowcount≠1回409。
索引至少覆蓋前表列出的查詢；query plan/數據量驗收後加新index，不因「可能用到」先全加。

備份索引留 `backup_id, owner, bytes, sha256, source_release, schema_revision, encryption_key_ref,
destination, retained_until, protected_state, restore_receipt_ref`；secret value不與檔一起公開。
restore receipt逐表count/identity-set/references及policy/epoch校验，對outbox先停發。
副本使用/清理與backup保留是兩種purpose；尚未證good替代不刪sole rollback/input。
DB/API audit append-only指正常角色不能改；高權DB owner仍可改，外部簽名/備份可提供篡改偵測，不能稱防所有管理员。

## 8. v0.2導入與DOWN順序

1. 保留v0.2基線DDL和既有資料fixture；只讀量實際DDL/row/ref/actor來源。
2. 精確符合才adopt baseline；不拿當次schema自產expected後自認正確。
3. additive tables先建，舊member/team/project對映待核定；不直接猜新controller。
4. public API compatibility adapter走新授權，不保留舊global PM後門。
5. 橋接讀取對帳，限制write-set；核定後才切current pointer。旧receipt保持原義。
6. DOWN先看新表非空／引用／外部effect和舊client相容；無損可逆才執行。
7. 不可逆則拒絕DOWN，提供明示受控restore方案；不能把drop新功能資料叫可逆。

本文件的型別/約束要由核定migration編成DDL後才有SQL執行證據；這輪没有建立DDL或執行資料庫升降版。

## 9. API與表的型別閉合要求

下表的field簡寫是物理模型候選，不能由ORM自行猜型別。新DDL逐欄具名型別／nullable／default／FK／CHECK／index。
SQL compiler／migration階段必須交可檢查schema manifest；未編DDL的此輪不宣稱constraint已生效。
SYSTEM worker也必須有受限member principal與created_by，不能填空作者／冒project controller。
enum與typed JSON schema以API_CONTRACT閉集合為依據；安全欄獨立columns，不信任body_json擴權。
所有revision pointer要帶resource_id複合FK；同project FK不因目標看似UUID而省略。
`source_manifest_sha256`只指manifest byte身份，不宣稱是整個repo所有bytes的直接hash。
submission要對manifest逐成員檢查，不以驗manifest自身hash取代驗它列出的source。
純query不寫context_pack_receipts；此表保留給明示受權的後續記錄操作，不在GET或context query暗寫。

物理型別預設：`*_id`與`*_revision_id`是uuid FK（git `object_id`例外為OID字串＋algorithm）；
`*_at`與`valid_from/valid_until/expires_at`為timestamptz；`*_sha256/*_digest`為char(64) hex；
`bytes/revision/ordinal/generation/sequence/epoch/*_seconds`為非負bigint；reported_progress為0..100 smallint；
`nullable/delegable/required/applicable`為boolean；狀態/kind/role/action為有閉集合CHECK的varchar；
原字／描述／理由／locator/path/URI為text且有輸入長度限制；typed lists和compiled_body為schema-checked JSONB。
default只有明訂值：revision=1，reported_progress=0，new work=DRAFT，new record=DRAFT，
new proposal=PROPOSED，capability=REQUESTED，max_uses=1。時間以DB UTC clock；所有scope/author/target不設隱式default。
credentials.token_digest、sessions.session_digest、code_digest是hash不是secret值；不得用default空字串。
