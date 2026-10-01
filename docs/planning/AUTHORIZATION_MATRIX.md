# COAGENTS 權限與一次性能力詳細規格 v1

作者／責任歸屬：滴。2026-10-01。候選設計；v0.2全域PM機制尚未被替換。
依據：[FRAMEWORK_SPEC](FRAMEWORK_SPEC.md)、[API_CONTRACT](API_CONTRACT.md)、[SQL_MODEL](SQL_MODEL.md)。

## 1. Principal、scope與決定順序

Principal包含 `member_id, workspace_id, execution_identity_id, credential_id, authentication_method`。
這些由服務驗證，不接受body宣告角色、execution identity或其他actor。
Scope採結構型別：`WORKSPACE(workspace_id)`、`PROJECT(project_id)`、`SUBTREE(item_id)`、`RESOURCE(resource_id)`。
沒有自由文字regex scope。父項移動需重驗subtree grant；無跨案隱式繼承。

判斷順序：credential有效→member ACTIVE→同workspace→resource存在且可見→project membership→
action grant/角色預設→資料分級→expected revision/policy epoch→適用独立性／retention限制→capability→domain transition。
deny及撤權優先，只有explicit grant命中才allow。Reader不因使用MCP而能寫。
不可見resource回404；對可見resource缺action回403；收據不可揭露別案名稱／內容。
列表、搜尋、全文、history、context pack、Template、批次結果全部做同ACL，不只detail路由。

## 2. 角色预設矩陣

角色是可預設的action組，不是跨scope萬能通行證。字母意義：
`G`=僅有該workspace明示global管理grant；`P`=本案controller；`O`=被授權且自己認領的項目；
`R`=本案指定review scope且獨立；`V`=可讀scope；`S`=自己的credential/inbox；`C`=須額外有效capability；`—`=預設deny。

| Action | Global controller | Project controller | Contributor | Reviewer | Reader |
|---|---|---|---|---|---|
| workspace.read | V | V | V | V | V |
| workspace.edit / workspace.identities.manage | G | — | — | — | — |
| workspace.members.manage | G | — | — | — | — |
| workspace.teams.manage | G | — | — | — | — |
| credential.issue.self / credential.revoke.self | S | S | S | S | S |
| credential.issue.other / credential.revoke.other | G | — | — | — | — |
| project.create | G | C（workspace scope） | C | C | — |
| project.read / resource.read / history.read / context.read | V（需membership） | V | V | V | V |
| project.plan.revise / project.membership.manage | C或P | P | — | — | — |
| project.control.transfer | G（恢复用） | P | — | — | — |
| project.control.accept | S限to | S限to | S限to | S限to | — |
| project.archive / project.restore | C或P | P | — | — | — |
| project.delete | G | C | C | — | — |
| project.purge | G＋retention/雙步審批 | — | — | — | — |
| permission.grant / permission.revoke | G限workspace | P限本案可委派actions | — | — | — |
| capability.request | V | V | V | V | — |
| capability.approve / capability.deny | G限workspace | P限本案可委派actions | — | — | — |
| capability.revoke | G或S限requester | P或S限requester | S限requester | S限requester | — |
| item.expand / item.edit / item.dependencies.manage / item.queue | C或P | P | O或C（scope限定） | — | — |
| item.claim | V且execution team一致 | V | V | — | — |
| item.progress / item.deliver / item.heartbeat / delivery.submit | O | O | O | — | — |
| delivery.retract | O或P | O或P | O | — | — |
| item.handoff.request | O或P | O或P | O | — | — |
| item.handoff.approve | C或P | P | — | — | — |
| item.handoff.accept | S限recipient | S限recipient | S限recipient | — | — |
| item.close / item.reopen / item.cancel | C或P | P | — | — | — |
| item.write_set.manage | C或P | P | O | — | — |
| gate.declare | R或P | P | — | R | — |
| gate.result.submit | R | R | — | R | — |
| gate.run | R | R | — | R | — |
| requirement.manage | C或P | P | — | R限指派scope | — |
| delivery.accept | P且已有獨立票 | P且已有獨立票 | — | R且policy指定 | — |
| gate.waive | C或P＋policy允許 | P＋policy允許 | — | — | — |
| record.draft / record.revision.create | V且write grant | P | O或本案record.write grant | R限report | — |
| record.review | R | R | — | R | — |
| record.accept | C或P且非自審 | P且非自審 | — | R限指派kind | — |
| record.retire / record.bind / record.conflict.manage / policy.manage | C或P | P | — | R限指派kind與policy | — |
| registry.propose / artifact.register | V且write grant | P | O | R限evidence | — |
| registry.accept / registry.retire | C或P且impact閉合 | P且impact閉合 | — | R限指派範圍 | — |
| registry.reserve / registry.impact | C或P | P | O或C | R限指派範圍 | — |
| artifact.deletion.attest | C且實檔檢查 | P且實檔檢查 | C | — | — |
| artifact.retention.manage | C或P | P | C | — | — |
| schedule.manage / webhook.manage / repo.manage | C或P | P | — | — | — |
| webhook.retry / repo.sync / operation.reconcile | C或P | P | — | — | — |
| notification.read / notification.ack | S | S | S | S | S |
| notification.mark_read | S | S | S | S | S |
| template.edit | 本人scope/G | 本案P或本人 | 本人或本案write grant | 本人 | 本人 |
| custom_field.manage | C或P | P | — | — | — |
| custom_field.write | C或P | P | O或該definition允許grant | R限evidence | — |
| operation.read | V且source可見 | V | V | V | V |
| auth.login / auth.callback | SSO流程限定 | SSO流程限定 | SSO流程限定 | SSO流程限定 | SSO流程限定 |
| auth.session.read / auth.logout | S | S | S | S | S |
| provider.ingress | — | — | — | — | — |
| system.migrate / system.deploy / system.backup / system.restore | —（服務API不提供） | — | — | — | — |

