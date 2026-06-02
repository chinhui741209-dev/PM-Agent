# 08 開發歷程／決策紀錄

> 最後更新：2026-06-02 ｜ 對應 git：258e55f ｜ 由 skill：record-devlog

---
## DEV-2026-06-02-1 — 解析容錯強化、程式化排程、簡轉繁、Excel 匯出與前端結構編輯
- **時間**：2026-06-02
- **做了什麼**：
  - **解析容錯**：新增欄位別名對應（name→title、end_date→due_date、owner→owner_unit…）與巢狀 children 攤平（`_flatten_nodes`/`_find_node_list`），成敗改以「組樹後節點數」判定。
  - **程式化排程**：`_detect_unit_days`/`_apply_schedule` 依條件偵測週/雙週/日/月粒度，由程式排連續時段並上捲父節點起訖日（取代僅靠 LLM 算日期）。
  - **簡轉繁**：新增 `zh_convert.to_tw`（OpenCC s2twp），產生後統一轉繁中；套件缺失時退化不轉換。
  - **Excel 匯出**：新增 `excel_export.build_wbs_workbook` 與 `GET /api/wbs/{id}/export.xlsx`，前端加下載鈕。
  - **前端 UX**：WbsReview 支援結構編輯（新增/刪除/升降級/排序）；Intake 顯示產生分階段進度與耗時。
  - 新增 TC-028~TC-034（含 zh_convert 測試檔），回測 fixture 增 1 筆；**41 passed / 0 failed**。
- **為什麼（關鍵決策）**：
  - **排程交給程式而非 LLM**：本地/大模型對「以週為單位」等要求常忽略且日期算術不可靠，抽成確定性程式以保證符合粒度。
  - **欄位別名 + 巢狀攤平**：大模型常改 schema（用 name/children/end_date），以別名表與攤平器吸收差異，避免整批失敗。
  - **以實測校正進度文案**：端到端實測單次產生約 153 秒，將「10–30 秒」改為「1–3 分鐘」並拉開階段門檻。
- **影響範圍**：ARC-001, ARC-004, ARC-011（新）, ARC-012（新）｜ 需求：SR-010~SR-013
- **關聯 commit**：`916ff45` 簡繁轉換、`16bffcc` 解析/排程、`c58486b` Excel 匯出、`d003dda` 合規文件、`264c34d` start.sh、`99d26e2` 前端結構編輯+進度、`258e55f` 進度時間校正
- **已知風險／待辦**：
  - SR-012（Excel 匯出）、SR-008（Jira 部署）無自動化測試；前端結構編輯（SR-013）無測試框架。
  - 本地模型單次產生偏慢（~2.5 分鐘）；進度為時間估計而非後端真實回報（可考慮 SSE）。

---
## DEV-2026-06-01-1 — 初版 PM-Agent MVP 與合規文件導入
- **時間**：2026-06-01
- **做了什麼**：
  - 完成 PM-Agent MVP：輸入解析、LLM 產 WBS、逐節點驗證、Jira 部署、前端三頁。
  - LLM 後端從 Anthropic → OpenAI → 本地 Ollama（qwen2.5:7b），改用 JSON 模式取代 function calling。
  - 加入產生紀錄（gen_log）與回測測試套件（33 passed）。
  - 初始 commit 推上 GitHub（chinhui741209-dev/PM-Agent）。
  - 導入合規文件 skills，產生 `docs/compliance/`。
- **為什麼（關鍵決策）**：
  - **JSON 模式取代 function calling**：本地小模型對複雜 tool schema 會回空；JSON 模式對 Ollama 與 OpenAI 都穩。
  - **排程約束注入 prompt**：本地模型無「今天」概念，需顯式餵入今天與交付日，否則排程掉到過去年份。
  - **容錯正規化 + 防呆**：模型輸出雜亂（裸陣列、字串化、壞 type），以 `_normalize_tool_input`/`_build_tree` 容錯，避免整批失敗。
- **影響範圍**：ARC-002~ARC-008 ｜ 需求：SR-001~SR-009
- **關聯 commit**：`9bdeecc Initial commit: AI Agent PM — 自動 WBS 產生與一鍵部署 Jira`
- **已知風險／待辦**：
  - SR-008（Jira 部署）無自動化測試；jira_client / store / parser docx,pdf 未覆蓋。
  - 覆蓋率工具未啟用。
  - WBS 品質受本地模型大小影響（qwen2.5:7b 仍偶有里程碑偏少）。
