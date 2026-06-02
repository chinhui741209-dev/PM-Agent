from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .. import store
from ..models import GenerateWbsRequest, WbsDraft
from ..services import excel_export, wbs_generator
from ..templates_data import get_template

router = APIRouter(prefix="/api/wbs", tags=["wbs"])


@router.post("/generate", response_model=WbsDraft)
def generate(req: GenerateWbsRequest):
    workflow = get_template(req.workflow_template_id)
    try:
        draft = wbs_generator.generate_wbs(req, workflow)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    store.save_draft(draft)
    return draft


@router.get("", response_model=list[dict])
def list_all():
    return store.list_drafts()


@router.get("/{draft_id}/export.xlsx")
def export_xlsx(draft_id: str):
    draft = store.get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="找不到這個 WBS 草稿")
    data = excel_export.build_wbs_workbook(draft)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="WBS-{draft_id}.xlsx"'},
    )


@router.get("/{draft_id}", response_model=WbsDraft)
def get_one(draft_id: str):
    draft = store.get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="找不到這個 WBS 草稿")
    return draft


@router.put("/{draft_id}", response_model=WbsDraft)
def update(draft_id: str, draft: WbsDraft):
    if draft.id != draft_id:
        raise HTTPException(status_code=400, detail="draft id 與路徑不符")
    existing = store.get_draft(draft_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="找不到這個 WBS 草稿")
    draft.created_at = existing.created_at
    store.save_draft(draft)
    return draft
