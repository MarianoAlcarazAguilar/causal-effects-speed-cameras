"""
Registra las fuentes de figures/fonts y aplica figures/tesis.mplstyle.

    from estilo_tesis import ANCHO, OSCURO, CLARO, ACENTO
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

FIGURES = Path(__file__).resolve().parents[1]

for fuente in (FIGURES / "fonts").glob("*.otf"):
    font_manager.fontManager.addfont(str(fuente))
plt.style.use(FIGURES / "tesis.mplstyle")

# \textwidth de la tesis: hoja de 17 cm con márgenes de 2.5 cm, en pulgadas
ANCHO = 12 / 2.54

# tratadas en gris oscuro, controles en gris claro; el acento solo para lo que
# el texto señala (una referencia, un grupo aparte)
OSCURO, CLARO, ACENTO = "#333333", "#A6A6A6", "#8C2D2D"
