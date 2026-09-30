# COAGENTS 完整產品計畫 v1

作者／責任歸屬：滴。日期：2026-10-01。
狀態：**規劃候選，等待使用者核定；不授權 DEV 或部署。**
實況基準：公開 v0.2，commit `b80435e920bd38b9212c08e1cfc1b7bb7d9591e7`。
自用專案：`CG-PLAN`。本文件描述未來設計，不代表列出的 API／表已存在。

## 1. 核心定位與完成定義

COAGENTS 是 Agent 優先、人能隨時檢視的一套專案控制與開發知識服務。
原生 SQL＋REST/OpenAPI＋MCP＋Dashboard；不是三套 PM 系統的 Connector。
It’s a Plan／Plane／Vikunja 是能力參考，不依賴其安裝，也不抄其程式。

核心三件事：**安全地授權、真實地開發、可證據化地驗收完工。**
AI 的價值在於分析、拆解、整理、提出判斷並写入可追溯紀錄；不是把一段文字當權限或證據。
人不必盯每一個 Agent 的視窗，也不必靠一堆 RD／報告檔找目前狀態。

完成必須同時滿足：

1. 至少兩個團隊可在同一部署服務內管理不同與共享專案，權限不串漏。
2. 專案開展、指派主控、授權、認領、交付、驗收、取消與刪除均有受控 API。
3. 每個完成項目對應明確版本、必要驗收格、證據及檢查者，不是單純 progress=100。
4. 人可點開任務、版本、決策、Rule、Memory、程式接點與檔案歷程。
5. Agent 可透過同一 API／MCP 分析讀寫，不需直接碰控制庫或 shell 部署。
6. 備份還原、升降版、失敗重試、權限撤銷、跨專案與併發負控均有實跑證據。
7. 羽／思的實際專案由指定 owner 接入並完成一條真實工作鏈；合成示範不能代替。

不把 COAGENTS 做成 Git 主機、任意 shell 執行器或自動寫正式資料庫的後門。
程式仍由 Git 版控；服務登錄精確 commit、檔案、介面與驗收關係。

## 2. 先用 v0.2 管一次自己：實況與缺口

已在服役 v0.2 建立 `CG-PLAN`，由實際 API 建立根項目與六個 FEATURE。
實做建案、認領、回報進度；接著用版本、Overview、Summary、Artifact 與 Gate 管本計畫。
證據：[自用收據](planning/v02_dogfood_receipt.json)、[自用說明](planning/DOGFOOD_V02.md)。
全程供應商／LLM 請求 0；同一執行者切換角色不算獨立審查。

| 格 | v0.2 真實結果 | 未來要補的能力 |
|---|---|---|
| 一般 Agent 開案 | Contributor POST /projects 得 403 | 明確 project.create 權限，不靠全域 PM 身分 |
| 開案者＝主控 | Project 回應沒有主控欄位 | creator、owner、轉交紀錄與主控權限 |
| PM 範圍 | 自用 PM 角色可見 CG-PLAN 和 DEMO | 全域控制與專案主控分層，預設專案隔離 |
| 開展子項／認領 | 六個子項可建、可認領 | 受控開展、租約、交接、多人工作分段 |
| 一次性授權 | OpenAPI 沒有 authorization 路由 | 雙身分＋操作／參數綁定的單次能力 |
| 專案知識 | 有 Overview／Summary，無 records／memory／rules／symbols 路由 | 專案紀錄、Rule、Memory、程式與欄位登錄 |
| 版本／Gate | 現有 API 可表示候選交付與待驗格 | Gate 綁計畫、原件、Git、環境及驗證身分 |
| 刪除 | 未提供專案／項目刪除 API | 受權限保護的 tombstone、引用與恢復流程 |
| Schema | v0.2 startup create_all | 真正版本化 migration 與 guarded rollback |

以上是特定服役版本的觀測，不把 API 沒有某路由推論成全機沒有任何相關檔案。
先前新增但未接入的權限／背景工作草稿不屬 v0.2，暫停，不承重。

## 3. 一條服務、一份權威料

