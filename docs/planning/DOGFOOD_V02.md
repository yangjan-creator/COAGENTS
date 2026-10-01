# 用 COAGENTS v0.2 管 COAGENTS 本身

作者：滴。2026-10-01。目的：驗產品規劃／進度／交付的真實操作，不是開發新功能。
服務：http://localhost:8310/dashboard；project key `CG-PLAN`。

## 實際做了什麼

- 註冊一個規劃團隊與兩個操作身分（同一執行者，不是獨立Agent）。
- Contributor嘗試開案，實測403；用v0.2現有PM權限建立專案。
- 建立一個SUBPROJECT與六個FEATURE、逐一認領／回報進度。
- 根項目設HOLD：「只規劃，等待核定」；不把未寫完的計畫稱完工。
- 將[完整產品計畫](../PROJECT_PLAN.md)登錄為版本／Artifact，記Overview和PM Summary。
- 把必要審核格留PENDING；未進行獨立審查，不填PASSED。

## 實測缺口與精確射程

| 觀測 | 方法／對象 | 能說什麼／不能說什麼 |
|---|---|---|
| Contributor不能開案 | member token POST /projects，403 | v0.2以全域role做此限制；不是細粒度scope |
| 主控未登錄 | POST /projects response／v0.2 Project schema | 無明確creator/owner欄位，不宣稱別處從未有owner紀錄 |
| PM跨案可見 | GET /projects，用自用PM token | 實看到CG-PLAN、DEMO；两者均為本機示範資料 |
| 缺一次性授權 | GET /openapi.json，掃authorization路由 | v0.2公开契约缺此功能；本機未接入草稿不算產品 |
| 缺知識／程式登錄 | OpenAPI路由及v0.2模型 | 现有Summary不是typed Rule/Memory/Function catalog |

API取證不用真LLM；供應商請求0、正式機／VPS／羽球庫寫入0。
臨時member keys用完即撤銷；報告／收據不存token或一次性安全碼。
模型不同role的表演不算獨立驗收；此次是dogfooding/selftest。

## 證據與目前狀態

原始初段：[v02_dogfood_receipt.json](v02_dogfood_receipt.json)。
規劃交付／SHA／版本／審核格以[plan_delivery_receipt.json](plan_delivery_receipt.json)為準。
後者在計畫登錄完成後產生；不足或操作失敗不得補造成功收據。
資料留在COAGENTS的SQL與audit history，MD是可點開的项目文件，不是唯一控制資料。
本輪新功能DEV停止；待核計畫，不部署新程式碼。

## 框架詳細設計交付（2026-10-01補記）

最新規劃交付為v4，候選詳細規格入口：[FRAMEWORK_SPEC.md](FRAMEWORK_SPEC.md)。
固定七檔與完整SHA：[framework_spec_manifest.json](framework_spec_manifest.json)；
實際SQL/API登錄與讀回：[framework_registration.json](framework_registration.json)。
原v1–v3收據保留，不改寫；產品進度仍0、root HOLD、四個必要Gate PENDING。
這輪登錄器兩次取錯v0.2欄位：/workspace沒有頂層versions/gates、AuditEvent使用version_id；
state已提交後以GET-only回讀補驗，沒有為器材失敗再造版本。臨時member key已撤销，具名read-only count=0。
靜態規格對帳不能宣稱runtime驗收通過；沒有接線產品草稿、migration、build或recreate。
