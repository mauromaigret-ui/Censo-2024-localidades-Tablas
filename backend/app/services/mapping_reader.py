from __future__ import annotations

from typing import Dict

import pandas as pd


REQUIRED_COLUMNS = {
    "tema": "Tema",
    "subtema": "Subtema",
    "variable_codigo": "Variable_Codigo",
    "descripcion_etiqueta": "Descripcion_Etiqueta",
    "valores_codigos_y_detalle": "Valores_Codigos_y_Detalle",
}


def load_mapping_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    # normalize expected columns
    col_map: Dict[str, str] = {}
    for key, expected in REQUIRED_COLUMNS.items():
        for col in df.columns:
            if col.strip().lower() == expected.lower():
                col_map[col] = expected
                break
    df = df.rename(columns=col_map)

    missing = [v for v in REQUIRED_COLUMNS.values() if v not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en diccionario: {', '.join(missing)}")

    for col in REQUIRED_COLUMNS.values():
        df[col] = df[col].astype(str).str.strip()

    return df
