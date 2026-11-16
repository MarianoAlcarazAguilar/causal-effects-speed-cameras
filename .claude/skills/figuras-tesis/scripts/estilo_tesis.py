"""
Estilo de las figuras de la tesis: registra las fuentes de ../assets/fonts y aplica
../assets/tesis.mplstyle.

    from estilo_tesis import ANCHO, OSCURO, CLARO, ACENTO, cero, menos, pct, guardar

Las convenciones están en ../references/convenciones.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

ASSETS = Path(__file__).resolve().parents[1] / "assets"

for fuente in (ASSETS / "fonts").glob("*.otf"):
    font_manager.fontManager.addfont(str(fuente))
plt.style.use(ASSETS / "tesis.mplstyle")

# \textwidth de la tesis: hoja de 17 cm con márgenes de 2.5 cm, en pulgadas
ANCHO = 12 / 2.54

# tratadas en gris oscuro, controles en gris claro; el acento solo para lo que
# el texto señala (una referencia, un grupo aparte)
OSCURO, CLARO, ACENTO = "#333333", "#A6A6A6", "#8C2D2D"
# Para capas encima de otros datos (la red vial sobre un mapa): el acento aclarado,
# para que no tape lo que está debajo.
ACENTO_CLARO = "#D9A3A3"
# Fondo neutro de mapas y categoría "resto".
FONDO = "#E3E3E3"


def cero(ax, horizontal: bool = True) -> None:
    """Línea de referencia en cero, punteada, debajo de los datos."""
    if horizontal:
        ax.axhline(0, color="black", lw=.6, ls=":", zorder=1)
    else:
        ax.axvline(0, color="black", lw=.6, ls=":", zorder=1)


def menos(texto: str) -> str:
    """Cambia el guion por el signo menos tipográfico (−) en etiquetas y anotaciones."""
    return texto.replace("-", "−")


def pct(valor: float, decimales: int = 1) -> str:
    """Porcentaje con signo explícito y signo menos tipográfico: +5.6%, −1.8%."""
    return menos(f"{valor:+.{decimales}f}%")


def guardar(figuras: dict, pdf_dir: Path, png_dir: Path | None = None) -> None:
    """Guarda cada figura como PDF en `pdf_dir`; con `--png` en la línea de comandos,
    también una vista previa en `png_dir` para revisarla sin compilar la tesis."""
    pdf_dir = Path(pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    vista = "--png" in sys.argv and png_dir is not None
    if vista:
        Path(png_dir).mkdir(parents=True, exist_ok=True)
    for nombre, fig in figuras.items():
        fig.savefig(pdf_dir / f"{nombre}.pdf")
        if vista:
            fig.savefig(Path(png_dir) / f"{nombre}.png", dpi=200)
        plt.close(fig)
