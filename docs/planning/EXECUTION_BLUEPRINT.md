# COAGENTS 剩餘建設執行藍圖 v1

作者／責任歸屬：滴。2026-10-01。
狀態：規劃候選；既有程式、DB、部署未因本文件改變。
這是 [完整產品計畫](../PROJECT_PLAN.md) 的落地補充，不是第二份專案主資料。
要求分母與真實完成條件見 [COMPLETION_MATRIX.md](COMPLETION_MATRIX.md)；本文件的名稱／路由均為候選設計，未實作。

## 1. 先後順序與開工閘門

| 階段 | 動作 | 此時不能做什麼 | 下一步依據 |
|---|---|---|---|
| E0 規劃核定 | 確定scope、主控/批准者、驗收policy、角色/API與環境限制 | 不部署未接入草稿、不產功能通過票 | 使用者核定的plan revision |
| E1 Migration底座 | 固定v0.2 schema、建版本/checksum與guarded CLI、真PG保資料升降版 | 不猜舊資料owner、不靠create_all做未知升級 | R01與B01–B10適用回歸 |
| E2 安全底座 | 專案ACL、controller/membership、scoped grants、單次operation、revisions | 不把可讀文檔Rule當可執行grant | X01–X03/R01通過 |
| E3 知識與開發 | typed revisions、context、Git/symbol/interface/field、write lease與impact | 不另寫一套資料權威、不複製Git當第二棵原文庫 | X04–X08與baseline相容 |
| E4 持久工作 | notification、scheduler、outbox/webhook與Git增量worker | 不自動發供應商LLM、不拿排程權當任意shell權 | R02–R04、R06失敗/恢復全過 |
| E5 真身分與試行 | SSO與Agent token、羽/思兩案+共同案、Dashboard教學 | 不以合成actor當真人接入 | R05/R07、X07 |
| E6 正式環境 | 候選release、host/TLS/secrets、migration/rollback、備份restore、觀察 | 無核定窗不動現役環境，觀察未滿不完工 | R08–R10完成收據 |

每階段交付具名版本、allowed write-set、schema變化、回退方案、實跑證據與未關項。
不是先把全部程式塞進一次發布；完整目標不縮掉，實作按相依分段。

## 2. SQL 升級／回退：不只是建立表

正式支援的控制庫以PostgreSQL為驗收對象；SQLite只供本機單元測試，不能替PG鎖／migration背書。
推薦使用標準版本化migration工具；選型與依賴版本在E1開工前查核，不現在捏造已有CLI。

候選CLI contract：

| 操作 | 輸出 | 不變量 |
|---|---|---|
| status | engine/server/schema rev、migration checksum、compatibility | 只讀，不自動更表 |
| plan upgrade | 實際schema與目標DDL差、資料風險、lock/停窗預估 | 不產生把現況自認正確的恆真期望 |
| upgrade target | transition receipt、before/after、實際rows與errors | 独立DDL版本、單一runner锁、失敗rollback |
| plan downgrade | destructive check、compatibility、受影響資料/feature | 有新資料／引用不相容即停止 |
| downgrade target | reversible receipt | 不暗自drop資料；不可逆需明示另案匯出/恢復方案 |
| bootstrap | 符合baseline新庫 | 既有非空不符合schema，不得當新庫覆蓋 |

