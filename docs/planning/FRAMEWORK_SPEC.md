# COAGENTS 框架詳細規格 v1（候選）

作者／責任歸屬：滴。2026-10-01。
本版是設計文件，不是 v0.2 已有功能、migration、API 或部署授權。

## 文件入口與權威

| 文件 | 回答什麼 | 生效條件 |
|---|---|---|
| [PROJECT_PLAN](../PROJECT_PLAN.md) | 產品定位、全範圍、階段及待核定選項 | 使用者核定 |
| [COMPLETION_MATRIX](COMPLETION_MATRIX.md) | 28條需求的實際完成證據 | 各格的指定版本／環境驗收 |
| [EXECUTION_BLUEPRINT](EXECUTION_BLUEPRINT.md) | 建設順序、風險和外部接入 | 核定後按相依開工 |
| [API_CONTRACT](API_CONTRACT.md) | 輸入／輸出、路由、錯誤、MCP／相容 | 同版schema及產品實跑 |
| [SQL_MODEL](SQL_MODEL.md) | 表／型別／引用／唯一性／索引／升降版 | 核定DDL及PostgreSQL驗收 |
| [AUTHORIZATION_MATRIX](AUTHORIZATION_MATRIX.md) | 誰可做、在哪一案、能否單次批准 | Server policy與必紅負控 |
| [STATE_MACHINES](STATE_MACHINES.md) | 工作／版本／能力／worker的合法變遷 | 每條轉移及crash boundary實跑 |
| [FRAMEWORK_SELFCHECK](FRAMEWORK_SELFCHECK.md) | 跨文件對帳量法／實際結果／必紅突變／限制 | 只證設計一致性，不代替獨立票或產品驗收 |

母計畫／補頁維持原SHA，不原地修改已登錄快照。本詳細規格有獨立manifest與交付版本。
三種版本分開：服務release、專案plan revision、工作delivery vN；一個不推定另外兩個已驗。
所有詞彙／路由是本案原生契約，不依賴外部PM產品，不把Git來源同步叫PM Connector。

## 架構與寫入邊界

| 步 | 收到 | 處理 | 交出給下一步 |
|---|---|---|---|
| F01 Dashboard／MCP | typed command、自己的credential、scope、request ID | 不補權、不改actor、不執行SQL | HTTP command給F02 |
| F02 API身分層 | credential或server session | 驗身分、撤權、大小／速率、CSRF適用性 | Principal＋validated command給F03 |
| F03 授權／revision層 | Principal、action/target、expected revision、optional capability | 同resource ACL、policy epoch、參數綁定、冪等核對 | AuthorizedOperation或typed error給F04 |
| F04 Domain transaction | AuthorizedOperation、typed payload | resource鎖、合法轉移、state＋revision＋event＋outbox同tx | CommitReceipt給F05；OutboxEntry給F06 |
| F05 Response/read model | CommitReceipt或查詢 | allowlisted欄位、當次revision、authority source | Response給Dashboard/MCP；不交secret內部欄 |
| F06 Worker | 受限OutboxEntry、lease、provider secret reference | 送出前再驗policy、去重、出站限制、有限retry | Attempt／OperationReceipt給F04/read model |
| F07 Git/CI ingress | 原始event bytes、signature、repository binding | 校驗、去重、有界cursor、commit身份 | Evidence candidate給F04；不能自己關產品Gate |
| F08 Agent analysis | 受ACL的context pack及逐塊revision | 分析來源、標推論／限制／成本 | record candidate給F02；不因分析取得新權限 |

Primary route：F01→F02→F03→F04→F05。Secondary：F06/F07仍經同policy/domain command。
Why not an earlier route：沒有自然語言planner擁有COAGENTS寫權；LLM只能提出typed request。
Leaf/action owner是server的versioned action registry；lock moment是F03通過後，不是Agent文字中的「已批准」。
deterministic-first→typed validator→transaction；沒有跨領域LLM judge或自然語言續句寫入。
ToolRegistryV2 impact：No ToolContract change。此repo為apc/API/MCP，不是TACLAW；
不改NL04/planner/slot_contracts/trace_sanitize/FC tools，該族註冊面不適用，不能硬套本案權限。
Action owner由server registry選定；在F03固定後domain handler不得偷偷換action/target。
Missing/ambiguous input在F02或F03終止；不自動猜另案、另角色或另工具。

## 已定的設計預設（仍待核定）

- PostgreSQL為正式控制庫；UUID為公共ID；UTC儲存時刻，timezone獨立欄。
- 開案者預設本案controller，代開與轉交明示；global controller不等於可冒稱獨立驗收。
- Agent用service key，人用server session／OIDC；兩者共用resource ACL。
- state write＋audit＋outbox同tx；跨外部系統僅at-least-once，不承諾不可證的exactly-once。
- 一般刪除tombstone；purge／實檔刪除／正式部署均不同action、另批權。
- API新契約有版本前綴；v0.2 unprefixed仍是舊契約，不以文件讓它「自動升版」。
- 規則、記憶、MD、Summary同一revision authority；模板與欄位擴充不執行任意程式。
- 無必要Gate不是通過；同execution identity換actor不是獨立。

## 待外部決定與未實現

需要核定：DEV權限、global/project controller人選、獨立檢查者、正式host/domain/backup、
真OIDC issuer/client、Webhook receiver、羽／思接入窗、長期觀察與RPO/RTO。
這些不是用規格替使用者做出的決定。所有新表、權限、路由及worker仍未實作。
設計自檢可以證明引用與分母一致；不能證明DB鎖、登入、網路、實際資料隔離或使用者操作已正確。
