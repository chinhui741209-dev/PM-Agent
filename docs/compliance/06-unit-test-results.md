# 06 單元測試結果（ASPICE SWE.4 / ISO 26262-6 §9）

> 最後更新：2026-06-02 ｜ 對應 git：258e55f ｜ 由 skill：record-ut

## 執行 @ 2026-06-02
- 環境：Python 3.14.4 / macOS（Darwin 25.5.0）｜ venv：`backend/.venv`
- 指令：`pytest -q`
- 結果：**41 passed, 0 failed, 0 skipped**，耗時 ~0.25s
  - （34 個 TC；TC-026 為參數化 8 子案例 → pytest 計為 41 項。本次有 log 檔故 TC-027 執行通過、無 skip。）
  - 分布：test_pipeline 22、test_validation 7、test_backtest 9、test_zh_convert 3。
- 覆蓋率：未量測（未安裝 pytest-cov）— 列為缺口。

| TR | 對應 TC | 被測單元 | 結果 |
|---|---|---|---|
| TR-001 | TC-001 | parser.parse_text | ✅ Pass |
| TR-002 | TC-002 | parser.parse_xlsx | ✅ Pass |
| TR-003..TR-018 | TC-003..TC-018 | _extract_json / _normalize_tool_input / parse_wbs_content / _build_tree / _parse_date | ✅ Pass（16 項） |
| TR-019..TR-025 | TC-019..TC-025 | validation.validate_node / validate_draft | ✅ Pass（7 項） |
| TR-026 | TC-026 | parse_wbs_content+_build_tree（回測 8 子案例） | ✅ Pass |
| TR-027 | TC-027 | 回測實際產生紀錄 | ✅ Pass |
| TR-028..TR-029 | TC-028..TC-029 | _normalize_tool_input/_flatten_nodes/_build_tree（別名+巢狀） | ✅ Pass（2 項） |
| TR-030..TR-031 | TC-030..TC-031 | _detect_unit_days / _apply_schedule（程式化排程） | ✅ Pass（2 項） |
| TR-032..TR-034 | TC-032..TC-034 | zh_convert.to_tw / _convert_nodes_to_tw（簡轉繁） | ✅ Pass（3 項） |

### 失敗詳情
- 無失敗。

### 備註
- 覆蓋率工具未啟用（建議 `pip install pytest-cov` 後 `pytest --cov=app`）。
- 未涵蓋單元見 05 之覆蓋缺口（jira_client、excel_export、store、parser docx/pdf）。
