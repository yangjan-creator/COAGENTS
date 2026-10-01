# COAGENTS 狀態轉移、併發與失敗恢復詳細規格 v1

作者／責任歸屬：滴。2026-10-01。設計候選；沒有執行這些狀態轉移測試。
路由和權限分別見 [API_CONTRACT](API_CONTRACT.md)、[AUTHORIZATION_MATRIX](AUTHORIZATION_MATRIX.md)。

## 1. 狀態不可混成一個百分比

分開儲存：resource lifecycle、work operational status、delivery quality、deployment/runtime observation、
capability authorization、operation effect、reported progress。人Dashboard並列，不取最好看的那格當整體完成。
`reported_progress=100` 只表示作者回報，不能導出ACCEPTED/RUNTIME_VERIFIED/CLOSED。
下列全是新契約；v0.2狀態的原義保留在舊revision／receipt，不批次改名冒稱新policy已驗。

## 2. Project與resource lifecycle

| From | Command→To | Guard | 失敗／副作用 |
|---|---|---|---|
| 無 | create→ACTIVE | create grant、creator/controller/membership、完整計畫欄、UQ key、預期revision0 | 原子建案與controller；不留無主project |
| ACTIVE | archive→ARCHIVED | 本案action、列pending work/operation、controller確認 | 排程／未出站operation暫停；歷史仍可讀 |
| ARCHIVED | restore→ACTIVE | 本案action、policy/owner仍有效、expected revision | 恢復不自動重發舊外送／補跑模型 |
| ACTIVE/ARCHIVED | delete→TOMBSTONED | delete權／capability、impact、依賴/retention允許、原revision | 只tombstone；引用者BLOCKED/STALE，原件/Git不刪 |
| TOMBSTONED | restore→ARCHIVED | 尚在保留窗、未purge、有主控、資料可復原 | 默认封存，主控再明示啟用 |
| TOMBSTONED | purge→PURGED | 另權、保留到期、無hold、二步批准、完整影響/備份 | 由受控operation，留下去敏receipt；不把實檔刪除混在其中 |

last controller/member刪除不合法；交接後原member可停用，但歷史作者ID留下。
取消單項與刪專案不同action；project archive也不等於工作已完成。

## 3. 工作與交付

工作 operational status：`DRAFT, QUEUED, WORKING, READY_FOR_REVIEW, VALIDATING, BLOCKED, HOLD, PARKED, CLOSED, CANCELLED`。
quality從current delivery及binding計算，不提供progress端自由寫入。

| From | Command→To | 誰／Guard |
|---|---|---|
| DRAFT | queue→QUEUED | controller或scoped contributor；scope/completion/write-set已定 |
| QUEUED/WORKING/BLOCKED/HOLD/PARKED | claim→WORKING | claim grant、execution team、未被他人有效認領；不能偷lease |
| WORKING/READY_FOR_REVIEW/VALIDATING | progress→WORKING/BLOCKED/HOLD/PARKED | owner；實際結果、下一步/阻點，不能改版本quality |
| WORKING | submit delivery→READY_FOR_REVIEW | owner；source manifest、requirement分母、selftest/限制；source固定 |
| READY_FOR_REVIEW | begin gate run→VALIDATING | 指定獨立reviewer，method/input/environment固定 |
| VALIDATING | required FAIL→BLOCKED | server以result推導；作者不能改回VERIFIED |
| READY_FOR_REVIEW/VALIDATING | all required acceptable→READY_FOR_REVIEW | server質量=ACCEPTED；operational仍待部署或結案政策 |
| 非CLOSED/CANCELLED | create successor→WORKING | owner；ordinal+1，舊票保留；active quality重算 |
| 非CLOSED/CANCELLED | close→CLOSED | controller；quality、子項、依賴、runtime/policy、notes全部可接受 |
| 非CLOSED | cancel→CANCELLED | controller；impact/原因/未完成effect；不產完成receipt |
| CLOSED/CANCELLED | reopen→QUEUED | 明示change request、controller、影響分母與新revision；不偷改旧完工票 |

