"""
Valida los seis insumos limpios que se reutilizan para reconstruir el análisis.

No modifica ni reescribe datos: solo inspecciona esquema, cobertura temporal,
coordenadas, faltantes y unidades, y reporta lo encontrado. Es el paso de
validación descrito en el README, previo a construir círculos y panel.

Uso
---
    python scripts/validate_inputs.py
    python scripts/validate_inputs.py --data-dir data --out reports/input-validation.md

Cada insumo se valida de forma independiente: si uno falla, los demás
igual se reportan y el script termina con código 1.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Caja aproximada de la CDMX y su zona metropolitana, en EPSG:4326.
# Sirve para detectar coordenadas invertidas, en cero, o fuera de la ciudad.
CDMX_BBOX = {"lon_min": -99.40, "lon_max": -98.90, "lat_min": 19.00, "lat_max": 19.65}

# Transición de Fotomultas a Fotocívicas.
TREATMENT_DATE = pd.Timestamp("2019-04-22")


class Report:
    """Acumula las líneas del reporte para imprimirlas y opcionalmente guardarlas."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.problems: list[str] = []

    def section(self, title: str) -> None:
        self.lines.append(f"\n## {title}\n")

    def add(self, text: str = "") -> None:
        self.lines.append(text)

    def flag(self, text: str) -> None:
        """Registra algo que requiere decisión o revisión humana."""
        self.problems.append(text)
        self.lines.append(f"- **Revisar:** {text}")

    def render(self) -> str:
        return "\n".join(self.lines)


def describe_frame(
    rep: Report, df: pd.DataFrame, geometry: gpd.GeoSeries | None = None
) -> None:
    """Reporta forma, esquema, faltantes y duplicados exactos.

    En capas geográficas, una misma vialidad se guarda como muchos segmentos que
    comparten todos sus atributos, así que duplicar atributos es esperado y no
    indica un problema. Por eso `geometry` se incluye en la comparación cuando
    se proporciona: solo ahí un duplicado significa una fila repetida de verdad.
    """
    rep.add(f"- Filas: {len(df):,} | Columnas: {len(df.columns)}")
    rep.add("- Esquema:")
    rep.add("")
    rep.add("  | Columna | Tipo | Nulos | % nulos | Únicos |")
    rep.add("  | --- | --- | ---: | ---: | ---: |")
    for col in df.columns:
        nulls = int(df[col].isna().sum())
        pct = (nulls / len(df) * 100) if len(df) else 0.0
        try:
            uniques = f"{df[col].nunique(dropna=True):,}"
        except TypeError:  # columnas no hasheables, p. ej. geometrías
            uniques = "n/a"
        rep.add(f"  | `{col}` | {df[col].dtype} | {nulls:,} | {pct:.1f}% | {uniques} |")
    rep.add("")

    for col in df.columns:
        nulls = int(df[col].isna().sum())
        if nulls:
            pct = nulls / len(df) * 100
            rep.flag(f"`{col}` tiene {nulls:,} nulos ({pct:.1f}%).")

    if geometry is not None:
        attr_dupes = int(df.duplicated().sum())
        dupes = int(df.assign(_wkb=geometry.to_wkb()).duplicated().sum())
        rep.add(
            f"- Filas duplicadas exactas: {dupes:,} "
            f"(solo atributos, sin geometría: {attr_dupes:,}; esperado en capas segmentadas)"
        )
    else:
        dupes = int(df.duplicated().sum())
        rep.add(f"- Filas duplicadas exactas: {dupes:,}")

    if dupes:
        rep.flag(f"{dupes:,} filas duplicadas exactas; decidir si se eliminan.")


