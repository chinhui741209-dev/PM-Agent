"""預設工作流模板與組織單位範例。AI 產生 WBS 時可套用、PM 可調整。"""
from .models import WorkflowTemplate

DEFAULT_WORKFLOW_TEMPLATES: list[WorkflowTemplate] = [
    WorkflowTemplate(
        id="software-standard",
        name="軟體標準流程",
        stages=["To Do", "開發中", "Code Review", "測試", "驗收", "完成"],
        description="一般軟體開發專案的看板階段。",
    ),
    WorkflowTemplate(
        id="hardware-npi",
        name="硬體導入（NPI）",
        stages=["規劃", "設計", "打樣", "驗證", "試產", "量產", "完成"],
        description="新產品導入（New Product Introduction）流程。",
    ),
    WorkflowTemplate(
        id="simple",
        name="精簡三階段",
        stages=["To Do", "進行中", "完成"],
        description="最簡單的看板，適合小型專案。",
    ),
]

# AI 指派 owner_unit 時的預設可選單位（PM 可在前端調整或覆寫）
DEFAULT_ORG_UNITS: list[str] = ["PM", "硬體", "韌體", "軟體", "測試", "品保", "採購", "機構"]


def get_template(template_id: str | None) -> WorkflowTemplate | None:
    if not template_id:
        return None
    for t in DEFAULT_WORKFLOW_TEMPLATES:
        if t.id == template_id:
            return t
    return None
