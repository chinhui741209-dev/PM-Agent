# 合規文件索引（PM-Agent）

> 最後更新：2026-06-02 ｜ 對應 git：258e55f ｜ 由 skill：end-of-work
>
> 本資料夾為符合 **ASPICE SWE.1–6** 與 **ISO 26262 Part 6（軟體層）** 的工作產出與雙向追溯證據，
> 由 `~/.claude/skills/` 的合規記錄 skills 自動產生與維護。

## 文件清單
| 檔案 | 內容 | ASPICE | ISO 26262-6 |
|---|---|---|---|
| [01-software-requirements.md](01-software-requirements.md) | 軟體需求（SR-） | SWE.1 | §6 |
| [02-software-architecture.md](02-software-architecture.md) | 架構、元件、介面（ARC-/IF-） | SWE.2 | §7 |
| [03-data-flow.md](03-data-flow.md) | 資料流、信任邊界（DF-） | SWE.2/3 | §7/§8 |
| [04-detailed-design.md](04-detailed-design.md) | 單元詳細設計（DD-） | SWE.3 | §8 |
| [05-unit-test-spec.md](05-unit-test-spec.md) | 單元測試規格（TC-） | SWE.4 | §9 |
| [06-unit-test-results.md](06-unit-test-results.md) | 測試結果（TR-） | SWE.4 | §9 |
| [07-traceability-matrix.md](07-traceability-matrix.md) | 雙向追溯矩陣 | SWE.1–6 | §6–9 |
| [08-development-history.md](08-development-history.md) | 開發歷程／決策（DEV-） | SUP.8/10 脈絡 | §5 脈絡 |
| [09-compliance-audit.md](09-compliance-audit.md) | 稽核檢查表＋缺口 | — | — |
| `.audit-log.jsonl` | 稽核軌跡（每次收工一筆） | — | — |

## ID 規則摘要
`SR-`需求 ｜ `ARC-`元件 ｜ `IF-`介面 ｜ `DF-`資料流 ｜ `DD-`單元設計 ｜ `TC-`測試案例 ｜ `TR-`測試結果 ｜ `DEV-`開發歷程。三位補零、不重用、不變更。

## 範圍與限制
- 涵蓋**軟體層**（SWE.1–6 / 26262-6 §6–9）。
- **範圍外**：系統層（SYS.1–5）、整合/合格測試（SWE.5/6）、管理/支援流程（MAN/SUP 完整）—文件中以「範圍外・預留」標註。
- 本文件為**追溯證據**，非功能安全認證；仍需人工審查與獨立確認（confirmation measures）。
