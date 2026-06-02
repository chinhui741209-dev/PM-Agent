"""呼叫 LLM（OpenAI 或本地 Ollama）產生 WBS。

用 JSON 模式（response_format=json_object）取得結構化輸出：模型回傳「扁平的節點清單」
（每個節點帶 parent_id）與里程碑清單，伺服器端再依 parent_id 組成樹狀結構。
扁平清單比遞迴 schema 更穩定，JSON 模式則對本地小模型（如 qwen2.5）遠比 function
calling 可靠（小模型常無法填完複雜的 tool schema）。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, timedelta

from openai import OpenAI

from ..config import get_settings
from . import gen_log
from .zh_convert import to_tw

logger = logging.getLogger("ai_agent_pm.wbs")
from ..models import (
    GenerateWbsRequest,
    Milestone,
    WbsDraft,
    WbsNode,
    WorkflowTemplate,
)

SYSTEM_PROMPT = """你是一位資深的專案經理（PM），專長是把需求或技術規格拆解成完整、可執行的工作分解結構（WBS）。

你的任務：
1. 把工作拆成階層：epic（大項）→ story（功能/模組）→ task（具體工作）→ subtask（選用）。
2. 從「交付日」往回反推每項工作的 start_date 與 due_date，考慮工作順序與依賴。
3. 為每個節點從「可用組織單位清單」中挑選最合適的 owner_unit（負責單位）。
4. 辨識節點之間的依賴關係（dependencies，填對方的 id）。
5. 規劃階段性里程碑（milestones），每個里程碑對應一個日期與相關交付物。
6. 依「工作流模板」的階段，為每個節點設定合理的初始 workflow_stage（通常是第一個階段）。

規則：
- 每個節點要有唯一的 id（例：e1、s1、s1.1、t1.1.1）。parent_id 指向上層節點 id，最上層的 epic parent_id 為 null。
- owner_unit 必須是可用組織單位清單中的其中一個。
- 【排程務必遵守】所有 start_date 與 due_date 都必須落在「今天日期」與「交付日」之間（含兩端）：最早的工作不可早於今天，最後的工作必須剛好或早於交付日。請以今天為起點往後排，不要使用過去的年份。
- 每個 milestone 都要有非空的 name（繁體中文）與合理的 date（同樣介於今天與交付日之間），deliverables 填交付物名稱而非節點 id。
- 用繁體中文撰寫 title 與 description。

