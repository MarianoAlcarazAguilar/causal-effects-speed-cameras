"""
Figuras del apéndice B: zonas con y sin vías primarias, en hexágonos H3.

Port de `scripts/writing/vias-primarias-vs-secundarias.ipynb` (accidentes) y
`scripts/writing/mexico-city-business-density.ipynb` (establecimientos), con
el estilo de la tesis. Los cálculos son los mismos que en esos notebooks:

- Accidentes: hexágonos de resolución 9 (~428 m de diagonal mayor) dentro de la
  Ciudad de México. Para cada hexágono, el promedio de incidentes por mes de
  calendario antes del 22 de abril de 2019, contando solo los meses con al
  menos un incidente, como en el notebook original.
- Establecimientos: los mismos hexágonos de resolución 9, solo los que tienen
  al menos un incidente en toda la ventana; el conteo de Google Places
  Aggregate se hizo en un círculo de 214 m alrededor del centro de cada
  hexágono (`data/raw/businesses-cdmx.json`). Ese archivo trae también 774
  hexágonos de resolución 8 de una corrida anterior, que no se usan.

Un hexágono "tiene vía primaria" si lo cruza alguna vía primaria o de acceso
controlado.

    python figures/scripts/apendice_figures.py [--png]

Requiere `h3` (v4). Los PDF van a tesis/Imagenes/.
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import h3
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
PDF_DIR = ROOT / "tesis" / "Imagenes"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "skills" / "figuras-tesis" / "scripts"))  # el estilo

from estilo_tesis import ANCHO, CLARO, OSCURO  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

FONDO = "#E3E3E3"  # hexágonos fuera del quintil más alto
VIAS = "#D9A3A3"  # el acento de la tesis, aclarado para no saturar el mapa

CRS = 4326
INICIO_PROGRAMA = pd.Timestamp("2019-04-22")


# =====================================================================
# Datos
# =====================================================================

def cdmx() -> Polygon:
    localidades = gpd.read_file(DATA / "localidadurbana" / "LocalidadUrbana.shp").to_crs(CRS)
    return localidades.loc[localidades.NOM == "DISTRITO FEDERAL"].union_all()


def hexagonos(contorno, resolucion: int) -> gpd.GeoDataFrame:
    """Hexágonos H3 cuyo centro cae dentro del contorno."""
    celdas = h3.geo_to_cells(contorno, resolucion)
    return gpd.GeoDataFrame(
        index=pd.Index(sorted(celdas), name="h3"),
        geometry=[Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)])
                  for c in sorted(celdas)],
        crs=CRS,
    )


def vialidades() -> gpd.GeoDataFrame:
    return gpd.read_file(DATA / "vialidades.json").to_crs(CRS)[["geometry"]]


def incidentes() -> gpd.GeoDataFrame:
    df = pd.read_parquet(DATA / "classified-incidents.parquet")
    return gpd.GeoDataFrame(
        df.drop(columns=["latitude", "longitude"]),
        geometry=gpd.points_from_xy(df.longitude, df.latitude), crs=CRS,
    )


def con_via_primaria(hex_: gpd.GeoDataFrame, vias: gpd.GeoDataFrame) -> pd.Series:
    cruzados = gpd.sjoin(vias, hex_, predicate="intersects")["h3"].unique()
    return pd.Series(hex_.index.isin(cruzados), index=hex_.index)


def accidentes_por_hexagono(contorno, vias, inc) -> gpd.GeoDataFrame:
    hex_ = hexagonos(contorno, 9)
    previos = inc[inc.timestamp <= INICIO_PROGRAMA]
    unidos = gpd.sjoin(previos, hex_, predicate="intersects")
    mensual = (unidos.groupby(["h3", pd.Grouper(key="timestamp", freq="ME")])
               .size().rename("n").reset_index())
    promedio = mensual.groupby("h3").n.mean().rename("promedio")
    out = hex_.join(promedio, how="inner")
    out["via_primaria"] = con_via_primaria(out, vias)
    return out


def establecimientos_por_hexagono(contorno, vias, inc) -> gpd.GeoDataFrame:
    hex_ = hexagonos(contorno, 9)
    con_incidente = gpd.sjoin(inc, hex_, predicate="intersects")["h3"].unique()
    hex_ = hex_.loc[hex_.index.isin(con_incidente)]
    conteo = pd.Series(
        {k: v["count"] for k, v in
         json.loads((DATA / "raw" / "businesses-cdmx.json").read_text()).items()},
        name="establecimientos",
    )
    out = hex_.join(conteo, how="inner")
    out["via_primaria"] = con_via_primaria(out, vias)
    return out


# =====================================================================
# Figuras
# =====================================================================

def mapa(hex_: gpd.GeoDataFrame, columna: str, vias, ax):
    """El 20% de hexágonos con el valor más alto, en negro; el resto, en gris.

    Las dos variables tienen colas muy largas: con una escala continua, unos
    cuantos hexágonos se llevan todo el rango y el resto queda del mismo tono.
    Marcar solo el quintil más alto deja ver dónde se concentran.
    """
    alto = hex_[columna] >= hex_[columna].quantile(.8)
    hex_[~alto].plot(ax=ax, color=FONDO, linewidth=.1, edgecolor="face")
    hex_[alto].plot(ax=ax, color=OSCURO, linewidth=.1, edgecolor="face")
    # la red vial encima, delgada y clara, para que no tape los hexágonos
    vias.clip(hex_.total_bounds).plot(ax=ax, color=VIAS, lw=.3)
    ax.set_axis_off()


def mapas(acc, est, vias) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(ANCHO, 2.9), layout="constrained")
    for ax, (datos, col, titulo) in zip(axes, [
        (acc, "promedio", "(a) Incidentes"),
        (est, "establecimientos", "(b) Establecimientos"),
    ]):
        mapa(datos, col, vias, ax)
        ax.set_title(titulo)
    fig.legend(handles=[Patch(color=OSCURO, label="20% de hexágonos con el valor más alto"),
                        Patch(color=FONDO, label="Resto de los hexágonos"),
                        Line2D([], [], color=VIAS, lw=1, label="Vías primarias y de acceso controlado")],
               loc="outside lower center", ncol=2, fontsize=7)
    return fig


def distribuciones(acc, est) -> plt.Figure:
    """Distribución acumulada, con y sin vía primaria."""
    fig, axes = plt.subplots(1, 2, figsize=(ANCHO, 2.2), layout="constrained")
    for ax, (datos, col, xlabel, limite, titulo) in zip(axes, [
        (acc, "promedio", "Incidentes al mes", 8, "(a) Incidentes"),
        (est, "establecimientos", "Establecimientos", 400, "(b) Establecimientos"),
    ]):
        for via, estilo in [(False, dict(color=CLARO, lw=2, label="Sin vía primaria")),
                            (True, dict(color=OSCURO, lw=1.1, label="Con vía primaria"))]:
            x = np.sort(datos.loc[datos.via_primaria == via, col].to_numpy())
            # la proporción se calcula con todos los hexágonos, aunque el eje se corte
            ax.step(np.r_[0, x, max(limite, x[-1])],
                    np.r_[0, np.arange(1, len(x) + 1) / len(x), 1],
                    where="post", **estilo)
        ax.set_xlim(0, limite)
        ax.set_ylim(0, 1.02)
        ax.set_title(titulo)
        ax.set_xlabel(xlabel)
    axes[0].set_ylabel("Proporción de hexágonos")
    axes[1].legend(loc="lower right")
    return fig


def resumen(acc, est) -> pd.DataFrame:
    return pd.concat({
        "incidentes": acc.groupby("via_primaria").promedio.agg(["mean", "std", "size"]),
        "establecimientos": est.groupby("via_primaria").establecimientos.agg(["mean", "std", "size"]),
    })


if __name__ == "__main__":
    contorno, vias, inc = cdmx(), vialidades(), incidentes()
    acc = accidentes_por_hexagono(contorno, vias, inc)
    est = establecimientos_por_hexagono(contorno, vias, inc)
    print(resumen(acc, est).round(2))
    figuras = {
        "vias-primarias-mapas": mapas(acc, est, vias),
        "vias-primarias-distribuciones": distribuciones(acc, est),
    }
    vista = "--png" in sys.argv
    for nombre, fig in figuras.items():
        fig.savefig(PDF_DIR / f"{nombre}.pdf")
        if vista:  # para revisar sin compilar la tesis
            fig.savefig(ROOT / "figures" / "png" / f"{nombre}.png", dpi=200)