```text
人 Dashboard ─┐
              ├─ 身分 → 專案 ACL／單次能力 → typed API → SQL transaction
Agent MCP ────┘                                   ├─ 目前狀態與不可覆寫 revision
                                                  ├─ 決策／證據／權限 audit event
                                                  └─ durable outbox → 通知／Webhook
Git／CI／檔案 → 授權匯入／登錄 → commit／symbol／source binding → 驗收格
AI 分析器    → 權限化 context pack → 草稿／建議／有限寫入 → Review／Accepted
```

資料權威分工：SQL 管專案狀態／角色／紀錄／介面關係；Git 管程式原文與 commit；
Artifact 管來源 locator＋SHA＋保留關係。MD 是可版本化的專案 document／匯出視圖，
不是另一份手改後跟 SQL 漂開的主資料。

同一件資料有一個穩定 ID、一個 current revision、可讀歷史及明確 consumer。
不得讓同一條 Rule 在多個 prompt、MD、SQL 中各自變成沒有關係的權威版本。

## 4. 組織、團隊與專案主控

部署下有 Workspace，Workspace 下有 Team、Project、Agent／Human。
一個 Agent 可以參加多個 Team／Project；不是只靠單一 team_id 推定全部權限。
專案可有一個主要團隊與多個協作團隊，工作項目可指定執行團隊。

| 角色 | 範圍與職責 | 不自動取得的權力 |
|---|---|---|
| Global Controller | 註冊身分、開案政策、全域授權、緊急停機／撤權 | 不因全域身分冒稱獨立驗收已完成 |
| Project Controller | 一案的開展、分派、計畫／Rule 核定、整合決策、結案提請 | 別案資料、正式機部署、自己驗自己的交付 |
| Contributor | 認領被授予的項目、開發、回報、提交版本與草稿紀錄 | 修改主控、擴權、改已通過證據、硬刪除 |
| Reviewer | 對指定範圍独立檢查，記驗收與缺口 | 假造原件、改交付內容、越權部署 |
| Reader | 授權範圍的查閱／歷程 | 寫入與授權 |

**預設開案者就是 Project Controller。** 前提是開案者已獲 `project.create` 權限。
不能靠「先開個案」逃過權限邊界。代開案須明示 on_behalf_of／owner，留實際 creator。
Global Controller 可指定新的主控；主控可發起轉交，接手者明示接受後生效。
每案恰一位有效主控；不可刪掉最後一位主控。離線／離職保留紀錄，交由上層恢復。
主控轉交與角色變更增加 policy epoch；舊授權需重新評估／撤銷，不能默默跟著繼承。

開案時記：目的、完成定義、主控、團隊、資料分級、code repositories、環境、
預算、權限 policy、驗收 policy、保留 policy、目前 plan revision。

## 5. 權限與一次性安全碼

所有 API／MCP／Dashboard 共用同一授權函式。按鈕隱藏不是安全機制。
可設定「只有一個 Agent 有常設開案／刪除權」；其他 Agent 只能在核准的單次操作使用。
權限由 action＋workspace/project/resource scope＋期限＋條件構成，不以角色名代替檢查。

單次流程：

1. Agent 以自己的身分 key 申請 operation proposal，寫具體目的與完整參數。
2. 服务產生足夠熵的隨機單次安全碼，只回一次；Agent 私下提供 request ID＋碼給 PM。
   不讓 LLM 自己「想一串碼」。碼不是登入 key，不能替代 Agent 本身的認證。
3. 專案主控／全域主控在自己的授權範圍內，看清目標、diff、後果後批准／拒絕。
   申請者不可自己批准；批者不可授予自己沒有的 action/scope。
4. 批准綁 subject、action、target、完整 canonical payload SHA、期限、policy epoch、
   使用次數=1，以及刪除等操作需要的 current revision／預期版本。
5. Agent 以自己的 key＋單次碼執行原 API。碼與不同 Agent／參數／資源組合皆拒絕。
6. SQL 把 consume 與受控狀態修改放同一 transaction。成功即用盡；若狀態修改失敗，
   不偽稱消耗成功。提供 idempotency key：重送只能取回同一次 receipt，不能再做一次。
7. 到期、PM 撤銷、主控轉交／policy 改變均不能用；碼 raw 不進日誌／Summary／Git。

