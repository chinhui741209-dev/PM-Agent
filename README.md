# AI Agent PM

以 PM 為角色的 AI Agent：輸入**需求/技術規格 + 交付物 + 交付日 + 條件** → 自動產生 **WBS（工作分解結構）** → PM 在介面檢視/編輯/指派負責單位 → **一鍵部署到 Jira Cloud**（含階層、里程碑、初始狀態）。

## 架構
- **backend/** — Python + FastAPI；透過 **OpenAI 相容 API**（`response_format=json_object` 結構化輸出，端點不支援時自動退回一般呼叫）產 WBS，**預設指向本地 Ollama（`qwen2.5:7b`）**，亦可改用官方 OpenAI；解析 Word/PDF/Excel、簡體自動轉繁中、依條件程式化排程、Excel 匯出、串 Jira Cloud REST API v3。
- **frontend/** — React + Vite + TypeScript；三頁流程：輸入需求 → WBS 檢視/編輯（可調整結構） → 部署 Jira。

## 設定
產生 WBS 透過 **OpenAI 相容 API**，編輯 `backend/.env`（從 `.env.example` 複製），二選一：

**A. 本地 Ollama（預設・免費・免金鑰）**
```env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama          # 佔位即可，Ollama 不驗證金鑰
WBS_MODEL=qwen2.5:7b           # 先 `ollama pull qwen2.5:7b`；想更高品質可用 qwen2.5:14b
```

**B. 官方 OpenAI**
```env
OPENAI_BASE_URL=               # 留空走官方端點
OPENAI_API_KEY=sk-xxxx         # https://platform.openai.com/api-keys
WBS_MODEL=gpt-4o               # 或 gpt-4o-mini / gpt-4.1 等
```

- `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN`：部署到 Jira 時才需要（[建立 API token](https://id.atlassian.com/manage-profile/security/api-tokens)）。

## 啟動
**一鍵啟動**（自動建 venv、裝依賴、起前後端）：
```bash
./start.sh            # 然後開 http://localhost:5173
```
> 用預設的本地 Ollama 時，請先確認 Ollama 已啟動（`ollama serve`）並已 `ollama pull qwen2.5:7b`。

或手動分別啟動 —
**後端**（http://localhost:8000，API 文件 `/docs`）：
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
**前端**（http://localhost:5173，已設定 `/api` proxy 到後端）：
```bash
cd frontend
npm install
npm run dev
```

## 流程
1. **輸入需求** — 貼文字或上傳檔（Word/PDF/MD/Excel），填交付物、交付日、條件、組織單位、工作流模板 → 產生 WBS。
2. **WBS 檢視** — 編輯每項工作的標題、**負責單位**、初始階段、起訖日、估時；**調整結構**（新增/刪除/升降級/排序節點）；查看里程碑；儲存或**下載 Excel**。
3. **部署 Jira** — 選目標專案 → 一鍵建立 Epic/Story/Task 階層；里程碑→Version；負責單位→label；初始狀態 transition；回傳每張 issue 連結。

## 測試與回測
```bash
cd backend && source .venv/bin/activate
pytest                      # 跑全部測試
pytest tests/test_backtest.py -v   # 只跑回測
```
- `tests/test_pipeline.py`：解析、正規化（含欄位別名/巢狀攤平）、組樹、程式化排程、型別防呆等逐環節單元測試。
- `tests/test_validation.py`：逐節點驗證器（型別、負責單位、日期區間、依賴一致性）。
- `tests/test_zh_convert.py`：簡體→繁體（台灣用語）轉換。
- `tests/test_backtest.py`：**回測**。把「模型原始輸出」重播過解析管線並驗證每個節點：
  - `tests/fixtures/raw_outputs.jsonl`：手工整理的代表性雜格式輸出。
  - `backend/data/logs/wbs_generations.jsonl`：每次線上產生都會存下請求＋模型原始輸出（見 `app/services/gen_log.py`），測試會自動重播這些真實紀錄做回歸。

## 已知限制
- Jira REST API 無法以程式穩定建立**自訂工作流/看板欄位**（需 admin 級操作）。本工具會把節點對應到專案**既有狀態**，並在部署頁顯示**建議看板欄位順序**供 PM 在 Jira 手動設定。
- WBS 草稿以 JSON 檔存在 `backend/data/`（MVP；之後可換 DB）。