`close`不要求所有文檔任務部署；completion policy先定 DOCUMENT/CODE/DEPLOYABLE/DATA_DELIVERY類型。
需runtime的工作必有相符環境觀察；靜態／合成／攔截三者不能替代真使用者入口。
子項/依賴集合在close tx中鎖project並釘hash，新增必要子項必須重開root或先做change request。

Delivery state：`DRAFT, SUBMITTED, IN_REVIEW, ACCEPTED, REJECTED, SUPERSEDED, RETRACTED`。
DRAFT可改草稿revision；SUBMITTED後source/requirement/gate分母不可原地變更。
新input/method/門檻修正需要successor或新的核定review scope；不得刷相同source找到一個PASS抹FAIL。
新delivery成current時舊ACCEPTED仍是真歷史，但effective validity按binding可為STALE。
SUPERSEDED不聲稱舊版錯；RETRACTED須原因與操作者，保留原結果。

## 4. Gate、record與registry

| 物件 | 開始／轉移 | 終態規則 |
|---|---|---|
| Gate definition | DECLARED→scope frozen | requirement/method/expected/input/environment/分母具名；0必要格NOT_DECLARED |
| Gate run | QUEUED→RUNNING→PASSED/FAILED/NOT_RUN/ERROR | run result immutable；ERROR/NOT_RUN不算PASS |
| Gate waiver | 已有FAIL或未執行→waiver receipt | policy允許、controller獨立批准、理由/到期；P0安全不允許 |
| Gate有效性 | 舊PASS＋source/policy/environment改→STALE | 不改歷史PASS；新impact指明哪些scope失效 |
| ProjectRecord | DRAFT→PROPOSED→ACCEPTED或REJECTED | accepted body固定；下一次改动新revision |
| Rule/Memory | ACCEPTED→SUPERSEDED/RETIRED/CONFLICTED | consumer差集/反證/影響具名；不以latest text解真相 |
| Registry entry | PROPOSED→ACTIVE→DEPRECATED→RETIRED | identity/source/consumer齊全；UNKNOWN側向/來源不得升VERIFIED |
| Artifact | REGISTERED→VERIFIED_AT_SOURCE 或 ATTESTED_ONLY | path登錄不等於服務讀過bytes |
| Artifact清理 | PROTECTED或REFERENCED→deny；允許→cleanup receipt | 原件/rollback/進程/mount/replacement驗證；服務不碰任意path |

Record accept與Gate pass不是同一action；報告accepted也不證它報的產品功能真的可用。
claim/write-set的owner和content reviewer分開；兩位API principal是否真獨立需要受信identity和policy。

## 5. Lease與交接

Lease：`ACTIVE→STALE→RELEASED/REPLACED`；heartbeat只能自己的generation更新。
STALE不自动解除owner，不让另一Agent抢進來；controller審停點後可approve handoff。
handoff：`REQUESTED→APPROVED→ACCEPTED` 或 `DENIED/CANCELLED/EXPIRED`。
接受者必須以自己的principal ACK；同tx換owner、lease generation、相關write-set，產兩方receipt。
to_id/停點/source改動使原approval失效；僅「通知已送」不代表接手完成。

## 6. Authorization與operation

| From | Event→To | 必要檢查 |
|---|---|---|
| 無 | request→REQUESTED | typed payload、有效scope、code digest、到期；不能用request當execute |
| REQUESTED | approve→APPROVED | proof code、approver scope、非同identity、未到期、epoch/revision |
| REQUESTED | deny→DENIED | 原因/approval actor；terminal |
| REQUESTED/APPROVED | revoke/expire→REVOKED/EXPIRED | server clock、撤權、policy轉移；terminal |
| APPROVED | 同tx成功consume→CONSUMED | subject/action/target/payload/revision/epoch一致；UQ usereceipt |
| APPROVED | domain rollback→APPROVED | 不留下use receipt/半完成state；原可用期內可受控重試 |
| CONSUMED | identical idempotent retry→同receipt | 不增加uses；仍驗現在principal權限與可見性 |

