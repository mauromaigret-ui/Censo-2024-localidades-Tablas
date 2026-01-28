from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ReportRequest, ReportResponse, ReportResult, ReportRow
from app.services.dictionary_reader import load_dictionary
from app.services.filter_reader import read_filter_excel
from app.services.gpkg_reader import load_layer, load_layer_by_names
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

        df_dict = load_dictionary(req.layer)
        df_dict["dtype_norm"] = df_dict["dtype"].astype(str).str.lower().str.strip()
        df_dict["field"] = df_dict["field"].astype(str)
        stats_df = df_dict[(df_dict["dtype_norm"].isin(NUMERIC_TYPES)) & (df_dict["field"].str.startswith("n_"))]

        all_fields = stats_df["field"].tolist()
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

        descriptions = {row.field: row.description for row in stats_df.itertuples(index=False)}

        reports_raw = build_reports(
            df,
            selected_groups,
            descriptions,
            output_prefix="reporte_",
        )

        reports = []
        for r in reports_raw:
            rows = [ReportRow(**row) for row in r["rows"]]
            reports.append(
                ReportResult(
                    group=r["group"],
                    total=r["total"],
                    rows=rows,
                    csv_path=r["csv_path"],
                )
            )

        for rep in reports_raw:
            print("\n===", rep["group"], "===")
            for row in rep["rows"]:
                print(f"{row['field']}: {row['value']} ({row['pct']}%)")

        return ReportResponse(
            layer=req.layer,
            entities_count=int(len(df.index)),
            reports=reports,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
