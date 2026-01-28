from __future__ import annotations

import re
from typing import Dict, List

import pandas as pd
from docx import Document

from app.config import RESULTS_DIR


def _humanize_group(name: str) -> str:
    label = name
    if label.startswith("n_"):
        label = label[2:]
    label = label.replace("_", " ").strip()
    return label.title()

def _safe_filename(name: str) -> str:
    name = name.strip()
    name = name.replace("/", "_")
    name = re.sub(r"[^A-Za-z0-9_ -]+", "", name)
    name = re.sub(r"\\s+", "_", name)
    return name[:80] if name else "grupo"


def build_reports(
    df: pd.DataFrame,
    groups: Dict[str, List[str]],
    labels: Dict[str, str],
    details: Dict[str, str],
    output_prefix: str,
    group_labels: Dict[str, str] | None = None,
) -> Dict[str, object]:
    reports = []
    combined_rows = []
    group_labels = group_labels or {}

    for group_name, cols in groups.items():
        if not cols:
            continue
        data = []
        col_sums = {}
        total = 0.0
        for col in cols:
            series = pd.to_numeric(df[col], errors="coerce").fillna(0)
            value = float(series.sum())
            col_sums[col] = value
            total += value

        for col in cols:
            value = col_sums[col]
            pct = round((value / total * 100), 1) if total > 0 else None
            row = {
                "group": group_name,
                "group_label": group_labels.get(group_name, _humanize_group(group_name)),
                "field": col,
                "label": labels.get(col, col),
                "detail": details.get(col, ""),
                "value": value,
                "pct": pct,
                "total": total,
            }
            data.append(row)
            combined_rows.append(row)

        report_df = pd.DataFrame(data)
        safe_name = _safe_filename(group_name)
        csv_path = RESULTS_DIR / f"{output_prefix}{safe_name}.csv"
        report_df.to_csv(csv_path, index=False)

        reports.append(
            {
                "group": group_name,
                "group_label": group_labels.get(group_name, _humanize_group(group_name)),
                "total": total,
                "rows": data,
                "csv_path": str(csv_path),
            }
        )

    combined_df = pd.DataFrame(combined_rows)
    combined_csv = RESULTS_DIR / f"{output_prefix}consolidado.csv"
    combined_df.to_csv(combined_csv, index=False)

    combined_xlsx = RESULTS_DIR / f"{output_prefix}consolidado.xlsx"
    with pd.ExcelWriter(combined_xlsx, engine="openpyxl") as writer:
        combined_df.to_excel(writer, index=False, sheet_name="Consolidado")
        for rep in reports:
            sheet_name = _safe_filename(rep["group_label"])[:31]
            pd.DataFrame(rep["rows"]).to_excel(writer, index=False, sheet_name=sheet_name)

    combined_html = RESULTS_DIR / f"{output_prefix}consolidado.html"
    html_parts = ["<h1>Reporte consolidado</h1>"]
    for rep in reports:
        html_parts.append(f"<h2>{rep['group_label']}</h2>")
        table_df = pd.DataFrame(rep["rows"])[["label", "detail", "value", "pct"]]
        table_df.columns = ["Etiqueta", "Detalle", "Valor", "%"]
        html_parts.append(table_df.to_html(index=False))
    combined_html.write_text("\n".join(html_parts), encoding="utf-8")

    combined_docx = RESULTS_DIR / f"{output_prefix}consolidado.docx"
    try:
        doc = Document()
        doc.add_heading("Reporte consolidado", level=1)
        for rep in reports:
            doc.add_heading(rep["group_label"], level=2)
            table = doc.add_table(rows=1, cols=4)
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            hdr[0].text = "Etiqueta"
            hdr[1].text = "Detalle"
            hdr[2].text = "Valor"
            hdr[3].text = "%"
            for row in rep["rows"]:
                cells = table.add_row().cells
                cells[0].text = str(row.get("label", ""))
                cells[1].text = str(row.get("detail", ""))
                cells[2].text = str(row.get("value", ""))
                cells[3].text = "" if row.get("pct") is None else str(row.get("pct"))
        doc.save(combined_docx)
    except Exception:
        combined_docx = RESULTS_DIR / f"{output_prefix}consolidado_docx_error.txt"
        combined_docx.write_text("Error generando DOCX. Use el HTML o XLSX.")

    return {
        "reports": reports,
        "combined_csv": str(combined_csv),
        "combined_html": str(combined_html),
        "combined_docx": str(combined_docx),
        "combined_xlsx": str(combined_xlsx),
    }
