from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.models.schemas import UploadFilterResponse
from app.services.filter_reader import read_filter_excel
from app.store import store

router = APIRouter()


@router.post("/upload-filter", response_model=UploadFilterResponse)
async def upload_filter(file: UploadFile = File(...)) -> UploadFilterResponse:
    try:
        content = await file.read()
        stored = store.save_upload(file.filename or "filtro.xlsx", content, suffix=".xlsx")
        info = read_filter_excel(str(stored.path))
        return UploadFilterResponse(
            filter_id=stored.file_id,
            rows=info["rows"],
            columns=info["columns"],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
