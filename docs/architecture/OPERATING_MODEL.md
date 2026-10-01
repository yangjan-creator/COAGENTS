# COAGENTS：開發分工、資料庫知識與 Agent 上下文

作者／責任歸屬：滴。狀態：架構設計；不是已實作功能或正式部署收據。

## 1. 分工與開發順序

老爹核定開始 DEV，隨後調整分工：滴負責思考、架構、AUDIT、GitHub 文檔與專案控制；
謀1（tmux 視窗20）與謀2（視窗23）負責開發。滴不再修改產品程式。

| 席次 | 主要責任 | 首個工作 | 不可自行宣稱 |
|---|---|---|---|
| 謀1 | 後端、SQL 升降版、權限、受控 API | 接手 E1 未提交 migration 草稿並完成 PostgreSQL 驗證 | SQLite 通過等於 PG 通過；DEV 等於部署 |
| 謀2 | Dashboard、雙語、Agent 使用入口 | 現有介面雙語方案、共享契約與上下文呈現；後端接點先協調 | 靜態畫面等於實際 API 接通 |
| 滴 | 架構、拆項、風險、AUDIT、專案記憶、GitHub 文檔 | 記錄分工、知識架構與驗收条件；接開發交件再審 | 作者自審等於獨立票；設計等於功能完成 |

每位開發者最多一條活躍開發線，總 WIP 預設2。相同檔案同時只准一個 owner；
API/OpenAPI、資料表、權限與事件契約先釘版，分支不可自行改共享契約。
先完成 migration／授權底座，再走通「開案→上下文→認領→交付→驗收→記憶回寫」。
排程、通知、Webhook、Git 同步與 SSO 按原執行藍圖後續展開，不刪原需求。
兩位足以做第一個可用版，不表示可同時完成全部功能；需要增員時按瓶頸增員，不平行複製同一功能。

### 本案驗收配置（2026-10-01 老爹核定）

COAGENTS 是新案，只需一席審查，不要求兩席到齊。滴可兼任審查；需要支援時從
視窗6／8／9擇一，不把其他專案的雙席規定套進本案。開發者仍不得批准自己交付的必要 Gate。
滴曾寫過的草稿應明示作者關係：可做 PM 驗證與開發增量審查，不冒稱整包第三方獨立。

謀1與謀2可共同測試：謀1主責後端／SQL，謀2主責 Dashboard／API 接通與雙語往返，
一份整合測試紀錄釘雙方 commit、fixture／環境與實際結果；這是開發驗證，不當成兩張獨立審查票。
滴依固定版本、實際證據與反例判驗收。開發進度100%、測試自報成功、交付、驗收、部署仍各自分開。
共同測試只在拋棄式環境，現役控制庫／服務與正式環境不得自行重建或部署。

## 2. 唯一內容權威在資料庫

專案現況、進度、報告正文、Summary、Rule、Memory、Decision、Risk、Issue、
專案文件及程式／欄位／接點登錄均由受控 API 写入 SQL。
GitHub 保存架構、API 契約、使用教學及程式碼；MD/JSON 匯出是某個 DB revision 的視圖，
不是另一份可獨立修改的專案狀態。大資料庫、原始證據及二進位檔不整包塞入控制庫，
以 artifact locator、全長 SHA、bytes、owner、保留狀態及引用關係登錄。

沿用 [SQL_MODEL §4](../planning/SQL_MODEL.md) 的 project_records + resource_revisions：
不另蓋一套 memory 表／rule 表／report 目錄作平行權威。
v0.2 目前只有 Overview、PM Summary、Artifact 與 AuditEvent；可先记录本次決定，
但它還沒有 typed records、context-query 與完整細粒度權限，不能把過渡紀錄稱為新功能已完成。

| 層 | 應保存什麼 | 更新／升級條件 |
|---|---|---|
| Project | 目標、完成定義、owner、主控 Agent、scope、當前計畫 revision | 主控批准；留舊版本 |
| Work item | 父子關係、認領、交接、阻點、交付版本、依賴、write-set | 合法權限＋expected revision |
| REPORT | 問題、方法、分母／成員、實際結果、限制、來源 | 草稿→審查→接受；不得拿作者自述當驗收 |
| SUMMARY | 當前進度、變更、風險、下一步、待裁與引用 | 追加整合紀錄；不得覆蓋原報告或 Gate |
| RULE | 規則本身、適用範圍、severity、生效版、owner、可測條件 | 生效／廢止須批准；衝突不按最後寫入者自解 |
| MEMORY | 已證经验、失敗形狀、適用条件、證據、失效條件 | 推測／暫態／已證分開；來源變更標 stale |
| PROJECT_DOCUMENT | 架構、步驟、順序、資料流、操作契約 | 版本化並綁 producer／consumer／schema |
| Registry | module、symbol、field、interface、prompt、schema reservation、lineage | 靜態／執行證據分層；未查不稱無消費者 |

