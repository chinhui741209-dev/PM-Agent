"""回測：把「模型原始輸出」重播過解析管線，驗證每個節點結構正確。

兩個來源：
1. tests/fixtures/raw_outputs.jsonl —— 手工整理的代表性輸出（含各種雜格式）。
2. data/logs/wbs_generations.jsonl —— 線上每次產生實際存下的輸出（若存在）。

這讓我們不呼叫 LLM 也能對「真實發生過的輸出」做回歸，避免之前那種
『模型回了但解析不到節點』的問題再悄悄復發。
"""
import json
import os

import pytest

from app.services.gen_log import read_generations
from app.services.wbs_generator import _build_tree, parse_wbs_content
from app.validation import validate_node

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "raw_outputs.jsonl")
LOG_PATH = os.path.join("data", "logs", "wbs_generations.jsonl")


def _load_fixtures():
    cases = []
    with open(FIXTURES, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _node_structurally_valid(node) -> bool:
    """回測時只看結構（不看日期/單位是否在清單），確保每個節點本身可用。"""
    issues = validate_node(node)  # 不帶 allowed_units/日期界限
    return not issues


@pytest.mark.parametrize("case", _load_fixtures(), ids=lambda c: c["label"])
def test_replay_fixture(case):
    parsed = parse_wbs_content(case["raw_content"])
    tree = _build_tree(parsed.get("nodes", []))

    def count(ns):
        return sum(1 + count(n.children) for n in ns)

    total = count(tree)
    assert total >= case["expect_min_nodes"], f"{case['label']} 期望至少 {case['expect_min_nodes']} 節點，實得 {total}"

    # 凡是被建出來的節點，逐一檢查結構（id/title/type 合法）
    def walk(ns):
        for n in ns:
            assert _node_structurally_valid(n), f"節點結構不合法：{n.id} / {n.title} / {n.type}"
            walk(n.children)

    walk(tree)


def test_replay_captured_logs():
    """重播線上實際存下的成功產生紀錄；沒有 log 檔就跳過。"""
    records = read_generations(LOG_PATH)
    successful = [r for r in records if r.get("success") and r.get("raw_content")]
    if not successful:
        pytest.skip("尚無已存的成功產生紀錄（data/logs/wbs_generations.jsonl）")

    for r in successful:
        parsed = parse_wbs_content(r["raw_content"])
        tree = _build_tree(parsed.get("nodes", []))
        assert tree, f"回測失敗：{r.get('ts')} 的輸出重播後沒有節點"
        # 每個節點結構需合法
        stack = list(tree)
        while stack:
            node = stack.pop()
            assert _node_structurally_valid(node), f"節點結構不合法：{node.id}"
            stack.extend(node.children)
