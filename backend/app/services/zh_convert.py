"""簡體→繁體（台灣用語）轉換。WBS 內容若被模型產成簡體，統一轉為繁體中文。

用 OpenCC 的 s2twp（簡體→繁體台灣標準，含常用詞彙轉換，如 软件→軟體、用户→使用者）。
若 OpenCC 不可用則原樣回傳（不阻擋主流程）。
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _converter():
    try:
        import opencc

        return opencc.OpenCC("s2twp")
    except Exception:  # noqa: BLE001 — 套件缺失或載入失敗時退化為不轉換
        return None


def to_tw(text):
    """把字串轉成繁體（台灣用語）。非字串或空值原樣回傳。"""
    if not isinstance(text, str) or not text:
        return text
    cc = _converter()
    if cc is None:
        return text
    try:
        return cc.convert(text)
    except Exception:  # noqa: BLE001
        return text
