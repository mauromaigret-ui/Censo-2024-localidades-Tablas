from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ReportRequest, ReportResponse, ReportResult, ReportRow
from app.services.dictionary_reader import dictionary_map
from app.services.filter_reader import read_filter_excel
from app.services.gpkg_reader import get_table_columns, load_layer, load_layer_by_names
from app.services.grouping import group_columns
from app.services.reporting import build_reports
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


@router.post("/report", response_model=ReportResponse)
def report(req: ReportRequest) -> ReportResponse:
    try:
        stored = store.get(req.filter_id)
        filter_info = read_filter_excel(str(stored.path))

        cols = get_table_columns(req.layer)
        all_fields = [
            name
            for name, dtype in cols
            if str(name).startswith("n_")
            and str(dtype).lower().strip() in NUMERIC_TYPES
        ]
        groups_map = group_columns(all_fields)

        selected_groups = {g: groups_map[g] for g in req.groups if g in groups_map}
        if not selected_groups:
            raise HTTPException(status_code=400, detail="No valid groups selected")

        needed_columns = set()
        for cols in selected_groups.values():
            needed_columns.update(cols)

        needed_columns.update(["ID_ENTIDAD", "ENTIDAD", "LOCALIDAD", "COMUNA"])

        ids = filter_info["ids"]
        if ids:
            df = load_layer(req.layer, list(needed_columns), filter_ids=ids)
        else:
            df = load_layer_by_names(req.layer, list(needed_columns), filter_info["names"])

        dict_map = dictionary_map(req.layer)
        descriptions = {k: v.get("description", "") for k, v in dict_map.items()}

        result = build_reports(
            df,
            selected_groups,
            descriptions,
            output_prefix="reporte_",
        )

        reports = []
        for r in result["reports"]:
            rows = [ReportRow(**row) for row in r["rows"]]
            reports.append(
                ReportResult(
                    group=r["group"],
                    group_label=r["group_label"],
                    total=r["total"],
                    rows=rows,
                    csv_path=r["csv_path"],
                )
            )

        for rep in result["reports"]:
            print("\n===", rep["group"], "===")
            for row in rep["rows"]:
                print(f"{row['field']}: {row['value']} ({row['pct']}%)")

        return ReportResponse(
            layer=req.layer,
            entities_count=int(len(df.index)),
            reports=reports,
            combined_csv=result["combined_csv"],
            combined_html=result["combined_html"],
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