Operation：`PROPOSED→COMMITTED→QUEUED→RUNNING→SUCCEEDED/FAILED/UNKNOWN_EFFECT/CANCELLED`。
純SQL mutation在COMMITTED便有成功domain receipt，不偽裝要外送；有外部effect則HTTP202且pending。
批准/consume/COMMITTED不能等同外部SUCCEEDED；worker terminal receipt不能反改授權歷史。
UNKNOWN_EFFECT需reconcile evidence；無法證外部未執行時不得盲retry建立另一operation。
reconcile不重新執行業務effect；只能以具名外部證據追加SUCCEEDED/FAILED或仍UNKNOWN_EFFECT的receipt。
原UNKNOWN_EFFECT收據保留，operation current_receipt pointer帶revision換頭；不是改寫已出的receipt。

## 7. Outbox、排程與外送

Outbox：`PENDING→LEASED→ACKED`；可證安全retry→`RETRY_PENDING`；超限→`DEAD_LETTER`；撤權→`CANCELLED`。
lease expiry不是外送失敗證據；已開始HTTP但沒receipt走UNKNOWN_EFFECT，不把workercrash當沒送。
Webhook at-least-once：delivery ID不變，attempt ordinal+1；receiver以delivery ID去重。
若receiver不支持去重且未知效果，人工reconcile，不承諾只投一次。
排程occurrence按scheduled instant唯一码；skip/coalesce/catch-up政策固定；pause/resume不偷偷補發全部。
Notification：UNREAD→READ→ACKNOWLEDGED；REVOKED正文隱藏。READ不等於owner認領或交付。
GET inbox不自動標READ；mark_read/ack是self受權mutation。Schedule為ENABLED/PAUSED/DISABLED；
pause→resume只重算下一個有界occurrence，不自動把停用期間全部送出去。

## 8. 併發與crash boundary逐格證明

| 邊界 | 故障／競爭 | 預期可讀證據 | 恢復／停止 |
|---|---|---|---|
| API驗權後、tx前 | revoke/transfer同時來 | final epoch重驗失敗，domain無write | 403/409，重新申請 |
| 能力consume、domain前 | DB exception | tx rollback：use=0/state未改/outbox0 | 同key可重試，不能有孤consume |
| domain更新、commit前 | 進程kill | domain/event/outbox同回滾 | 不回報完成 |
| commit後、response前 | client timeout | 原operation＋receipt存在，重送相同key返回它 | 不新建operation |
| 兩Agent claim/version/close | 同時操作 | 仅一claim成功/ordinal唯一/closed集合完整 | loser409，讀最新revision |
| 兩worker領同occurrence | lease競爭 | 一个有效generation、notification一份 | stale owner受fencing拒寫 |
| HTTP出門前 | secret缺／endpoint撤權 | 未出網attempt error/cancel，outcome非success | 停發／具名缺設定 |
| HTTP已到receiver、ACK前 | workercrash | receiver receipt/delivery ID與本機UNKNOWN_EFFECT | receiver去重或人工reconcile |
| Git sync中途 | cursor未commit | 已有object/event UQ，重送不重複 | 續cursor，不刪舊歷程 |
| migration中途 | DDL/data failure | applied ledger未產生、attempt FAILED、舊schema可用或明示停窗 | rollback/指定restore，不正常啟動錯schema |
| restore後worker啟動 | 舊outbox/keys還在 | recovery epoch/stop flag阻外送，key重新核定 | operator批准resume，舊receipt仍可讀 |

每條至少一個正控證會完成、一個故障反例證指定格紅；不只看全程rc非零。
這張表是預期結果，不是本輪實跑actual；動態驗收必須分開寫expected/actual與實際環境。
