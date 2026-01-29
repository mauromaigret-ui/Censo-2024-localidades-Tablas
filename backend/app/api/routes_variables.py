from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import VariablesResponse, VariableGroup, VariableField
from app.services.dictionary_reader import dictionary_map
from app.services.gpkg_reader import get_table_columns
from app.services.mapping_reader import load_mapping_csv
from app.services.group_rules import build_group_specs
from app.config import VARIABLES_DICT_PATH

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
        cols = get_table_columns(layer)
        dict_map = dictionary_map(layer)

        available_fields = [
            name
            for name, dtype in cols
            if str(dtype).lower().strip() in NUMERIC_TYPES
        ]

        group_list = []
        if VARIABLES_DICT_PATH.exists():
            mapping_df = load_mapping_csv(str(VARIABLES_DICT_PATH))
            group_specs, labels = build_group_specs(mapping_df, available_fields)
            for group_title, spec in group_specs.items():
                field_list = []
                for code in spec["variables"]:
                    meta = dict_map.get(code, {})
                    field_list.append(
                        VariableField(
                            name=code,
                            description=meta.get("description", ""),
                            label=labels.get(code),
                            detail=None,
                            dtype=meta.get("dtype", ""),
                        )
                    )
                group_list.append(VariableGroup(group=group_title, fields=field_list))
        else:
            # fallback simple grouping
            fields = [
                name
                for name, dtype in cols
                if str(name).startswith("n_") and str(dtype).lower().strip() in NUMERIC_TYPES
            ]
            for name in fields:
                meta = dict_map.get(name, {})
                group_list.append(
                    VariableGroup(
                        group=name,
                        fields=[
                            VariableField(
                                name=name,
                                description=meta.get("description", ""),
                                dtype=meta.get("dtype", ""),
                            )
                        ],
                    )
                )

        return VariablesResponse(layer=layer, groups=group_list)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
