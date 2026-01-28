from __future__ import annotations

from typing import Dict, List

import pandas as pd

from app.config import RESULTS_DIR


def build_reports(
    df: pd.DataFrame,
    groups: Dict[str, List[str]],
    descriptions: Dict[str, str],
    output_prefix: str,
) -> List[Dict[str, object]]:
    reports = []

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
            data.append(
                {
                    "group": group_name,
                    "field": col,
                    "description": descriptions.get(col, ""),
                    "value": value,
                    "pct": pct,
                }
            )

        report_df = pd.DataFrame(data)
        csv_path = RESULTS_DIR / f"{output_prefix}{group_name}.csv"
        report_df.to_csv(csv_path, index=False)

        reports.append(
            {
                "group": group_name,
                "total": total,
                "rows": data,
                "csv_path": str(csv_path),
            }
        )

    return reports
