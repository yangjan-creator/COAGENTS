# COAGENTS 整體開發進度｜2026-10-01 14:17 台北
作者／責任歸屬：滴（PM）；這是一次快照，動態權威是 COAGENTS SQL 的 item/history/gates/Overview。
分母28項＝10項v0.2基線＋18項完整目標。全架構終驗完成0/28；下表B的「完成」只指既有基線，不代表新架構終驗。E1、雙語UI、共同測試三個**限定增量**已驗，未部署；TX-0 v3待審。不可用10/28冒稱整案完成率。

| ID／內容 | 負責人 | 現況＋具名來源 | 下一個時點（台北；條件式） | 卡點 |
|---|---|---|---|---|
| B01 Dashboard | 謀2；美設計 | 完成：v0.2；雙語候選ecc593a已驗 | 10/02列新架構UI接線寫集 | 新ACL/授權/知識視圖未接 |
| B02 多團隊協作 | 謀1 | 完成：基線b80435e，api.py/project_teams | E2-A交件重驗 | 新membership/撤權未實作 |
| B03 認領／進度 | 謀1 | 完成：基線b80435e；CG-PLAN真認領 | E2-B交件重驗 | lease/fencing待E2-B |
| B04 交付版本 | 謀1 | 完成：基線b80435e；v1→vN真歷史 | E2-B交件重驗 | 新revision/idempotency |
| B05 驗證紀錄 | 滴；謀1實作 | 完成：基線b80435e；真FAILED/VERIFIED | 10/01 15:00 TX-0 v3首票 | 新需求binding/acceptance receipt未接 |
| B06 全歷程 | 謀1；謀2呈現 | 完成：基線b80435e；item/project history | E2切換時重驗 | 新ACL需覆蓋舊歷史 |
| B07 PM Summary／Overview | 滴；謀1實作 | 完成：基線b80435e；本案真SQL紀錄 | 10/01 14:20本總表入SQL | typed revision/context尚未接 |
| B08 檔案登錄 | 謀1 | 完成：基線b80435e；artifacts/ref/deletion-check | E3 artifact交件重驗 | 同path多版本/實檔驗證待接 |
| B09 自訂Template | 謀2 | 完成：基線b80435e；受限JSON render | 10/02 UI增量排程 | 視覺editor/歷史view未實作 |
| B10 REST／MCP／Skill | 謀1＋謀2；滴文檔 | 完成：基線b80435e；docs/API.md、skills/coagents-api | 每新增API同步契約測試 | 新版三端教程未交 |
| R01 SQL正式升降版 | 謀1；滴審 | 審核中：E1v2 96c98da已驗；TX-0v3 26fe175a待審 | 10/01 15:00 v3首票；不保證通過 | v2 CHECK假綠已退；完整新模型未完成 |
| R02 排程 | 謀3（視窗24） | DEV：CORE GO 75a3cb13；本人已ACK/認領 | 10/02 12:00第一固定增量目標待作者核可守時刻 | 核心並行；operation/outbox/lease接線待驗 |
| R03 持久通知 | 將核心；謀2UI | 未開始：已派限定CORE GO，17bf271e；待本人ACK | 10/01 14:15 ACK；10/02 12:00首件目標待作者確認 | 將原任務安全點；E2/API接線仍待 |
| R04 Webhook | 謀3（R02第一增量後） | 未開始：CORE GO 75a3cb13；本人已認領、按序實作 | 10/03 12:00第一固定增量目標待作者確認 | 出站policy/receiver/lease接線待驗 |
| R05 SSO | 謀1後端＋謀2登入 | 未開始：EXECUTION_BLUEPRINT §7 | 10/05核issuer/client選擇 | 使用者/ops指定真issuer；E2先行 |
| R06 Git自動同步 | 謀2 | 計畫：047bdcc/5064f62已核；typedv2退件、v3 973c08e待綁版 | 10/01 16:00 typed首票目標；10/02核S1 GO | resources/scope提案待核；TX-0/E2未驗 |
| R07 羽／思真人接入 | 滴協調；羽／思本人 | 未開始：EXECUTION_BLUEPRINT §10 | 10/05安排試行窗 | 不用合成actor冒真人；依E2/教程 |
| R08 正式部署 | 滴PM；ops執行者待指定 | 未開始：EXECUTION_BLUEPRINT §11 | 10/05核host/domain/TLS/owner | 沒有正式環境授權；8310仍v0.2 |
| R09 備份／還原 | 謀1；滴驗 | 未開始：EXECUTION_BLUEPRINT §11 | 10/02 18:00排隔離restore寫集 | 完整schema/release、backup位置未定 |
| R10 長期運作 | 滴；四開發支援 | 未開始：COMPLETION_MATRIX R10 | 正式部署後實跑7日/30日 | 不能用短測試替代觀察時間 |
| X01 專案主控／ACL | 謀1 | 計畫：E2計畫v2 b2ee43ac，E2-A未開 | TX-0過後24h內發E2-A限定GO | TX-0與舊PM旁路切換 |
| X02 單次授權／細粒度API | 謀1 | 計畫：E2計畫v2 §5，E2-C未開 | E2-A/B過後開；10/02重估工期 | 身分/epoch/原子consume未實作 |
| X03 刪除／恢復／引用保護 | 謀1 | 計畫：SQL_MODEL／STATE_MACHINES | 10/02 18:00拆可驗增量 | tombstone/purge、controller保護待實作 |
| X04 Rule／Memory／MD／Context | 謀2接口；謀1底座；滴規則 | 未開始：SQL_MODEL §4；CG-DEV-CONTEXT DRAFT | 10/02 18:00釘E3写集 | shared revision/ACL未成；Summary不等自動注入 |
| X05 Code／Function／欄位／接點 | 謀2；滴架構 | 未開始：SQL_MODEL §4 registry | Git S1＋E2過後開；10/02排期 | exact source/revision/producer-consumer |
| X06 真開發／驗收／完工 | 謀1；滴審 | 審核中：TX-0v3 26fe175a；E2-B僅計畫 | 10/01 15:00 TX-0首票 | write-set/lease/推導完工未接 |
| X07 完整工作台／Template／教學 | 謀2；美設計；滴審 | 計畫：ecc593a僅雙語已驗，完整工作台未完 | 10/02 18:00下一個UI增量 | E2/records/API依賴；不是全a11y票 |
| X08 副本內容／路徑／保留 | 謀1；滴policy | 計畫：SQL_MODEL §5/§7；基線有登錄 | 10/02 18:00artifact/retention寫集 | revision/實檔receipt；不自動任意刪檔 |

