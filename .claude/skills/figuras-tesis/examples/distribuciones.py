"""
Dos formas de comparar distribuciones de dos grupos, las dos de la tesis:

1. Histogramas antes y después de emparejar (figura 3.2, soporte común): el grupo de
   comparación relleno en gris claro y el principal solo en contorno oscuro, para
   que se vea el traslape. Eje x en log10 cuando los valores se amontonan cerca de
   cero, y el mismo eje en los dos paneles.
2. Distribución acumulada (figura B.2): mejor que el histograma cuando las colas son
   largas y lo que importa es qué grupo tiene valores más altos en toda la
   distribución. El eje se corta para que se vea la forma, pero la proporción se
   calcula con todos los datos, y la nota de LaTeX lo dice.

    python distribuciones.py   →   png/distribuciones-soporte.png, png/distribuciones-acumulada.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from estilo_tesis import ANCHO, CLARO, OSCURO  # noqa: E402

PNG = Path(__file__).parent / "png"
rng = np.random.default_rng(2)

# 1. soporte común
controles = rng.lognormal(-5.5, 1.0, 15000)
tratadas = rng.lognormal(-4.4, .9, 99)
emparejados = rng.choice(controles[controles > np.quantile(controles, .55)], 93)
logs = np.log10(np.r_[controles, tratadas])
bordes = np.linspace(np.quantile(logs, .005), logs.max(), 30)
fig, axes = plt.subplots(1, 2, figsize=(ANCHO, 2.1), sharex=True, layout="constrained")
for ax, (c, t, titulo) in zip(axes, [(controles, tratadas, "(a) Antes del emparejamiento"),
                                     (emparejados, tratadas[:93], "(b) Después del emparejamiento")]):
    ax.hist(np.log10(c), bins=bordes, density=True, color=CLARO, histtype="stepfilled", label="Controles")
    ax.hist(np.log10(t), bins=bordes, density=True, color="black", lw=1, histtype="step", label="Tratadas")
    ax.set_title(titulo)
    ax.set_xlabel(r"$\log_{10}$ del propensity score")
axes[0].set_ylabel("Densidad")
axes[0].legend(loc="upper left")
fig.savefig(PNG / "distribuciones-soporte.png", dpi=200)

# 2. distribución acumulada
grupos = {"Sin vía primaria": rng.gamma(9, .15, 2300) + .9, "Con vía primaria": rng.gamma(2.2, 1.1, 2500) + .9}
fig, ax = plt.subplots(figsize=(ANCHO / 2, 2.2), layout="constrained")
limite = 8
for (nombre, x), estilo in zip(grupos.items(), [dict(color=CLARO, lw=2), dict(color=OSCURO, lw=1.1)]):
    x = np.sort(x)
    ax.step(np.r_[0, x, max(limite, x[-1])], np.r_[0, np.arange(1, len(x) + 1) / len(x), 1],
            where="post", label=nombre, **estilo)
ax.set_xlim(0, limite)
ax.set_ylim(0, 1.02)
ax.set_xlabel("Incidentes al mes")
ax.set_ylabel("Proporción de hexágonos")
ax.legend(loc="lower right")
fig.savefig(PNG / "distribuciones-acumulada.png", dpi=200)
