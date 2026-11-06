"""
Figuras de la introducción: incidentes por año y nivel, accidentes fatales por
año e infracciones por tipo de sanción, con el estilo de la tesis
(figures/tesis.mplstyle).

    python figures/scripts/intro_figures.py [--png]

Los PDF van a causal-effects-speed-cameras/Imagenes/; con --png queda además
una vista previa en figures/png/.

Los datos están escritos aquí porque no hay otra copia de ellos en el repo. Los
totales y los fatales salen de la base del C5 2014-2023 (incidentes-viales.parquet),
que no está versionada; son los valores que anotaba scripts/auxiliar/5-other-stuff.ipynb
y sus promedios anuales reproducen los de ese notebook (85,150 y 383). Los
lesionados se leyeron de los marcadores de la figura vieja, calibrando el eje
con los totales: el error es de unos cien incidentes y su suma cae a 42 de la
que implica el notebook. Los menores son el residuo, para que las series sumen
el total. Las infracciones las transcribió Mariano a mano de un PDF de la
autoridad.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "causal-effects-speed-cameras" / "Imagenes"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from estilo_tesis import ACENTO, ANCHO, CLARO, OSCURO  # noqa: E402

ALTO = 2.4

# La política arranca el 22 de abril de 2019. Con datos anuales, la línea va
# entre 2018 (último año completo previo) y 2019 (primer año con fotocívicas).
POLICY_X = 2018.5

FATALES = pd.Series(
    [482, 457, 351, 316, 295, 345, 303, 330, 491, 464],
    index=range(2014, 2024),
)

INCIDENTES = pd.DataFrame(
    {
        "total": [138_396, 109_620, 77_468, 75_929, 75_853, 75_513, 56_254, 71_922, 87_336, 83_211],
        "lesionados": [52_824, 39_722, 27_126, 30_169, 31_184, 32_198, 28_986, 37_270, 48_429, 48_429],
        "fatales": FATALES.to_list(),
    },
    index=range(2014, 2024),
).assign(menores=lambda df: df.total - df.lesionados - df.fatales)

INFRACCIONES = pd.DataFrame(
    {
        "civica": [500_082, 566_395, 720_718, 667_598, 202_758],
        "economica": [1_598_331, 2_039_552, 3_235_329, 2_773_361, 1_237_133],
    },
    index=range(2019, 2024),
)


def marcar_politica(ax) -> None:
    ax.axvline(POLICY_X, color="black", lw=0.6, ls="--", zorder=1)
    ax.annotate("Fotocívicas", xy=(POLICY_X, 1), xycoords=("data", "axes fraction"),
                xytext=(3, 0), textcoords="offset points", va="top", ha="left")


def incidentes() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO), layout="constrained")

    # El texto compara menores con lesionados (se cruzan en 2020): esa serie
    # lleva el acento. Cada serie se etiqueta al final, sin leyenda.
    series = [
        ("total", "Total", "black", "o"),
        ("menores", "Menores", CLARO, "^"),
        ("lesionados", "Con lesionados", ACENTO, "s"),
        ("fatales", "Fatales", OSCURO, "x"),
    ]
    for columna, etiqueta, color, marcador in series:
        y = INCIDENTES[columna] / 1e3
        ax.plot(INCIDENTES.index, y, color=color, marker=marcador, ms=3)
        # los fatales viven pegados al eje: su etiqueta sube para no montarse en él
        abajo = columna == "fatales"
        ax.annotate(etiqueta, xy=(2023, y.iloc[-1]), xytext=(7, 3 if abajo else 0),
                    textcoords="offset points", va="bottom" if abajo else "center",
                    color=color)

    # Tras una caída fuerte, la línea entra por arriba a la izquierda y taparía
    # la etiqueta centrada; ahí se corre a la derecha.
    total = INCIDENTES.total
    a_la_derecha = (total.shift(1) - total > 10_000) & (total.shift(-1) - total < 5_000)
    for anio, valor in total.items():
        ax.annotate(f"{valor / 1e3:.1f}", xy=(anio, valor / 1e3),
                    xytext=(7, 3) if a_la_derecha[anio] else (0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(INCIDENTES.index)
    ax.set_xlabel("Año")
    ax.set_ylabel("Incidentes (miles)")
    ax.set_ylim(0, 155)
    ax.set_xlim(2013.5, 2023.4)
    marcar_politica(ax)
    return fig


def fatales() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO), layout="constrained")
    ax.plot(FATALES.index, FATALES, color=OSCURO, marker="o", ms=3)
    for anio, valor in FATALES.items():
        ax.annotate(f"{valor}", xy=(anio, valor), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(FATALES.index)
    ax.set_xlabel("Año")
    ax.set_ylabel("Accidentes fatales")
    ax.set_ylim(0, 560)
    ax.set_xlim(2013.5, 2023.5)
    marcar_politica(ax)
    return fig


def infracciones() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO), layout="constrained")
    civica = INFRACCIONES.civica / 1e6
    economica = INFRACCIONES.economica / 1e6
    total = civica + economica

    ax.bar(INFRACCIONES.index, civica, width=0.6, color=OSCURO, label="Cívicas")
    ax.bar(INFRACCIONES.index, economica, width=0.6, bottom=civica, color=CLARO,
           label="Económicas")

    # El texto cita la proporción de sanciones cívicas, así que es lo que se anota.
    for anio, proporcion, alto in zip(INFRACCIONES.index, civica / total, total):
        ax.annotate(f"{proporcion:.0%} cívicas", xy=(anio, alto), xytext=(0, 3),
                    textcoords="offset points", ha="center", va="bottom")

    ax.set_xticks(INFRACCIONES.index)
    ax.set_xlabel("Año")
    ax.set_ylabel("Infracciones (millones)")
    ax.set_ylim(0, 4.5)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="upper right", handlelength=1.2, borderaxespad=0.2)
    return fig


if __name__ == "__main__":
    figuras = {
        "yearly-number-of-incidents": incidentes(),
        "yearly-fatal-number-of-incidents": fatales(),
        "yearly-number-of-sanctions": infracciones(),
    }
    vista = "--png" in sys.argv
    for nombre, fig in figuras.items():
        fig.savefig(PDF_DIR / f"{nombre}.pdf")
        if vista:  # para revisar sin compilar la tesis
            fig.savefig(ROOT / "figures" / "png" / f"{nombre}.png", dpi=200)
