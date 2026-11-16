"""
Love plot: balance de covariables antes y después de emparejar (figura 3.3).

Patrón: un renglón por covariable, en el mismo orden que el cuadro de balance que
acompaña (para leerlos juntos), círculo vacío = antes y relleno = después, unidos
por una línea gris, cero sólido y umbrales de ±0.1 punteados en gris claro. Los
nombres son los de las variables, en monoespaciada, como en el cuadro.

    python love_plot.py   →   png/love_plot.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from estilo_tesis import ANCHO, CLARO, OSCURO  # noqa: E402

covariables = ["nivel_incidentes", "pct_lesionados", "tendencia", "hubo_fsc", "road_length_m",
               "n_vialidades", "carriles_ponderados", "afluencia_nivel"]
antes = np.array([.63, 0, .17, .65, .24, .2, .5, .32])
despues = np.array([.07, .12, -.05, -.05, .12, .07, .02, .14])

orden = covariables[::-1]  # el eje y crece hacia arriba
a = dict(zip(covariables, antes))
d = dict(zip(covariables, despues))
y = np.arange(len(orden))
fig, ax = plt.subplots(figsize=(ANCHO, 2.4), layout="constrained")
ax.axvline(0, color="black", lw=.6)
for signo in (-1, 1):
    ax.axvline(signo * .1, color=CLARO, lw=.6, ls="--")
ax.hlines(y, [a[v] for v in orden], [d[v] for v in orden], color=CLARO, lw=.6)
ax.plot([a[v] for v in orden], y, "o", mfc="white", mec=OSCURO, ms=4, label="Antes del emparejamiento")
ax.plot([d[v] for v in orden], y, "o", color=OSCURO, ms=4, label="Después del emparejamiento")
ax.set_yticks(y, orden, family="monospace", fontsize=7)
ax.tick_params(axis="y", length=0)
ax.spines["left"].set_visible(False)
ax.set_xlabel("Diferencia de medias estandarizada (SMD)")
ax.legend(loc="lower right", bbox_to_anchor=(1, 1), ncol=2)
fig.savefig(Path(__file__).parent / "png" / "love_plot.png", dpi=200)
