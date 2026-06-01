"""MVP 用 JSON 檔暫存 WBS 草稿。每個草稿存成一個檔案。"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .config import get_settings
from .models import WbsDraft


def _data_dir() -> str:
    d = get_settings().data_dir
    os.makedirs(d, exist_ok=True)
    return d


def _path(draft_id: str) -> str:
    return os.path.join(_data_dir(), f"{draft_id}.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_draft(draft: WbsDraft) -> WbsDraft:
    if draft.created_at is None:
        draft.created_at = _now_iso()
    draft.updated_at = _now_iso()
    with open(_path(draft.id), "w", encoding="utf-8") as f:
        f.write(draft.model_dump_json(indent=2))
    return draft


def get_draft(draft_id: str) -> WbsDraft | None:
    path = _path(draft_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return WbsDraft.model_validate(json.load(f))


def list_drafts() -> list[dict]:
    out: list[dict] = []
    d = _data_dir()
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, name), "r", encoding="utf-8") as f:
                data = json.load(f)
            out.append(
                {
                    "id": data.get("id"),
                    "requirement_text": (data.get("requirement_text") or "")[:120],
                    "delivery_date": data.get("delivery_date"),
                    "updated_at": data.get("updated_at"),
                    "node_count": len(data.get("nodes", [])),
                }
            )
        except (OSError, json.JSONDecodeError):
            continue
    out.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return out
