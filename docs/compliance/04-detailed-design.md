# 04 軟體詳細設計（ASPICE SWE.3 / ISO 26262-6 §8）

> 最後更新：2026-06-01 ｜ 對應 git：9bdeecc ｜ 由 skill：record-architecture

各關鍵單元的設計重點與演算法。

### DD-001 輸入解析分派
- 單元：`backend/app/services/parser.py::parse_upload`
- 設計：依副檔名分派至 `parse_docx/parse_pdf/parse_xlsx`，否則當純文字；回傳 `(text, source, deliverables)`。
- 對應：SR-001, SR-002, ARC-003 ｜ 測試：TC-001, TC-002

### DD-002 LLM 呼叫與容錯解析
- 單元：`backend/app/services/wbs_generator.py::generate_wbs` / `parse_wbs_content` / `_normalize_tool_input`
- 設計：JSON 模式呼叫 LLM；`parse_wbs_content` 認 `{`/`[` 開頭或抽圍欄 JSON；`_normalize_tool_input` 解開 parameters/wbs 包裝、別名鍵、字串化清單、裸陣列；空節點重試一次；`max_tokens=8000` 防截斷。
- 對應：SR-003, SR-006, ARC-004 ｜ 測試：TC-006~TC-013, TC-026~TC-027

### DD-003 樹狀組裝與防呆
- 單元：`wbs_generator.py::_build_tree`
- 設計：依 parent_id 組樹；濾掉空 id/title 節點；不合法 type→task；非數字 estimate→None；非 list dependencies→[]。孤兒節點升為 root。
- 對應：SR-006, ARC-004 ｜ 測試：TC-014~TC-018

### DD-004 排程約束
- 單元：`wbs_generator.py::generate_wbs`（prompt 組裝）
- 設計：把 `date.today()` 注入 prompt 並硬性要求所有日期介於今天與交付日之間。
- 對應：SR-005, ARC-004 ｜ 測試：（無直接 UT — 見稽核缺口，目前靠人工/回測觀察）

### DD-005 逐節點驗證
- 單元：`backend/app/validation.py::validate_node` / `validate_draft`
- 設計：檢查 id/title/type、owner_unit 是否在允許清單、日期區間與 start≤due、依賴 id 是否存在；回傳 `NodeIssue` 清單（不丟例外）。
- 對應：SR-007, ARC-008 ｜ 測試：TC-019~TC-025

### DD-006 產生紀錄
- 單元：`backend/app/services/gen_log.py::log_generation` / `read_generations`
- 設計：append JSONL；讀取時逐行容錯解析。寫檔失敗不影響主流程。
- 對應：SR-009, ARC-006 ｜ 測試：（經 test_backtest 的 read 路徑間接覆蓋）

### DD-007 Jira 部署
- 單元：`backend/app/services/jira_client.py` + `routers/jira.py::deploy`
- 設計：建 Version（里程碑）、依 parent 建階層、label（負責單位）、狀態 transition；逐筆錯誤回報不中斷。
- 對應：SR-008, ARC-005 ｜ 測試：（無自動化測試 — 見稽核缺口）
