"""逐節點驗證器測試。"""
import datetime

from app.models import WbsDraft, WbsNode
from app.validation import validate_draft, validate_node

TODAY = datetime.date(2026, 6, 1)
DELIVERY = datetime.date(2026, 9, 30)
UNITS = {"PM", "前端", "後端", "測試"}


def _node(**kw) -> WbsNode:
    base = dict(id="n1", type="task", title="工作")
    base.update(kw)
    return WbsNode(**base)


def test_valid_node_has_no_issues():
    n = _node(
        owner_unit="前端",
        start_date=datetime.date(2026, 6, 10),
        due_date=datetime.date(2026, 7, 1),
    )
    issues = validate_node(n, allowed_units=UNITS, earliest=TODAY, latest=DELIVERY)
    assert issues == []


def test_invalid_owner_unit_flagged():
    n = _node(owner_unit="前段")  # 不在清單
    issues = validate_node(n, allowed_units=UNITS)
    assert any(i.field == "owner_unit" for i in issues)


def test_date_before_today_flagged():
    n = _node(start_date=datetime.date(2025, 1, 1))
    issues = validate_node(n, earliest=TODAY, latest=DELIVERY)
    assert any(i.field == "start_date" for i in issues)


def test_date_after_delivery_flagged():
    n = _node(due_date=datetime.date(2026, 12, 31))
    issues = validate_node(n, earliest=TODAY, latest=DELIVERY)
    assert any(i.field == "due_date" for i in issues)


def test_due_before_start_flagged():
    n = _node(start_date=datetime.date(2026, 7, 1), due_date=datetime.date(2026, 6, 1))
    issues = validate_node(n)
    assert any("早於 start_date" in i.message for i in issues)


def test_unknown_dependency_flagged():
    n = _node(id="t1", dependencies=["nope"])
    issues = validate_node(n, known_ids={"t1"})
    assert any(i.field == "dependencies" for i in issues)


def test_validate_draft_walks_all_nodes():
    draft = WbsDraft(
        id="d1",
        org_units=list(UNITS),
        delivery_date=DELIVERY,
        nodes=[
            WbsNode(
                id="e1",
                type="epic",
                title="根",
                owner_unit="PM",
                children=[
                    _node(id="s1", owner_unit="不存在單位"),  # 應被抓到
                ],
            )
        ],
    )
    issues = validate_draft(draft, today=TODAY)
    assert any(i.node_id == "s1" and i.field == "owner_unit" for i in issues)
