"""管線各環節的單元測試：解析、正規化、組樹、日期、空節點過濾。"""
import io

from app.services import parser
from app.services.wbs_generator import (
    _build_tree,
    _extract_json,
    _normalize_tool_input,
    _parse_date,
    parse_wbs_content,
)


# ---- parser ----

def test_parse_text_trims():
    text, deliv = parser.parse_text("  做一個登入頁  ")
    assert text == "做一個登入頁"
    assert deliv == []


def test_parse_xlsx_extracts_deliverables():
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["交付物", "說明"])
    ws.append(["登入頁", "含SSO"])
    ws.append(["後台", "權限"])
    buf = io.BytesIO()
    wb.save(buf)
    text, source, deliv = parser.parse_upload("spec.xlsx", buf.getvalue())
    assert source == "xlsx"
    assert deliv == ["登入頁", "後台"]
    assert "登入頁" in text


# ---- _extract_json ----

def test_extract_json_from_fences():
    raw = "前綴\n```json\n{\"a\": {\"b\": 1}}\n```\n後綴"
    assert _extract_json(raw) == '{"a": {"b": 1}}'


def test_extract_json_none_when_absent():
    assert _extract_json("沒有大括號") is None


# ---- _normalize_tool_input（各種雜格式）----

def test_normalize_standard():
    out = _normalize_tool_input({"nodes": [{"id": "1", "title": "a"}], "milestones": []})
    assert len(out["nodes"]) == 1


def test_normalize_bare_array():
    out = _normalize_tool_input([{"id": "1", "title": "a", "type": "task"}])
    assert len(out["nodes"]) == 1


def test_normalize_wrapped_parameters_with_string_nodes():
    out = _normalize_tool_input({"parameters": {"nodes": '[{"id":"1","title":"a"}]'}})
    assert len(out["nodes"]) == 1


def test_normalize_alt_key_tasks():
    out = _normalize_tool_input({"tasks": [{"id": "1", "title": "a", "type": "task"}], "milestones": []})
    assert len(out["nodes"]) == 1


def test_normalize_any_nodelike_value():
    out = _normalize_tool_input(
        {"breakdown": [{"id": "1", "title": "a", "type": "epic"}, {"id": "2", "title": "b", "type": "task"}]}
    )
    assert len(out["nodes"]) == 2


def test_normalize_garbage_returns_empty():
    assert _normalize_tool_input("not json") == {}


# ---- parse_wbs_content（端到端字串 → dict）----

def test_parse_wbs_content_with_fences():
    raw = '```json\n{"nodes":[{"id":"1","title":"a","type":"task"}],"milestones":[]}\n```'
    out = parse_wbs_content(raw)
    assert len(out["nodes"]) == 1


def test_parse_wbs_content_truncated_is_empty():
    out = parse_wbs_content('{"nodes": [{"id": "1", "title": "截斷')
    assert out["nodes"] == []


# ---- _build_tree ----

def test_build_tree_hierarchy_and_deps():
    flat = [
        {"id": "e1", "parent_id": None, "type": "epic", "title": "根"},
        {"id": "s1", "parent_id": "e1", "type": "story", "title": "子", "dependencies": ["e1"]},
        {"id": "t1", "parent_id": "s1", "type": "task", "title": "孫"},
    ]
    tree = _build_tree(flat)
    assert len(tree) == 1
    assert tree[0].id == "e1"
    assert tree[0].children[0].id == "s1"
    assert tree[0].children[0].children[0].id == "t1"
    assert tree[0].children[0].dependencies == ["e1"]


def test_build_tree_filters_empty_nodes():
    flat = [
        {"id": "e1", "parent_id": None, "type": "epic", "title": "根"},
        {"id": "", "parent_id": "e1", "type": "task", "title": ""},
        {"id": "t1", "parent_id": "e1", "type": "task", "title": "   "},
        {"id": "t2", "parent_id": "e1", "type": "task", "title": "有效"},
    ]
    tree = _build_tree(flat)
    titles = [c.title for c in tree[0].children]
    assert titles == ["有效"]


def test_build_tree_coerces_bad_type():
    # 模型吐出不合法 type 不應讓整批失敗，應防呆成 task
    flat = [{"id": "x1", "parent_id": None, "type": "milestone", "title": "怪型別"}]
    tree = _build_tree(flat)
    assert len(tree) == 1
    assert tree[0].type == "task"


def test_build_tree_handles_string_estimate_and_deps():
    flat = [{"id": "x1", "parent_id": None, "type": "task", "title": "a",
             "estimate_days": "三天", "dependencies": "s1"}]
    tree = _build_tree(flat)
    assert tree[0].estimate_days is None      # 非數字 → None，不炸
    assert tree[0].dependencies == []         # 非 list → []，不炸


def test_build_tree_orphan_becomes_root():
    flat = [
        {"id": "a", "parent_id": "missing", "type": "task", "title": "孤兒"},
    ]
    tree = _build_tree(flat)
    assert len(tree) == 1
    assert tree[0].id == "a"


# ---- _parse_date ----

def test_parse_date_variants():
    assert _parse_date("2026-09-30").isoformat() == "2026-09-30"
    assert _parse_date("2026-09-30T12:00:00").isoformat() == "2026-09-30"
    assert _parse_date(None) is None
    assert _parse_date("not-a-date") is None