def describe_dates(rep: Report, s: pd.Series, name: str = "timestamp") -> None:
    """Reporta cobertura temporal, frecuencia inferida y huecos."""
    s = pd.to_datetime(s, errors="coerce")
    bad = int(s.isna().sum())
    if bad:
        rep.flag(f"`{name}`: {bad:,} valores no convertibles a fecha.")
    s = s.dropna()
    if s.empty:
        rep.flag(f"`{name}`: sin fechas válidas.")
        return

    rep.add(f"- Cobertura `{name}`: {s.min():%Y-%m-%d} a {s.max():%Y-%m-%d}")

    pre = int((s < TREATMENT_DATE).sum())
    post = int((s >= TREATMENT_DATE).sum())
    rep.add(
        f"- Respecto al {TREATMENT_DATE:%Y-%m-%d}: {pre:,} previas, {post:,} posteriores"
    )
    if pre == 0 or post == 0:
        rep.flag(
            f"`{name}` no cubre ambos lados de la fecha de tratamiento "
            f"(previas={pre:,}, posteriores={post:,})."
        )

    months = s.dt.to_period("M")
    observed = set(months.unique())
    expected = set(pd.period_range(months.min(), months.max(), freq="M"))
    missing = sorted(expected - observed)
    rep.add(f"- Meses con datos: {len(observed):,} de {len(expected):,} en el rango")
    if missing:
        shown = ", ".join(str(m) for m in missing[:12])
        suffix = " ..." if len(missing) > 12 else ""
        rep.flag(f"`{name}`: {len(missing)} meses sin observaciones: {shown}{suffix}")


def describe_coords(rep: Report, lon: pd.Series, lat: pd.Series) -> None:
    """Reporta rangos de coordenadas y puntos fuera de la CDMX."""
    lon = pd.to_numeric(lon, errors="coerce")
    lat = pd.to_numeric(lat, errors="coerce")

    rep.add(f"- Longitud: {lon.min():.5f} a {lon.max():.5f}")
    rep.add(f"- Latitud: {lat.min():.5f} a {lat.max():.5f}")

    null_coords = int((lon.isna() | lat.isna()).sum())
    if null_coords:
        rep.flag(f"{null_coords:,} filas sin coordenada utilizable.")

    zeros = int(((lon == 0) | (lat == 0)).sum())
    if zeros:
        rep.flag(f"{zeros:,} filas con coordenada en cero.")

    outside = (
        (lon < CDMX_BBOX["lon_min"])
        | (lon > CDMX_BBOX["lon_max"])
        | (lat < CDMX_BBOX["lat_min"])
        | (lat > CDMX_BBOX["lat_max"])
    )
    n_outside = int(outside.fillna(False).sum())
    pct = (n_outside / len(lon) * 100) if len(lon) else 0.0
    rep.add(f"- Fuera de la caja CDMX: {n_outside:,} ({pct:.2f}%)")
    if n_outside:
        rep.flag(
            f"{n_outside:,} puntos ({pct:.2f}%) fuera de la caja CDMX; "
            "decidir si se recortan antes de agregar a círculos."
        )


def describe_geo(rep: Report, gdf: gpd.GeoDataFrame) -> None:
    """Reporta CRS, tipos de geometría y validez."""
    rep.add(f"- CRS declarado: {gdf.crs}")
    if gdf.crs is None:
        rep.flag("Sin CRS declarado; hay que fijarlo explícitamente antes de proyectar.")

    types = gdf.geometry.geom_type.value_counts()
    rep.add(f"- Tipos de geometría: {types.to_dict()}")

    empty = int(gdf.geometry.is_empty.sum())
    missing = int(gdf.geometry.isna().sum())
    invalid = int((~gdf.geometry.is_valid).sum())
    rep.add(f"- Geometrías vacías: {empty:,} | nulas: {missing:,} | inválidas: {invalid:,}")
    for label, n in (("vacías", empty), ("nulas", missing), ("inválidas", invalid)):
        if n:
            rep.flag(f"{n:,} geometrías {label}.")

    bounds = gdf.total_bounds
    rep.add(
        f"- Extensión: lon {bounds[0]:.5f} a {bounds[2]:.5f}, "
        f"lat {bounds[1]:.5f} a {bounds[3]:.5f}"
    )


# =========================================================================
# Un validador por insumo
# =========================================================================