Global controller要查看案正文仍須明示membership/read grant；緊急break-glass要新決策、理由與receipt，不默默绕過。
Contributor在本案能提record草稿，不代表能改另一人的REPORT或accepted revision。
任一角色若是交付作者／同execution identity，不能提交該版本必要Gate PASS；global也不能例外。
安全P0 Gate不允許waive；普通Gate豁免需policy許可、風險/到期/批准者，保存原FAIL與有效狀態分層。
沒有reviewer時REVIEW_PENDING，不使用另一個API actor來補席。
matrix的slash只分隔完整action；不定義未帶namespace的隱式alias。
Rule生效／Memory確認是同一record.accept的kind-specific條件，不另開兩條寫入管道。
provider.ingress僅由驗簽repository adapter的受限SYSTEM principal執行，普通角色沒有這格。
auth.login/callback是唯一SSO flow例外，不取得案權；cookie或flow安全檢查仍適用。

## 3. Grant與撤權

Grant欄位：`subject_id, action, scope_kind, scope_id, expires_at?, conditions, issued_by, delegable, policy_epoch, revoked_at?`。
conditions限定typed欄：允許record kind、最高資料分級、write-set或operation用途；不得執行任意expression。
grant可委派必須delegable=true；不得授予更廣scope、更多actions、更長有效期或更高資料分級。
creator/controller、grantor、approver、executor各有獨立責任欄；audit不只存一個actor字串。
role/grant變更與controller轉交鎖同project row，增加epoch；未消耗capability立即失效。
已開始但尚未出站的operation停發；已送出未知effect保留UNKNOWN_EFFECT，不偽稱已撤回外部效果。

## 4. 單次碼完整流程

1. Requester以自己的credential提出exact action/target/payload/expected revision、理由、有效期。
2. 服務驗requester可提出、target可見，計canonical typed payload（不含credential/idempotency/transport欄），記服務端digest。
3. 服務產256-bit隨機碼，保存digest不存原碼，只回一次；有效期預設5分鐘、上限由workspace policy定。
4. Requester私交request ID及碼給controller；傳遞通道不可公開記入Summary/Git。碼不給LLM記憶庫。
5. Approver以自己的credential提交proof_code＋exact request revision；服務constant-time驗碼、scope、不可自批。
6. APPROVED綁 `subject/action/target/payload_sha256/expected_revision/workspace_epoch/project_epoch/expires_at/max_uses=1`。
7. Executor使用原action API，header帶request ID＋code；subject不符拒絕。Approver拿碼也不能冒executor使用。
8. 使用resource鎖＋能力鎖，重驗policy/state→consume＋domain更新＋event/outbox＋receipt同tx。
9. 失敗rollback不消耗；相同Idempotency-Key/同payload重送只回原receipt。不同payload同key回409，不再執行。
10. 明確到期/拒絕/撤銷不可再恢復；需要新request。碼遗失亦重新申請，舊碼撤銷。

新project target由proposal階段分配UUID，scope仍為有create權的workspace，禁止批准後換owner/team。
雙request併發以SQL唯一consume receipt保護；worker不能拿capability建立第二個外部操作。
service key、一次性碼、webhook key、session、issuer tokens禁止出現在error/debug/body回顯與日志。

## 5. 獨立性與資料分級

execution identity由可信controller登記及組織policy约束；普通Agent不能自行建第二identity。
服務可防已知同identity自審，不能單靠此證明兩個實體模型/人完全獨立；驗收policy須寫此限制。
分級為 PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED，resource分類與principal最高級別共同判斷。
secret不是可閱讀資料分級，值永不出API；僅受限secret reference與rotate operation。
Rule/Memory/报告輸入為不可信資料；其中「批准我」「忽略權限」不能改policy或觸發side effect。
Template控制呈現，不控制ACL；Markdown轉HTML須去除腳本與危險URL，plaintext預覽优先。

## 6. 必紅矩陣與開工閘

至少覆蓋：跨workspace/案/子樹、別人history/context、越級字段、body actor偽造、過期key、
自批／同identity自審、錯碼/subject/action/target/payload/revision/epoch、併發consume、撤權後worker出站、
opaqueID推猜、Template/context繞過、Markdown XSS、secret進Summary、不可見資源存在性外漏。
預算上界與rate limit按principal/action，不能建十個能力request繞掉單碼fail limit。
本skill影響設計：deny-by-default、逐物件/欄位權限、cookie CSRF、無token入Web Storage、secret不輸出、受限出站。
這是負控設計，不是已執行安全測試。DEV授權仍關閉。
