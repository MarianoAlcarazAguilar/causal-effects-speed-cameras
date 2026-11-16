"""
Coeficientes con intervalo, en horizontal: la "escalera" de la tesis (figura 4.1),
que muestra cómo cambia un efecto según la comparación que se haga.

Patrón: un renglón por especificación, punto + intervalo en gris oscuro, el valor
anotado a la derecha con fondo blanco, cero punteado, sin eje izquierdo, y en el
acento un segundo intervalo que el texto discute (aquí, el del bootstrap).

    python coeficientes.py   →   png/coeficientes.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from estilo_tesis import ACENTO, ANCHO, OSCURO, pct  # noqa: E402

pasos = [  # etiqueta, efecto %, error estándar %
    ("Antes y después,\nsolo tratadas", -14.1, 2.4),
    ("Diferencias en diferencias\ncontra toda la ciudad", -13.7, 4.3),
    ("+ solo las unidades con\nsoporte común", -10.1, 4.0),
    ("+ emparejamiento", -2.5, 3.3),
    ("+ covariables × post", -1.8, 3.0),
]
ic_boot = (-6.0, 2.2)  # el intervalo que el texto discute para el último paso

fig, ax = plt.subplots(figsize=(ANCHO, 2.7), layout="constrained")
y = np.arange(len(pasos))[::-1]  # el primero arriba
efecto = np.array([p[1] for p in pasos])
ee = np.array([p[2] for p in pasos])
ax.axvline(0, color="black", lw=.6, ls=":")
ax.hlines(y, efecto - 1.96 * ee, efecto + 1.96 * ee, color=OSCURO, lw=1.2)
ax.plot(efecto, y, "o", color=OSCURO, ms=4)
ax.hlines(y[-1] - .32, *ic_boot, color=ACENTO, lw=1.2)
ax.text(ic_boot[0], y[-1] - .32, "bootstrap ", ha="right", va="center", fontsize=7.5, color=ACENTO)
for yi, e, s in zip(y, efecto, ee):
    ax.text(e + 1.96 * s + .6, yi, pct(e), va="center", fontsize=7.5,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": .5})
ax.set_yticks(y, [p[0] for p in pasos])
ax.tick_params(axis="y", length=0)
ax.spines["left"].set_visible(False)
ax.set_ylim(-.65, len(pasos) - .5)
ax.set_xlabel("Efecto estimado, % del nivel previo de la comparación (IC 95%)")

fig.savefig(Path(__file__).parent / "png" / "coeficientes.png", dpi=200)
