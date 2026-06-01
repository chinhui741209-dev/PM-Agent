from __future__ import annotations

import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

NodeType = Literal["epic", "story", "task", "subtask"]


class WbsNode(BaseModel):
    """WBS 的一個節點，可遞迴包含子節點。階層：epic -> story -> task -> subtask。"""

    id: str
    type: NodeType
    title: str
    description: str = ""
    deliverable: Optional[str] = None          # 對應的交付物
    owner_unit: Optional[str] = None           # AI 建議 / PM 指派的負責單位
    assignee_account_id: Optional[str] = None  # 部署時對應的 Jira 使用者（選填）
    estimate_days: Optional[float] = None
    start_date: Optional[datetime.date] = None
    due_date: Optional[datetime.date] = None
    milestone_id: Optional[str] = None
    workflow_stage: Optional[str] = None       # 對應工作流階段（初始狀態）
    dependencies: list[str] = Field(default_factory=list)  # 依賴的其他 node id
    children: list["WbsNode"] = Field(default_factory=list)


class Milestone(BaseModel):
    id: str
    name: str
    date: Optional[datetime.date] = None
    deliverables: list[str] = Field(default_factory=list)


class WorkflowTemplate(BaseModel):
    id: str
    name: str
    stages: list[str]                       # 看板欄位 / 狀態順序
    description: str = ""


class WbsDraft(BaseModel):
    id: str
    requirement_text: str = ""
    deliverables: list[str] = Field(default_factory=list)
    delivery_date: Optional[datetime.date] = None
    conditions: str = ""
    org_units: list[str] = Field(default_factory=list)
    workflow: Optional[WorkflowTemplate] = None
    milestones: list[Milestone] = Field(default_factory=list)
    nodes: list[WbsNode] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ---- Request / Response payloads ----

class GenerateWbsRequest(BaseModel):
    requirement_text: str
    deliverables: list[str] = Field(default_factory=list)
    delivery_date: Optional[datetime.date] = None
    conditions: str = ""
    org_units: list[str] = Field(default_factory=list)
    workflow_template_id: Optional[str] = None


class IntakeResponse(BaseModel):
    requirement_text: str
    source: str                              # text | docx | pdf | xlsx | md | txt
    extracted_deliverables: list[str] = Field(default_factory=list)
    note: str = ""
