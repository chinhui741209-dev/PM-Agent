# 05 單元測試規格（ASPICE SWE.4 / ISO 26262-6 §9）

> 最後更新：2026-06-01 ｜ 對應 git：9bdeecc ｜ 由 skill：record-test

由 `backend/tests/` 既有測試整理。共 27 個測試案例（TC-026 為參數化，含 7 個子案例）。

| TC | 目的 | 被測單元 | 對應需求 | 測試實作 |
|---|---|---|---|---|
| TC-001 | 純文字輸入去除前後空白 | `parser.parse_text` | SR-001 | test_pipeline::test_parse_text_trims |
| TC-002 | Excel 抽取交付物（每列首欄） | `parser.parse_xlsx` | SR-002 | test_pipeline::test_parse_xlsx_extracts_deliverables |
| TC-003 | 從 markdown 圍欄抽 JSON | `_extract_json` | SR-006 | test_pipeline::test_extract_json_from_fences |
| TC-004 | 無大括號時回 None | `_extract_json` | SR-006 | test_pipeline::test_extract_json_none_when_absent |
| TC-005 | 標準 {nodes,milestones} 正規化 | `_normalize_tool_input` | SR-006 | test_pipeline::test_normalize_standard |
| TC-006 | 裸陣列當作 nodes | `_normalize_tool_input` | SR-006 | test_pipeline::test_normalize_bare_array |
| TC-007 | 解開 parameters 包裝、字串化 nodes | `_normalize_tool_input` | SR-006 | test_pipeline::test_normalize_wrapped_parameters_with_string_nodes |
| TC-008 | 別名鍵 tasks → nodes | `_normalize_tool_input` | SR-006 | test_pipeline::test_normalize_alt_key_tasks |
| TC-009 | 任意 node-like 值救回 | `_normalize_tool_input` | SR-006 | test_pipeline::test_normalize_any_nodelike_value |
| TC-010 | 垃圾輸入回空 dict | `_normalize_tool_input` | SR-006 | test_pipeline::test_normalize_garbage_returns_empty |
| TC-011 | 圍欄 JSON 端到端解析 | `parse_wbs_content` | SR-006 | test_pipeline::test_parse_wbs_content_with_fences |
| TC-012 | 截斷 JSON → 空 nodes | `parse_wbs_content` | SR-006 | test_pipeline::test_parse_wbs_content_truncated_is_empty |
| TC-013 | 階層與依賴正確組樹 | `_build_tree` | SR-003 | test_pipeline::test_build_tree_hierarchy_and_deps |
| TC-014 | 過濾空 id/title 節點 | `_build_tree` | SR-006 | test_pipeline::test_build_tree_filters_empty_nodes |
| TC-015 | 不合法 type 防呆成 task | `_build_tree` | SR-006 | test_pipeline::test_build_tree_coerces_bad_type |
| TC-016 | 字串 estimate/deps 不致崩 | `_build_tree` | SR-006 | test_pipeline::test_build_tree_handles_string_estimate_and_deps |
| TC-017 | 孤兒節點升為 root | `_build_tree` | SR-006 | test_pipeline::test_build_tree_orphan_becomes_root |
| TC-018 | 日期解析各種格式 | `_parse_date` | SR-003 | test_pipeline::test_parse_date_variants |
| TC-019 | 合法節點無問題 | `validation.validate_node` | SR-007 | test_validation::test_valid_node_has_no_issues |
| TC-020 | 不合規負責單位被標記 | `validate_node` | SR-004, SR-007 | test_validation::test_invalid_owner_unit_flagged |
| TC-021 | 早於今天的日期被標記 | `validate_node` | SR-005, SR-007 | test_validation::test_date_before_today_flagged |
| TC-022 | 晚於交付日被標記 | `validate_node` | SR-005, SR-007 | test_validation::test_date_after_delivery_flagged |
| TC-023 | due 早於 start 被標記 | `validate_node` | SR-007 | test_validation::test_due_before_start_flagged |
| TC-024 | 未知依賴被標記 | `validate_node` | SR-007 | test_validation::test_unknown_dependency_flagged |
| TC-025 | validate_draft 走訪所有節點 | `validate_draft` | SR-007 | test_validation::test_validate_draft_walks_all_nodes |
| TC-026 | 回測：重播代表性原始輸出（7 子案例） | `parse_wbs_content`+`_build_tree` | SR-006, SR-009 | test_backtest::test_replay_fixture |
| TC-027 | 回測：重播實際產生紀錄 | `parse_wbs_content`+`_build_tree` | SR-009 | test_backtest::test_replay_captured_logs |

## 覆蓋缺口（待補測試）
- `services/jira_client.py`（DD-007, ARC-005, SR-008）：**無單元測試**。
- `store.py`（ARC-009）：**無單元測試**。
- `parser.parse_docx` / `parse_pdf`（DD-001 之一部分）：僅 xlsx 與 text 有測試，docx/pdf 未覆蓋。
- DD-004 排程約束（SR-005 產生側）：僅驗證側（TC-021/022）有測，產生側需 LLM，無離線 UT。
- `gen_log.log_generation` 寫入路徑（DD-006）：僅讀取路徑經 TC-027 間接覆蓋。
