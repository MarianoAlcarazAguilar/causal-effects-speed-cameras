"""
Figuras del capítulo 3, con el estilo de la tesis (figures/tesis.mplstyle).

1. Componentes traslapadas: las mismas cinco unidades tratadas a 100, 200 y
   300 m. Port de `scripts/resume-911/auxiliary-figures.ipynb`.
2. Soporte común a 300 m, antes y después de emparejar. Figura 2 de
   `propensity-score.ipynb`.
3. Unidades excluidas contra las 93 analizadas. Port de `conclusiones.ipynb`.

Todo sale de la muestra que se reporta: los 93 pares de `muestra_comun`.

    python figures/scripts/capitulo3_figures.py

Los PDF van a causal-effects-speed-cameras/Imagenes/.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "causal-effects-speed-cameras" / "Imagenes"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from estilo_tesis import ACENTO, ANCHO, CLARO, OSCURO  # noqa: E402
from pipeline import Datos, Panel, muestra_comun  # noqa: E402

RADIO_TESIS = 300


def componentes(emparejamientos) -> plt.Figure:
    """Las mismas cinco unidades tratadas en tres radios."""
    radios = (100, 200, 300)

    # la única componente de cinco unidades a 300 m
    panel = Panel(emparejamientos[300])
    grupos = pd.DataFrame({"uid": panel.unidades.uid, "cluster": panel.clusters})
    grupos = grupos[grupos.uid.str.startswith("T")]
    tamanos = grupos.groupby("cluster").size()
    cluster = tamanos[tamanos == 5].index[0]
    ids = sorted(int(u[1:]) for u in grupos.loc[grupos.cluster == cluster, "uid"])

    centros = (emparejamientos[300].features.tratadas.centros
               .set_index("unidad_id").loc[ids].geometry)
    xy = {u: (p.x, p.y) for u, p in centros.items()}
    xs, ys = np.array(list(xy.values())).T
    margen = max(radios) + 60
    lim_x = (xs.min() - margen, xs.max() + margen)
    lim_y = (ys.min() - margen, ys.max() + margen)

    # la red vial del encuadre, para ver sobre qué vías caen los círculos
    vialidades = emparejamientos[300].features.datos.vialidades.cx[
        lim_x[0]:lim_x[1], lim_y[0]:lim_y[1]]

    fig, axes = plt.subplots(1, 3, figsize=(ANCHO, 2.3), layout="constrained")
    for ax, radio, letra in zip(axes, radios, "abc"):
        vialidades.plot(ax=ax, color=CLARO, lw=.5, zorder=0)
        geometria = (emparejamientos[radio].features.tratadas.unidades
                     .set_index("unidad_id").loc[ids].geometry)
        enlaces = [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]
                   if geometria.loc[a].intersects(geometria.loc[b])]
        posicion = {u: i for i, u in enumerate(ids)}
        ady = coo_matrix((np.ones(len(enlaces)),
                          ([posicion[a] for a, _ in enlaces],
                           [posicion[b] for _, b in enlaces])),
                         shape=(len(ids),) * 2)
        n = connected_components(ady, directed=False)[0]

        for u in ids:
            ax.add_patch(Circle(xy[u], radio, facecolor=(0, 0, 0, .06),
                                edgecolor=OSCURO, lw=.7))
        for a, b in enlaces:
            ax.plot(*zip(xy[a], xy[b]), color=ACENTO, lw=1.2)
        for u in ids:
            ax.plot(*xy[u], "o", ms=2.2, color=OSCURO)

        ax.set_xlim(*lim_x)
        ax.set_ylim(*lim_y)
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(f"({letra}) {radio} m: {n} "
                     f"{'componente' if n == 1 else 'componentes'}")

    # una sola escala: el encuadre es el mismo en los tres paneles
    x0, y0 = lim_x[0] + 40, lim_y[0] + 40
    axes[0].plot([x0, x0 + 300], [y0, y0], color="black", lw=1)
    axes[0].text(x0 + 150, y0 + 25, "300 m", ha="center", fontsize=7)
    return fig


def soporte_comun(emparejamientos) -> plt.Figure:
    """Distribución del propensity score a 300 m, antes y después de emparejar."""
    emp = emparejamientos[RADIO_TESIS]
    logs = np.log10(emp.datos_ps.ps)
    bordes = np.linspace(logs.quantile(.005), logs.max(), 30)

    fig, axes = plt.subplots(1, 2, figsize=(ANCHO, 2.1), sharex=True,
                             layout="constrained")
    for ax, (muestra, titulo) in zip(axes, [
        (emp.datos_ps, "(a) Antes del emparejamiento"),
        (emp.emparejados, "(b) Después del emparejamiento"),
    ]):
        # controles rellenos y tratadas en contorno, para que se vea el traslape
        ax.hist(np.log10(muestra.loc[muestra.tratado == 0, "ps"]), bins=bordes,
                density=True, color=CLARO, histtype="stepfilled", label="Controles")
        ax.hist(np.log10(muestra.loc[muestra.tratado == 1, "ps"]), bins=bordes,
                density=True, color="black", lw=1, histtype="step", label="Tratadas")
        ax.set_title(titulo)
        ax.set_xlabel(r"$\log_{10}$ del propensity score")
    axes[0].set_ylabel("Densidad")
    axes[0].legend(loc="upper left")
    return fig


def excluidas(emparejamientos, comunes) -> plt.Figure:
    """Las seis unidades excluidas, como múltiplo de las 93 analizadas."""
    e300 = emparejamientos[RADIO_TESIS]
    m = e300.features.matriz
    tratadas = m[m.tratado == 1]
    fuera = [u for u in tratadas.index if u not in set(comunes)]
    columnas = {
        "nivel_incidentes": ("Incidentes al mes", "{:.1f}"),
        "tendencia": ("Tendencia previa", "{:.2f}"),
        "afluencia_nivel": ("Afluencia mensual del Metro", "{:,.0f}"),
        "pct_acceso_controlado": ("Vía de acceso controlado", "{:.0%}"),
        "hubo_fcs": ("Al menos un incidente fatal", "{:.0%}"),
        "pct_desnivel": ("Vía a desnivel", "{:.0%}"),
        "carriles_ponderados": ("Carriles promedio", "{:.1f}"),
        "pct_lesionados": ("Proporción con lesionados", "{:.0%}"),
    }
    perfil = pd.DataFrame({
        "excluidas": tratadas.loc[fuera, list(columnas)].mean(),
        "analizadas": tratadas.loc[list(comunes), list(columnas)].mean(),
        "controles": m.loc[e300.pares.control, list(columnas)].mean(),
    })
    razon = (perfil[["excluidas", "controles"]].div(perfil.analizadas, axis=0)
             .sort_values("excluidas"))

    fig, ax = plt.subplots(figsize=(ANCHO, 2.6), layout="constrained")
    y = np.arange(len(razon))
    ax.axvline(1, color="black", lw=.6, ls=":")
    ax.hlines(y, 1, razon.excluidas, color=CLARO, lw=.6)
    ax.plot(razon.controles, y, "o", mfc="white", mec=OSCURO, ms=4,
            label="93 controles emparejados")
    ax.plot(razon.excluidas, y, "o", color=OSCURO, ms=4, label="6 tratadas excluidas")
    for yi, valor in zip(y, razon.excluidas):
        derecha = valor >= 1
        ax.text(valor * (1.07 if derecha else 1 / 1.07), yi, f"{valor:.1f}",
                va="center", ha="left" if derecha else "right", fontsize=7.5)
    etiquetas = [f"{columnas[v][0]} ({columnas[v][1].format(perfil.loc[v, 'analizadas'])})"
                 for v in razon.index]
    ax.set_yticks(y, etiquetas)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xscale("log")
    ax.set_xticks([.5, 1, 2, 4], ["0.5", "1", "2", "4"])
    ax.minorticks_off()
    ax.set_xlim(.5, 5)
    ax.set_xlabel("Múltiplo del promedio de las 93 tratadas analizadas (escala logarítmica)")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1), ncol=2)
    return fig


if __name__ == "__main__":
    emparejamientos, comunes = muestra_comun(Datos())
    figuras = {
        "componente-tratado-100-200-300": componentes(emparejamientos),
        "soporte-comun-300": soporte_comun(emparejamientos),
        "unidades-excluidas": excluidas(emparejamientos, comunes),
    }
    vista = "--png" in sys.argv
    for nombre, fig in figuras.items():
        fig.savefig(PDF_DIR / f"{nombre}.pdf")
        if vista:  # para revisar sin compilar la tesis
            fig.savefig(ROOT / "figures" / "png" / f"{nombre}.png", dpi=200)