碼是交付授權的安全材料，不靠猜字串或剪貼文本判權。申請／決策／執行各有不同 receipt。
有外部副作用時，只消耗一次以建立 durable operation；worker 依同一 operation 重試，
不是重用能力再執行第二個操作。Timeout 不能盲重送未具冪等性的外部動作。

必測：未批、拒批、到期、錯人、錯案、參數改一字、換 target、舊 revision、撤權、
兩個併發請求、重播、操作失敗、部分外部成功、日誌不漏碼。

### 開展與刪除的分級

一般授權可限定某一專案／父項目開展子功能；跨 scope 必須新批准。
一般刪除是 tombstone／取消／封存，保留版本、原因、來源及引用，不能讓證據消失。
已被依賴／引用的項目先顯示影響清單；若主控批准取消，依賴者變 BLOCKED／需重評。
實體 purge 是另一權限、保留期、雙步確認與 legal/retention hold，不跟一般 DELETE 混用。
刪專案不等於刪 Git、原件、資料庫、副本或外部系統；每一種要不同 operation 和 owner。

## 6. 實際開發與版本流程

Project → Subproject → Feature → Task；可有依賴、里程碑、問題、風險、變更提案。
任務有 scope、排除項、完成定義、owner、write-set、輸入／輸出、驗收格與交付版本。
Agent 開展時先讀既有工作／接點，避免另一位 Agent 平行改同一個檔案而不知。

```text
提案 → 計畫核定 → scope/write-set 認領 → 開發 → 候選交付 vN
     → 自測證據 → 獨立驗收 → 可發布／可部署 → 指定環境驗證 → 完工
                                    ↓失敗
                     具名缺陷 → successor v(N+1)／HOLD，不覆寫原結果
```

認領有 lease、heartbeat、預期交件與 next_check；離線到期只標 stale，不自動搶走。
交接是主控批准的移轉，記原 owner、接手 owner、停點、輸入及待關格。
衝突單位可設 file／component／schema／migration number，而不只看功能名稱。
Git branch／worktree／PR／commit／code SHA 與交付 version 分開：v3 不必等於第三個 commit。
Plan 變更須有 change request、理由、diff、影響項目與新驗收格，不能事後改門檻假裝已過。

## 7. 驗收、完工與證據的真偽

把 DRAFT、WORKING、DELIVERED、READY_FOR_REVIEW、ACCEPTED、DEPLOYED、RUNTIME_VERIFIED、
CLOSED 等狀態區分；具體類型可裁剪 policy，不要求純文檔工作做部署。
progress 是報告值，不能直接轉 VERIFIED。驗收格也不能從被驗物自己產生空期望而恆綠。

每格綁：計畫／交付 revision、requirement ID、環境、方法、input manifest、expected、
actual、正負控、證據 locator＋SHA、作者／checker、時間、coverage 與限制。
區分靜態檢查、合成實跑、真路徑攔截、runtime 和使用者回覆；不能互相冒充。
證據不在服務可讀範圍時標 `REGISTERED_ATTESTATION`，不宣稱服務已驗檔案 SHA。

所有必要格的適用分母先定；0 必要格是 NOT_DECLARED，不是通過。
相同執行者换 API actor，不等於獨立審查；記 execution identity／review organization
或人工指定 independent reviewer，不能只比兩個字串不同。
自動 CI 可關「測試是否過」的格，不得自己關「產品取捨已被批准」的格。
P0 安全格不可 waive。其他可豁免格須具名批准、理由、期限及曝露風險，保留原 FAIL。

新 commit／輸入／部署環境漂移，失效範圍按 source binding 重新計算，不無差別重審整包。
根項目完工按必要子項、例外、runtime scope 推導；不能只由主控寫 CLOSED。
完工 receipt 列交付／accepted revisions、必要格清單、未關 note 與監測／回退責任。
Memory 檢索不可以把舊版通過票當新版現況。

## 8. 專案紀錄：Report／Summary／Rule／MD／Memory

統一 ProjectRecord 模型＋專門的 typed kind，不各蓋一份不相通的文檔庫。

