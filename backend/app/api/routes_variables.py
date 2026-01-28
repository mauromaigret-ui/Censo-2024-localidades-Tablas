from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import VariablesResponse, VariableGroup, VariableField
from app.services.dictionary_reader import load_dictionary
from app.services.grouping import group_columns

router = APIRouter()


NUMERIC_TYPES = {
    "integer",
    "smallinteger",
    "mediumint",
    "double",
    "real",
    "float",
}


@router.get("/variables", response_model=VariablesResponse)
def variables(layer: str = Query(...)) -> VariablesResponse:
    try:
        df = load_dictionary(layer)
        df["dtype_norm"] = df["dtype"].astype(str).str.lower().str.strip()
        df["field"] = df["field"].astype(str)

        # keep only numeric fields that look like tabulated counts (n_)
        stats_df = df[(df["dtype_norm"].isin(NUMERIC_TYPES)) & (df["field"].str.startswith("n_"))]

        fields = stats_df["field"].tolist()
        groups = group_columns(fields)

        description_map = {row.field: row.description for row in stats_df.itertuples(index=False)}
        dtype_map = {row.field: row.dtype for row in stats_df.itertuples(index=False)}

        group_list = []
        for group_name, cols in groups.items():
            field_list = [
                VariableField(name=c, description=description_map.get(c, ""), dtype=dtype_map.get(c, ""))
                for c in cols
            ]
            group_list.append(VariableGroup(group=group_name, fields=field_list))

        group_list = sorted(group_list, key=lambda g: g.group)
        return VariablesResponse(layer=layer, groups=group_list)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
