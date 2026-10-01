# COAGENTS 全範圍完成矩陣

作者／責任歸屬：滴。2026-10-01。
狀態：規劃補頁，未核定、未授權 DEV；不是已完成票。
母計畫：[PROJECT_PLAN.md](../PROJECT_PLAN.md)。母計畫 v1 固定內容以 [PLAN_V1_SNAPSHOT.md](PLAN_V1_SNAPSHOT.md) 為準。

## 1. 本輪依據與範圍

原目標完整保留：已有 Dashboard、多團隊、認領／進度、交付／驗證／歷程、PM Summary、檔案登錄、Template、REST／MCP／教學；仍須完成排程、通知、Webhook、SSO、正式 SQL 升降版、Git 歷程自動同步、羽／思真實接入、正式部署、備份還原與長期運作。
使用者另要求的主控 Agent、單次授權、開展／刪除 API、Rule／Memory／程式／Function／欄位／接點控制，亦不能因原目標清單較短而刪掉。

現況來源：[current_state_20261001.json](current_state_20261001.json)。
量法：本機認證 GET `/healthz`、`/openapi.json`、限定 `CG-PLAN` 的 `/workspace`，容器三檔 `sha256sum` 對公開 v0.2 commit；未匯入工作樹草稿、未重建容器。
當次 34 個 OpenAPI 操作；固定來源 AST 列出 23 個 MCP tool。數字僅對該收據承重。
`docs/VERIFICATION.md` 是以前的檢查紀錄，本輪未把它冒稱重新跑過。
實做範圍只在本機自用專案；真 LLM 0、VPS／羽球庫操作 0。

## 2. 已有功能保留與回歸分母

「v0.2 可用」不是「新版本仍已驗」；每次發布需對核定版本重驗適用格。

| ID | 原功能 | 現有依據及限制 | 下一版必須保留的證據 |
|---|---|---|---|
| B01 | 人用 Dashboard | 原 screenshot／browser smoke 為歷史證據；当前 `/dashboard` 路由存在 | 新版本瀏覽器實跑：登入、查案、點歷程、錯誤狀態、窄螢幕；不能只驗 HTTP 200 |
| B02 | 多團隊協作 | `project_teams`、API、既有合成測試 | 兩個有不同身分的團隊協作，同案可見、別案不可见，撤權後查閱失敗 |
| B03 | 認領與進度 | CG-PLAN 六子項真實認領／回報 | 併發認領不搶佔、具名 blocker、進度100不變完工、交接可追溯 |
| B04 | 交付版本 | CG-PLAN 現有交付及 v1→v2 嘗試歷史 | 各版固定來源SHA，旧票不替新版本背書，序位併發唯一 |
| B05 | 驗證紀錄 | 四格真實 PENDING；舊合成測試有 PASS/FAIL | FAIL不可抹掉、必要格非空、檢查者獨立性、目前版本與環境相符 |
| B06 | 歷程 | `/projects/{id}/history`、`/items/{id}/history` | 分頁無漏／重、任一狀態可回來源事件及revision、ACL覆蓋舊版 |
| B07 | PM Summary／Overview | CG-PLAN已寫入並讀回 | revision、來源引用、衝突／撤回、SQL本文与MD转换可對帳 |
| B08 | 檔案登錄 | 原件path/SHA/bytes及固定計畫快照 | 同路徑不同內容有版本關係；註冊與實驗檔分層；引用保護與cleanup receipt |
| B09 | 自訂 Template | JSON型別與歷史rendering smoke | 同schema實際render、版本／匯入／回退、任何binding不突破ACL |
| B10 | REST／MCP／教學 | 當次34操作／23tool；固定API Skill | 三端契約一致、錯誤不被MCP吞、教學逐步實跑、舊客戶相容或明示升版 |

這十格以「有基線；新版本回歸待跑」表述，不由路由存在推導 UX／安全完整通過。

## 3. 原目標未完成項：逐項離場條件

下表全部尚未達成。相依指下一步建設順序，不是刪掉其他項目。

