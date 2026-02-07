from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd


def normalize_id(value) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
            if value.isdigit():
                return int(value)
            if value.replace(".", "", 1).isdigit():
                return int(float(value))
        if isinstance(value, (int,)):
            return int(value)
        if isinstance(value, float):
            return int(value)
    except Exception:
        return None
    return None


def normalize_code(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None
        if text.isdigit():
            return text
        if text.replace(".", "", 1).isdigit():
            return str(int(float(text)))
        return text
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    return str(value).strip() or None


def normalize_manzent(value) -> int | None:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            text = value.strip()
            if text == "":
                return None
            if text.isdigit():
                return int(text)
            if text.replace(".", "", 1).isdigit():
                return int(float(text))
            return None
        if isinstance(value, (int,)):
            return int(value)
        if isinstance(value, float):
            return int(value)
    except Exception:
        return None
    return None


def read_filter_excel(path: str) -> Dict[str, object]:
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = [str(c).strip().upper() for c in df.columns]

    id_col = "ID_ENTIDAD" if "ID_ENTIDAD" in df.columns else None
    entidad_col = "ENTIDAD" if "ENTIDAD" in df.columns else None
    localidad_col = "LOCALIDAD" if "LOCALIDAD" in df.columns else None
    comuna_col = "COMUNA" if "COMUNA" in df.columns else None
    manzent_col = "MANZENT" if "MANZENT" in df.columns else None

    ids: List[int] = []
    if id_col:
        for v in df[id_col].tolist():
            nid = normalize_id(v)
            if nid is not None:
                ids.append(nid)

    names: List[Tuple[str, str, str]] = []
    if entidad_col:
        for _, row in df.iterrows():
            ent = str(row.get(entidad_col, "")).strip()
            loc = str(row.get(localidad_col, "")) if localidad_col else ""
            com = str(row.get(comuna_col, "")) if comuna_col else ""
            if ent:
                names.append((ent, loc, com))

    manzent: List[int] = []
    if manzent_col:
        for v in df[manzent_col].tolist():
            code = normalize_manzent(v)
            if code is not None:
                manzent.append(code)

    return {
        "rows": int(len(df.index)),
        "columns": list(df.columns),
        "ids": list(dict.fromkeys(ids)),
        "names": names,
        "manzent": list(dict.fromkeys(manzent)),
    }
