from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ReportRequest, ReportResponse, ReportResult
from app.services.filter_reader import read_filter_excel
from app.services.gpkg_reader import get_table_columns, load_layer, load_layer_by_names
from app.services.mapping_reader import load_mapping_csv
from app.services.group_rules import build_group_specs
from app.services.reporting import build_reports
from app.store import store
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


@router.post("/report", response_model=ReportResponse)
def report(req: ReportRequest) -> ReportResponse:
    try:
        localidad = (req.localidad or "").strip()
        if not localidad:
            raise HTTPException(status_code=400, detail="Debe indicar la localidad/sector")

        stored = store.get(req.filter_id)
        filter_info = read_filter_excel(str(stored.path))

        cols = get_table_columns(req.layer)
        available_fields = [
            name
            for name, dtype in cols
            if str(name).startswith("n_") and str(dtype).lower().strip() in NUMERIC_TYPES
        ]

        if not VARIABLES_DICT_PATH.exists():
            raise HTTPException(status_code=400, detail="No se encontró data/diccionario_variables.csv")

        mapping_df = load_mapping_csv(str(VARIABLES_DICT_PATH))
        group_specs, labels = build_group_specs(mapping_df, available_fields)

        selected_groups = {g: group_specs[g] for g in req.groups if g in group_specs}
        if not selected_groups:
            raise HTTPException(status_code=400, detail="No valid groups selected")

        needed_columns = set()
        for spec in selected_groups.values():
            needed_columns.update(spec["variables"])
            denom = spec.get("denominator")
            if denom in {"n_per", "n_hog", "n_vp"}:
                needed_columns.add(denom)

        needed_columns.update(["ID_ENTIDAD", "ENTIDAD", "LOCALIDAD", "COMUNA"])

        ids = filter_info["ids"]
        if ids:
            df = load_layer(req.layer, list(needed_columns), filter_ids=ids)
        else:
            df = load_layer_by_names(req.layer, list(needed_columns), filter_info["names"])

        var_sum = {}
        for col in needed_columns:
            if col in df.columns and col.startswith("n_"):
                series = df[col]
                var_sum[col] = float(series.fillna(0).sum())

        result = build_reports(
            var_sum,
            selected_groups,
            labels,
            localidad=localidad,
            output_prefix="reporte_",
        )

        reports = []
        for r in result["reports"]:
            reports.append(
                ReportResult(
                    group=r["title"],
                    group_label=r["title"],
                    total=None,
                    rows_count=len(r["rows"]),
                    csv_path=r["csv_path"],
                )
            )

        return ReportResponse(
            layer=req.layer,
            entities_count=int(len(df.index)),
            reports=reports,
            combined_csv=result["combined_csv"],
            combined_html=result["combined_html"],
            combined_docx=result["combined_docx"],
            combined_xlsx=result["combined_xlsx"],
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
