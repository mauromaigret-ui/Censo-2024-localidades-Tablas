from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd


def _unit_from_vars(vars_list: List[str]) -> str | None:
    if any(v.startswith(("n_hog", "n_tenencia", "n_comb", "n_serv_", "n_internet", "n_serv_tel")) for v in vars_list):
        return "hogares"
    if any(v.startswith(("n_vp", "n_viv", "n_tipo_viv", "n_mat", "n_dormitorios")) for v in vars_list):
        return "viviendas"
    if any(v.startswith("n_") for v in vars_list):
        return "personas"
    return None


def _strip_prefix(label: str, prefixes: List[str]) -> str:
    for p in prefixes:
        if label.startswith(p):
            return label[len(p):].strip()
    return label


def build_group_specs(mapping_df: pd.DataFrame, available_fields: List[str]) -> Tuple[Dict[str, Dict], Dict[str, str]]:
    df = mapping_df[mapping_df["Variable_Codigo"].isin(available_fields)].copy()

    labels = {row.Variable_Codigo: row.Descripcion_Etiqueta for row in df.itertuples(index=False)}

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

    # Sexo + General -> Población según sexo (personas)
    sexo_vars = get_group("2. Variables de Población (Personas)", "Sexo")
    general_vars = get_group("2. Variables de Población (Personas)", "General")
    sexo_table_vars = [v for v in ["n_hombres", "n_mujeres", "n_per"] if v in (sexo_vars + general_vars + available_fields)]
    add_group(
        "Población según sexo (personas)",
        sexo_table_vars,
        denominator="n_per",
        total_label="",
        no_total=True,
        unit="personas",
    )
    remove_group("2. Variables de Población (Personas) / Sexo")
    remove_group("2. Variables de Población (Personas) / General")

    # Edad
    edad_vars = [v for v in get_group("2. Variables de Población (Personas)", "Edad") if v != "prom_edad"]
    if edad_vars:
        add_group(
            "Población según tramos de edad (personas)",
            edad_vars,
            denominator="sum",
            total_label="Total",
            unit="personas",
        )
        remove_group("2. Variables de Población (Personas) / Edad")

    # Discapacidad
    discapacidad_vars = get_group("2. Variables de Población (Personas)", "Discapacidad")
    if discapacidad_vars:
        add_group(
            "Discapacidad (personas)",
            discapacidad_vars,
            denominator="n_per",
            total_label="Población total",
            unit="personas",
        )
        remove_group("2. Variables de Población (Personas) / Discapacidad")

    # Etnicidad split
    etnicidad_vars = get_group("2. Variables de Población (Personas)", "Etnicidad")
    if etnicidad_vars:
        if "n_pueblos_orig" in etnicidad_vars:
            add_group(
                "Población pueblos originarios (personas)",
                ["n_pueblos_orig"],
                denominator="n_per",
                total_label="Población total",
                unit="personas",
            )
        if "n_afrodescendencia" in etnicidad_vars:
            add_group(
                "Población afrodescendiente (personas)",
                ["n_afrodescendencia"],
                denominator="n_per",
                total_label="Población total",
                unit="personas",
            )
        if "n_lengua_indigena" in etnicidad_vars:
            add_group(
                "Hablantes de lengua indígena (personas)",
                ["n_lengua_indigena"],
                denominator="n_per",
                total_label="Población total",
                unit="personas",
            )
        remove_group("2. Variables de Población (Personas) / Etnicidad")

    # Religión
    religion_vars = get_group("2. Variables de Población (Personas)", "Religión")
    if religion_vars:
        add_group(
            "Religión (personas)",
            religion_vars,
            denominator="n_per",
            total_label="Población total",
            unit="personas",
        )
        remove_group("2. Variables de Población (Personas) / Religión")

    # Empleo: estado, dependencia (CISE) y ocupación (CIUO)
    empleo_vars = get_group("3. Educación y Empleo", "Empleo")
    if empleo_vars:
        status_vars = [v for v in ["n_ocupado", "n_desocupado", "n_fuera_fuerza_trabajo"] if v in empleo_vars]
        dependencia_vars = [v for v in empleo_vars if v.startswith("n_cise_rec_")]
        if status_vars:
            add_group(
                "Empleo (personas)",
                status_vars,
                denominator="sum",
                total_label="Total",
                unit="personas",
            )
        if dependencia_vars:
            add_group(
                "Empleo - Dependencia (personas)",
                dependencia_vars,
                denominator="sum",
                total_label="Total",
                unit="personas",
            )
        remove_group("3. Educación y Empleo / Empleo")

    ciuo_vars = get_group("3. Educación y Empleo", "Ocupación (CIUO)")
    if ciuo_vars:
        add_group(
            "Empleo - Ocupación (personas)",
            ciuo_vars,
            denominator="sum",
            total_label="Total",
            unit="personas",
        )
        remove_group("3. Educación y Empleo / Ocupación (CIUO)")

    # TICs
    tics_vars = get_group("4. Viviendas y Hogares", "TICs")
    if tics_vars:
        add_group(
            "TICs (hogares)",
            tics_vars,
            denominator="n_hog",
            total_label="Total hogares",
            unit="hogares",
        )
        remove_group("4. Viviendas y Hogares / TICs")

    # Tenencia
    tenencia_vars = get_group("4. Viviendas y Hogares", "Tenencia")
    if tenencia_vars:
        add_group(
            "Tenencia de vivienda (hogares)",
            tenencia_vars,
            denominator="n_hog",
            total_label="Total hogares",
            unit="hogares",
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
            "Materialidad (viviendas)",
            mat_vars,
            denominator="by_category",
            total_label="Subtotal",
            category_col="Elemento",
            category_map=category_map,
            unit="viviendas",
        )
        remove_group("4. Viviendas y Hogares / Materialidad Paredes")
        remove_group("4. Viviendas y Hogares / Materialidad Piso")
        remove_group("4. Viviendas y Hogares / Materialidad Techo")

    # Servicios básicos with category column
    serv_vars = get_group("4. Viviendas y Hogares", "Servicios Básicos")
    if serv_vars:
        category_map = {}
        label_override = {}
        for v in serv_vars:
            base_label = labels.get(v, v)
            if v.startswith("n_fuente_agua_"):
                category_map[v] = "Agua"
                label_override[v] = _strip_prefix(base_label, ["Agua:"])
            elif v.startswith("n_distrib_agua_"):
                category_map[v] = "Distribución"
                label_override[v] = _strip_prefix(base_label, ["Distribución:"])
            elif v.startswith("n_serv_hig_"):
                category_map[v] = "WC"
                label_override[v] = _strip_prefix(base_label, ["WC:"])
            elif v.startswith("n_fuente_elect_"):
                category_map[v] = "Electricidad"
                label_override[v] = _strip_prefix(base_label, ["Electricidad:"])
            elif v.startswith("n_basura_"):
                category_map[v] = "Basura"
                label_override[v] = _strip_prefix(base_label, ["Basura:"])
            else:
                category_map[v] = "Otros"
                label_override[v] = base_label
        add_group(
            "Servicios básicos (viviendas)",
            serv_vars,
            denominator="by_category",
            total_label="Subtotal",
            category_col="Servicio Vivienda",
            category_map=category_map,
            label_override=label_override,
            unit="viviendas",
        )
        remove_group("4. Viviendas y Hogares / Servicios Básicos")

    # Remaining base groups (skip Tema 1)
    for group_key, vars_list in base_groups.items():
        if not vars_list:
            continue
        if group_key.startswith("1. Identificación Geográfica"):
            continue
        title = group_key.split(" / ")[1] if " / " in group_key else group_key
        unit = _unit_from_vars(vars_list)
        if unit:
            title = f"{title} ({unit})"
        add_group(title, vars_list, denominator="sum", total_label="Total", unit=unit)

    def order_key(title: str) -> tuple:
        t = title.lower()
        if "población según sexo" in t:
            return (1, 1, t)
        if "población según tramos de edad" in t:
            return (1, 2, t)
        if "estado civil" in t:
            return (1, 3, t)
        if "discapacidad" in t:
            return (1, 4, t)
        if "educación" in t:
            return (2, 1, t)
        if "migración" in t:
            return (3, 1, t)
        if "pueblos originarios" in t:
            return (4, 1, t)
        if "afrodescendiente" in t:
            return (4, 2, t)
        if "lengua indígena" in t:
            return (4, 3, t)
        if "religión" in t:
            return (5, 1, t)
        if "empleo - dependencia" in t:
            return (6, 1, t)
        if "empleo - ocupación" in t or "ocupación" in t:
            return (6, 2, t)
        if "empleo" in t or "rama" in t or "transporte" in t:
            return (6, 3, t)
        if "hogares" in t or "(hogares)" in t or "tenencia" in t or "tics" in t:
            return (7, 1, t)
        if "(viviendas)" in t or "vivienda" in t or "materialidad" in t or "servicios básicos" in t:
            return (8, 1, t)
        return (9, 1, t)

    ordered_titles = sorted(group_specs.keys(), key=order_key)
    group_specs = {title: group_specs[title] for title in ordered_titles}

    return group_specs, labels
