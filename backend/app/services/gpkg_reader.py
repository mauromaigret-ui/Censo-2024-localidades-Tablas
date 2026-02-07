from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from app.config import GPKG_PATH


def list_layers(gpkg_path: Path = GPKG_PATH) -> List[str]:
    con = sqlite3.connect(gpkg_path)
    try:
        cur = con.cursor()
        cur.execute("SELECT table_name FROM gpkg_contents ORDER BY table_name")
        return [row[0] for row in cur.fetchall()]
    finally:
        con.close()


def get_table_columns(layer: str, gpkg_path: Path = GPKG_PATH) -> List[Tuple[str, str]]:
    con = sqlite3.connect(gpkg_path)
    try:
        cur = con.cursor()
        cur.execute(f"PRAGMA table_info({layer})")
        return [(row[1], row[2]) for row in cur.fetchall()]
    finally:
        con.close()


def load_layer(
    layer: str,
    columns: List[str],
    filter_ids: List[int] | None = None,
    filter_manzent: List[int] | List[str] | None = None,
    gpkg_path: Path = GPKG_PATH,
) -> pd.DataFrame:
    select_cols = list(dict.fromkeys(columns))
    cols_sql = ", ".join([f'"{c}"' for c in select_cols])
    sql = f"SELECT {cols_sql} FROM {layer}"
    params = None

    if filter_ids:
        placeholders = ",".join(["?"] * len(filter_ids))
        sql += f" WHERE CAST(ID_ENTIDAD AS INTEGER) IN ({placeholders})"
        params = filter_ids
    elif filter_manzent:
        placeholders = ",".join(["?"] * len(filter_manzent))
        if all(isinstance(v, int) for v in filter_manzent):
            sql += f" WHERE CAST(MANZENT AS INTEGER) IN ({placeholders})"
            params = filter_manzent
        else:
            sql += f" WHERE TRIM(CAST(MANZENT AS TEXT)) IN ({placeholders})"
            params = filter_manzent

    con = sqlite3.connect(gpkg_path)
    try:
        df = pd.read_sql_query(sql, con, params=params)
    finally:
        con.close()

    return df


def load_layer_by_names(
    layer: str,
    columns: List[str],
    names: List[Tuple[str, str, str]],
    gpkg_path: Path = GPKG_PATH,
) -> pd.DataFrame:
    if not names:
        return pd.DataFrame(columns=list(dict.fromkeys(columns)))

    select_cols = list(dict.fromkeys(columns))
    cols_sql = ", ".join([f'"{c}"' for c in select_cols])

    has_localidad = "LOCALIDAD" in select_cols
    has_comuna = "COMUNA" in select_cols

    def build_where(ent: str, loc: str, com: str) -> Tuple[str, List[str]]:
        conditions = ['UPPER(TRIM(ENTIDAD)) = ?']
        params = [ent]
        if has_localidad:
            conditions.append('UPPER(TRIM(LOCALIDAD)) = ?')
            params.append(loc)
        if has_comuna:
            conditions.append('UPPER(TRIM(COMUNA)) = ?')
            params.append(com)
        return f"({' AND '.join(conditions)})", params

    con = sqlite3.connect(gpkg_path)
    try:
        chunks = []
        chunk_size = 250
        for i in range(0, len(names), chunk_size):
            where_parts = []
            params: List[str] = []
            for ent, loc, com in names[i : i + chunk_size]:
                ent_norm = str(ent).strip().upper()
                if not ent_norm:
                    continue
                loc_norm = str(loc or "").strip().upper()
                com_norm = str(com or "").strip().upper()
                clause, clause_params = build_where(ent_norm, loc_norm, com_norm)
                where_parts.append(clause)
                params.extend(clause_params)
            if not where_parts:
                continue
            sql = f"SELECT {cols_sql} FROM {layer} WHERE " + " OR ".join(where_parts)
            chunks.append(pd.read_sql_query(sql, con, params=params))

        if not chunks:
            return pd.DataFrame(columns=select_cols)
        return pd.concat(chunks, ignore_index=True)
    finally:
        con.close()
