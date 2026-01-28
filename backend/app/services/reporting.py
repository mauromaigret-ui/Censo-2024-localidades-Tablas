from __future__ import annotations

from typing import Dict, List

import pandas as pd

from app.config import RESULTS_DIR


def _humanize_group(name: str) -> str:
    label = name
    if label.startswith("n_"):
        label = label[2:]
    label = label.replace("_", " ").strip()
    return label.title()


def build_reports(
    df: pd.DataFrame,
    groups: Dict[str, List[str]],
    descriptions: Dict[str, str],
    output_prefix: str,
) -> Dict[str, object]:
    reports = []
    combined_rows = []

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
                "group_label": _humanize_group(group_name),
                "field": col,
                "description": descriptions.get(col, ""),
                "value": value,
                "pct": pct,
                "total": total,
            }
            data.append(row)
            combined_rows.append(row)

        report_df = pd.DataFrame(data)
        csv_path = RESULTS_DIR / f"{output_prefix}{group_name}.csv"
        report_df.to_csv(csv_path, index=False)

        reports.append(
            {
                "group": group_name,
                "group_label": _humanize_group(group_name),
                "total": total,
                "rows": data,
                "csv_path": str(csv_path),
            }
        )

    combined_df = pd.DataFrame(combined_rows)
    combined_csv = RESULTS_DIR / f\"{output_prefix}consolidado.csv\"
    combined_df.to_csv(combined_csv, index=False)

    combined_html = RESULTS_DIR / f\"{output_prefix}consolidado.html\"
    combined_df.to_html(combined_html, index=False)

    return {
        "reports": reports,
        "combined_csv": str(combined_csv),
        "combined_html": str(combined_html),
    }
