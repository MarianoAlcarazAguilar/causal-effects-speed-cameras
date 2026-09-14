"""
Arranque para notebooks: una línea en vez de repetir imports y rutas.

    from nbsetup import *

Deja el working directory en la raíz del repo, sin importar desde qué carpeta
se abrió el notebook, para que las rutas relativas ("data/...") funcionen igual
en todos lados. Expone pandas, numpy, geopandas, shapely, matplotlib y las
rutas ROOT y DATA, y activa autoreload para que editar un .py se refleje sin
reiniciar el kernel.

El módulo es importable desde cualquier directorio gracias al archivo .pth del
entorno tesis-cameras, que agrega la raíz del repo al sys.path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"

# Ejecutar siempre como si el notebook viviera en la raíz.
os.chdir(ROOT)

# `scripts/` en el path permite tanto `import grid_builder` como
# `from scripts import grid_builder`.
for path in (ROOT, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    import shapely
except ImportError:  # el entorno puede no tener el stack geoespacial
    gpd = None
    shapely = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def _enable_autoreload() -> None:
    """Recarga módulos editados sin reiniciar el kernel. Silencioso fuera de IPython."""
    try:
        from IPython import get_ipython
    except ImportError:
        return

    ipython = get_ipython()
    if ipython is None:
        return

    ipython.run_line_magic("load_ext", "autoreload")
    ipython.run_line_magic("autoreload", "2")


_enable_autoreload()

__all__ = [
    "ROOT",
    "DATA",
    "SCRIPTS",
    "Path",
    "np",
    "pd",
    "gpd",
    "shapely",
    "plt",
]