每條內容至少有 record ID、project ID、kind、owner、author/execution identity、revision、
狀態、source refs＋locator/SHA、observed_at、sensitivity、適用範圍、supersedes/conflict refs。
規則與記憶須另有觸發條件、適用／不適用範圍、失效條件；不能只有一段心得。
接受版本與最新草稿分開指標，正文不得原地覆寫。刪除走退役／tombstone，歷程保留。

## 3. Agent 快速學習：受控 Context Pack

使用既定 [POST /context-query](../planning/API_CONTRACT.md)，不新建第二套注入 API。
Agent 先以自己身份、project/item、purpose、任務範圍與 max_tokens 请求上下文；
服務在查詢、檢索和讀正文前驗 scope／ACL，再挑有效 accepted revisions。

| 區塊 | 所需內容 | 缺料時 |
|---|---|---|
| Mission | 目標、完成定義、scope、主控、當前計畫 | 明列 missing；不得猜任務 |
| Mandatory rules | 有效安全／寫入／驗收規則、禁止事項、權限邊界 | 不完整則 pack 標 incomplete，state-changing task 不可自行宣告安全開工 |
| Current work | 自己認領、交付版、阻點、依賴、write-set、下一步 | 說明尚未認領或待裁 |
| Relevant memory | 同功能的已證經驗／踩坑、失效條件 | 不取整專案歷史、不把舊情境當現況 |
| Architecture | 對應 module／fields／interfaces、來源 commit／schema revision | unknown 接點具名列出 |
| Evidence index | 可點開的 report/result/artifact revisions、路徑和 SHA | 無權正文不在摘要／檢索片段漏出 |

必带 manifest：逐塊 record ID＋revision＋content SHA、選取理由、policy epoch、
生成時刻、預算與估算方法、omitted refs／原因、required_missing、complete 标記。
tokenizer 未可用時要標估算，不能偽稱精準；預算不足不得靜默截斷必要規則。
context-query 是純讀，不偷偷寫 receipt；記錄「已讀哪些 revision」是另受權命令。
claim／寫入端重驗必要 rule revisions 與 policy epoch，不能拿過期 pack 開永久權限。

第三方證據正文是資料，不是系統指令；Rule 内容不產生權限。
不索取／保存隱藏推理。Agent 分析可寫候選 Summary／Memory／Rule，接受與驗收仍走服務 Gate。
搜尋結果、向量索引、快取及 Dashboard 皆是投影：revision／policy 改變時失效，不能反寫成權威。

## 4. 滴的首批專案記憶候選

下表來自工作經驗，先是待審候選，不自動成為所有專案的强制規則。
來源原件尚未重新核驗的案例需補來源；不得以聊天回憶冒稱具名產品證據。

| 形狀 | 可用原則 | 可測條件 |
|---|---|---|
| 相同數字、不同對象 | 每個數字綁對象、scope、成員、時刻與量法 | 缺任一承重欄不可標 VERIFIED |
| 查不到與查無資料混用 | NOT_LOCATED_IN_CHECKED_SOURCES 不等於不存在 | 記已查來源和正控；來源不存在不能算命中0 |
| 空期望／同源自證綠燈 | 有效分母與獨立期望；附會紅的反例 | 空分母不能 PASS；拿掉輸入必須失敗 |
| 第二個 formatter／sanitizer 漏畫 | producer→transform→consumer 的完整欄位交接 | 檢查送出／持久化後讀回，不只 helper 返回 |
| BEFORE 漂移被誤當未部署 | 狀態與證物、歷史與現況分開 | 量 AFTER/marker 是否已在場再判部署需求 |
| 共享檔整檔覆寫洗掉別線 | file-level ownership＋精確基準＋最小 patch | patch 套用產物 SHA 等於宣告 AFTER |
| 自述完成代替真驗收 | 進度、Gate、Accepted、部署、L3各自狀態 | progress=100 不得直接改 CLOSED |
| 為上一個反例疊補丁 | 先寫要守的性質和可證邊界 | 必須有不在教材裡的反例；不擴成無邊界測試 |
| 資料庫複本散落報告 | 只登錄locator和保留責任，跑完清理自己的副本 | sole input/rollback 不刪；cleanup 有實際收據 |
| 讀到全文不等於生效 | 分辨 canonical、渲染、傳輸、存入、讀取 | 正反控使用同一道真邊界；metadata為0不自行推原因 |