| Kind | 目的 | AI 可以直接做 | 需批准才能改什麼 |
|---|---|---|---|
| REPORT | 可重播調查／交付報告 | 寫草稿、來源綁定、限制 | Accepted receipt／完成狀態 |
| SUMMARY | PM 整合目前狀態與取捨 | 引證整合、下一步候選 | 核定決策、門檻、例外 |
| RULE | 可機械檢查的專案規則 | 提案、冲突／影響分析 | 規則生效／廢止、policy |
| PROJECT_DOCUMENT | 藍圖、步驟、資料流、操作說明 | 以來源產生有版本的 MD | 標 Accepted／發布 canonical |
| MEMORY | 長期可檢索的已證經驗／事實 | 建議條目、去重候選 | 把暫態推測升成 accepted fact |
| DECISION | 誰裁、為何、影響範圍 | 整理當次原話／證據 | 代人裁示／改既定決策 |
| RISK／ISSUE | 缺口、阻點、責任、檢查時刻 | 紀錄、分類、追蹤 | 自動放行未關風險 |

每個 record 有穩定 ID/key、revision、作者、來源、confidence、資料分級、scope、
status、supersedes、有效期、reviewer、consumer。MD 可匯出，匯入用 optimistic revision guard。
「快速更新」是追加 revision／局部 patch＋ETag，不覆寫凍結／accepted 歷史。
Rule 由 RuleBinding 表指定哪些模組／prompt／Gate 在消費；退役需列 consumer 与接手者。
Memory 分 confirmed／hypothesis／obsolete／conflict，記支持與反證，不把提問當事實。
摘要是可丟棄的衍生 view，源紀錄不能因壓縮而消失。Conflict 不以 last-write-wins 決定真相。

## 9. 核心 Code、Function、接點與欄位控管

Git 是原文權威；登錄 SourceRepository → commit → path/blob → CodeSymbol。
區分人／Agent 宣告、AST/static extraction、runtime observed；找不到不等於不存在。
核心 code 標記只是有 owner 的登錄，不另複製一棵可被當來源的程式樹。

| 登錄物 | 最小欄位與關係 | 變更需要回答 |
|---|---|---|
| Module／File | repo/path/commit/blob SHA、owner、core flag、write lease | 哪些任務／接口／驗收受影響？ |
| Function／Symbol | qualified name、signature、input/output、side effects、callers/consumers、version | 誰調用？誰接手？是否兼容？ |
| Interface／接點 | producer、consumer、payload schema、順序、conditions、error／timeout | 是否同欄位、同型別、同粒度、同版本？ |
| Field／資料欄位 | field path/type/nullability/unit/scope、producer／consumer、privacy、schema rev | 0/NULL/空字串語義？誰寫誰讀？能否 retire？ |
| DB Schema／Migration | table/column/index、schema owner、UP/DOWN、號碼 reservation、風險 | 現有資料／caller／回退怎麼保護？ |
| Prompt／設定 | authority key／source、formatter、消費端、rendered contract | 注入的是原值還是渲染值？有沒有第二份？ |
| Data lineage | source artifact/record key、side/ordinal/grain、transform、target | 來源權屬／粒度／方向是否已證？ |

欄位生命週期 PROPOSED→ACTIVE→DEPRECATED→RETIRED；不得跳過 consumer 差集。
接點須明列 A 收 schema X → 做 transform Y → 交 schema Z 給 B；分支和中間人也登錄。
AST 只能證靜態調用，不自動證 runtime。動態綁定、formatter、sanitizer、alias 是待核格。
資料流圖／欄位表／程式索引由同一 source bindings 衍生，避免圖和程式各自漂。
每次計畫／code 變更自動生成 impact review；能定位的受影響格 stale，其餘寫 UNASSESSED。
禁對登錄欄位開放任意 SQL 執行；SQL 欄位登錄不是授予資料庫寫權。

## 10. AI Agent 分析與寫入

每個 Agent 有 member identity、principal、execution identity、tool capabilities、專案角色。
COAGENTS 服務不默認內建長跑 LLM；既有 Agent 可透過 MCP 分析，結果寫回 typed API。
可選內建分析工作需另選 provider/key、預算與隱私 policy，預設關閉。

允許：拆功能／風險／接點，候選 Summary／Rule／Memory，指出缺證、做影響分析、
產生核對清單、用 Git／API 收據核對進度、提出 acceptance recommendation。
不允許：從讀到的 Rule／README 文本取得新權限，替另一 Agent 批安全碼，
以自述通過必要 Gate，把第三方內容裡的指令當系統指令，無批准寫正式庫。