v0.2導入流程：讀目前DDL→與固定commit的獨立baseline比對→核對差集→通過才stamp baseline。
版本migration與upgrade/downgrade的候選機制參考 [Alembic 官方教學](https://alembic.sqlalchemy.org/en/latest/tutorial.html)；選型未等於接入。
導入不猜creator/controller：從既有audit可定位的列附來源；無來源以MIGRATION_REVIEW_PENDING待人工指派。
啟動只檢查相容schema；錯version/漂移即拒絕服務，不在startup默默migrate。
Postgres migrator與runtime用不同角色；runtime無DDL權。環境DB憑證不寫入公開範例配置。
測試至少：新庫、v0.2含历史fixture、空/非空DOWN、重複啟動、同時migration、半途失敗、未知schema。
restore是獨立R09，不把一個DOWN綠當備份可用。

## 3. Operation 與一次性權限：所有寫入的共同邊界

寫入必帶idempotency key、expected_revision，principal由認證得出；不信任Agent自報actor。
核心關係為 `operation_proposal → authority_decision → capability → operation_receipt`。
固定actor/scope/action/target/canonical payload hash/policy epoch/過期時刻；raw code僅顯示一次。
批准不能擴大批准者本來的權限；同execution identity不能以換actor名字自批。
碼與實際狀態更新同tx：驗證→條件鎖→消耗→改狀態→audit/outbox→commit。
外部動作僅在commit後由worker處理，能力不供worker重播；worker重試同operation/delivery ID。
Timeout未知外部效果標UNKNOWN_EFFECT，不能偽稱失敗後再發新操作。
單次grant不自動變常設grant；主控轉交/revocation使未使用grant失效。
先完成這層，才能安全上Webhooks、授權開展與刪除。

## 4. 排程與通知：提醒不是自動開發

| 物件 | 候選欄位 | 狀態／責任 |
|---|---|---|
| Schedule | project、rule type、IANA timezone、next_run_at、misfire policy、creator、revision | ENABLED/PAUSED/DISABLED；主控可管本案 |
| Occurrence | schedule revision、scheduled instant、operation ID、lease/deadline | 計畫時刻作去重，不用worker當前秒鐘 |
| Notification | source_event ID、recipient ID、scope、redacted摘要、read_at、ack_at | read≠ACK≠任務開始 |
| WorkerReceipt | attempt、lease owner、start/end、outcome、error code | 可查crash/retry，不靠log猜 |

check-in默认只產inbox提醒；分析、LLM、部署/刪除不是Schedule類型可隨意夾帶的字串。
時區保存名稱和UTC instant；遇重複/不存在本地時刻的處置先明訂，默認每個occurrence只一份。
missed policy採coalesce、skip或明示有限catch-up；不能重啟後補一萬條通知。
兩worker按lease領取；新notification與source event綁唯一码，崩潰不多寄一份內部inbox。
送出/讀取當下再驗recipient權限；撤權後僅保留「有已撤回事件」的去敏提示，不洩舊正文。
測時使用可控clock及拋棄式DB；仍需真worker重啟與雙worker證據，mock sleep不能替代。

## 5. Webhook：唯一outbox，不與Notification複製狀態

Domain event→同tx OutboxEntry→Delivery→Attempt→ACK/DEAD_LETTER。
簽名覆蓋固定原始payload bytes與時戳；endpoint secret僅作secret reference，不向Agent顯示值。
Git入站的secret/payload簽名驗證參考 [GitHub 官方文件](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)；COAGENTS出站的時戳與重播policy是本案設計，不能誤称GitHub簽名已有這些欄位。
event_id與delivery_id固定；attempt ID分開。receiver以delivery_id去重，重試不產新業務事件。
記status code、耗時、受限response摘要；secret/header/raw私人內容不入log。
有限backoff+jitter/max_attempts/過期窗，人工retry要新receipt但仍同delivery identity。
endpoint disabled/revoked後不再送；未完成attempt與未知effect如實保留。
allowlist、TLS、DNS/resolved IP、每次redirect與proxy環境均受檢；正式模式拒私網/localhost。
測試用明示test-only loopback receiver，不能把此allowlist帶進正式模式；不發真人通知。
必紅：錯簽名、篡改body、replay、redirect私網、dns再綁定、超大/超慢response、workercrash。
最後需核定receiver真收到且ACK的一筆；單純outbox INSERT不算Webhook接通。

## 6. Git 歷程同步：證據源，不是自動授權源

repo由本案controller綁定canonical URL/remote identity、可讀branch/range、credential reference。
初次以有界cursor抓commit/父鏈/PR/CI；增量pull與Webhook events共用provider_event id冪等。
已登錄交付的full commit不可被branch移動、force-push或同名repo替換。
history覆蓋率獨立記：完整到哪一個commit、是否shallow、缺權/暫時不可取、force-push事件。
符號登錄綁repo＋fullcommit＋blob SHA＋qualified name；line number只作該blob內locator。
CI check只填相應「該版本測試結果」；不可同時批准產品決策/合併PR/正式部署/完工。
無網路、rate-limit、壞簽名、錯repo、cursor中斷能續跑，不重抓所有歷史。
不執行repo hooks、不checkout未信任repo再執行任意腳本。
測試repository先用COAGENTS自身或本機臨時Git；指定真repo增量sync是獨立接入證據。

## 7. SSO 與人／Agent 身分分層

SSO屬本案必要完成項，部署所需issuer/client/人員由使用者指定，不由Agent代建帳戶。
人登入走受驗證OIDC flow；Agent保持獨立service credential，不挾人cookie續用。
subject以(issuer,sub)绑定，不以相同email靜默合帳；合帳需已登入身分與批准receipt。
ID token與subject驗證要求依 [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation) 與 [Claim Stability](https://openid.net/specs/openid-connect-core-1_0.html#ClaimStability)；本案session/ACL仍由COAGENTS管。
驗issuer/audience/state/nonce/過期與適用PKCE；provider role claims不能直接取得COAGENTS controller。
Dashboard用服務端session及HttpOnly/Secure cookie；不將SSO bearer token放sessionStorage。
cookie寫入路由做CSRF防護；API key路由也必須保持同一resource ACL。
logout、停用member、撤session/key、provider不可用與break-glass都需有receipt與負控。
至少一個核定真issuer上兩個測試人帳戶，驗正常登入及跨案deny；合成JWT只算單元測試。
不公開client secret、不把人員token交給Agent。

## 8. 知識／欄位／Code 不只是備註文字

ProjectRecord共用revision authority；各kind有schema与狀態，不把所有東西塞自由JSON。
Field registry必記unit/grain/方向/NULL語義/producer/consumer/privacy；interface必記schema與變換。
RuleBindings與source-bindings連到使用者；退役節點先列consumer與接手者，不靠檔名搜尋結論。
AI產出是帶source revision的candidate；若輸入變版，推薦變STALE，不自行生效。
Current Summary/MD/DataMap由accepted records／bindings產生；人修改MD需受revision guard。
API context pack需選scope、purpose與budget，每塊留ID/revision/來源；被引用文件不授予權限。
服務可保存可解釋理由，不要求或保存模型隱藏思維鏈。
歷程查閱與檔案locator須同ACL；正文被purge时保留安全receipt，但不永久保留敏感全文。

## 9. 人用Dashboard與教學的驗收情境

導航不是新建另一套狀態：Portfolio→Project→Item→Delivery→Gate→Evidence→source。
授權桌面需顯示實際diff/後果/subject/scope/expiry；PM點批准≠操作已完成。
工作台明示stale lease、PENDING/FAILED/NOT_RUN、各版本差異、目前環境及rollback owner。
資料圖點某欄位可查producer/consumer/退役影響，core code返回精確repo/blob，而非新副本。
Template預覽、修改/歷史、匯入/匯出均留revision；unknown binding拒絕，不執行SQL/JS。
教程分persona：global owner、project controller、contributor、reviewer、human reader、ops。
每篇具成功receipt、缺權/衝突/重送例、何時找PM；REST與MCP用同schema并實跑。
不能把母計畫的候選路由提前寫成現有Skill操作；教學與版本一起發布。

## 10. 羽／思接入：不能用我們表演代替

在核定接入窗中由羽、思各領自己的credential，選實際小型工作，不先灌歷史庫。
各有專案controller与協作規則；共同案只給必要team/project membership。
兩人實際讀規則→開展/認領→回報阻點→交付固定版本→指定獨立者驗→Summary→查舊歷程。
至少一個錯scope負控、一個拒驗後successor、一個跨團隊交接；真人ACK不是偽造API actor。
記舊tmux/文檔工具仍需做什麼，遷移哪些狀態到COAGENTS，source evidence不強搬。
現有羽球Z2/Z2z/VPS3寫權不因COAGENTS接入而轉給服務；真寫仍守原owner和部署規則。
日常回饋記issue/usage receipt，使用者確認不必靠旁路文檔找目前版本後才關R07。

## 11. 正式部署、備份還原與長期觀察

需要使用者選：host/domain/TLS、TLS終端owner、OIDC issuer、backup位置/retention、實際release owner。
部署包釘image digest、schema range、code commit、config fingerprint（不含secret）、rollback相容窗。
範例Compose仅dev：現值預設DB帳密与容許空admin模式不能冒稱安全正式配置。
正式啟動需強制認證、專用runtime DB角色、只曝受TLS保护API；secret經部署secret store。
遷移由獨立操作runner，API只驗schema；不借服務帳戶自動DDL。
備份包括SQL資料/角色策略/版本與物件locator；secret來源另留復原方式，不把secret明文打包。
還原至乾淨隔離環境，驗專案/成員/版本/gate/records/events/outbox/leases/references守恒。
pending外送不得在restore副本自動發出；恢復新epoch/認證撤銷與排程resume需operator批准。
備份checksum、加密、權限、owner、保留及不可刪唯一rollback點，均有實跑證據。
RPO/RTO先核定再量；建議起點RPO≤24小時/RTO≤60分鐘，未演練不宣稱達標。
建議7日初期穩定觀察＋30日回顧；觀察窗由使用者核定，實際長期需求不被這個建議縮掉。
觀察包含真使用、queue/workercrash recovery、backup/restore、權限撤銷、磁碟、未知副作用、失敗率。
健康檢查只報所覆蓋依賴；不把health200當登入/外送/restore/使用者體驗全部成功。

## 12. 本輪自檢與開工前缺項

工具自檢skill的共通要求在此落為：REST/MCP/Dashboard→同授權→typed validator→SQL transaction→receipt，沒有隱藏LLM二次決策。
Primary route是原生API；Secondary route是MCP/人Dashboard調同API；owner由核定action/resource identity決定，不由文檔文字改route。
TACLAW的NL04/planner leaf/trace_sanitize/ToolRegistryV2不適用：本repo是COAGENTS `apc.api`/`apc.mcp.server`，不修改TACLAW碼。
成功需權威receipt/state readback；not_found/ambiguous/missing_slot/unauthorized/conflict/unknown_effect不得包成完成文字。
需要外部選擇的項目：DEV核定、真issuer、真host/backup/receiver、羽／思接入窗與獨立驗收者、長期觀察policy。
沒有以上權限不偷偷接入；能先完善的計畫/分母/合成測試設計持續記入CG-PLAN。
