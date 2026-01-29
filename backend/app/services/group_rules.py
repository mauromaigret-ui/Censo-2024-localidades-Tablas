from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd


def _unit_from_vars(vars_list: List[str]) -> str | None:
    if any(v.startswith(("n_hog", "n_tenencia", "n_comb", "n_serv_", "n_internet", "n_serv_tel")) for v in vars_list):
        return "Hogares"
    if any(v.startswith(("n_vp", "n_viv", "n_tipo_viv", "n_mat", "n_dormitorios")) for v in vars_list):
        return "Viviendas"
    if any(v.startswith("n_") for v in vars_list):
        return "Personas"
    return None


def build_group_specs(mapping_df: pd.DataFrame, available_fields: List[str]) -> Tuple[Dict[str, Dict], Dict[str, str], Dict[str, str]]:
    df = mapping_df[mapping_df["Variable_Codigo"].isin(available_fields)].copy()
    labels = {row.Variable_Codigo: row.Descripcion_Etiqueta for row in df.itertuples(index=False)}
    details = {row.Variable_Codigo: row.Valores_Codigos_y_Detalle for row in df.itertuples(index=False)}

    base_groups: Dict[str, List[str]] = {}
    for (tema, subtema), gdf in df.groupby(["Tema", "Subtema"]):
        base_groups[f"{tema} / {subtema}"] = gdf["Variable_Codigo"].tolist()

    group_specs: Dict[str, Dict] = {}

    def add_group(title: str, vars_list: List[str], **meta):
        if not vars_list:
            return
        group_specs[title] = {"variables": vars_list, "title": title, **meta}

    def remove_group(group_key: str):
        if group_key in base_groups:
            del base_groups[group_key]

    def get_group(tema: str, subtema: str) -> List[str]:
        return base_groups.get(f"{tema} / {subtema}", [])

    # Custom: Sexo + General -> Población según sexo
    sexo_vars = get_group("2. Variables de Población (Personas)", "Sexo")
    general_vars = get_group("2. Variables de Población (Personas)", "General")
    sexo_table_vars = [v for v in ["n_hombres", "n_mujeres", "n_per"] if v in (sexo_vars + general_vars + available_fields)]
    add_group(
        "Población según sexo",
        sexo_table_vars,
        denominator="n_per",
        total_label="Total",
        unit="Personas",
    )
    remove_group("2. Variables de Población (Personas) / Sexo")
    remove_group("2. Variables de Población (Personas) / General")

    # Custom: Edad title
    edad_vars = get_group("2. Variables de Población (Personas)", "Edad")
    if edad_vars:
        add_group(
            "Población según tramos de edad",
            edad_vars,
            denominator="sum",
            total_label="Total",
            unit="Personas",
        )
        remove_group("2. Variables de Población (Personas) / Edad")

    # Discapacidad: compare to total population
    discapacidad_vars = get_group("2. Variables de Población (Personas)", "Discapacidad")
    if discapacidad_vars:
        add_group(
            "Discapacidad",
            discapacidad_vars,
            denominator="n_per",
            total_label="Población total",
            unit="Personas",
        )
        remove_group("2. Variables de Población (Personas) / Discapacidad")

    # Etnicidad split
    etnicidad_vars = get_group("2. Variables de Población (Personas)", "Etnicidad")
    if etnicidad_vars:
        if "n_pueblos_orig" in etnicidad_vars:
            add_group(
                "Población pueblos originarios",
                ["n_pueblos_orig"],
                denominator="n_per",
                total_label="Población total",
                unit="Personas",
            )
        if "n_afrodescendencia" in etnicidad_vars:
            add_group(
                "Población afrodescendiente",
                ["n_afrodescendencia"],
                denominator="n_per",
                total_label="Población total",
                unit="Personas",
            )
        if "n_lengua_indigena" in etnicidad_vars:
            add_group(
                "Hablantes de lengua indígena",
                ["n_lengua_indigena"],
                denominator="n_per",
                total_label="Población total",
                unit="Personas",
            )
        remove_group("2. Variables de Población (Personas) / Etnicidad")

    # Religión compare to total population
    religion_vars = get_group("2. Variables de Población (Personas)", "Religión")
    if religion_vars:
        add_group(
            "Población con religión",
            religion_vars,
            denominator="n_per",
            total_label="Población total",
            unit="Personas",
        )
        remove_group("2. Variables de Población (Personas) / Religión")

    # TICs add total hogares
    tics_vars = get_group("4. Viviendas y Hogares", "TICs")
    if tics_vars:
        add_group(
            "TICs (Hogares)",
            tics_vars,
            denominator="n_hog",
            total_label="Total hogares",
            unit="Hogares",
        )
        remove_group("4. Viviendas y Hogares / TICs")

    # Tenencia
    tenencia_vars = get_group("4. Viviendas y Hogares", "Tenencia")
    if tenencia_vars:
        add_group(
            "Tenencia de vivienda (Hogares)",
            tenencia_vars,
            denominator="n_hog",
            total_label="Total hogares",
            unit="Hogares",
        )
        remove_group("4. Viviendas y Hogares / Tenencia")

    # Materialidad merged
    mat_pared = get_group("4. Viviendas y Hogares", "Materialidad Paredes")
    mat_piso = get_group("4. Viviendas y Hogares", "Materialidad Piso")
    mat_techo = get_group("4. Viviendas y Hogares", "Materialidad Techo")
    mat_vars = mat_pared + mat_piso + mat_techo
    if mat_vars:
        category_map = {v: "Pared" for v in mat_pared}
        category_map.update({v: "Piso" for v in mat_piso})
        category_map.update({v: "Techo" for v in mat_techo})
        add_group(
            "Materialidad de la vivienda (Viviendas)",
            mat_vars,
            denominator="by_category",
            total_label="Subtotal",
            category_col="Elemento",
            category_map=category_map,
            unit="Viviendas",
        )
        remove_group("4. Viviendas y Hogares / Materialidad Paredes")
        remove_group("4. Viviendas y Hogares / Materialidad Piso")
        remove_group("4. Viviendas y Hogares / Materialidad Techo")

    # Servicios básicos with category column
    serv_vars = get_group("4. Viviendas y Hogares", "Servicios Básicos")
    if serv_vars:
        category_map = {}
        for v in serv_vars:
            if v.startswith("n_fuente_agua_"):
                category_map[v] = "Agua"
            elif v.startswith("n_distrib_agua_"):
                category_map[v] = "Distribución"
            elif v.startswith("n_serv_hig_"):
                category_map[v] = "WC"
            elif v.startswith("n_fuente_elect_"):
                category_map[v] = "Electricidad"
            elif v.startswith("n_basura_"):
                category_map[v] = "Basura"
            else:
                category_map[v] = "Otros"
        add_group(
            "Servicios básicos (Viviendas)",
            serv_vars,
            denominator="by_category",
            total_label="Subtotal",
            category_col="Tipo",
            category_map=category_map,
            unit="Viviendas",
        )
        remove_group("4. Viviendas y Hogares / Servicios Básicos")

    # Remaining base groups
    for group_key, vars_list in base_groups.items():
        if not vars_list:
            continue
        title = group_key
        unit = _unit_from_vars(vars_list)
        if unit and group_key.startswith("4. Viviendas y Hogares"):
            title = f"{group_key.split(' / ')[1]} ({unit})"
        add_group(title, vars_list, denominator="sum", total_label="Total", unit=unit)

    return group_specs, labels, details
