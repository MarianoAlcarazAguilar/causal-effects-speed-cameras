"""Arranque del visor: python3 -m visor desde scripts/, o python3 scripts/visor desde la raíz."""
from __future__ import annotations

import sys
from pathlib import Path

# Con `python3 scripts/visor` Python ejecuta este archivo suelto: se agrega scripts/ al path
# para que `visor` sea importable igual que con `python3 -m visor`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import shutil
import threading
import webbrowser
from http.server import ThreadingHTTPServer

from visor.config import OUT  # noqa: E402
from visor.servidor import Handler  # noqa: E402
from visor.trabajos import enqueue, watcher, worker  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Visor local de la tesis: compila el LaTeX al guardar "
                                             "y compara contra versiones de git.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    for tool in ("tectonic", "latexdiff"):
        if not shutil.which(tool):
            print(f"Falta `{tool}`: brew install {tool}")
            return 1
    OUT.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=watcher, daemon=True).start()
    enqueue("actual")
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}"
    print(f"Visor en {url}  (Ctrl+C para salir)")
    if not a.no_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
