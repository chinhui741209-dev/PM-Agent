from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..models import IntakeResponse
from ..services import parser

router = APIRouter(prefix="/api/intake", tags=["intake"])


@router.post("", response_model=IntakeResponse)
async def intake(
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
):
    """接受純文字（Form 欄位 text）或上傳檔（multipart file）。
    回傳正規化後的需求文字，供前端確認後送去產生 WBS。"""
    if text and text.strip():
        req_text, deliv = parser.parse_text(text)
        return IntakeResponse(requirement_text=req_text, source="text", extracted_deliverables=deliv)

    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="上傳的檔案是空的")
        try:
            req_text, source, deliv = parser.parse_upload(file.filename or "", data)
        except Exception as exc:  # noqa: BLE001 — 解析各種格式可能丟多種例外
            raise HTTPException(status_code=422, detail=f"檔案解析失敗：{exc}") from exc
        note = ""
        if not req_text:
            note = "檔案解析後沒有抽取到文字內容，請確認檔案格式或改用貼上文字。"
        return IntakeResponse(
            requirement_text=req_text,
            source=source,
            extracted_deliverables=deliv,
            note=note,
        )

    raise HTTPException(status_code=400, detail="請提供 text 或上傳一個檔案")