只輸出一個 JSON 物件（不要任何說明文字、不要 markdown 圍欄），格式如下：
{
  "nodes": [
    {"id": "e1", "parent_id": null, "type": "epic", "title": "...", "description": "...",
     "deliverable": "對應交付物或 null", "owner_unit": "負責單位", "estimate_days": 5,
     "start_date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD", "milestone_id": "m1 或 null",
     "workflow_stage": "初始階段", "dependencies": ["其他節點id"]},
    {"id": "s1", "parent_id": "e1", "type": "story", "title": "...", ...}
  ],
  "milestones": [
    {"id": "m1", "name": "...", "date": "YYYY-MM-DD", "deliverables": ["..."]}
  ]
}
type 只能是 epic / story / task / subtask。"""

def _extract_json(text: str) -> str | None:
    """從可能含 ```json 圍欄或前後文的字串中，抽出第一個平衡的大括號 JSON 物件。"""
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


# 各欄位的可接受別名（模型常用不同名稱；大模型對長文件尤其愛改 schema）
_ALIASES = {
    "id": ["id", "ID", "wbs_id", "code", "no"],
    "parent_id": ["parent_id", "parent", "parentId", "parent_code"],
    "title": ["title", "name", "summary", "label", "task", "task_name", "名稱", "名称", "標題", "标题", "工作項目", "工作项目"],
    "description": ["description", "desc", "detail", "details", "說明", "描述", "备注", "備註"],
    "type": ["type", "level", "node_type", "類型", "类型"],
    "owner_unit": ["owner_unit", "owner", "unit", "department", "responsible", "負責單位", "负责单位", "責任單位", "责任单位"],
    "start_date": ["start_date", "start", "begin", "begin_date", "start_dt", "開始", "开始", "起始日"],
    "due_date": ["due_date", "end_date", "end", "finish", "finish_date", "deadline", "due", "結束", "结束", "到期", "截止"],
    "estimate_days": ["estimate_days", "estimate", "duration_days", "duration", "工時", "工时", "工期"],
    "milestone_id": ["milestone_id", "milestone"],
    "workflow_stage": ["workflow_stage", "stage", "status", "phase", "狀態", "状态", "階段", "阶段"],
    "dependencies": ["dependencies", "deps", "depends_on", "predecessors", "依賴", "依赖", "前置"],
    "deliverable": ["deliverable", "deliverables", "output", "產出", "产出", "交付物"],
}
_CHILD_KEYS = ["children", "subtasks", "sub_tasks", "subs", "tasks", "items", "子項", "子项", "子任務", "子任务"]


def _pick(d: dict, field: str):
    for k in _ALIASES.get(field, [field]):
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _schedule_directive(conditions: str, today: str, delivery: str) -> str:
    """依『相關條件』偵測排程粒度（週/雙週/日/月），產生明確的排程硬指令。
    本地模型對埋在條件裡的要求常忽略，故抽出來放成獨立、具體的規則。"""
    c = conditions or ""
    base = (
        "每一個工作項都必須同時填寫 start_date 與 due_date（不可只填其一、不可留空），"
        f"且都落在 {today} 與交付日（{delivery}）之間；依相依順序前後串接，葉節點（task/subtask）要有 estimate_days。"
    )
    has = lambda *ks: any(k in c for k in ks)  # noqa: E731
    if has("雙週", "双周", "兩週", "两周", "二週", "sprint", "Sprint", "2週", "2周"):
        return base + " 以『雙週(2 週)』為規劃單位：每個葉節點工期約 10 個工作天（estimate_days≈10），日期以兩週為粒度切分，不要用整月粒度。"
    if has("週", "周", "week", "Week", "WEEK", "每周", "每週"):
        return (
            base + " 以『週』為規劃單位：每個葉節點工期約 1 週（estimate_days≈5），"
            "start_date 與 due_date 以週為粒度切分（例如週一開始、同週或隔週週五結束），"
            "整份 WBS 的時間軸是一連串連續的『週』，不要把到期日全部壓在月底。"
        )
    if has("日", "天", "每日", "day", "Day", "daily"):
        return base + " 以『日』為規劃單位：estimate_days 以天計，日期精確到日。"
    if has("月", "每月", "month", "Month"):
        return base + " 以『月』為規劃單位：每個葉節點工期約 1 個月。"
    return base


def _as_str(v):
    """把欄位值正規化成字串（模型偶爾給 list/數字）。None→None。"""
    if v is None:
        return None
    if isinstance(v, list):
        s = "、".join(str(x) for x in v if x not in (None, ""))
        return s or None
    return str(v)


def _looks_like_nodes(v) -> bool:
    """判斷一個值是不是「節點清單」：list 裡多數元素含 id/title/name/type 任一鍵。"""
    if not isinstance(v, list) or not v:
        return False
    keys = {"title", "name", "type", "id", "task", "summary"}
    hits = sum(1 for x in v if isinstance(x, dict) and (keys & set(x.keys())))
    return hits >= max(1, len(v) // 2)


def _coerce_list(v):
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return []
    return v if isinstance(v, list) else []


def _flatten_nodes(raw_nodes: list, parent_id=None, depth: int = 0, out=None, counter=None) -> list:
    """把任意 WBS 表示法攤平成扁平節點清單（統一欄位名 + parent_id）。
    同時支援：① 扁平 + parent_id ② 巢狀 children。並把 name→title、end_date→due_date 等別名統一。"""
    if out is None:
        out = []
    if counter is None:
        counter = {"n": 0}
    depth_type = ["epic", "story", "task", "subtask", "subtask"]
    for n in raw_nodes:
        if not isinstance(n, dict):
            continue
        # 以 0 起算的出現序作為備援 id：有些模型用整數 index 當 parent_id
        idx = counter["n"]
        counter["n"] += 1
        nid = _pick(n, "id")
        nid = str(nid) if nid not in (None, "") else str(idx)
        ntype = _pick(n, "type")
        if ntype not in ("epic", "story", "task", "subtask"):
            ntype = depth_type[min(depth, len(depth_type) - 1)]
        # parent_id：巢狀時用結構上的父；扁平時讀自身的 parent 欄位
        pid = parent_id if parent_id is not None else _pick(n, "parent_id")
        deps = _pick(n, "dependencies")
        out.append(
            {
                "id": nid,
                "parent_id": str(pid) if pid not in (None, "") else None,
                "type": ntype,
                "title": _as_str(_pick(n, "title")) or "",
                "description": _as_str(_pick(n, "description")) or "",
                "deliverable": _as_str(_pick(n, "deliverable")),
                "owner_unit": _as_str(_pick(n, "owner_unit")),
                "estimate_days": _pick(n, "estimate_days"),
                "start_date": _as_str(_pick(n, "start_date")),
                "due_date": _as_str(_pick(n, "due_date")),
                "milestone_id": _as_str(_pick(n, "milestone_id")),
                "workflow_stage": _as_str(_pick(n, "workflow_stage")),
                "dependencies": [str(d) for d in deps] if isinstance(deps, list) else [],
            }
        )
        # 遞迴攤平巢狀子節點
        for ck in _CHILD_KEYS:
            kids = n.get(ck)
            if isinstance(kids, list) and kids and all(isinstance(k, dict) for k in kids):
                _flatten_nodes(kids, parent_id=nid, depth=depth + 1, out=out, counter=counter)
                break
    return out


def _find_node_list(obj: dict) -> list:
    """從 dict 中找出節點清單：先試常見鍵（不分大小寫），再退而求任何 node-like 的值。"""
    # 包裝層：值可能本身就是清單，或內含 nodes
    candidates = ["nodes", "wbs", "tasks", "work_items", "items", "wbs_nodes",
                  "work_breakdown", "result", "data", "parameters", "arguments", "input"]
    lower = {k.lower(): k for k in obj.keys()}
    for c in candidates:
        if c in lower:
            v = obj[lower[c]]
            if isinstance(v, dict):  # 再往內一層找
                inner = _find_node_list(v)
                if inner:
                    return inner
            lst = _coerce_list(v)
            if _looks_like_nodes(lst):
                return lst
    # 退路：任何看起來像節點清單的值
    for v in obj.values():
        lst = _coerce_list(v)
        if _looks_like_nodes(lst):
            return lst
    return []


def _normalize_tool_input(obj):
    """把模型各種雜格式正規化成 {nodes:[扁平、統一欄位], milestones:[...]}。
    處理：裸陣列、外層包裝、別名鍵、字串化清單、name/title 別名、巢狀 children 攤平。"""
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError:
            return {"nodes": [], "milestones": []}
    if isinstance(obj, list):
        raw_nodes = obj if _looks_like_nodes(obj) else []
        return {"nodes": _flatten_nodes(raw_nodes), "milestones": []}
    if not isinstance(obj, dict):
        return {"nodes": [], "milestones": []}

    raw_nodes = _find_node_list(obj)
    flat = _flatten_nodes(raw_nodes)

    # 里程碑（同樣容忍別名）
    lower = {k.lower(): k for k in obj.keys()}
    raw_ms = []
    for mk in ("milestones", "milestone", "里程碑"):
        if mk in lower:
            raw_ms = _coerce_list(obj[lower[mk]])
            break
    milestones = []
    for m in raw_ms:
        if not isinstance(m, dict):
            continue
        milestones.append(
            {
                "id": str(_pick(m, "id") or f"m{len(milestones)+1}"),
                "name": _pick(m, "title") or "",
                "date": _pick(m, "due_date") or m.get("date"),
                "deliverables": m.get("deliverables") if isinstance(m.get("deliverables"), list) else [],
            }
        )
    return {"nodes": flat, "milestones": milestones}


def parse_wbs_content(content: str) -> dict:
    """把 LLM 的原始輸出字串解析、正規化成 {nodes:[...], milestones:[...]}。
    供 runtime 與回測共用——同一條管線，確保測試打到的就是線上行為。"""
    if not content:
        return {"nodes": [], "milestones": []}
    stripped = content.strip()
    raw = stripped if stripped[:1] in "{[" else (_extract_json(content) or content)
    try:
        return _normalize_tool_input(json.loads(raw))
    except json.JSONDecodeError:
        return {"nodes": [], "milestones": []}


def _parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _convert_nodes_to_tw(nodes: list[WbsNode]) -> None:
    """就地把節點的文字欄位轉成繁體（台灣用語）。owner_unit 也轉，方便對回單位清單。"""
    for n in nodes:
        n.title = to_tw(n.title)
        n.description = to_tw(n.description)
        n.deliverable = to_tw(n.deliverable)
        n.owner_unit = to_tw(n.owner_unit)
        n.workflow_stage = to_tw(n.workflow_stage)
        if n.children:
            _convert_nodes_to_tw(n.children)


def _detect_unit_days(conditions: str) -> int | None:
    """從條件偵測排程粒度，回傳每個工作項的『日曆天』跨度；無指定回 None。"""
    c = conditions or ""
    if any(k in c for k in ("雙週", "双周", "兩週", "两周", "二週", "sprint", "Sprint", "2週", "2周")):
        return 14
    if any(k in c for k in ("週", "周", "week", "Week", "WEEK", "每周", "每週")):
        return 7
    if any(k in c for k in ("日", "天", "每日", "day", "Day", "daily")):
        return 1
    if any(k in c for k in ("月", "每月", "month", "Month")):
        return 30
    return None


def _iter_nodes(nodes: list[WbsNode]):
    for n in nodes:
        yield n
        if n.children:
            yield from _iter_nodes(n.children)


def _has_missing_dates(nodes: list[WbsNode]) -> bool:
    for n in _iter_nodes(nodes):
        if not n.children and (n.start_date is None or n.due_date is None):
            return True
    return False


def _apply_schedule(roots: list[WbsNode], today: date, delivery: date | None, unit_days: int) -> None:
    """以指定粒度，把葉節點依序排成連續時段，再把父節點的起訖日由子節點上捲。
    LLM 擅長拆解、不擅長日期算術，故排程在此以程式決定，確保符合『以週為單位』等要求。"""
    # 工作天估時：週→5、雙週→10、其餘≈跨度
    work_days = {7: 5, 14: 10, 1: 1, 30: 22}.get(unit_days, max(1, unit_days - 2))
    # 週/雙週對齊到下一個週一
    cursor = today
    if unit_days in (7, 14):
        cursor = today + timedelta(days=(0 - today.weekday()) % 7 or 0)

    leaves = [n for n in _iter_nodes(roots) if not n.children]
    span_end_offset = {7: 4, 14: 11}.get(unit_days, unit_days - 1)  # 週一→週五為 +4
    for leaf in leaves:
        start = cursor
        due = start + timedelta(days=span_end_offset)
        if delivery:  # 不超過交付日
            if start > delivery:
                start = delivery
            if due > delivery:
                due = delivery
        leaf.start_date = start
        leaf.due_date = due
        leaf.estimate_days = float(work_days)
        # 推進到下一個時段起點
        cursor = start + timedelta(days=unit_days)

    # 由葉往根上捲父節點起訖日
    def rollup(node: WbsNode):
        if not node.children:
            return node.start_date, node.due_date
        starts, dues = [], []
        for ch in node.children:
            s, d = rollup(ch)
            if s:
                starts.append(s)
            if d:
                dues.append(d)
        if starts:
            node.start_date = min(starts)
        if dues:
            node.due_date = max(dues)
        return node.start_date, node.due_date

    for r in roots:
        rollup(r)


def _build_tree(flat_nodes: list[dict]) -> list[WbsNode]:
    """依 parent_id 把扁平清單組成樹。會濾掉沒有 id 或 title 的空節點（小模型偶爾會吐）。"""
    flat_nodes = [
        n for n in flat_nodes
        if isinstance(n, dict) and str(n.get("id") or "").strip() and str(n.get("title") or "").strip()
    ]
    by_id: dict[str, WbsNode] = {}
    order: list[str] = []
    valid_types = {"epic", "story", "task", "subtask"}
    for n in flat_nodes:
        # 模型偶爾吐出不合法的 type（如 "milestone"），防呆成 task，避免整批產生失敗
        node_type = n.get("type") if n.get("type") in valid_types else "task"
        deps = n.get("dependencies")
        node = WbsNode(
            id=str(n.get("id")),
            type=node_type,
            title=n.get("title", ""),
            description=n.get("description", "") or "",
            deliverable=n.get("deliverable"),
            owner_unit=n.get("owner_unit"),
            estimate_days=n.get("estimate_days") if isinstance(n.get("estimate_days"), (int, float)) else None,
            start_date=_parse_date(n.get("start_date")),
            due_date=_parse_date(n.get("due_date")),
            milestone_id=n.get("milestone_id"),
            workflow_stage=n.get("workflow_stage"),
            dependencies=[str(d) for d in deps] if isinstance(deps, list) else [],
        )
        by_id[node.id] = node
        order.append(node.id)

    roots: list[WbsNode] = []
    for nid in order:
        parent_id = next(
            (n.get("parent_id") for n in flat_nodes if str(n.get("id")) == nid), None
        )
        if parent_id and str(parent_id) in by_id and str(parent_id) != nid:
            by_id[str(parent_id)].children.append(by_id[nid])
        else:
            roots.append(by_id[nid])
    return roots


def generate_wbs(req: GenerateWbsRequest, workflow: WorkflowTemplate | None) -> WbsDraft:
    settings = get_settings()
    if not settings.openai_configured:
        raise RuntimeError(
            "尚未設定 OPENAI_API_KEY，無法產生 WBS。請在 backend/.env 填入金鑰。"
        )

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )

    org_units = req.org_units or []
    workflow_desc = (
        f"工作流模板「{workflow.name}」階段：{', '.join(workflow.stages)}"
        if workflow
        else "未指定工作流模板，請自行規劃合理的看板階段。"
    )

    # 規則類描述（與 system prompt 一起放在前段，OpenAI 會自動快取長 prompt）
    rules_context = (
        f"可用組織單位清單（owner_unit 只能從中挑選）：{', '.join(org_units) if org_units else '（未提供，請用合理的單位名稱）'}\n"
        f"{workflow_desc}"
    )

    today = date.today()
    delivery = req.delivery_date.isoformat() if req.delivery_date else f"（未指定，請以今天 {today} 起算合理排程）"
    user_content = (
        f"# 今天日期\n{today.isoformat()}（所有排程的最早起點，請勿使用早於此日期的年份）\n\n"
        f"# 需求 / 技術規格\n{req.requirement_text}\n\n"
        f"# 交付物\n{chr(10).join('- ' + d for d in req.deliverables) if req.deliverables else '（請依需求自行歸納）'}\n\n"
        f"# 交付日（最後期限）\n{delivery}\n\n"
        f"# 相關條件 / 限制\n{req.conditions or '（無）'}\n\n"
        f"# 排程規則（務必嚴格遵守）\n{_schedule_directive(req.conditions, today.isoformat(), delivery)}\n\n"
        f"請拆解成完整 WBS。所有日期必須介於 {today.isoformat()} 與交付日之間。\n"
        f"務必使用欄位名：title（不要用 name）、due_date（不要用 end_date）、parent_id 表示階層、type 為 epic/story/task/subtask。\n"
        "只輸出 JSON 物件，最外層鍵為 \"nodes\" 與 \"milestones\"。"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + rules_context},
        {"role": "user", "content": user_content},
    ]

    def _generate_once():
        try:
            completion = client.chat.completions.create(
                model=settings.wbs_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=8000,  # 避免長 WBS 被截斷成不完整 JSON
            )
        except Exception:  # noqa: BLE001 — 少數端點不支援 response_format，退回一般呼叫
            completion = client.chat.completions.create(
                model=settings.wbs_model, messages=messages, temperature=0.2, max_tokens=8000
            )
        content = completion.choices[0].message.content or ""
        return parse_wbs_content(content), content

    # 本地模型偶爾回空/雜輸出，最多嘗試兩次；以「組樹後」的節點數判定成敗
    tool_input, last_content, attempts, nodes = {}, "", 0, []
    for attempt in range(2):
        attempts = attempt + 1
        try:
            tool_input, last_content = _generate_once()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"呼叫 LLM 失敗：{exc}") from exc
        nodes = _build_tree(tool_input.get("nodes", []))
        if nodes:
            break
        logger.warning("WBS 產生第 %d 次組樹後沒有節點，原始輸出前 800 字：%s", attempts, last_content[:800])

    success = bool(nodes)
    # 不論成功與否，存下請求與模型原始輸出，供回測（replay）
    gen_log.log_generation(
        model=settings.wbs_model,
        request={
            "requirement_text": req.requirement_text,
            "deliverables": req.deliverables,
            "delivery_date": req.delivery_date.isoformat() if req.delivery_date else None,
            "conditions": req.conditions,
            "org_units": org_units,
            "workflow": workflow.name if workflow else None,
        },
        raw_content=last_content,
        node_count=len(tool_input.get("nodes", [])),
        success=success,
        attempts=attempts,
    )

    if not success:
        raise RuntimeError(
            "模型連續兩次都沒有產出有效的 WBS 節點。建議改用更大的模型"
            "（在 .env 把 WBS_MODEL 改成 qwen2.5:14b）或縮短需求內容後重試。"
        )

    # 排程以程式決定（LLM 不擅長日期算術）：指定了粒度，或葉節點缺起訖日時都套用。
    unit_days = _detect_unit_days(req.conditions)
    if unit_days or _has_missing_dates(nodes):
        _apply_schedule(nodes, today, req.delivery_date, unit_days or 7)

    # 內容統一為繁體中文（台灣用語）：本地模型常產出簡體，於此確定性轉換。
    _convert_nodes_to_tw(nodes)

    milestones = [
        Milestone(
            id=str(m.get("id")),
            name=to_tw(m.get("name", "")),
            date=_parse_date(m.get("date")),
            deliverables=[to_tw(d) for d in (m.get("deliverables") or [])],
        )
        for m in tool_input.get("milestones", [])
    ]

    draft = WbsDraft(
        id=uuid.uuid4().hex[:12],
        requirement_text=req.requirement_text,
        deliverables=req.deliverables,
        delivery_date=req.delivery_date,
        conditions=req.conditions,
        org_units=org_units,
        workflow=workflow,
        milestones=milestones,
        nodes=nodes,
    )
    return draft
