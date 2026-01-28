from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import LayersResponse, LayerInfo
from app.services.gpkg_reader import list_layers

router = APIRouter()


@router.get("/layers", response_model=LayersResponse)
def layers() -> LayersResponse:
    try:
        layers = list_layers()
        return LayersResponse(layers=[LayerInfo(name=l) for l in layers])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
