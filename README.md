# Censo 2024 Localidades Tablas

App local con interfaz en navegador para generar tabulados por entidad censal a partir de la cartografía (GPKG).

## ✅ Estado seguro (reporte Word OK)
Tag en GitHub: `word-report-ok`  
Para volver a este estado:
```bash
git fetch --tags
git checkout word-report-ok
```

## Requisitos
- Python 3.11+

## Inicio rápido
```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
uvicorn --app-dir backend app.main:app --reload --port 8000
```

Luego abre `http://localhost:8000`.

## Datos esperados
- GPKG: `Cartografia_Censal/Cartografia_censo2024_Pais.gpkg`
- Diccionario cartográfico (XLSX): `Cartografia_Censal/Diccionario_variables_geograficas_CPV24.xlsx`
- Diccionario de variables (CSV): `data/diccionario_variables.csv`
- Filtro: Excel con `ID_ENTIDAD` (y opcionalmente `ENTIDAD`, `LOCALIDAD`, `COMUNA`).

## Salidas
- CSV por variable en `Resultados/reporte_[grupo].csv`
- Consolidado: `Resultados/reporte_consolidado.csv`, `Resultados/reporte_consolidado.html`, `Resultados/reporte_consolidado.xlsx`, `Resultados/reporte_consolidado.docx`
