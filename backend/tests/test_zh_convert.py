"""簡轉繁（台灣用語）測試。"""
from app.models import WbsNode
from app.services.wbs_generator import _convert_nodes_to_tw
from app.services.zh_convert import to_tw


def test_to_tw_basic_terms():
    assert to_tw("软件") == "軟體"
    assert to_tw("硬件") == "硬體"
    assert to_tw("用户界面") == "使用者介面"
    assert to_tw("数据") == "資料"


def test_to_tw_handles_none_and_empty():
    assert to_tw(None) is None
    assert to_tw("") == ""
    assert to_tw(123) == 123  # 非字串原樣回傳


def test_convert_nodes_tree_in_place():
    nodes = [
        WbsNode(
            id="e1", type="epic", title="系统设计", owner_unit="软件",
            children=[WbsNode(id="t1", type="task", title="数据处理", owner_unit="硬件")],
        )
    ]
    _convert_nodes_to_tw(nodes)
    assert nodes[0].title == "系統設計"
    assert nodes[0].owner_unit == "軟體"
    assert nodes[0].children[0].title == "資料處理"
    assert nodes[0].children[0].owner_unit == "硬體"
