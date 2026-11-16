"""Visor local de la tesis: compila el LaTeX al guardar y compara contra versiones de git.

Uso (desde la raíz del repo):
    python3 scripts/visor                     # abre http://127.0.0.1:8765
    python3 scripts/visor --port 9000 --no-browser

Requiere `tectonic` y `latexdiff` (brew install tectonic latexdiff).

- "Actual": el PDF de lo que hay en disco ahora, recompilado cada vez que guardas un .tex.
- "Comparar": una versión de git (commit) contra lo que tienes ahora o contra otro commit, en
  tres vistas: PDF con los cambios marcados (latexdiff), los dos PDFs lado a lado y el diff
  del código fuente.

Las imágenes no están en git. Si `tesis/Imagenes/` no existe o le
faltan archivos, se compila con rellenos grises y una nota roja «Imagen pendiente» debajo. Todo lo que
genera vive en `.visor/` (ignorado por git); nunca escribe en las fuentes.
"""
