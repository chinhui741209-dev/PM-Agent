# 07 雙向追溯矩陣（ASPICE SWE.1–6 / ISO 26262-6 §6–9）

> 最後更新：2026-06-01 ｜ 對應 git：9bdeecc ｜ 由 skill：compliance-audit

追溯鏈：SR → ARC → DD/單元 → 原始碼 → TC → TR。

| SR | ARC | DD / 單元 | 原始碼 (file::symbol) | TC | TR (P/F) | 備註 |
|---|---|---|---|---|---|---|
| SR-001 | ARC-003 | DD-001 | `services/parser.py::parse_text/parse_upload` | TC-001 | ✅ | docx/pdf 分支未測 |
| SR-002 | ARC-003 | DD-001 | `services/parser.py::parse_xlsx` | TC-002 | ✅ | |
| SR-003 | ARC-004 | DD-002, DD-003 | `services/wbs_generator.py::_build_tree/_parse_date` | TC-013, TC-018 | ✅ | 產生側需 LLM |
| SR-004 | ARC-004, ARC-008 | DD-005 | `validation.py::validate_node` | TC-020 | ✅ | |
| SR-005 | ARC-004 | DD-004, DD-005 | `wbs_generator.py::generate_wbs`; `validation.py` | TC-021, TC-022 | ✅ | 產生側約束無離線 UT 🟡 |
| SR-006 | ARC-004 | DD-002, DD-003 | `wbs_generator.py::parse_wbs_content/_normalize_tool_input/_build_tree` | TC-003..TC-017, TC-026 | ✅ | 覆蓋充分 |
| SR-007 | ARC-008 | DD-005 | `validation.py::validate_node/validate_draft` | TC-019, TC-023, TC-024, TC-025 | ✅ | |
| SR-008 | ARC-005 | DD-007 | `services/jira_client.py`; `routers/jira.py::deploy` | — | ❌ | **無自動化測試（缺口）** |
| SR-009 | ARC-006 | DD-006 | `services/gen_log.py::log_generation/read_generations` | TC-027 | ✅ | 寫入路徑僅間接覆蓋 🟡 |

## 反向追溯摘要
- **需求 → 測試**：9 個 SR 中 8 個有對應 TC（SR-008 無）→ 孤兒需求 1。
- **單元 → 測試**：核心邏輯單元（解析、正規化、組樹、驗證）均有 TC；未測單元：`jira_client`、`store`、`parser.parse_docx/parse_pdf`。
- **測試 → 需求**：27 個 TC 全部對應到至少一個 SR（無無主測試）。
- **測試結果**：33 passed / 0 failed → 無失敗 TR。
