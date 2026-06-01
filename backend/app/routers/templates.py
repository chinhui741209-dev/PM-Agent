from fastapi import APIRouter

from ..models import WorkflowTemplate
from ..templates_data import DEFAULT_ORG_UNITS, DEFAULT_WORKFLOW_TEMPLATES

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("/workflows", response_model=list[WorkflowTemplate])
def list_workflow_templates():
    return DEFAULT_WORKFLOW_TEMPLATES


@router.get("/org-units", response_model=list[str])
def list_org_units():
    return DEFAULT_ORG_UNITS