def validate_incidents(rep: Report, path: Path) -> None:
    df = pd.read_parquet(path)
    describe_frame(rep, df)

    if {"longitude", "latitude"} <= set(df.columns):
        describe_coords(rep, df["longitude"], df["latitude"])
    else:
        rep.flag("Faltan `longitude`/`latitude`, que `ps_features_builder` espera.")

    if "timestamp" in df.columns:
        describe_dates(rep, df["timestamp"])
    else:
        rep.flag("Falta `timestamp`, que la agregación mensual espera.")

    if "incident_level" in df.columns:
        counts = df["incident_level"].value_counts(dropna=False)
        rep.add("- Distribución de `incident_level`:")
        rep.add("")
        for level, n in counts.items():
            rep.add(f"  - `{level}`: {n:,} ({n / len(df) * 100:.1f}%)")
        rep.add("")
    else:
        rep.flag("Falta `incident_level`, que el panel por nivel espera.")


def validate_cameras(rep: Report, path: Path) -> None:
    gdf = gpd.read_file(path)
    describe_frame(rep, pd.DataFrame(gdf.drop(columns="geometry")), gdf.geometry)
    describe_geo(rep, gdf)

    pts = gdf.geometry.dropna()
    if not pts.empty and pts.geom_type.eq("Point").all():
        describe_coords(rep, pts.x, pts.y)
        # Cámaras exactamente coincidentes: relevante para agrupación de centros.
        coords = pd.DataFrame({"x": pts.x.round(6), "y": pts.y.round(6)})
        dupes = int(coords.duplicated().sum())
        rep.add(f"- Cámaras con coordenada idéntica: {dupes:,}")
        if dupes:
            rep.flag(
                f"{dupes:,} cámaras comparten coordenada exacta; afecta la definición "
                "de centros y el conteo de unidades tratadas."
            )


def validate_roads(rep: Report, path: Path) -> None:
    gdf = gpd.read_file(path)
    describe_frame(rep, pd.DataFrame(gdf.drop(columns="geometry")), gdf.geometry)
    describe_geo(rep, gdf)

    # El feature builder mapea estas tres columnas y falla si aparecen valores nuevos.
    expected_maps = {
        "TIPO_VIA": {"Vía primaria", "Vía de acceso controlado"},
        "CIRCULA": {
            "Un sentido",
            "Dos sentidos",
            "Un sentido con carril de contraflujo",
        },
    }
    for col, known in expected_maps.items():
        if col not in gdf.columns:
            rep.flag(f"Falta `{col}`, que `ps_features_builder` mapea.")
            continue
        observed = set(gdf[col].dropna().unique())
        rep.add(f"- Valores de `{col}`: {sorted(observed)}")
        unknown = observed - known
        if unknown:
            rep.flag(
                f"`{col}` tiene valores sin mapeo en `ps_features_builder`: "
                f"{sorted(unknown)}; quedarían como nulos."
            )

    if "CARRILES" in gdf.columns:
        carriles = pd.to_numeric(gdf["CARRILES"], errors="coerce")
        bad = int(carriles.isna().sum() - gdf["CARRILES"].isna().sum())
        rep.add(
            f"- `CARRILES`: min {carriles.min()}, max {carriles.max()}, "
            f"mediana {carriles.median()}"
        )
        if bad:
            rep.flag(
                f"`CARRILES` tiene {bad:,} valores no numéricos; "
                "`ps_features_builder` usa `errors='raise'` y fallaría."
            )
    else:
        rep.flag("Falta `CARRILES`.")

    if "ID_VIA" in gdf.columns:
        dupes = int(gdf["ID_VIA"].duplicated().sum())
        rep.add(f"- `ID_VIA` duplicados: {dupes:,}")


def validate_metro_coords(rep: Report, path: Path) -> None:
    df = pd.read_parquet(path)
    describe_frame(rep, df)

    if {"longitude", "latitude"} <= set(df.columns):
        describe_coords(rep, df["longitude"], df["latitude"])
    else:
        rep.flag("Faltan `longitude`/`latitude`.")

    if "estacion" in df.columns:
        dupes = int(df["estacion"].duplicated().sum())
        rep.add(f"- `estacion` duplicadas: {dupes:,}")
        if dupes:
            rep.flag(
                f"{dupes:,} estaciones repetidas; el merge con afluencia "
                "multiplicaría filas."
            )
    else:
        rep.flag("Falta `estacion`, que es la llave del merge con afluencia.")


