# 09 合規稽核報告（ASPICE SWE.1–6 / ISO 26262-6 §6–9）

> 最後更新：2026-06-01 ｜ 對應 git：9bdeecc ｜ 由 skill：compliance-audit

## 稽核就緒度：約 80%（範圍內項目）

## 標準覆蓋對照
| 項目 | ASPICE | ISO 26262-6 | 狀態 | 證據／缺口 |
|---|---|---|---|---|
| 軟體需求 | SWE.1 | §6 | 🟡 部分 | 9 SR 已記錄；SR-008 無測試。安全需求(ASIL)範圍外 |
| 軟體架構 | SWE.2 | §7 | ✅ 有 | 02-architecture：10 ARC、7 IF、mermaid 圖 |
| 資料流 | SWE.2/3 | §7/§8 | ✅ 有 | 03-data-flow：6 DF、3 信任邊界 |
| 詳細設計 | SWE.3 | §8 | ✅ 有 | 04-detailed-design：7 DD |
| 單元驗證 | SWE.4 | §9 | 🟡 部分 | 33 passed / 0 failed；核心覆蓋佳，但 Jira/store/docx,pdf 未測、無覆蓋率量測 |
| 雙向追溯 | SWE.1–6 BP | §6–9 | ✅ 有 | 07-traceability：9 SR↔27 TC↔33 TR |
| 開發歷程 | SUP.8/10 脈絡 | §5 脈絡 | ✅ 有 | 08-development-history：DEV-2026-06-01-1 |
| 整合/合格測試 | SWE.5/6 | §10/11 | ⬜ 範圍外 | 本套件不涵蓋 |
| 系統層 | SYS.1–5 | §4 | ⬜ 範圍外 | 本套件不涵蓋 |

## 缺口清單（依風險排序）
1. ❌ **SR-008（Jira 部署）無自動化測試** — `jira_client.py` / `routers/jira.py::deploy` 未覆蓋。建議補整合測試或以 mock 測 payload 組裝。
2. 🟡 **未量測測試覆蓋率** — 安裝 `pytest-cov`，`pytest --cov=app` 取得行/分支覆蓋，補足 §9 證據。
3. 🟡 **`store.py`、`parser.parse_docx/parse_pdf` 未測** — 補單元測試。
4. 🟡 **SR-005 產生側排程約束無離線 UT** — 目前僅驗證側（TC-021/022）覆蓋；可加假 LLM 回應的回測案例。
5. 🟡 **gen_log 寫入路徑僅間接覆蓋** — 補 `log_generation` 的直接測試。

## 雙向追溯摘要
- 需求 9，已驗證 8，孤兒 1（SR-008）。
- 核心單元均已測；未測單元 3 類（Jira、store、docx/pdf 解析）。
- 測試 27 TC（33 項執行），全部對應到 SR，無無主測試，無失敗。

## 稽核員備註
- 本報告為**追溯與覆蓋證據**，非功能安全認證；ISO 26262 要求的獨立確認（confirmation measures / reviews）仍須人工執行。
- 範圍外項目（SYS、SWE.5/6、MAN/SUP）已明確標示，未納入就緒度分母。
