"""逐節點驗證 WBS：型別、負責單位、日期區間、parent/依賴一致性。

回傳問題清單（不丟例外），可用於測試、回測、或日後在 API 回傳警告。
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from .models import WbsDraft, WbsNode

VALID_TYPES = {"epic", "story", "task", "subtask"}


@dataclass
class NodeIssue:
    node_id: str
    field: str
    message: str


def _iter_nodes(nodes: list[WbsNode]):
    for n in nodes:
        yield n
        if n.children:
            yield from _iter_nodes(n.children)


def validate_node(
    node: WbsNode,
    *,
    allowed_units: set[str] | None = None,
    earliest: datetime.date | None = None,
    latest: datetime.date | None = None,
    known_ids: set[str] | None = None,
) -> list[NodeIssue]:
    """驗證單一節點，回傳問題清單（空清單代表通過）。"""
    issues: list[NodeIssue] = []

    if not (node.id or "").strip():
        issues.append(NodeIssue(node.id, "id", "節點缺少 id"))
    if not (node.title or "").strip():
        issues.append(NodeIssue(node.id, "title", "節點缺少 title"))
    if node.type not in VALID_TYPES:
        issues.append(NodeIssue(node.id, "type", f"type「{node.type}」不在 {VALID_TYPES}"))

    if allowed_units and node.owner_unit and node.owner_unit not in allowed_units:
        issues.append(NodeIssue(node.id, "owner_unit", f"負責單位「{node.owner_unit}」不在可用單位清單"))

    if node.start_date and node.due_date and node.start_date > node.due_date:
        issues.append(NodeIssue(node.id, "due_date", "due_date 早於 start_date"))
    for field, val in (("start_date", node.start_date), ("due_date", node.due_date)):
        if val is None:
            continue
        if earliest and val < earliest:
            issues.append(NodeIssue(node.id, field, f"{field} {val} 早於最早起點 {earliest}"))
        if latest and val > latest:
            issues.append(NodeIssue(node.id, field, f"{field} {val} 晚於交付日 {latest}"))

    if known_ids:
        for dep in node.dependencies:
            if dep not in known_ids:
                issues.append(NodeIssue(node.id, "dependencies", f"依賴的 id「{dep}」不存在"))

    return issues


def validate_draft(draft: WbsDraft, today: datetime.date | None = None) -> list[NodeIssue]:
    """走訪整份 WBS，對每個節點套用 validate_node，彙整所有問題。"""
    today = today or datetime.date.today()
    allowed = set(draft.org_units) if draft.org_units else None
    latest = draft.delivery_date
    all_nodes = list(_iter_nodes(draft.nodes))
    known_ids = {n.id for n in all_nodes}

    issues: list[NodeIssue] = []
    for n in all_nodes:
        issues.extend(
            validate_node(
                n,
                allowed_units=allowed,
                earliest=today,
                latest=latest,
                known_ids=known_ids,
            )
        )
    return issues