def validate_metro_ridership(rep: Report, path: Path) -> None:
    df = pd.read_parquet(path)
    describe_frame(rep, df)

    date_cols = [c for c in df.columns if "fecha" in c.lower() or "time" in c.lower()]
    for col in date_cols:
        describe_dates(rep, df[col], name=col)

    if "estacion" in df.columns:
        rep.add(f"- Estaciones distintas: {df['estacion'].nunique():,}")
    else:
        rep.flag("Falta `estacion`, llave del merge con coordenadas.")

    num_cols = df.select_dtypes("number").columns
    for col in num_cols:
        rep.add(
            f"- `{col}`: min {df[col].min():,.2f}, mediana {df[col].median():,.2f}, "
            f"max {df[col].max():,.2f}"
        )
        if (df[col] < 0).any():
            rep.flag(f"`{col}` tiene valores negativos.")


def validate_volume(rep: Report, path: Path) -> None:
    df = pd.read_parquet(path)
    describe_frame(rep, df)

    if "timestamp" in df.columns:
        describe_dates(rep, df["timestamp"])
    else:
        rep.flag("Falta `timestamp`.")

    if "volumen_mensual" in df.columns:
        v = df["volumen_mensual"]
        rep.add(
            f"- `volumen_mensual`: min {v.min():,.2f}, mediana {v.median():,.2f}, "
            f"max {v.max():,.2f}"
        )
        # El README advierte sobre una división entre 1,000 en el notebook de origen.
        # La magnitud indica si los valores guardados ya vienen reescalados.
        rep.add(
            "- Magnitud mediana sugiere unidades en "
            f"{'miles de vehículos' if v.median() < 100_000 else 'vehículos'} "
            "(verificar contra la fuente antes de reescalar coeficientes)."
        )
        if (v <= 0).any():
            rep.flag("`volumen_mensual` tiene valores no positivos.")
    else:
        rep.flag("Falta `volumen_mensual`, que el builder usa para tasas.")


INPUTS = [
    ("Incidentes clasificados", "classified-incidents.parquet", validate_incidents),
    (
        "Ubicación de cámaras (Fotocívicas)",
        "fotocivicas-ubicacion-puntos",
        validate_cameras,
    ),
    ("Vialidades", "vialidades.json", validate_roads),
    ("Coordenadas de estaciones del Metro", "metro-station-coordinates.parquet", validate_metro_coords),
    ("Afluencia semanal del Metro", "afluencia-metro-semanal.parquet", validate_metro_ridership),
    ("Volumen vehicular mensual", "volumen-total-mensual.parquet", validate_volume),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", type=Path)
    parser.add_argument("--out", type=Path, help="Guarda el reporte en Markdown.")
    args = parser.parse_args()

    rep = Report()
    rep.add("# Validación de insumos limpios")
    rep.add("")
    rep.add(f"Directorio: `{args.data_dir}`")
    rep.add(f"Fecha de tratamiento de referencia: {TREATMENT_DATE:%Y-%m-%d}")

    failed = False
    for title, filename, validator in INPUTS:
        path = args.data_dir / filename
        rep.section(f"{title} — `{filename}`")

        if not path.exists():
            rep.flag(f"No existe `{path}`.")
            failed = True
            continue

        size = sum(f.stat().st_size for f in path.rglob("*")) if path.is_dir() else path.stat().st_size
        rep.add(f"- Tamaño: {size / 1e6:.1f} MB")

        try:
            validator(rep, path)
        except Exception:
            failed = True
            rep.flag(f"La validación falló con excepción:\n\n```\n{traceback.format_exc()}```")

    rep.section("Resumen")
    if rep.problems:
        rep.add(f"{len(rep.problems)} puntos requieren revisión o decisión:")
        rep.add("")
        for i, problem in enumerate(rep.problems, 1):
            rep.add(f"{i}. {problem}")
    else:
        rep.add("Ningún punto requiere revisión.")

    text = rep.render()
    print(text)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"\nReporte guardado en {args.out}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
