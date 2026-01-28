from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import VariablesResponse, VariableGroup, VariableField
from app.services.dictionary_reader import dictionary_map
from app.services.gpkg_reader import get_table_columns
from app.services.grouping import group_columns
from app.services.mapping_reader import load_mapping_csv
from app.store import store

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
def variables(layer: str = Query(...), dictionary_id: str | None = Query(None)) -> VariablesResponse:
    try:
        cols = get_table_columns(layer)
        dict_map = dictionary_map(layer)

        fields = []
        for name, dtype in cols:
            dtype_norm = str(dtype).lower().strip()
            if not str(name).startswith("n_"):
                continue
            if dtype_norm in NUMERIC_TYPES:
                fields.append(name)

        group_list = []
        if dictionary_id:
            stored = store.get(dictionary_id)
            mapping_df = load_mapping_csv(str(stored.path))
            mapping_df = mapping_df[mapping_df["Variable_Codigo"].isin(fields)]
            for (tema, subtema), gdf in mapping_df.groupby(["Tema", "Subtema"]):
                group_name = f"{tema} / {subtema}"
                field_list = []
                for row in gdf.itertuples(index=False):
                    meta = dict_map.get(row.Variable_Codigo, {})
                    field_list.append(
                        VariableField(
                            name=row.Variable_Codigo,
                            description=meta.get("description", ""),
                            label=row.Descripcion_Etiqueta,
                            detail=row.Valores_Codigos_y_Detalle,
                            dtype=meta.get("dtype", ""),
                        )
                    )
                group_list.append(VariableGroup(group=group_name, fields=field_list))
        else:
            groups = group_columns(fields)
            for group_name, cols in groups.items():
                field_list = []
                for c in cols:
                    meta = dict_map.get(c, {})
                    field_list.append(
                        VariableField(
                            name=c,
                            description=meta.get("description", ""),
                            dtype=meta.get("dtype", ""),
                        )
                    )
                group_list.append(VariableGroup(group=group_name, fields=field_list))

        group_list = sorted(group_list, key=lambda g: g.group)
        return VariablesResponse(layer=layer, groups=group_list)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
