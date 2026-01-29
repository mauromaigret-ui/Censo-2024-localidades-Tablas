from __future__ import annotations

import random
import re
from typing import Dict, List

import pandas as pd
from docx import Document

from app.config import RESULTS_DIR


def _format_n(value: float) -> int | float:
    if value is None:
        return 0
    if abs(value - round(value)) < 1e-6:
        return int(round(value))
    return round(value, 1)


def _format_pct(value: float) -> str:
    text = f"{round(value, 1):.1f}".replace(".", ",")
    return f"{text}%"


def _parse_pct(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text.replace("%", "").replace(",", "."))
    except Exception:
        return None


def _row_value(row: Dict[str, object]) -> float:
    try:
        return float(row.get("n") or 0)
    except Exception:
        return 0.0


def _build_narrative(rows: List[Dict[str, object]]) -> str:
    source_terms = [
        "De acuerdo al Censo 2024,",
        "Según el Censo 2024,",
        "De acuerdo al Censo (2024),",
    ]
    major_terms = [
        "La mayor proporción corresponde a",
        "La mayoría se concentra en",
        "La categoría predominante es",
        "La proporción más alta se observa en",
    ]
    dominance_terms = [
        "Es la categoría predominante.",
        "Abarca más de la mitad de la muestra.",
        "Concentra más del 50% de los casos.",
    ]
    closing_terms = [
        "A continuación, se presentan los resultados señalados en la siguiente tabla.",
        "A continuación, se presenta la tabla con los resultados indicados.",
        "En la tabla siguiente se detallan los resultados reportados.",
    ]

    base_rows = [r for r in rows if not r.get("is_total") and not r.get("is_subtotal")]
    if not base_rows:
        return f"{random.choice(source_terms)} {random.choice(closing_terms)}"

    if len(base_rows) == 1:
        row = base_rows[0]
        label = row.get("Etiqueta", "")
        n_val = _row_value(row)
        pct_val = _parse_pct(row.get("Porcentaje"))
        if n_val == 0:
            text = f"{random.choice(source_terms)} No se registran casos en {label} (0 casos)."
        else:
            pct_text = _format_pct(pct_val) if pct_val is not None else ""
            text = f"{random.choice(source_terms)} {label} representa {pct_text} del total observado."
        return f"{text} {random.choice(closing_terms)}"

    non_zero = [r for r in base_rows if _row_value(r) > 0]
    if not non_zero:
        return f"{random.choice(source_terms)} No se registran casos con valores distintos de cero. {random.choice(closing_terms)}"
    rows_for_stats = non_zero
    denom = sum(_row_value(r) for r in rows_for_stats) or 0.0

    def row_pct(row: Dict[str, object]) -> float:
        parsed = _parse_pct(row.get("Porcentaje"))
        if parsed is not None:
            return parsed
        if denom <= 0:
            return 0.0
        return (_row_value(row) / denom) * 100

    sorted_rows = sorted(rows_for_stats, key=row_pct, reverse=True)
    leader = sorted_rows[0]
    leader_pct = row_pct(leader)
    leader_label = leader.get("Etiqueta", "")
    leader_n = _row_value(leader)
    leader_n_text = int(leader_n) if leader_n.is_integer() else leader_n

    parts = [
        f"{random.choice(source_terms)} {random.choice(major_terms)} {leader_label} ({_format_pct(leader_pct)})."
    ]

    if leader_pct > 50:
        parts.append(random.choice(dominance_terms))

    if len(sorted_rows) > 1:
        ordered = [f"{r.get('Etiqueta', '')} ({_format_pct(row_pct(r))})" for r in sorted_rows[1:]]
        if ordered:
            parts.append(f"Le sigue {ordered[0]}." if len(ordered) == 1 else f"En orden decreciente, continúan {', '.join(ordered)}.")

    minor_rows = [r for r in sorted_rows if row_pct(r) < 5]
    if len(minor_rows) >= 3:
        minor_sum = sum(row_pct(r) for r in minor_rows)
        parts.append(f"En conjunto, las categorías con menos del 5% suman {_format_pct(minor_sum)}.")
    elif minor_rows and len(sorted_rows) > 2:
        smallest = min(minor_rows, key=row_pct)
        parts.append(
            f"Por el contrario, la menor presencia se registra en {smallest.get('Etiqueta', '')} con solo {_format_pct(row_pct(smallest))}."
        )

    parts.append(random.choice(closing_terms))
    return " ".join(parts)

