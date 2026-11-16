"""Rutas y constantes del visor."""
from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]  # scripts/visor/config.py → raíz del repo
PACKAGE = Path(__file__).resolve().parent
STATIC = PACKAGE / "static"


SRC_NAME = "tesis"


# Antes del 16 de noviembre de 2026 la tesis vivía en esta carpeta. Los commits viejos se
# buscan ahí, para poder seguir comparando contra cualquier versión.
OLD_SRC_NAMES = ("causal-effects-speed-cameras",)


SRC_PATHS = (SRC_NAME, *OLD_SRC_NAMES)


SRC = REPO / SRC_NAME


MAIN = "main.tex"


WORK = REPO / ".visor"


OUT = WORK / "out"


WORKTREE = "WORKTREE"


WATCH_EXT = {".tex", ".bib", ".sty", ".cls", ".bst", ".png", ".jpg", ".jpeg", ".pdf"}


SKIP_COPY = {".aux", ".log", ".toc", ".lof", ".lot", ".out", ".fls", ".synctex.gz",
             ".fdb_latexmk", ".xdv", ".bbl", ".blg", ".bcf", ".nav", ".snm"}
