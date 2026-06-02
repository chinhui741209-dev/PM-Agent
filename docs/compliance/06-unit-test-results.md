# 06 單元測試結果（ASPICE SWE.4 / ISO 26262-6 §9）

> 最後更新：2026-06-01 ｜ 對應 git：9bdeecc ｜ 由 skill：record-ut

## 執行 @ 2026-06-01
- 環境：Python 3.14.4 / macOS（Darwin 25.5.0）｜ venv：`backend/.venv`
- 指令：`pytest -q`
- 結果：**33 passed, 0 failed, 1 skipped**，耗時 ~0.25s
  - （27 個 TC；TC-026 為參數化 7 子案例 → pytest 計為 33 項。1 skipped = TC-027 在無 log 檔時跳過；本次有 log 故執行通過。）
- 覆蓋率：未量測（未安裝 pytest-cov）— 列為缺口。

| TR | 對應 TC | 被測單元 | 結果 |
|---|---|---|---|
| TR-001 | TC-001 | parser.parse_text | ✅ Pass |
| TR-002 | TC-002 | parser.parse_xlsx | ✅ Pass |
| TR-003..TR-018 | TC-003..TC-018 | _extract_json / _normalize_tool_input / parse_wbs_content / _build_tree / _parse_date | ✅ Pass（16 項） |
| TR-019..TR-025 | TC-019..TC-025 | validation.validate_node / validate_draft | ✅ Pass（7 項） |
| TR-026 | TC-026 | parse_wbs_content+_build_tree（回測 7 子案例） | ✅ Pass |
| TR-027 | TC-027 | 回測實際產生紀錄 | ✅ Pass |

### 失敗詳情
- 無失敗。

### 備註
- 覆蓋率工具未啟用（建議 `pip install pytest-cov` 後 `pytest --cov=app`）。
- 未涵蓋單元見 05 之覆蓋缺口（jira_client、store、parser docx/pdf）。