def _safe_filename(name: str) -> str:
    name = name.strip()
    name = name.replace("/", "_")
    name = re.sub(r"[^A-Za-z0-9_ -]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name[:80] if name else "grupo"


def build_reports(
    var_sum: Dict[str, float],
    group_specs: Dict[str, Dict],
    labels: Dict[str, str],
    output_prefix: str,
) -> Dict[str, object]:
    reports = []

    for group_title, spec in group_specs.items():
        vars_list = spec["variables"]
        if not vars_list:
            continue

        category_col = spec.get("category_col")
        category_map = spec.get("category_map", {})
        label_override = spec.get("label_override", {})
        denominator = spec.get("denominator", "sum")
        total_label = spec.get("total_label", "Total")
        no_total = spec.get("no_total", False)

        rows = []

        for code in vars_list:
            value = float(var_sum.get(code, 0.0))
            value_display = _format_n(value)
            row = {
                "Etiqueta": label_override.get(code, labels.get(code, code)),
                "n": value_display,
                "Porcentaje": "",
                "is_total": False,
                "is_subtotal": False,
            }
            if category_col:
                row[category_col] = category_map.get(code, "")
            rows.append(row)

        if denominator == "by_category" and category_col:
            categories = {}
            for row in rows:
                cat = row.get(category_col, "")
                categories.setdefault(cat, 0.0)
                categories[cat] += float(row["n"]) if row["n"] is not None else 0.0

            for row in rows:
                cat = row.get(category_col, "")
                denom = categories.get(cat, 0.0)
                if denom > 0:
                    row["Porcentaje"] = _format_pct((float(row["n"]) / denom) * 100)

            for cat, subtotal in categories.items():
                subtotal_display = _format_n(subtotal)
                rows.append(
                    {
                        "Etiqueta": total_label,
                        category_col: cat,
                        "n": subtotal_display,
                        "Porcentaje": _format_pct(100) if subtotal > 0 else "",
                        "is_total": True,
                        "is_subtotal": True,
                    }
                )
        else:
            if denominator in var_sum:
                denom_value = float(var_sum.get(denominator, 0.0))
            elif denominator == "sum":
                denom_value = sum(float(r["n"]) for r in rows if r["n"] is not None)
            else:
                denom_value = 0.0

            for row in rows:
                if denom_value > 0 and row["n"] is not None:
                    row["Porcentaje"] = _format_pct((float(row["n"]) / denom_value) * 100)

            if not no_total and total_label:
                total_display = _format_n(denom_value)
                rows.append(
                    {
                        "Etiqueta": total_label,
                        **({category_col: ""} if category_col else {}),
                        "n": total_display,
                        "Porcentaje": _format_pct(100) if denom_value > 0 else "",
                        "is_total": True,
                        "is_subtotal": False,
                    }
                )

        safe_name = _safe_filename(group_title)
        csv_path = RESULTS_DIR / f"{output_prefix}{safe_name}.csv"
        df_rows = pd.DataFrame(rows)
        cols = [c for c in df_rows.columns if c not in {"is_total", "is_subtotal"}]
        if category_col:
            cols = [category_col] + [c for c in cols if c != category_col]
        df_rows[cols].to_csv(csv_path, index=False)

        reports.append(
            {
                "title": group_title,
                "rows": rows,
                "csv_path": str(csv_path),
                "category_col": category_col,
            }
        )

    # consolidated outputs
    combined_csv = RESULTS_DIR / f"{output_prefix}consolidado.csv"
    combined_xlsx = RESULTS_DIR / f"{output_prefix}consolidado.xlsx"
    combined_html = RESULTS_DIR / f"{output_prefix}consolidado.html"
    combined_docx = RESULTS_DIR / f"{output_prefix}consolidado.docx"

    all_rows = []
    for rep in reports:
        for row in rep["rows"]:
            out = {"Variable": rep["title"], **{k: v for k, v in row.items() if k not in {"is_total", "is_subtotal"}}}
            all_rows.append(out)

    combined_df = pd.DataFrame(all_rows)
    combined_df.to_csv(combined_csv, index=False)

    with pd.ExcelWriter(combined_xlsx, engine="openpyxl") as writer:
        combined_df.to_excel(writer, index=False, sheet_name="Consolidado")
        for rep in reports:
            sheet_name = _safe_filename(rep["title"])[:31]
            df_rows = pd.DataFrame(rep["rows"])
            cols = [c for c in df_rows.columns if c not in {"is_total", "is_subtotal"}]
            df_rows[cols].to_excel(writer, index=False, sheet_name=sheet_name)

    html_parts = ["<h1>Reporte consolidado</h1>"]
    for rep in reports:
        html_parts.append(f"<h2>{rep['title']}</h2>")
        df_rows = pd.DataFrame(rep["rows"])
        cols = [c for c in df_rows.columns if c not in {"is_total", "is_subtotal"}]
        html_parts.append(df_rows[cols].to_html(index=False))
    combined_html.write_text("\n".join(html_parts), encoding="utf-8")

    try:
        doc = Document()
        doc.add_heading("Reporte consolidado", level=1)

        def add_table(
            doc_ref: Document,
            row_dicts: List[Dict[str, object]],
            category_col: str | None = None,
        ) -> None:
            df_rows = pd.DataFrame(row_dicts)
            cols = [c for c in df_rows.columns if c not in {"is_total", "is_subtotal"}]
            if category_col and category_col in cols:
                cols = [category_col] + [c for c in cols if c != category_col]
            table = doc_ref.add_table(rows=1, cols=len(cols))
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            for idx, col in enumerate(cols):
                run = hdr[idx].paragraphs[0].add_run(col)
                run.bold = True
            for _, row in df_rows.iterrows():
                cells = table.add_row().cells
                is_total = bool(row.get("is_total", False))
                for idx, col in enumerate(cols):
                    text = "" if pd.isna(row[col]) else str(row[col])
                    run = cells[idx].paragraphs[0].add_run(text)
                    if is_total:
                        run.bold = True

        # Seccion 1: solo tablas
        doc.add_heading("Sección 1: Tablas", level=1)
        for idx, rep in enumerate(reports, start=1):
            doc.add_heading(f"Tabla {idx}. {rep['title']}", level=2)
            add_table(doc, rep["rows"], rep.get("category_col"))

        # Seccion 2: narrativa + tablas
        doc.add_heading("Sección 2: Tablas con narrativa", level=1)
        table_counter = 1
        for rep in reports:
            category_col = rep.get("category_col")
            rows = rep["rows"]
            if category_col:
                categories = [
                    cat
                    for cat in sorted({r.get(category_col, "") for r in rows})
                    if cat
                ]
                for cat in categories:
                    sub_rows = [
                        r
                        for r in rows
                        if r.get(category_col) == cat
                        or (r.get("is_subtotal") and r.get(category_col) == cat)
                    ]
                    doc.add_heading(f"Tabla {table_counter}. {rep['title']} - {cat}", level=2)
                    doc.add_paragraph(_build_narrative(sub_rows))
                    add_table(doc, sub_rows, rep.get("category_col"))
                    table_counter += 1
            else:
                doc.add_heading(f"Tabla {table_counter}. {rep['title']}", level=2)
                doc.add_paragraph(_build_narrative(rows))
                add_table(doc, rows, rep.get("category_col"))
                table_counter += 1
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
