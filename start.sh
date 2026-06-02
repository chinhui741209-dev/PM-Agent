#!/usr/bin/env bash
# 一鍵啟動 PM-Agent web（後端 FastAPI + 前端 Vite）
# 用法： ./start.sh        然後瀏覽 http://localhost:5173
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo "▶ PM-Agent 啟動中…"

# --- 後端 ---
if ! curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
  echo "  啟動後端 (http://localhost:8000)…"
  cd "$BACKEND"
  [ -d .venv ] || python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q -r requirements.txt
  (uvicorn app.main:app --port 8000 >/tmp/pmagent_backend.log 2>&1 &)
else
  echo "  後端已在跑 ✓"
fi

# --- 前端 ---
if ! curl -s http://localhost:5173/ >/dev/null 2>&1; then
  echo "  啟動前端 (http://localhost:5173)…"
  cd "$FRONTEND"
  [ -d node_modules ] || npm install
  (npm run dev >/tmp/pmagent_frontend.log 2>&1 &)
else
  echo "  前端已在跑 ✓"
fi

# --- 等待就緒 ---
echo -n "  等待服務就緒"
for _ in $(seq 1 30); do
  if curl -s http://localhost:8000/api/health >/dev/null 2>&1 && curl -s http://localhost:5173/ >/dev/null 2>&1; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo "✅ PM-Agent 已就緒："
echo "   前端 Web ：http://localhost:5173"
echo "   後端 API ：http://localhost:8000/docs"
echo ""
echo "（log：/tmp/pmagent_backend.log、/tmp/pmagent_frontend.log）"

# macOS 自動開瀏覽器
command -v open >/dev/null 2>&1 && open http://localhost:5173 || true