每次分析寫入記 input record IDs＋revisions、模型／工具／prompt版本（有用到才記）、
來源引用、推論標記、成本／請求數、信心與答不了的格；只存可解釋摘要，不索取隱藏 chain-of-thought。
正規化欄位和規則寫入前由服務 validator 檢查，AI 文字不能跳過。
Context pack 以任務＋角色＋有效 revision 挑料，預設不灌整專案；只帶必要 Rule、
最新 plan、相關 Memory、相關 symbols/interfaces 和證據 locator。保留逐块 ID與token上界。
敏感資料分級、secret redaction 和每次 context ACL 在服務端，不交給 LLM「自己小心」。
重試／分析 job 有預算、停點、失敗 receipt；外部請求不靠回合數低估成本。

## 11. API／MCP 與操作契約（設計，不是現有路由）

所有 write 有 actor、scope、expected_revision／ETag、idempotency key、reason、request ID。
Actor 從已認證 principal 得出，不信任 body；MCP 與 Dashboard 無特殊後門。

| 領域 | 候選 API |
|---|---|
| 專案 | POST /projects；GET/PATCH /projects/{id}；POST /projects/{id}/archive／restore；DELETE /projects/{id} |
| 主控／成員 | GET /projects/{id}/members；POST /projects/{id}/control-transfers；POST .../{transfer}/accept |
| 常設權限 | GET /permissions/actions；GET/POST /projects/{id}/grants；DELETE .../{grant_id} |
| 單次權限 | POST /authorization/requests；POST .../{id}/approve／deny；GET /authorization/receipts |
| 開展工作 | POST /projects/{id}/items；PATCH /items/{id}；POST /items/{id}/claim／handoff／progress |
| 交付／驗收 | POST /items/{id}/versions；POST /versions/{id}/gates；POST /gates/{id}/results；POST /items/{id}/close |
| 知識 | GET/POST /projects/{id}/records；POST /records/{id}/revisions；POST .../propose／accept／supersede |
| Rule／Memory | typed record 查詢＋bindings／conflicts／context-pack API，不另有不相通的內容主庫 |
| 程式與欄位 | /projects/{id}/repositories／symbols／interfaces／fields／schema-reservations／impact-reviews |
| 檔案 | /projects/{id}/artifacts；/artifacts/{id}/bindings／retention-check／deletion-operations |
| 通知與整合 | /notifications；/projects/{id}/schedules／webhooks；/operations/{id}/receipts |
| 人用模板 | /dashboard-templates＋revisions／saved-views；無任意 JS／SQL execution |

最終 OpenAPI 與 MCP tool names 由核定 schema 產生，避免教學、工具與實作三套不一致。
API版本／相容期明示；缺權403、缺資料404、revision/state衝突409、格式422、失效能力403。
長工作202＋operation ID，不能單靠 HTTP200 宣告外部動作完成。
Skill 依「開案／管理／執行／驗收／記憶整理」提供流程與例子；授權不足時請 PM，不繞路。

## 12. 人用 Dashboard 與 Template

保持工作台而非行銷首頁。人看整體、Agent用API，兩者讀同一份狀態。

1. Portfolio：跨團隊專案、主控、milestone、阻點、風險、成本與下一個檢查時刻。
2. Project home：完成定義、plan revision、最新 PM Summary、接點圖、目前 pending approvals。
3. Work／Versions：層級、依賴、owner/lease、write-set、交付、逐格證據及 stale。
4. Authorization desk：一次性申請的主體、exact目標、完整 diff、期限、批准／拒絕、使用 receipt。
5. Knowledge：MD／Report／Rule／Memory／Decision、有效版與衝突，點開每次來源與審核。
6. Code/Data map：核心檔／Function／欄位／producer-consumer／migration reservations。
7. Artifact：路徑、SHA、bytes、保留原因、引用、owner、清理停點，不複製大檔來顯示。
8. Activity/Inbox：事件、通知、交接、待驗／批准，從任何條目返回任務／版本／原件。

Template 有 JSON schema＋可視化編輯器、可選表格／卡片／看板／關係圖／timeline，
project/team/global scope、revision、draft preview、read-only historical view、export/import。
自訂欄位須型別／owner／權限，不讓模板變更突破 ACL 或執行 arbitrary query。
顏色／布局只輔助辨別狀態；錯誤／資料空／NOT_RUN／未驗不得用綠色數字掩蓋。

