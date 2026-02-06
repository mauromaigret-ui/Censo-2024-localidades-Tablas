from __future__ import annotations

from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class LayerInfo(BaseModel):
    name: str


class LayersResponse(BaseModel):
    layers: List[LayerInfo]


class UploadFilterResponse(BaseModel):
    filter_id: str
    rows: int
    columns: List[str]


class VariableField(BaseModel):
    name: str
    description: str
    label: str | None = None
    detail: str | None = None
    dtype: str


class VariableGroup(BaseModel):
    group: str
    fields: List[VariableField]


class VariablesResponse(BaseModel):
    layer: str
    groups: List[VariableGroup]


class ReportRequest(BaseModel):
    layer: str
    filter_id: str
    groups: List[str]
    localidad: str


class ReportRow(BaseModel):
    group: str
    group_label: str
    field: str
    label: str
    detail: str | None = None
    value: float
    pct: Optional[float]
    total: float


class ReportResult(BaseModel):
    group: str
    group_label: str
    total: Optional[float] = None
    rows_count: int
    csv_path: str


class ReportResponse(BaseModel):
    layer: str
    entities_count: int
    reports: List[ReportResult]
    combined_csv: str
    combined_html: str
    combined_docx: str
    combined_xlsx: str
