"""把每次 WBS 產生的請求與模型原始輸出存成 JSONL，供之後回測（replay）。

每行一筆 JSON：{ts, model, request, raw_content, node_count, success, attempts}。
測試可讀這個檔，把 raw_content 重播過解析管線，驗證不靠 LLM 也能回歸。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from ..config import get_settings

LOG_NAME = "wbs_generations.jsonl"


def _log_path() -> str:
    d = os.path.join(get_settings().data_dir, "logs")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, LOG_NAME)


def log_generation(
    *,
    model: str,
    request: dict,
    raw_content: str,
    node_count: int,
    success: bool,
    attempts: int,
) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "request": request,
        "raw_content": raw_content,
        "node_count": node_count,
        "success": success,
        "attempts": attempts,
    }
    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        # 記錄失敗不應影響主流程
        pass


def read_generations(path: str | None = None) -> list[dict]:
    path = path or _log_path()
    out: list[dict] = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