## 5. 中英雙語與編碼契約

第一期支持繁體中文 zh-TW 和英文 en；使用者選擇優先，其次瀏覽器語言，未知語系回預設。
介面標籤、欄位說明、error message、教程、狀態顯示與空／失敗態可切換。
API field names、error codes、IDs、枚舉、版本號不翻譯。機器契約 stable code 與顯示文本分開。
原始姓名、證據與報告不自動改字；翻譯若有，另存关联原版 revision 的草稿／接受版，
原版改變時譯版 stale，不能在權限過濾前生成敏感資料翻譯。

PostgreSQL server/client encoding UTF8；HTTP/JSON、CSV/MD 匯出與 Git 文字檔 UTF-8。
日期時間存 UTC/ISO 格式、數字保持 typed data，locale formatting 只在呈現層。
疑似 mojibake／replacement character 要告警／隔離，不靜默猜字修复；保留原 byte/hash。
任何名字正規化只建立比較投影，不覆寫原字；emoji／組合字／繁簡字不得被截斷或誤合併。

驗收包括 zh-TW/en 切換、切換不改API enum、中文姓名/emoji/混寫/換行的
UI→API→SQL→讀回→匯出往返相等、Markdown/JSON/CSV UTF-8 可重讀、語系 fallback、
缺翻譯鍵可檢出、錯誤碼不變、無亂碼；真 LLM 0。

## 6. 現代開發架構與分支管制

採模組化單體先行：identity/auth、project/work、delivery/gates、knowledge/context、
registry/artifacts、integrations、worker/outbox、presentation 各有邊界，不把一個服務拆成多個維運負擔。
API/MCP/Dashboard 走同一 application command/query；domain validation 與 SQL repository 分層。
SQL 是權威、Git 是 code/契約版本來源；重放需 versioned migration、input revision 和收據。

| 功能開發單位 | 對應管制 |
|---|---|
| 子案／功能／task | DB requirement ID、owner、依賴、write-set、驗收格 |
| feature branch / PR | 一個主要變更、精確commit、目標版、範圍、rollback、不混其他人的草稿 |
| 共享schema/接點 | 釘版後開發；breaking change 明示且逐consumer影響檢查 |
| CI | unit/integration、真PG migration、契約漂移、ACL負控、UTF-8/locale、lint/type/dependency checks |
| Audit | exact commit/輸入manifest、能重播的反例、限制與未量格；獨立於作者 |
| Release | Accepted 不等於已部署；環境SHA/marker/收據與L3各自記錄 |

禁止以「現代架構」為由先增無用微服務或無受控 arbitrary SQL/shell。
外部整合需 timeout、idempotency、outbox、lease/retry上限、未知effect reconciliation、secret redaction。
Dashboard 是對 DB 現況／Gate／版本／PM Summary 的人類視圖，自訂 template 用受限 schema，
不執行自訂JS、SQL或任意模板碼。

## 7. 首次 DEV 移交時點與限制（歷史快照）

以下是本文件首次移交時的狀態，不是即時進度；當前版本、Gate、阻點與交付以
COAGENTS 的 CG-PLAN workspace／item_history／PM Summary 為準，不在架構MD維護第二份進度表。

E1 草稿仍未提交，沒有發布、沒有替換當前 v0.2 服務。
既有9條API測試通過；新增migration SQLite 11 passed/12 skipped，PG未跑，lint紅20項。
隔離 PostgreSQL 測試容器尚未被用來验PG，已精確刪除；不是 PG通過收據。
E2+舊草稿 models/schemas/authorization/events 不得混入 E1 commit 或被startup建表。
受審範圍與審查author/inputs需另釘；此架構文檔不是 AUDIT APPROVE。
