from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ReportRequest, ReportResponse, ReportResult
from app.services.dictionary_reader import dictionary_map
from app.services.filter_reader import read_filter_excel
from app.services.gpkg_reader import get_table_columns, load_layer, load_layer_by_names
from app.services.grouping import group_columns
from app.services.mapping_reader import load_mapping_csv
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

        labels = {}
        details = {}
        group_labels = {}

        if req.dictionary_id:
            dict_file = store.get(req.dictionary_id)
            mapping_df = load_mapping_csv(str(dict_file.path))
            mapping_df = mapping_df[mapping_df["Variable_Codigo"].isin(all_fields)]
            groups_map = {
                f"{tema} / {subtema}": gdf["Variable_Codigo"].tolist()
                for (tema, subtema), gdf in mapping_df.groupby(["Tema", "Subtema"])
            }
            for row in mapping_df.itertuples(index=False):
                labels[row.Variable_Codigo] = row.Descripcion_Etiqueta
                details[row.Variable_Codigo] = row.Valores_Codigos_y_Detalle
            for (tema, subtema), _ in mapping_df.groupby(["Tema", "Subtema"]):
                group_labels[f"{tema} / {subtema}"] = f"{subtema}"
        else:
            groups_map = group_columns(all_fields)
            dict_map = dictionary_map(req.layer)
            for key, meta in dict_map.items():
                labels[key] = meta.get("description", key)
                details[key] = meta.get("visual", "")

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

        result = build_reports(
            df,
            selected_groups,
            labels,
            details,
            output_prefix="reporte_",
            group_labels=group_labels,
        )

        reports = []
        for r in result["reports"]:
            reports.append(
                ReportResult(
                    group=r["group"],
                    group_label=r["group_label"],
                    total=r["total"],
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
