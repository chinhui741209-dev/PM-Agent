# 04 軟體詳細設計（ASPICE SWE.3 / ISO 26262-6 §8）

> 最後更新：2026-06-02 ｜ 對應 git：258e55f ｜ 由 skill：record-architecture

各關鍵單元的設計重點與演算法。

### DD-001 輸入解析分派
- 單元：`backend/app/services/parser.py::parse_upload`
- 設計：依副檔名分派至 `parse_docx/parse_pdf/parse_xlsx`，否則當純文字；回傳 `(text, source, deliverables)`。
- 對應：SR-001, SR-002, ARC-003 ｜ 測試：TC-001, TC-002

### DD-002 LLM 呼叫與容錯解析
- 單元：`backend/app/services/wbs_generator.py::generate_wbs` / `parse_wbs_content` / `_normalize_tool_input` / `_find_node_list` / `_flatten_nodes`
- 設計：JSON 模式呼叫 LLM；`parse_wbs_content` 認 `{`/`[` 開頭或抽圍欄 JSON；`_find_node_list` 不分大小寫找節點清單；`_normalize_tool_input` 解開包裝、欄位別名（`_ALIASES`：name→title、end_date→due_date、owner→owner_unit…）、字串化清單、裸陣列；`_flatten_nodes` 把巢狀 children 攤平成扁平+parent_id 並依深度推斷 type；以「組樹後節點數」判定成敗、空則重試一次；`max_tokens=8000` 防截斷。
- 對應：SR-003, SR-006, ARC-004 ｜ 測試：TC-006~TC-013, TC-028~TC-029, TC-026~TC-027

### DD-003 樹狀組裝與防呆
- 單元：`wbs_generator.py::_build_tree`
- 設計：依 parent_id 組樹；濾掉空 id/title 節點；不合法 type→task；非數字 estimate→None；非 list dependencies→[]。孤兒節點升為 root。
- 對應：SR-006, ARC-004 ｜ 測試：TC-014~TC-018, TC-029

### DD-004 排程約束（prompt 指令）
- 單元：`wbs_generator.py::generate_wbs` / `_schedule_directive`
- 設計：把 `date.today()` 與交付日注入 prompt，並依條件粒度產生明確排程硬指令（週/雙週/日/月）；硬性要求日期介於今天與交付日之間、欄位名與最外層鍵格式。
- 對應：SR-005, SR-010, ARC-004 ｜ 測試：（prompt 端無直接 UT；排程結果由 DD-008 驗證）

### DD-008 排程粒度偵測與程式化排程
- 單元：`wbs_generator.py::_detect_unit_days` / `_apply_schedule` / `_iter_nodes` / `_has_missing_dates`
- 設計：`_detect_unit_days` 由條件偵測粒度回日曆天跨度（週=7/雙週=14/日=1/月=30）。指定了粒度或葉節點缺起訖日時，`_apply_schedule` 把葉節點依序排成連續時段（週/雙週對齊下個週一、工作天估時 5/10）、不超過交付日，再由葉往根上捲父節點起訖日。日期算術以程式決定（LLM 不擅長）。
- 對應：SR-010, ARC-004 ｜ 測試：TC-030, TC-031

### DD-009 簡繁轉換
- 單元：`backend/app/services/zh_convert.py::to_tw`（`_converter` 以 lru_cache 載入 OpenCC s2twp）/ `wbs_generator.py::_convert_nodes_to_tw`
- 設計：`to_tw` 對字串轉繁中，非字串/空值原樣回傳，套件缺失或轉換例外時退化為不轉換；`_convert_nodes_to_tw` 就地遞迴轉換節點的 title/description/deliverable/owner_unit/workflow_stage 與里程碑。
- 對應：SR-011, ARC-011 ｜ 測試：TC-032, TC-033, TC-034

### DD-010 Excel 匯出
- 單元：`backend/app/services/excel_export.py::build_wbs_workbook`
- 設計：以 openpyxl 建立「工作項」與「里程碑」兩工作表；表頭填色、依 type（epic/story/task/subtask）著色、欄寬調整；回傳 .xlsx bytes 供 `routers/wbs.py::export_xlsx` 以附件回應。
- 對應：SR-012, ARC-012 ｜ 測試：（無自動化測試 — 見稽核缺口）

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
