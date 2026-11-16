"""
Mapa de una variable con cola larga (figura B.1): en vez de una escala continua,
donde unos cuantos valores extremos se llevan todo el rango y el resto queda del
mismo gris, se resalta el 20% más alto en negro sobre un fondo gris claro, con la
red vial encima en el acento aclarado y delgada para que no sature.

En la tesis los polígonos son hexágonos H3 con geopandas; aquí se dibujan con
matplotlib para que el ejemplo corra sin dependencias geoespaciales. El patrón de
color es el mismo.

Lecciones de la tesis: a media página los mapas con miles de polígonos se ven como
ruido, apilarlos no los agranda (los limita la altura de la página), y la leyenda va
afuera, compartida por los paneles.

    python mapa_resaltado.py   →   png/mapa_resaltado.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, RegularPolygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from estilo_tesis import ACENTO_CLARO, ANCHO, FONDO, OSCURO  # noqa: E402

rng = np.random.default_rng(3)
# una "ciudad" de hexágonos con unas cuantas avenidas
centros = [(x + (y % 2) * .5, y * .866) for y in range(40) for x in range(40)
           if (x - 20) ** 2 + (y - 20) ** 2 < 330]
centros = np.array(centros, dtype=float)
avenidas = [np.array([[0, k], [40, k + rng.uniform(-6, 6)]]) for k in (8, 15, 22, 29)] + \
           [np.array([[k, 0], [k + rng.uniform(-6, 6), 35]]) for k in (10, 20, 30)]


def distancia_a_avenida(p):
    d = []
    for a, b in avenidas:
        t = np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1)
        d.append(np.linalg.norm(p - (a + t * (b - a))))
    return min(d)


cerca = np.array([distancia_a_avenida(p) for p in centros])
valores = {
    "(a) Incidentes": np.exp(-cerca / .9) * rng.gamma(4, 1, len(centros)) + rng.gamma(1, .15, len(centros)),
    "(b) Establecimientos": rng.gamma(1.2, 30, len(centros)) * np.exp(-np.hypot(*(centros - 20).T) / 12),
}

fig, axes = plt.subplots(1, 2, figsize=(ANCHO, 2.9), layout="constrained")
for ax, (titulo, v) in zip(axes, valores.items()):
    alto = v >= np.quantile(v, .8)
    hexs = [RegularPolygon(c, 6, radius=.58) for c in centros]
    ax.add_collection(PatchCollection(hexs, facecolors=np.where(alto, OSCURO, FONDO), linewidths=0))
    ax.add_collection(LineCollection(avenidas, colors=ACENTO_CLARO, linewidths=.6))
    ax.set_xlim(-1, 41)
    ax.set_ylim(-1, 36)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(titulo)
fig.legend(handles=[Patch(color=OSCURO, label="20% con el valor más alto"),
                    Patch(color=FONDO, label="Resto"),
                    Line2D([], [], color=ACENTO_CLARO, lw=1, label="Vías primarias")],
           loc="outside lower center", ncol=3, fontsize=7)
fig.savefig(Path(__file__).parent / "png" / "mapa_resaltado.png", dpi=200)
