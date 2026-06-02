# 08 開發歷程／決策紀錄

> 最後更新：2026-06-01 ｜ 對應 git：9bdeecc ｜ 由 skill：record-devlog

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