**開發授權**：老爹在「框架細節都完成了嗎」後回「可以」，再明示「視窗20 謀1、視窗23 謀2主要負責開發」，並把滴限定為PM/審查/架構/文檔；我據此發E1與I18N限定GO，原生紀錄97a6ba33。不是06d21af或某張MD自行授權，也沒有老爹逐SHA簽章的證據。ROADMAP的全面HOLD句是未同步的舊狀態，應改為「限定GO已開，其他功能/部署仍須限定授權」。今天R03另有13:53「將可以支援他！請他加速 多」。

**整案工期**：不能承諾已鎖完成日。PM暫定可用完整候選11/20、7日初驗11/27、含30日觀察的整案目標12/20（不是已核發布承諾）。10/02 18:00以四位可投入時數與逐段寫集重估；10/05須核host/issuer/backup/receiver。依據：謀1E2作者估18開發日＋四段審、Git四段估9–12日；其他未開項目前是PM估算。新增謀3可並行排程/Webhook，但不能保證工期減半。若將非專任、外部選擇未到或審查退件，目標順延且更新SQL，不能以增加計畫篇數稱進度。

最近實際狀態：TX-0 v1/v2 FAILED、v3 DRAFT；typed v1/v2 FAILED、v3草案未驗；E1v2/UIv4/TESTv2限定VERIFIED。完整架構圖另見 ../architecture/COAGENTS_FULL_ARCHITECTURE.svg；綠色只代表基線、黃色是限定DEV/審查、灰色未實作。
