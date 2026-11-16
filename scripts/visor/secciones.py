"""Qué secciones del índice cambiaron entre dos versiones (los puntitos del índice)."""
from __future__ import annotations

import re

from .comentarios import CMD_RE, words
from .config import MAIN, SRC_NAME, WORKTREE
from .git_utils import diff_spec, file_at, git, src_name_at


# Para los puntitos del índice: cada bloque del diff de git se asigna al último título
# (\chapter, \section, ...) que lo precede en su archivo. La clave es el título en palabras
# minúsculas, que es como la interfaz empata contra los marcadores del PDF.

HEAD_START = re.compile(r"\\(?:chapter|section|subsection|subsubsection)\*?\s*")


def braced(s: str, i: int) -> tuple[str, int] | None:
    """Contenido de un argumento {...} o [...] que empieza en s[i], con llaves anidadas."""
    if i >= len(s) or s[i] not in "{[":
        return None
    close, depth = {"{": "}", "[": "]"}[s[i]], 0
    for j in range(i, len(s)):
        if s[j] == s[i]:
            depth += 1
        elif s[j] == close:
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
    return None


def heading_key(line: str) -> str | None:
    code = re.split(r"(?<!\\)%", line, maxsplit=1)[0]
    m = HEAD_START.search(code)
    if not m:
        return None
    i, short = m.end(), None
    opt = braced(code, i)
    if opt and code[i] == "[":
        short, i = opt[0], opt[1]
    arg = braced(code, i)
    if not arg:
        return None
    title = short if short is not None else arg[0]  # hyperref usa el título corto
    return " ".join(words(CMD_RE.sub(" ", title))) or None


def changed_sections(base: str, target: str) -> dict:
    spec, prefijo = diff_spec(base, target)
    out = git("diff", "-M", "-U0", "--no-color", *spec)
    if not prefijo:  # diff árbol contra árbol: las rutas no traen la carpeta de la tesis
        prefijo = (SRC_NAME if target == WORKTREE else src_name_at(target)) + "/"
    sections: dict[str, int] = {}
    outside, path, starts = 0, None, {}
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = None if line.endswith("/dev/null") else line[6:]
            if path and not path.startswith(prefijo):
                path = prefijo + path
            if path:
                starts.setdefault(path, [])
        elif line.startswith("@@") and path:
            m = re.search(r"\+(\d+)", line)
            starts[path].append(int(m.group(1)) if m else 1)
    for rel, hunks in starts.items():
        heads = [(i, k) for i, l in enumerate(file_at(target, rel)) if (k := heading_key(l))]
        for start in hunks:
            prev = [k for i, k in heads if i <= start - 1]
            # cambios antes del primer título del archivo (\label, etc.) van a ese primer título
            key = prev[-1] if prev else (heads[0][1] if heads and not rel.endswith("/" + MAIN) else None)
            if key:
                sections[key] = sections.get(key, 0) + 1
            else:
                outside += 1
    return {"sections": sections, "outside": outside}
