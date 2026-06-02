# 07 雙向追溯矩陣（ASPICE SWE.1–6 / ISO 26262-6 §6–9）

> 最後更新：2026-06-02 ｜ 對應 git：258e55f ｜ 由 skill：compliance-audit

追溯鏈：SR → ARC → DD/單元 → 原始碼 → TC → TR。

| SR | ARC | DD / 單元 | 原始碼 (file::symbol) | TC | TR (P/F) | 備註 |
|---|---|---|---|---|---|---|
| SR-001 | ARC-003 | DD-001 | `services/parser.py::parse_text/parse_upload` | TC-001 | ✅ | docx/pdf 分支未測 |
| SR-002 | ARC-003 | DD-001 | `services/parser.py::parse_xlsx` | TC-002 | ✅ | |
| SR-003 | ARC-004 | DD-002, DD-003 | `services/wbs_generator.py::_build_tree/_parse_date` | TC-013, TC-018 | ✅ | 產生側需 LLM |
| SR-004 | ARC-004, ARC-008 | DD-005 | `validation.py::validate_node` | TC-020 | ✅ | |
| SR-005 | ARC-004 | DD-004, DD-005 | `wbs_generator.py::generate_wbs`; `validation.py` | TC-021, TC-022, TC-031 | ✅ | 排程結果由 TC-031 覆蓋 |
| SR-006 | ARC-004 | DD-002, DD-003 | `wbs_generator.py::parse_wbs_content/_normalize_tool_input/_flatten_nodes/_build_tree` | TC-003..TC-017, TC-026, TC-028, TC-029 | ✅ | 覆蓋充分 |
| SR-007 | ARC-008 | DD-005 | `validation.py::validate_node/validate_draft` | TC-019, TC-023, TC-024, TC-025 | ✅ | |
| SR-008 | ARC-005 | DD-007 | `services/jira_client.py`; `routers/jira.py::deploy` | — | ❌ | **無自動化測試（缺口）** |
| SR-009 | ARC-006 | DD-006 | `services/gen_log.py::log_generation/read_generations` | TC-027 | ✅ | 寫入路徑僅間接覆蓋 🟡 |
| SR-010 | ARC-004 | DD-004, DD-008 | `wbs_generator.py::_detect_unit_days/_apply_schedule/_schedule_directive` | TC-030, TC-031 | ✅ | 程式化排程，覆蓋佳 |
| SR-011 | ARC-011 | DD-009 | `services/zh_convert.py::to_tw`; `wbs_generator.py::_convert_nodes_to_tw` | TC-032, TC-033, TC-034 | ✅ | |
| SR-012 | ARC-012 | DD-010 | `services/excel_export.py::build_wbs_workbook`; `routers/wbs.py::export_xlsx` | — | ❌ | **無自動化測試（缺口）** |
| SR-013 | ARC-001 | （前端） | `frontend/src/pages/WbsReview.tsx::addChild/removeNode/moveNode/indentNode/outdentNode` | — | 🟡 | 前端無測試框架；經 tsc/build 與端到端手動驗證 |

## 反向追溯摘要
- **需求 → 測試**：13 個 SR 中 10 個有對應 TC；SR-008、SR-012 無自動化測試（孤兒需求 2），SR-013 為前端、以手動/建置驗證（🟡）。
- **單元 → 測試**：核心邏輯單元（解析、別名/巢狀正規化、組樹、程式化排程、簡轉繁、驗證）均有 TC；未測單元：`jira_client`、`excel_export`、`store`、`parser.parse_docx/parse_pdf`、前端結構編輯。
- **測試 → 需求**：34 個 TC 全部對應到至少一個 SR（無無主測試）。
- **測試結果**：41 passed / 0 failed → 無失敗 TR。