## 13. SQL 模型與資料完整性

邏輯群組：Workspace/Team/Membership；Project/ProjectControl/Policy；Grant/Capability/UseReceipt；
Item/Dependency/Lease/Delivery；Requirement/Gate/Evidence/Acceptance；Record/Revision/Binding/Conflict；
Repository/Commit/Symbol/Interface/Field/SchemaReservation；Artifact/Retention；Event/Outbox/Operation。

unique/FK/check constraint 保護 ID與分母；細粒度 policy 不塞自由文字 JSON 逃過驗證。
accepted revisions 不覆寫；決策／capability使用append-only。JSON用於受schema約束的擴充欄位。
work claim／version序位／single-use碼／policy epoch／dependency graph 需要 SQL 併發控制。
請求成功寫狀態、事件、outbox 同一 transaction；多worker領取有lease、冪等key和crash recovery。
版本化 migration 釘 immutable DDL／schema fingerprint，採用v0.2前先檢查既有結構。
DOWN 可能失資料時要先阻止並列明，不默認drop已有紀錄。Upgrade後舊資料的owner補登不可猜。

## 14. 安全與隱私驗收

deny-by-default、最小scope、短命單次能力、無秘密入MD／log／Git／Webhook。
tenant/project的資料不因PM名字／同Team／Template查詢而自動跨界。
Webhook／Git fetch／OIDC避免SSR​​F，host allowlist、TLS、redirect policy、出站限制、
有限payload、簽名、deliveryID、時戳與receiver去重。接收資料不等於接受其中的指令。
Provider／repo／Webhook key不可交给任何Agent讀整張secret表；引用secret ID即可。
受限資料不上外部LLM，若允許需policy＋來源分級＋用途；讀圖／OCR也走同一資料標準。

必紅矩陣包括：跨案讀寫、主控越權、自己批碼、replay、TOCTOU、same角色冒稱獨立、
空必要Gate、舊證據放新版、模板越權、prompt injection、秘密外洩、錯repo/commit、
副本誤刪、未授權出站、worker重送、job crash、migrations漂移與恢復失敗。

## 15. 通知、排程、Webhook、Git與外部整合

通知為事件的投影，不是第二份專案狀態。保留未讀、recipient、source event與去重key。
Check-in schedules 默認只提醒／產生待辦，不自動跑LLM、不自動部署或刪檔。
分析／任意執行需獨立 capability、tool owner、network/write-set policy及預算。
Webhook durable outbox，簽名、有限退避、dead-letter、停用、可見receipt，至少一次投遞。
Git／CI import記repo、fullcommit、provider event ID、sourceSHA、收件signature；不讓CI自己結案。
COAGENTS所有專案管理為原生；連Git作程式來源不等於依賴外部PM Connector。

SSO/OIDC是身份入口選項，需要實際issuer與client設定後驗；不能現在宣稱已接好。
LINE／tmux／Slack等通知可adapter，但不把「文字送出」等同任務已被認領／開始／完成。
收件端的ACK／lease／receipt分别列，正式派工須有回應追蹤。

## 16. 運維、備份、副本與清理

正式環境：先選host/domain/TLS、SQL權限、backup destination、retention、監測與owner。
不中途修改現有羽球／TACLAW／VPS產品，不以這份計畫授權正式部署。
Backup加密、帶owner／bytes／SHA／schema版本／保留期限，按restore演練證明有用。
復原測私有環境，source locator引用庫不是把大DB放進reports／Git。
副本登记creator、purpose、唯一輸入／回滾依賴、lease、使用程序、驗證完成與清理receipt。
預設短保留、空間配額、超限告警；確認不是唯一輸入／rollback／bind mount才發起刪除。
服務登錄不能替代實際lsof/mount检查；Agent的清理operation需要独立policy，不能delete-check綠就刪。
環境變更／重啟／升級有窗、基準、承重檔、受影響pending operations、回退和驗證owner。

## 17. 分階段建設與放行順序

不先做大量旁支功能，再補權限；不把「文件写完」當产品验收。

