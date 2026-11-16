"""Comentarios del visor guardados en las fuentes como bloques de comentario LaTeX."""
from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
from pathlib import Path

from .config import SRC


# Se guardan en las fuentes como bloques de comentario LaTeX, arriba de la línea comentada:
#   % >>> COMENTARIO (2026-11-01 18:00) sobre «texto seleccionado»
#   % lo que escribiste
#   % <<<
# No cambian el PDF, quedan en git y se editan en cualquier editor.

COMMENT_START = "% >>> COMENTARIO"


COMMENT_END = "% <<<"


UNPLACED = "comentarios-sin-ubicar.tex"


CMD_RE = re.compile(r"\\[a-zA-Z@]+\*?")


WORD_RE = re.compile(r"\w+")


WRITE_LOCK = threading.Lock()


def words(text: str) -> list[str]:
    # NFKC deshace ligaduras del PDF (ﬁ → fi).
    return WORD_RE.findall(unicodedata.normalize("NFKC", text).lower())


def tex_files() -> list[Path]:
    return sorted(f for f in SRC.rglob("*.tex") if f.name != UNPLACED)


def locate(quote: str) -> tuple[Path, int] | None:
    """Encuentra la línea de las fuentes donde está el texto seleccionado en el PDF."""
    # Se buscan en la fuente los grupos de k palabras seguidas de la selección y gana el lugar
    # con la cadena coincidente más larga. Así un caption casi idéntico a otro pierde contra el
    # que coincide también en el número, y si la selección incluye texto borrado (rojo en el
    # diff) el resto igual apunta al lugar correcto.
    q = words(quote)
    n = len(q)
    if n < 2:
        return None
    k = min(4, n)
    grams: dict[tuple, list[int]] = {}
    for j in range(n - k + 1):
        grams.setdefault(tuple(q[j:j + k]), []).append(j)
    need = 1 if n - k + 1 <= 2 else 2  # con un solo grupo coincidente es casualidad
    best = None
    for f in tex_files():
        toks, lines = [], []
        for i, line in enumerate(f.read_text("utf-8", "replace").splitlines()):
            if line.lstrip().startswith("%"):
                continue
            code = re.split(r"(?<!\\)%", line, maxsplit=1)[0]
            for w in words(CMD_RE.sub(" ", code)):
                toks.append(w)
                lines.append(i)
        hits = [(p, j) for p in range(len(toks) - k + 1)
                for j in grams.get(tuple(toks[p:p + k]), ())]
        # Cadena más larga de grupos que avanzan a la vez en la selección (j) y en la fuente (p).
        # Se permite que la selección tenga hasta 40 palabras que la fuente no (texto borrado en
        # el diff) y que la fuente tenga hasta 8 que el PDF no (\label, \cite, opciones).
        score, start = [1] * len(hits), [p for p, _ in hits]
        for a, (p, j) in enumerate(hits):
            for b in range(a - 1, -1, -1):
                pb, jb = hits[b]
                if p - pb > 60:
                    break
                dp, dj = p - pb, j - jb
                if dp > 0 and dj > 0 and dp - dj <= 8 and dj - dp <= 40 and score[b] + 1 > score[a]:
                    score[a], start[a] = score[b] + 1, start[b]
            if best is None or score[a] > best[0]:
                best = (score[a], f, lines[start[a]])
    return (best[1], best[2]) if best and best[0] >= need else None


def add_comment(quote: str, text: str, page: str = "", view: str = "") -> dict:
    stamp = time.strftime("%Y-%m-%d %H:%M")
    qshort = " ".join(quote.split())
    qshort = qshort if len(qshort) <= 90 else qshort[:87] + "…"
    with WRITE_LOCK:
        hit = locate(quote)
        if hit:
            f, idx = hit
            head = f"{COMMENT_START} ({stamp}) sobre «{qshort}»"
        else:
            f, idx = SRC / UNPLACED, None
            if not f.exists():
                f.write_text("% Comentarios del visor cuyo texto no se encontró en las fuentes\n"
                             "% (por ejemplo, texto que ya borraste). Este archivo no se compila.\n\n",
                             "utf-8")
            head = f"{COMMENT_START} ({stamp}) página {page} de «{view}», sobre «{qshort}»"
        block = [head] + ["% " + l for l in text.strip().splitlines()] + [COMMENT_END]
        lines = f.read_text("utf-8").splitlines(keepends=True)
        if idx is None:
            idx = len(lines)
        if idx == len(lines) and lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines[idx:idx] = [b + "\n" for b in block]
        tmp = f.with_name(f.name + ".visor-tmp")
        tmp.write_text("".join(lines), "utf-8")
        os.replace(tmp, f)
    return {"file": str(f.relative_to(SRC)), "line": idx + 1, "located": bool(hit)}


def list_comments() -> list[dict]:
    out = []
    files = tex_files() + ([SRC / UNPLACED] if (SRC / UNPLACED).exists() else [])
    for f in files:
        lines = f.read_text("utf-8", "replace").splitlines()
        i = 0
        while i < len(lines):
            if lines[i].lstrip().startswith(COMMENT_START):
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith(COMMENT_END):
                    j += 1
                out.append({
                    "file": str(f.relative_to(SRC)), "line": i + 1,
                    "head": lines[i].strip()[len(COMMENT_START):].strip(),
                    "text": "\n".join(re.sub(r"^\s*%\s?", "", l) for l in lines[i + 1:j]),
                    "unplaced": f.name == UNPLACED,
                })
                i = j + 1
            else:
                i += 1
    return out


def safe_src_path(rel: str) -> Path:
    f = (SRC / rel).resolve()
    if SRC.resolve() not in f.parents or f.suffix != ".tex":
        raise ValueError("ruta fuera de la tesis")
    return f


def resolve_comment(rel: str, line: int, head: str) -> bool:
    """Borra el bloque. Verifica que siga en esa línea con el mismo encabezado."""
    f = safe_src_path(rel)
    with WRITE_LOCK:
        lines = f.read_text("utf-8").splitlines(keepends=True)
        i = line - 1
        if not (0 <= i < len(lines) and lines[i].strip() == f"{COMMENT_START} {head}".strip()):
            return False
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith(COMMENT_END):
            j += 1
        del lines[i:j + 1]
        tmp = f.with_name(f.name + ".visor-tmp")
        tmp.write_text("".join(lines), "utf-8")
        os.replace(tmp, f)
    return True
