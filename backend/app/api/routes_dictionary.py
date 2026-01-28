from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.models.schemas import UploadFilterResponse
from app.services.mapping_reader import load_mapping_csv
from app.store import store

router = APIRouter()


@router.post("/upload-dictionary", response_model=UploadFilterResponse)
async def upload_dictionary(file: UploadFile = File(...)) -> UploadFilterResponse:
    try:
        content = await file.read()
        stored = store.save_upload(file.filename or "diccionario.csv", content, suffix=".csv")
        info = load_mapping_csv(str(stored.path))
        return UploadFilterResponse(
            filter_id=stored.file_id,
            rows=int(len(info.index)),
            columns=list(info.columns),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