| 階段 | 交付 | 離開本階段必須證明 |
|---|---|---|
| P0 本輪 | 完整計畫＋v0.2自用＋差距表＋使用者裁示 | scope／owner／安全與完成定義已核；DEV仍關閉 |
| P1 安全底座 | workspace/project主控、membership/ACL、單次能力、tombstone、migration | 授權矩陣／併發／rollback必紅負控全過 |
| P2 專案知識 | typed records/revisions、Rule bindings、Memory、context packs、MD匯出 | 有效版一致、跨案/secret不可泄露、變更可追溯 |
| P3 實際開發 | Git/symbol/interface/field catalog、write leases、impact review、Schema reservations | source/consumer双向對帳，不能假static當runtime |
| P4 驗收闭環 | requirements／evidence／independence／accepted release／runtime scopes | 一條真实开发链可验收，空／旧／伪证据必红 |
| P5 人與Agent工具 | Dashboard授权/知识/资料图、Template editor、MCP/Skill同步 | 人能查全链，Agent无需旁路SQL/任意shell |
| P6 持續運作 | durable通知/排程/Webhook、budget、backup/restore、可选SSO | crash/retry/replay/restore演练，0未批准外部副作用 |
| P7 羽／思試行 | 選一個真实小專案、指定兩主控、輸入源與验收者 | 不把合成例當接入，現有主線不中斷 |

每阶段用COAGENTS自身管理：feature、需求、交付vN、gate、summary、rule、memory。
v0.2缺欄用有label的record payload／artifact暫記，不用假欄位宣稱已有型別控制。
估時與日期在P0核scope及资源後再定，当前不造保证上线时间。

## 18. AI 自動化成熟度與保留人的判斷

先自動整理、提出candidate，再逐步開放低風險寫入；不是所有分析都要叫模型。
SQL/Git确定事实、机器测试、结构守恒由确定程序处理；歧义/设计取舍可由Agent分析。
重复scan/失败全套重跑不算进度；影響範圍明確后只跑对应的负控/格。
预算先写供应商请求上界、context bytes/tokens、会回答什么、答不出来停在哪。
一个Agent可以当专案主控，但作者、分析者、验收者、批准者仍是不同责任槽。
无法提供独立席时写REVIEW_PENDING，不用换名切role骗过「两人」的要求。

## 19. 核定前需要使用者裁示的有限選項

建議默认值可調整；此表是待决定，不是偷偷生效。

| 項目 | 建議 | 为何 |
|---|---|---|
| 全域主控 | 一位GLOBAL_CONTROLLER Agent＋人可break-glass | 贴合「一个Agent有常设权、其他单次」 |
| 專案主控 | 有权开案者自动主控，可受控转交 | 降低漏登记owner；不给全域扩权 |
| 开展子项 | 主控常设、执行者按父项scope授权 | 不让无上限开子案污染任务母体 |
| 单次码 | 服务产生，Agent申领并私交PM批准；默认5分钟 | 足够随机、不让模型造密码、绑实际参数 |
| 一般DELETE | tombstone；实质purge另权＋保留窗 | 保住历史证据／rollback／依赖 |
| AI写入 | 草稿与进度可直接；Rule生效／验收／删项需批准 | 利用AI而不把推论当授权 |
| 完工独立性 | 作者不能验自己的必要格，同execution identity算一人 | v0.2只比actor字串不够 |
| 第一次实案 | 羽、思各指定一个很小的项目，先不导全历史 | 能验权限/交界/完成链，低迁移风险 |
| 正式host／SSO | 先保留配置点，选定环境再部署接入 | 不能替用户决定域名/身份provider/线上变更 |

## 20. 全案未完成項與本輪停點

本輪只交计划、实用收据和候选版本，所有新增安全／知识／开发功能仍未实现。
P0 的對外計畫與服務 revision 必須內容可對帳：分別記原檔 SHA 與 API 本文 SHA；v0.2 會去除首尾空白，須明示此轉換並驗正文相等，不把兩者誤稱逐位元相同。本計畫必要格保持 PENDING，等使用者／指定獨立者審。
不把两个 API actor当两席，不把自测当真部署，不把候选代码当可发布产品。
下一步：使用者确认／修正§19与功能scope → 核定plan revision → 才开P1。
