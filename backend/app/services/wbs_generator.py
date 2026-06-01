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
from datetime import date

from openai import OpenAI

from ..config import get_settings
from . import gen_log

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


def _looks_like_nodes(v) -> bool:
    """判斷一個值是不是「節點清單」：list 裡多是含 title/type/id 的 dict。"""
    if not isinstance(v, list) or not v:
        return False
    hits = sum(1 for x in v if isinstance(x, dict) and ({"title", "type", "id"} & set(x.keys())))
    return hits >= max(1, len(v) // 2)


def _coerce_list(v):
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return []
    return v if isinstance(v, list) else []


def _normalize_tool_input(obj):
    """把本地模型常見的雜格式正規化成 {nodes:[...], milestones:[...]}。
    處理：直接回陣列、外層多包 parameters/wbs、節點放在別的 key、字串化的清單。"""
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError:
            return {}
    # 模型直接回一個陣列 → 當成 nodes
    if isinstance(obj, list):
        return {"nodes": obj if _looks_like_nodes(obj) else [], "milestones": []}
    if not isinstance(obj, dict):
        return {}

    # 解開常見包裝層（值可能是 dict 或字串化 dict）
    if "nodes" not in obj:
        for wrapper in ("parameters", "arguments", "input", "wbs", "result", "data"):
            inner = obj.get(wrapper)
            if isinstance(inner, str):
                try:
                    inner = json.loads(inner)
                except json.JSONDecodeError:
                    inner = None
            if isinstance(inner, dict) and "nodes" in inner:
                obj = inner
                break

    # 還是沒有 nodes → 找其他常見鍵名，或任何「看起來像節點清單」的值
    if not _coerce_list(obj.get("nodes")):
        for alt in ("nodes", "tasks", "work_items", "items", "wbs_nodes", "work_breakdown"):
            if _looks_like_nodes(_coerce_list(obj.get(alt))):
                obj["nodes"] = _coerce_list(obj.get(alt))
                break
        else:
            for v in obj.values():
                if _looks_like_nodes(_coerce_list(v)):
                    obj["nodes"] = _coerce_list(v)
                    break

    obj["nodes"] = _coerce_list(obj.get("nodes"))
    obj["milestones"] = _coerce_list(obj.get("milestones"))
    return obj


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
        f"請拆解成完整 WBS。所有日期必須介於 {today.isoformat()} 與交付日之間。只輸出 JSON。"
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

    # 本地模型偶爾回空/雜輸出，最多嘗試兩次
    tool_input, last_content, attempts = {}, "", 0
    for attempt in range(2):
        attempts = attempt + 1
        try:
            tool_input, last_content = _generate_once()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"呼叫 LLM 失敗：{exc}") from exc
        if tool_input.get("nodes"):
            break
        logger.warning("WBS 產生第 %d 次沒有節點，原始輸出前 800 字：%s", attempts, last_content[:800])

    success = bool(tool_input.get("nodes"))
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

    nodes = _build_tree(tool_input.get("nodes", []))
    milestones = [
        Milestone(
            id=str(m.get("id")),
            name=m.get("name", ""),
            date=_parse_date(m.get("date")),
            deliverables=m.get("deliverables") or [],
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
