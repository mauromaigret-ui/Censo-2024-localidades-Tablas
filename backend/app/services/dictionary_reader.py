from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from app.config import DICT_PATH


def load_dictionary(layer: str, dict_path: Path = DICT_PATH) -> pd.DataFrame:
    df = pd.read_excel(dict_path, sheet_name=layer, engine="openpyxl")
    df = df.rename(columns={
        "Nombre de campo": "field",
        "Tipo": "dtype",
        "Descripción": "description",
        "Visualización": "visual",
    })
    df = df[["field", "dtype", "description", "visual"]]
    df = df.dropna(subset=["field"])
    df["field"] = df["field"].astype(str).str.strip()
    df["dtype"] = df["dtype"].astype(str).str.strip()
    df["description"] = df["description"].astype(str).str.strip()
    return df


def dictionary_map(layer: str) -> Dict[str, Dict[str, str]]:
    df = load_dictionary(layer)
    return {
        row.field: {
            "dtype": row.dtype,
            "description": row.description,
            "visual": row.visual,
        }
        for row in df.itertuples(index=False)
    }