| ID／自用 task key | 目前缺口 | 交付＋通過證據 | 必紅反例／失敗處置 | 相依／需誰核定 |
|---|---|---|---|---|
| R01／CG-PLAN-MIGRATE | runtime仍create_all；工作樹baseline草稿未接入 | 新庫及v0.2既有資料UP；guarded DOWN；版本/校驗碼/只讀status；PG實跑；舊記錄與引用保留 | 漂移schema、重複序號、同時兩個migrate、含新資料破壞性DOWN均拒絕；留原庫，不啟動不相容API | P1；使用者准DEV，migration owner |
| R02／CG-PLAN-SCHEDULE | 無排程路由／worker | 指定時區check-in；過期/停用/恢復；雙worker仅領一次；重啟後missed policy；有receipt | 重播同occurrence、撤權、crash後不重複副作用；錯誤進dead-letter，不盲重跑模型 | R01＋授權/operation底座 |
| R03／CG-PLAN-NOTIFY | 無通知API | 真事件→持久化inbox→recipient實際讀取/ACK；未讀與處理分開；不越案 | 撤權後不能看到原正文；跨案receiver不收；通知沒ACK不當認領 | R01＋專案ACL |
| R04／CG-PLAN-WEBHOOK | 無WebhookAPI/outbox執行 | 同tx outbox、簽名、retry/去重、disable/dead-letter、局部網路receipt；真正配置receiver收到 | 改body/錯簽名、重播、私網/redirect SSRF、receiver timeout、權限撤銷；停發不抹receipt | R01＋出站policy；receiver由使用者選定 |
| R05／CG-PLAN-SSO | 僅API key；無SSO入口 | 核定OIDC issuer/client上真登入、帳號連結、logout/撤權、Agent key互不繞權；無token入瀏覽器持久儲存 | 錯issuer/audience、nonce/state不符、過期、role claim擴權；deny並留去敏事件 | SSO在本目標是必要項，不因母計畫提「可選」而消失；需issuer/client/人帳戶 |
| R06／CG-PLAN-GITSYNC | 僅source_ref/commit/PR登錄 | 受控repository綁定、初次歷程、增量commit/PR/CI同步；full commit父關係；重播與force-push分層 | 錯repo、偽event、force-push不能抹已驗交付；CI綠不自動結案 | R01＋ACL；需指定可讀repo與授權 |
| R07／CG-PLAN-ONBOARD | 自用合成角色≠羽／思接入 | 羽、思各真principal、各自案和一共同案；至少一條真認領→交付→獨立驗收→Summary→查歷程工作鏈；雙方確認日常可用 | 模擬兩個actor不得當兩人；未完成格如實PENDING；不匯入/改現有羽球真庫 | P1–P5；羽／思本人與指定驗收者、接入窗 |
| R08／CG-PLAN-DEPLOY | localhost Compose不是正式部署；範例DB凭证與空admin模式不能上線 | 核定host/domain/TLS/secret/ports/health/owner；新容器對同SHA；必填認證與最小DB角色；回退窗 | 空admin、範例密码、暴露DB/管理口、錯schema、不合版本即拒啟動；按窗回退 | release驗收＋實際環境授权 |
| R09／CG-PLAN-RESTORE | 無備份還原驗收 | 加密備份、owner/保留/SQL schema/SHA；乾淨環境真restore；各類資料及receipt守恒；復原後撤銷／重發憑證流程 | 壞備份、缺secret、錯migration、唯一rollback刪除必紅；原備份留證 | R01＋正式backup destination/owner |
| R10／CG-PLAN-SOAK | 無長期運作證據 | 核定觀察窗及SLO；真流量、worker重啟、磁碟/queue/失敗率/備份演練紀錄；明示實際起訖，不縮時間 | 未滿觀察窗、待處理死信、未修安全缺陷不得宣稱完工；保留owner/next_check | 正式部署後；建議7日初期＋30日回顧，最終窗由使用者核定 |

## 4. 擴充需求：不能被未完成清單掩蓋

| ID | 必須保留的完整需求 | 通過證據／負控 |
|---|---|---|
| X01 | 開案者為本案主控；跨團隊且主控不可任意跨案 | 代開/轉交/接手/撤權/policy epoch；另一案不因PM字串放行 |
| X02 | 細粒度API＋一次性安全碼 | subject/action/target/payload/revision綁定；單tx consume；併發重播僅一receipt；自批、碼外洩必紅 |
| X03 | 展開／刪除／恢復／取消／引用保護 | tombstone和purge分離；一案刪除不刪Git或原件；不可移除最後controller |
| X04 | Project Report／Summary／Rule／MD／Memory | typed record与revision、有效版、來源／反證／衝突／consumer；AI提案不能自己使policy生效 |
| X05 | 核心CODE／FUNCTION／欄位／接點／schema控管 | exact source commit＋field grain/producer/consumer；退役雙向差集；靜態≠runtime；側向未證不verified |
| X06 | 真實開發／驗收／完工 | write-set/lease、版本、需求分母、正負控、execution identity、runtime scope、root推導，不靠progress100 |
| X07 | 人用Dashboard、自由Template、API／MCP／Skill完整教學 | 人能點整案→版本→證據；Agent流程教程實跑；模板不執行任意JS/SQL、不繞ACL |
| X08 | 副本內容／路徑／保留與實際釋放 | bytes/SHA/source/owner/目的/依賴/lease、實檔檢查與清理receipt；大DB不進Git/reports；唯一輸入保護 |

## 5. 狀態與證據規則

- `NOT_IMPLEMENTED`：公開／服役契約沒有功能；工作樹草稿不算。
- `IMPLEMENTED_NOT_ACCEPTED`：程式可執行但缺適用驗收；不能把單元測試冒稱接入/正式驗收。
- `PENDING_AUTHORITY`：需DEV批准、環境/issuer/owner等外部選擇；不得暗自執行。
- `EVIDENCE_VERIFIED`：某項證據精確有效；不表示整案通過。
- `ACCEPTED`：核定版本、環境、分母、必要格與未關項满足該policy。
- `LONG_RUNNING`：真觀察窗在跑；要能指明live handle/job與實際日期。

發布每個requirement的status、version/commit/environment、evidence引用、owner、下一步。
資料可變時收據帶測量時刻與對象；不覆寫舊收據來假裝它當時量到現在的值。
每個未關項具名：誰要給什麼、等到何時再檢查；無法給時點就寫具名阻點，不虛報。

## 6. 本輪可做與不可做

本輪可完善契約、列完成分母、在自用v0.2登錄規劃task與待驗版本。
不可開始新功能DEV、build/recreate、建立外部帳號／角色、正式部署、替羽／思接入或以本人名義回ACK。
目前P0只證明「用v0.2管本案規劃能走通」，不證明未完成功能已落地。
計畫核定後才以 [EXECUTION_BLUEPRINT.md](EXECUTION_BLUEPRINT.md) 的順序開工；此頁本身不開DEV。
