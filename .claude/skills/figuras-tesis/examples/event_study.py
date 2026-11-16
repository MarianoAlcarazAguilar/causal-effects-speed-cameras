"""
Event study en paneles: la figura 4.2 de la tesis, un panel por grupo (radio).

Patrón: un coeficiente por año con su intervalo, el año de referencia como punto
hueco fijo en cero, el periodo posterior sombreado en gris (no con una línea
vertical), "antes" y "después" escritos arriba, eje y compartido para comparar
magnitudes entre paneles y las etiquetas comunes con supxlabel/supylabel.

    python event_study.py   →   png/event_study.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from estilo_tesis import ANCHO, CLARO, OSCURO, cero, menos  # noqa: E402

rng = np.random.default_rng(1)
anios = np.array([-3, -2, -1, 1, 2, 3])
grupos = [100, 150, 200, 250, 300]

fig, axes = plt.subplots(2, 3, figsize=(ANCHO, 3.6), sharey=True, layout="constrained")
axes = axes.ravel()
axes[-1].set_axis_off()  # cinco paneles en una cuadrícula de seis
for ax, grupo, letra in zip(axes, grupos, "abcde"):
    coef = np.where(anios == -1, 0, rng.normal(0, 2.5, len(anios)))
    ee = np.where(anios == -1, 0, rng.uniform(2.5, 4.5, len(anios)))
    ax.axvspan(0, 3.6, color=CLARO, alpha=.25, lw=0)
    cero(ax)
    ax.vlines(anios, coef - 1.96 * ee, coef + 1.96 * ee, color=OSCURO, lw=1.2)
    ax.plot(anios[anios != -1], coef[anios != -1], "o", color=OSCURO, ms=4)
    ax.plot([-1], [0], "o", mfc="white", mec=OSCURO, ms=4)  # referencia
    ax.set_xticks(anios, [menos(f"{k:+d}") for k in anios], fontsize=7)
    ax.set_xlim(-3.6, 3.6)
    ax.set_title(f"({letra}) {grupo} m")
for ax in axes[:-1]:
    ax.text(-2, ax.get_ylim()[1], "antes", ha="center", va="top", fontsize=7.5)
    ax.text(2, ax.get_ylim()[1], "después", ha="center", va="top", fontsize=7.5)
fig.supylabel("Tratado × año, % de la media previa del control\n(IC 95%)", fontsize=9)
fig.supxlabel("Años desde el inicio del programa (año −1 = referencia, punto hueco)", fontsize=9)

fig.savefig(Path(__file__).parent / "png" / "event_study.png", dpi=200)
