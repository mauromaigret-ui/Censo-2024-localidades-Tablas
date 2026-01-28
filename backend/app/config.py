from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
CARTO_DIR = ROOT_DIR / "Cartografia_Censal"
GPKG_PATH = CARTO_DIR / "Cartografia_censo2024_Pais.gpkg"
DICT_PATH = CARTO_DIR / "Diccionario_variables_geograficas_CPV24.xlsx"
RESULTS_DIR = ROOT_DIR / "Resultados"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
VARIABLES_DICT_PATH = ROOT_DIR / "data" / "diccionario_variables.csv"
