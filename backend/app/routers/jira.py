from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import store
from ..models import WbsNode
from ..services import jira_client
from ..services.jira_client import JiraError

router = APIRouter(prefix="/api/jira", tags=["jira"])


# 預設把 WBS 節點型別對應到 Jira issue type 名稱（PM 可在部署請求覆寫）
DEFAULT_TYPE_MAP = {"epic": "Epic", "story": "Story", "task": "Task", "subtask": "Sub-task"}


class DeployRequest(BaseModel):
    draft_id: str
    project_key: str
    type_map: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_TYPE_MAP))
    apply_initial_status: bool = True  # 是否嘗試把 issue 推進到 workflow_stage


class DeployedIssue(BaseModel):
    node_id: str
    title: str
    issue_key: str | None = None
    url: str | None = None
    status_applied: str | None = None
    error: str | None = None


class DeployResult(BaseModel):
    project_key: str
    created: list[DeployedIssue]
    milestones_created: list[str]
    suggested_board_columns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


@router.get("/projects", response_model=list[dict])
def projects():
    try:
        return jira_client.list_projects()
    except JiraError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/meta", response_model=dict)
def meta(project_key: str):
    try:
        return jira_client.get_project_meta(project_key)
    except JiraError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _flatten(nodes: list[WbsNode], parent_id: str | None = None):
    """深度優先攤平，產出 (node, parent_node_id)，確保父節點先於子節點建立。"""
    for n in nodes:
        yield n, parent_id
        if n.children:
            yield from _flatten(n.children, n.id)


@router.post("/deploy", response_model=DeployResult)
def deploy(req: DeployRequest):
    draft = store.get_draft(req.draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="找不到這個 WBS 草稿")

    try:
        meta = jira_client.get_project_meta(req.project_key)
    except JiraError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    project_id = str(meta.get("id"))
    valid_statuses = {s.lower(): s for s in meta.get("statuses", [])}
    warnings: list[str] = []

    # 1. 里程碑 -> Jira Version
    milestone_version: dict[str, str] = {}
    milestones_created: list[str] = []
    for m in draft.milestones:
        vid = jira_client.ensure_version(
            project_id, m.name, m.date.isoformat() if m.date else None
        )
        if vid:
            milestone_version[m.id] = vid
            milestones_created.append(m.name)
        else:
            warnings.append(f"里程碑「{m.name}」對應的 Version 建立失敗（可能權限不足）。")

    # 2. 逐節點建立 issue（父先於子）
    base_url = jira_client.get_settings().jira_base_url.rstrip("/")
    id_to_key: dict[str, str] = {}
    created: list[DeployedIssue] = []

    for node, parent_id in _flatten(draft.nodes):
        type_name = req.type_map.get(node.type, DEFAULT_TYPE_MAP.get(node.type, "Task"))
        # subtask / 有父節點者掛到父 issue；epic 無父
        parent_key = id_to_key.get(parent_id) if parent_id else None
        version_id = milestone_version.get(node.milestone_id) if node.milestone_id else None
        labels = [node.owner_unit] if node.owner_unit else []

        rec = DeployedIssue(node_id=node.id, title=node.title)
        try:
            fields = jira_client.build_fields(
                project_key=req.project_key,
                issue_type_name=type_name,
                summary=node.title,
                description=node.description or "",
                labels=labels,
                assignee_account_id=node.assignee_account_id,
                parent_key=parent_key,
                version_id=version_id,
            )
            result = jira_client.create_issue(fields)
            key = result.get("key")
            rec.issue_key = key
            rec.url = f"{base_url}/browse/{key}" if key else None
            id_to_key[node.id] = key

            # 3. 套用初始狀態（若 workflow_stage 對應到專案既有狀態）
            if req.apply_initial_status and node.workflow_stage and key:
                stage = node.workflow_stage.lower()
                if stage in valid_statuses:
                    if jira_client.transition_issue(key, valid_statuses[stage]):
                        rec.status_applied = valid_statuses[stage]
                else:
                    warnings.append(
                        f"工作流階段「{node.workflow_stage}」在專案中沒有對應狀態，{key} 維持預設狀態。"
                    )
        except JiraError as exc:
            rec.error = str(exc)
        created.append(rec)

    suggested = draft.workflow.stages if draft.workflow else []
    if suggested:
        warnings.append(
            "Jira REST API 無法自動建立自訂看板工作流；請依「建議看板欄位順序」在 Jira 專案設定中調整欄位。"
        )

    return DeployResult(
        project_key=req.project_key,
        created=created,
        milestones_created=milestones_created,
        suggested_board_columns=suggested,
        warnings=warnings,
    )
