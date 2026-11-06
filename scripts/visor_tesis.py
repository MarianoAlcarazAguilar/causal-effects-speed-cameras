#!/usr/bin/env python3
"""Visor local de la tesis: compila el LaTeX al guardar y compara contra versiones de git.

Uso (desde la raíz del repo):
    python3 scripts/visor_tesis.py            # abre http://127.0.0.1:8765
    python3 scripts/visor_tesis.py --port 9000 --no-browser

Requiere `tectonic` y `latexdiff` (brew install tectonic latexdiff).

- "Actual": el PDF de lo que hay en disco ahora, recompilado cada vez que guardas un .tex.
- "Comparar": una versión de git (commit) contra lo que tienes ahora o contra otro commit, en
  tres vistas: PDF con los cambios marcados (latexdiff), los dos PDFs lado a lado y el diff
  del código fuente.

Las imágenes no están en git. Si `causal-effects-speed-cameras/Imagenes/` no existe o le
faltan archivos, se compila con rellenos grises y una nota roja «Imagen pendiente» debajo. Todo lo que
genera vive en `.visor/` (ignorado por git); nunca escribe en las fuentes.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io

import json
import os
import re
import shutil
import struct
import subprocess
import tarfile
import threading
import time
import unicodedata
import webbrowser
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parent.parent
SRC_NAME = "causal-effects-speed-cameras"
SRC = REPO / SRC_NAME
MAIN = "main.tex"
WORK = REPO / ".visor"
OUT = WORK / "out"
WORKTREE = "WORKTREE"

WATCH_EXT = {".tex", ".bib", ".sty", ".cls", ".bst", ".png", ".jpg", ".jpeg", ".pdf"}
SKIP_COPY = {".aux", ".log", ".toc", ".lof", ".lot", ".out", ".fls", ".synctex.gz",
             ".fdb_latexmk", ".xdv", ".bbl", ".blg", ".bcf", ".nav", ".snm"}


# --------------------------------------------------------------------------- utilidades

def git(*args: str, binary: bool = False):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def resolve(ref: str) -> str:
    return ref if ref == WORKTREE else git("rev-parse", ref).strip()


def placeholder_png(w: int = 400, h: int = 300) -> bytes:
    raw = b"".join(b"\x00" + b"\xdd\xdd\xdd" * w for _ in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


IMG_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")


def fill_missing_images(d: Path) -> list[str]:
    """Crea rellenos para imágenes referenciadas que no existen. Devuelve las faltantes."""
    missing = []
    for tex in d.rglob("*.tex"):
        for raw in IMG_RE.findall(tex.read_text("utf-8", "replace")):
            name = raw.strip()
            cands = [name] if Path(name).suffix else [name + e for e in (".png", ".pdf", ".jpg")]
            # \graphicspath{{Imagenes/}}: se busca relativo a la raíz y dentro de Imagenes/.
            if any((d / c).exists() or (d / "Imagenes" / c).exists() for c in cands):
                continue
            missing.append(name)
            target = d / (name if Path(name).suffix else name + ".png")
            if Path(name).suffix.lower() not in ("", ".png"):
                target = target.with_suffix(".png")  # graphicx probará la extensión .png
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(placeholder_png())
    if missing:
        # Solo en la copia que se compila: una nota bajo cada recuadro gris.
        miss = set(missing)

        def note(m: re.Match) -> str:
            if m.group(1).strip() not in miss:
                return m.group(0)
            return (m.group(0) + "\\par{\\footnotesize\\color{red}Imagen pendiente: "
                    "{\\ttfamily\\detokenize{" + m.group(1).strip() + "}}}\\par")

        for tex in d.rglob("*.tex"):
            text = tex.read_text("utf-8", "replace")
            new = IMG_RE.sub(note, text)
            if new != text:
                tex.write_text(new, "utf-8")
    return sorted(set(missing))


def materialize(ref: str, dest: Path) -> list[str]:
    """Deja en `dest` las fuentes de la tesis en `ref` (o del disco). Devuelve imágenes faltantes."""
    if dest.exists():
        shutil.rmtree(dest)
    if ref == WORKTREE:
        shutil.copytree(SRC, dest, ignore=lambda _d, names: [
            n for n in names if any(n.endswith(e) for e in SKIP_COPY) or n in ("main.pdf", "Icon\r")])
    else:
        data = git("archive", "--format=tar", ref, SRC_NAME, binary=True)
        tmp = dest.with_name(dest.name + ".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(tmp)
        shutil.move(str(tmp / SRC_NAME), dest)
        shutil.rmtree(tmp)
        # Las imágenes no están versionadas: se usan las del disco.
        if (SRC / "Imagenes").is_dir():
            shutil.copytree(SRC / "Imagenes", dest / "Imagenes", dirs_exist_ok=True)
    return fill_missing_images(dest)


INC_RE = re.compile(r"\\(include|input)\s*\{([^}]+)\}")


def flatten(d: Path, rel: str = MAIN, depth: int = 0) -> str:
    """Expande \\include/\\input. No se usa `latexdiff --flatten` porque con nombres como
    `Chapters/1.Rev` toma `.Rev` por extensión y deja el capítulo fuera del diff en silencio."""
    text = (d / rel).read_text("utf-8", "replace")
    if depth > 10:
        return text
    out = []
    for line in text.splitlines(keepends=True):
        code = re.split(r"(?<!\\)%", line, maxsplit=1)[0]
        m = INC_RE.search(code)
        if not m:
            out.append(line)
            continue
        name = m.group(2).strip()
        f = next((c for c in (name + ".tex", name) if (d / c).is_file()), None)
        if f is None:
            out.append(line)
            continue
        body = flatten(d, f, depth + 1)
        if m.group(1) == "include":
            body = "\\clearpage\n" + body + "\n\\clearpage\n"
        out.append(code[:m.start()] + body + code[m.end():] + ("\n" if line.endswith("\n") else ""))
    return "".join(out)


def tex_error(output: str) -> str:
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("!"):
            # El último archivo abierto antes del error suele ser donde está.
            before = "\n".join(lines[:i])
            files = re.findall(r"\(((?:\./)?[\w./-]+\.tex)", before)
            where = f"Archivo probable: {files[-1]}\n" if files else ""
            return where + "\n".join(lines[i:i + 8])
    errs = [l for l in lines if l.startswith("error")]
    return "\n".join(errs) or output[-2000:]


def compile_tex(d: Path, tex: str) -> tuple[bool, str]:
    try:
        r = subprocess.run(["tectonic", "-X", "compile", tex], cwd=d,
                           capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return False, "tectonic tardó más de 10 minutos."
    if r.returncode != 0:
        return False, tex_error(r.stdout + "\n" + r.stderr)
    return True, ""


# --------------------------------------------------------------------------- estado y trabajos

LOCK = threading.Lock()
COND = threading.Condition(LOCK)
QUEUE: list[tuple] = []


def blank(**kw):
    return {"v": 0, "ok": None, "building": False, "error": "", "missing": [], "took": 0, **kw}


STATE = {
    "actual": blank(),
    "compare": {"base": None, "target": WORKTREE, "diff": blank(), "base_pdf": blank(),
                "target_pdf": blank(), "diff_mode": ""},
}


def enqueue(*job):
    with COND:
        if job not in QUEUE:
            QUEUE.append(job)
            COND.notify()


def run_step(slot: dict, fn):
    with LOCK:
        slot["building"] = True
    t0 = time.time()
    try:
        ok, err, missing = fn()
    except Exception as e:  # noqa: BLE001 - se muestra en la UI
        ok, err, missing = False, f"{type(e).__name__}: {e}", []
    with LOCK:
        slot.update(building=False, ok=ok, error=err, missing=missing,
                    took=round(time.time() - t0, 1), v=slot["v"] + 1)


def job_actual():
    def fn():
        d = WORK / "build" / "actual"
        missing = materialize(WORKTREE, d)
        ok, err = compile_tex(d, MAIN)
        if ok:
            shutil.copy(d / "main.pdf", OUT / "actual.pdf")
        return ok, err, missing
    run_step(STATE["actual"], fn)


def build_signature() -> str:
    """El PDF de un commit depende también de las imágenes del disco y de cómo compila el visor."""
    parts = [hashlib.sha1(Path(__file__).read_bytes()).hexdigest()]
    img = SRC / "Imagenes"
    if img.is_dir():
        for p in sorted(img.rglob("*")):
            if p.is_file():
                st = p.stat()
                parts.append(f"{p.relative_to(img)}:{st.st_size}:{st.st_mtime_ns}")
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()


def job_ref(sha: str, slot_name: str):
    slot = STATE["compare"][slot_name]

    def fn():
        pdf, sig_file = OUT / f"ref-{sha}.pdf", OUT / f"ref-{sha}.sig"
        sig = build_signature()
        if pdf.exists() and sig_file.exists() and sig_file.read_text() == sig:
            return True, "", []
        d = WORK / "build" / f"ref-{sha[:12]}"
        missing = materialize(sha, d)
        ok, err = compile_tex(d, MAIN)
        if ok:
            shutil.copy(d / "main.pdf", pdf)
            sig_file.write_text(sig)
        shutil.rmtree(d, ignore_errors=True)
        return ok, err, missing
    run_step(slot, fn)


def job_diff(base: str, target: str):
    def fn():
        old, new = WORK / "build" / "diff-old", WORK / "build" / "diff-new"
        materialize(base, old)
        missing = materialize(target, new)
        (old / "flat.tex").write_text(flatten(old), "utf-8")
        (new / "flat.tex").write_text(flatten(new), "utf-8")
        attempts = [("completo", []),
                    ("conservador (sin marcar matemáticas ni figuras)",
                     ["--math-markup=off", "--graphics-markup=none"]),
                    # Tablas reestructuradas (\multicolumn, \cmidrule) y \textbf que cruzan
                    # párrafos rompen la marca fina: se comparan como bloque entero.
                    ("por bloques (tablas y negritas completas)",
                     ["--math-markup=off", "--graphics-markup=none",
                      "--exclude-textcmd=textbf,textit,texttt,emph,textsc",
                      "--config=PICTUREENV=(?:picture|DIFnomarkup|table|tabular|tabularx"
                      "|longtable|adjustbox)[\\w\\d*@]*"])]
        err = ""
        for mode, extra in attempts:
            r = subprocess.run(["latexdiff", *extra, str(old / "flat.tex"), str(new / "flat.tex")],
                               cwd=new, capture_output=True, text=True)
            if r.returncode != 0:
                err = r.stderr[-2000:]
                continue
            (new / "diff.tex").write_text(r.stdout, "utf-8")
            ok, err = compile_tex(new, "diff.tex")
            if ok:
                shutil.copy(new / "diff.pdf", OUT / "diff.pdf")
                with LOCK:
                    STATE["compare"]["diff_mode"] = mode
                return True, "", missing
        return False, ("latexdiff no logró un PDF compilable. Usa la vista «Fuente» o "
                       "«Lado a lado».\n\n" + err), missing
    run_step(STATE["compare"]["diff"], fn)


def worker():
    while True:
        with COND:
            while not QUEUE:
                COND.wait()
            job = QUEUE.pop(0)
        kind = job[0]
        if kind == "actual":
            job_actual()
        elif kind == "ref":
            job_ref(job[1], job[2])
        elif kind == "diff":
            with LOCK:
                cur = (STATE["compare"]["base"], STATE["compare"]["target"])
            if cur == (job[1], job[2]):  # descarta comparaciones que ya no se piden
                job_diff(job[1], job[2])


def signature() -> tuple:
    sig = []
    for p in SRC.rglob("*"):
        if p.is_file() and p.suffix.lower() in WATCH_EXT and p.name != "main.pdf":
            st = p.stat()
            sig.append((str(p), st.st_mtime_ns, st.st_size))
    return tuple(sorted(sig))


def watcher():
    last = signature()
    while True:
        time.sleep(0.8)
        try:
            cur = signature()
        except FileNotFoundError:
            continue  # un editor guardando con archivo temporal
        if cur != last:
            time.sleep(0.4)  # deja que el editor termine de escribir
            last = signature()
            enqueue("actual")
            with LOCK:
                base, target = STATE["compare"]["base"], STATE["compare"]["target"]
            if base and target == WORKTREE:
                enqueue("diff", base, target)


# --------------------------------------------------------------------------- git: versiones y diff

def list_refs() -> dict:
    fmt = "@@%H%x09%h%x09%ad%x09%s"
    log = git("log", f"--format={fmt}", "--date=format:%Y-%m-%dT%H:%M", "--shortstat",
              "-n", "80", "HEAD", "--", SRC_NAME)
    refs = []
    for l in log.splitlines():
        if l.startswith("@@"):
            refs.append(dict(zip(("sha", "short", "date", "subject"), l[2:].split("\t", 3)),
                             files=0))
        elif refs and "changed" in l:
            m = re.search(r"(\d+) files? changed", l)
            refs[-1]["files"] = int(m.group(1)) if m else 0
    dirty = [l[3:] for l in git("status", "--porcelain", "--", SRC_NAME).splitlines()]
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    return {"refs": refs, "dirty": dirty, "branch": branch, "head": resolve("HEAD")}


def source_diff(base: str, target: str) -> str:
    args = ["diff", "--no-color", "--word-diff=porcelain", "-U2", base]
    if target != WORKTREE:
        args.append(target)
    out = git(*args, "--", SRC_NAME)
    if not out.strip():
        return '<p class="empty">Sin diferencias en las fuentes.</p>'
    parts, row, file_open = [], [], False

    def flush():
        if row:
            parts.append('<div class="ln">' + "".join(row) + "</div>")
            row.clear()

    for line in out.splitlines():
        if line.startswith("diff --git"):
            flush()
            if file_open:
                parts.append("</section>")
            name = line.split(" b/", 1)[-1].removeprefix(SRC_NAME + "/")
            parts.append(f'<section class="file"><h3>{html.escape(name)}</h3>')
            file_open = True
        elif line.startswith(("index ", "--- ", "+++ ", "new file", "deleted file", "similarity")):
            continue
        elif line.startswith("@@"):
            flush()
            m = re.search(r"\+(\d+)", line)
            parts.append(f'<div class="hunk">línea {m.group(1) if m else "?"}</div>')
        elif line.startswith("~"):
            flush()
        elif line[:1] in (" ", "-", "+"):
            cls = {" ": "c", "-": "del", "+": "add"}[line[0]]
            row.append(f'<span class="{cls}">{html.escape(line[1:])}</span>')
    flush()
    if file_open:
        parts.append("</section>")
    untracked = [l[3:] for l in git("status", "--porcelain", "--", SRC_NAME).splitlines()
                 if l.startswith("??")]
    if untracked and target == WORKTREE:
        parts.insert(0, '<p class="warn">Archivos nuevos sin <code>git add</code> (no salen en este '
                     "diff): " + ", ".join(html.escape(u) for u in untracked) + "</p>")
    return "".join(parts)


# --------------------------------------------------------------------------- cambios por sección
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


def file_at(ref: str, rel: str) -> list[str]:
    if ref == WORKTREE:
        p = REPO / rel
        return p.read_text("utf-8", "replace").splitlines() if p.exists() else []
    try:
        return git("show", f"{ref}:{rel}").splitlines()
    except subprocess.CalledProcessError:
        return []


def changed_sections(base: str, target: str) -> dict:
    args = ["diff", "-U0", "--no-color", base] + ([target] if target != WORKTREE else [])
    out = git(*args, "--", SRC_NAME)
    sections: dict[str, int] = {}
    outside, path, starts = 0, None, {}
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = None if line.endswith("/dev/null") else line[6:]
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
            key = prev[-1] if prev else (heads[0][1] if heads and rel != f"{SRC_NAME}/{MAIN}" else None)
            if key:
                sections[key] = sections.get(key, 0) + 1
            else:
                outside += 1
    return {"sections": sections, "outside": outside}


# --------------------------------------------------------------------------- comentarios
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


# --------------------------------------------------------------------------- servidor

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silencio
        pass

    def send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json(self, obj, code: int = 200):
        self.send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/":
                self.send(200, PAGE.encode(), "text/html; charset=utf-8")
            elif u.path == "/api/status":
                with LOCK:
                    self.json(json.loads(json.dumps(STATE)))
            elif u.path == "/api/refs":
                self.json(list_refs())
            elif u.path == "/api/comments":
                self.json(list_comments())
            elif u.path == "/api/changes":
                self.json(changed_sections(resolve(q.get("base", "HEAD")),
                                           resolve(q.get("target", WORKTREE))))
            elif u.path == "/api/source-diff":
                self.send(200, source_diff(resolve(q["base"]), resolve(q.get("target", WORKTREE)))
                          .encode(), "text/html; charset=utf-8")
            elif u.path.startswith("/pdf/"):
                name = Path(u.path).name
                f = OUT / name
                if not re.fullmatch(r"[\w.-]+\.pdf", name) or not f.exists():
                    return self.send(404, b"no existe", "text/plain")
                self.send(200, f.read_bytes(), "application/pdf")
            else:
                self.send(404, b"", "text/plain")
        except subprocess.CalledProcessError as e:
            self.json({"error": e.stderr.decode("utf-8", "replace")}, 400)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        try:
            if u.path == "/api/build":
                enqueue("actual")
                self.json({"ok": True})
            elif u.path == "/api/compare":
                base, target = resolve(body["base"]), resolve(body.get("target", WORKTREE))
                with LOCK:
                    c = STATE["compare"]
                    same = (c["base"], c["target"]) == (base, target) and c["diff"]["ok"] is not None
                if same:  # ya está lista o compilándose; el watcher la actualiza al guardar
                    return self.json({"base": base, "target": target})
                with LOCK:
                    c["base"], c["target"] = base, target
                    # que la interfaz no muestre el PDF de la comparación anterior mientras compila
                    for slot in ("diff", "base_pdf", "target_pdf"):
                        c[slot].update(ok=None, error="")
                enqueue("ref", base, "base_pdf")
                if target != WORKTREE:
                    enqueue("ref", target, "target_pdf")
                enqueue("diff", base, target)
                self.json({"base": base, "target": target})
            elif u.path == "/api/comments":
                if not body.get("text", "").strip() or not body.get("quote", "").strip():
                    return self.json({"error": "falta el texto"}, 400)
                self.json(add_comment(body["quote"], body["text"], str(body.get("page", "")),
                                      body.get("view", "")))
            elif u.path == "/api/comments/resolve":
                ok = resolve_comment(body["file"], int(body["line"]), body["head"])
                self.json({"ok": ok, "error": "" if ok else
                           "El comentario se movió o cambió en el archivo; resuélvelo a mano."})
            elif u.path == "/api/open":
                f = safe_src_path(body["file"])
                editor = shutil.which("cursor") or shutil.which("code")
                if editor:
                    subprocess.Popen([editor, "-g", f"{f}:{int(body['line'])}"])
                else:
                    subprocess.Popen(["open", "-t", str(f)])
                self.json({"ok": True})
            else:
                self.send(404, b"", "text/plain")
        except subprocess.CalledProcessError as e:
            self.json({"error": e.stderr.decode("utf-8", "replace")}, 400)
        except (ValueError, KeyError) as e:
            self.json({"error": str(e)}, 400)


PAGE = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Visor de tesis</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<style>
:root{--bg:#eceef1;--panel:#fff;--ink:#1d2330;--mute:#677085;--line:#d9dde4;--acc:#2f5bd3;
--ok:#1f8a4c;--bad:#c23a32;--warn:#9a6a00;--add:#e3f3e6;--addi:#17602f;--del:#fbe4e2;--deli:#9b2a22}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,system-ui,sans-serif;display:flex;flex-direction:column}
header{display:flex;gap:12px;align-items:center;padding:8px 14px;background:var(--panel);border-bottom:1px solid var(--line);flex-wrap:wrap}
header h1{font-size:15px;margin:0 8px 0 0}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:7px;overflow:hidden}
.seg button{border:0;background:none;padding:5px 11px;cursor:pointer;color:var(--mute);font:inherit}
.seg button.on{background:var(--acc);color:#fff}
.b{border:1px solid var(--line);background:var(--panel);border-radius:6px;padding:4px 10px;cursor:pointer;font:inherit;color:var(--ink);text-decoration:none;display:inline-block;line-height:normal}
.b:hover{background:#f1f3f7}
select{font:inherit;padding:4px;border-radius:6px;border:1px solid var(--line);max-width:330px}
.pill{font-size:12px;padding:2px 9px;border-radius:99px;background:#eef0f4;color:var(--mute)}
.pill.ok{background:#e1f2e8;color:var(--ok)}.pill.bad{background:#f8e0de;color:var(--bad)}.pill.run{background:#e3eafc;color:var(--acc)}
.sp{flex:1}a{color:var(--acc)}
#bar2{display:none;gap:10px;align-items:center;padding:7px 14px;background:#f6f7f9;border-bottom:1px solid var(--line);flex-wrap:wrap}
.msg{margin:0;padding:8px 14px;font-size:13px;white-space:pre-wrap;border-bottom:1px solid var(--line)}
.msg.err{background:#fdf0ef;color:var(--bad);font-family:ui-monospace,Menlo,monospace;max-height:30vh;overflow:auto}
.msg.warn{background:#fff8e6;color:var(--warn)}
main{flex:1;display:flex;min-height:0}
.pane{flex:1;display:flex;flex-direction:column;min-width:0;border-right:1px solid var(--line)}
.pane:last-child{border-right:0}
.pane h2{margin:0;font-size:12px;font-weight:600;color:var(--mute);padding:5px 12px;background:#f6f7f9;border-bottom:1px solid var(--line)}
.scroll{flex:1;overflow:auto;padding:14px 0;position:relative}
#wrap{flex:1;display:flex;min-height:0}
#toc{width:270px;flex:none;background:var(--panel);border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0}
body.notoc #toc{display:none}
.stabs{margin:8px 10px;display:flex}.stabs button{flex:1}
#verl{flex:1;overflow:auto;padding:4px 0 10px}
#verl .hint{font-size:11.5px;color:var(--mute);padding:4px 14px 8px;line-height:1.35}
.ver{display:grid;grid-template-columns:18px 1fr;gap:0 6px;padding:8px 12px;cursor:pointer;border-left:3px solid transparent}
.ver:hover{background:#f1f3f7}
.ver .dot{grid-row:span 3;width:11px;height:11px;border-radius:50%;border:2px solid #aab2c2;margin-top:3px;background:#fff}
.ver .d{font-weight:600;font-size:13px}
.ver .s{font-size:12.5px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ver .m{font-size:11.5px;color:var(--mute)}
.ver .tag{font-size:10.5px;font-weight:600;border-radius:4px;padding:0 5px;margin-left:5px;vertical-align:1px}
.ver.now .dot{border-color:var(--ok)}
.ver.base{border-left-color:#c23a32;background:#fdf3f2}.ver.base .dot{background:#c23a32;border-color:#c23a32}
.ver.base .tag{background:#f8e0de;color:#c23a32}
.ver.tgt{border-left-color:var(--acc);background:#eef2fc}.ver.tgt .dot{background:var(--acc);border-color:var(--acc)}
.ver.tgt .tag{background:#e3eafc;color:var(--acc)}
#cmptitle{font-size:14px}
#tocl{flex:1;overflow:auto;padding:6px 0}
#tocl a{display:block;padding:3px 12px;cursor:pointer;color:var(--ink);text-decoration:none;font-size:13px;line-height:1.3;border-left:3px solid transparent;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#tocl a:hover{background:#f1f3f7}
#tocl a.l0{font-weight:600;margin-top:6px}
#tocl a.l1{padding-left:24px}
#tocl a.l2,#tocl a.l3{padding-left:38px;font-size:12px;color:var(--mute)}
#tocl a.on{border-left-color:var(--acc);background:#e9eefb;color:var(--acc)}
#tocl a{display:flex;align-items:center;gap:6px}
#tocl a .tt{flex:1;overflow:hidden;text-overflow:ellipsis}
#tocl .chg{flex:none;font-size:10.5px;font-weight:600;color:#c46a00;display:inline-flex;align-items:center;gap:3px}
#tocl .chg::before{content:"";width:8px;height:8px;border-radius:50%;background:#e8890c}
#tocl .chg.sub{color:#b8a07a}#tocl .chg.sub::before{background:none;border:1.5px solid #e8a33c;width:6px;height:6px}
#tocl .chgleg{font-size:11.5px;color:var(--mute);padding:2px 12px 6px;display:flex;align-items:center;gap:5px}
#tocl .chgleg::before{content:"";width:8px;height:8px;border-radius:50%;background:#e8890c;flex:none}
.page{margin:0 auto 14px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.15);position:relative}
.page canvas{display:block;width:100%;height:100%}
.page .n{position:absolute;right:-34px;top:0;font-size:11px;color:var(--mute);user-select:none}
.hl{position:absolute;z-index:1;pointer-events:none;border-radius:2px}
body.nohl .hl{display:none}
.hl.del{background:rgba(214,48,39,.22)}.hl.add{background:rgba(47,91,211,.22)}
.hl.cur.del{background:rgba(214,48,39,.45);box-shadow:0 0 0 2px rgba(214,48,39,.7)}
.hl.cur.add{background:rgba(47,91,211,.42);box-shadow:0 0 0 2px rgba(47,91,211,.7)}
#nav{display:inline-flex;align-items:center;gap:4px;font-size:13px}
#navc{min-width:64px;text-align:center;color:var(--mute)}
.empty{color:var(--mute);text-align:center;padding:40px}
#src{flex:1;overflow:auto;padding:16px 24px;background:var(--panel)}
.file h3{font-size:14px;margin:18px 0 6px;padding-bottom:4px;border-bottom:1px solid var(--line)}
.hunk{font-size:11px;color:var(--mute);margin:10px 0 2px}
.ln{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;white-space:pre-wrap;word-break:break-word;padding:1px 0}
.del{background:var(--del);color:var(--deli);text-decoration:line-through}.add{background:var(--add);color:var(--addi)}
.warn{color:var(--warn)}
.legend{font-size:12px;color:var(--mute)}.legend b{font-weight:500}
.textLayer{position:absolute;inset:0;overflow:hidden;line-height:1;text-size-adjust:none;-webkit-text-size-adjust:none;forced-color-adjust:none;transform-origin:0 0;z-index:2}
.textLayer span,.textLayer br{color:transparent;position:absolute;white-space:pre;cursor:text;transform-origin:0 0}
.textLayer ::selection{background:rgba(47,91,211,.28)}
.textLayer br::selection{background:transparent}
.textLayer span.markedContent{top:0;height:0}
.textLayer .endOfContent{display:block;position:absolute;inset:100% 0 0;z-index:-1;cursor:default;user-select:none}
.textLayer .endOfContent.active{top:0}
#cbtn{position:fixed;display:none;z-index:20;background:var(--acc);color:#fff;border:0;border-radius:6px;padding:5px 10px;font:inherit;font-size:13px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.25)}
#cmodal{position:fixed;inset:0;background:rgba(20,25,35,.35);display:none;align-items:center;justify-content:center;z-index:30}
#cmodal .box{background:var(--panel);border-radius:10px;padding:16px;width:min(560px,92vw);box-shadow:0 10px 40px rgba(0,0,0,.3)}
#cmodal blockquote{margin:0 0 10px;padding:6px 10px;border-left:3px solid var(--acc);background:#f4f6fb;color:var(--mute);font-size:13px;max-height:120px;overflow:auto}
#cmodal textarea{width:100%;min-height:110px;font:inherit;padding:8px;border:1px solid var(--line);border-radius:6px;resize:vertical}
#cmodal .row{display:flex;gap:8px;justify-content:flex-end;align-items:center;margin-top:10px}
#cmodal .row .legend{flex:1}
button.p{background:var(--acc);color:#fff;border:0;border-radius:6px;padding:6px 14px;cursor:pointer;font:inherit}
#cpanel{position:fixed;right:0;top:0;bottom:0;width:360px;background:var(--panel);border-left:1px solid var(--line);box-shadow:-4px 0 18px rgba(0,0,0,.08);z-index:15;display:none;flex-direction:column}
#cpanel header{justify-content:space-between}
body.cp #wrap,body.cp #bar2,body.cp>header{margin-right:360px}
#clist{flex:1;overflow:auto;padding:8px 12px}
.cm{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:8px}
.cm .loc{font-size:12px;color:var(--acc);cursor:pointer;background:none;border:0;padding:0;font-family:ui-monospace,Menlo,monospace}
.cm .q{font-size:12px;color:var(--mute);margin:3px 0}
.cm .t{white-space:pre-wrap;margin:4px 0}
.cm .acts{display:flex;gap:6px;justify-content:flex-end}
.cm.un{border-color:#e8c46a;background:#fffaf0}
#toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);background:#1d2330;color:#fff;padding:8px 14px;border-radius:8px;font-size:13px;display:none;z-index:40}
</style></head><body>
<header>
  <h1>Tesis</h1>
  <span class="pill" id="pill">…</span><span class="legend" id="took"></span>
  <span class="sp"></span>
  <button class="b" id="tocbtn" title="Mostrar u ocultar el panel de índice y versiones">☰ Panel</button>
  <button class="b" id="zout" title="Alejar">−</button><button class="b" id="zin" title="Acercar">+</button>
  <button class="b" id="cpanelbtn" title="Selecciona texto en el PDF para comentar">Comentarios (0)</button>
  <button class="b" id="rebuild">Recompilar</button>
  <a class="b" id="open" href="/pdf/actual.pdf" target="_blank" title="Abrir el PDF en una pestaña nueva">Abrir PDF ↗</a>
</header>
<div id="bar2">
  <b id="cmptitle"></b>
  <div class="seg" id="views"><button data-v="marcado" class="on">Marcado</button><button data-v="lado">Lado a lado</button><button data-v="fuente">Código</button></div>
  <span id="nav"><button class="b" id="navp" title="Cambio anterior (tecla k)">◀</button><span id="navc">…</span><button class="b" id="navn" title="Cambio siguiente (tecla j)">▶</button></span>
  <label class="legend" id="hllbl" title="Tecla c"><input type="checkbox" id="hlon" checked> colores</label>
  <label class="legend" id="synclbl"><input type="checkbox" id="sync" checked> scroll sincronizado</label>
  <span class="legend" id="leg"><b style="color:#00f">azul</b> = agregado · <b style="color:red">rojo tachado</b> = borrado</span>
  <span class="sp"></span><button class="b" id="back">✕ Volver a Ahora</button>
</div>
<pre class="msg err" id="err" hidden></pre>
<div id="wrap"><nav id="toc">
  <div class="seg stabs"><button data-s="toc" class="on">Índice</button><button data-s="ver">Versiones</button></div>
  <div id="tocl"></div>
  <div id="verl" hidden></div>
</nav><main id="main"></main></div>
<button id="cbtn">💬 Comentar</button>
<div id="cmodal"><div class="box">
  <blockquote id="cquote"></blockquote>
  <textarea id="ctext" placeholder="Tu comentario…"></textarea>
  <div class="row"><span class="legend">Se guarda como comentario LaTeX arriba de ese texto · ⌘↵ guarda</span>
    <button class="b" id="ccancel">Cancelar</button><button class="p" id="csave">Guardar</button></div>
</div></div>
<aside id="cpanel"><header><b>Comentarios</b><button class="b" id="cclose">Cerrar</button></header><div id="clist"></div></aside>
<div id="toast"></div>
<script>
pdfjsLib.GlobalWorkerOptions.workerSrc="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
let scale=+(localStorage.getItem('zoom')||1.4);
const $=s=>document.querySelector(s);

class Viewer{
  constructor(title){
    this.el=document.createElement('div');this.el.className='pane';
    this.el.innerHTML=`<h2>${title}</h2><div class="scroll"><p class="empty">Compilando…</p></div>`;
    this.sc=this.el.querySelector('.scroll');this.url=null;this.doc=null;this.token=0;
    this.io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)this.render(e.target)}),{root:this.sc,rootMargin:'800px'});
  }
  async load(url){
    if(!url){this.sc.innerHTML='<p class="empty">Compilando…</p>';this.url=null;return}
    if(url===this.url)return; this.url=url; const tok=++this.token;
    let doc; try{doc=await pdfjsLib.getDocument({url,isEvalSupported:false}).promise}catch(e){return}
    if(tok!==this.token)return;
    this.doc=doc; await this.layout(tok);
    const ol=await outlineOf(doc); if(tok!==this.token)return;
    this.outline=ol; if(this===tocViewer())renderToc(); computeLado();
  }
  async layout(tok=++this.token){
    const doc=this.doc; if(!doc)return;
    const p1=await doc.getPage(1); const vp=p1.getViewport({scale}); this.ptH=p1.view[3]-p1.view[1];
    const box=document.createElement('div'); const pages=[];
    for(let i=1;i<=doc.numPages;i++){const d=document.createElement('div');d.className='page';d.dataset.i=i;
      d.style.width=vp.width+'px';d.style.height=vp.height+'px';d.innerHTML=`<span class="n">${i}</span>`;box.appendChild(d);pages.push(d)}
    // pinta antes de cambiar lo que está a la vista, para que no parpadee
    const top=this.sc.scrollTop, h=this.sc.clientHeight, ph=vp.height+14;
    const first=Math.max(0,Math.floor(top/ph)-1), last=Math.min(pages.length-1,Math.ceil((top+h)/ph)+1);
    for(let i=first;i<=last;i++) await this.render(pages[i],tok);
    if(tok!==this.token)return;
    this.io.disconnect(); this.sc.replaceChildren(box); this.sc.scrollTop=top;
    pages.forEach(p=>this.io.observe(p));
  }
  async render(div,tok=this.token){
    if(div.dataset.done||!this.doc)return; div.dataset.done=1;
    const page=await this.doc.getPage(+div.dataset.i); const vp=page.getViewport({scale});
    const dpr=window.devicePixelRatio||1; const c=document.createElement('canvas');
    c.width=Math.floor(vp.width*dpr);c.height=Math.floor(vp.height*dpr);
    await page.render({canvasContext:c.getContext('2d'),viewport:vp,transform:dpr!==1?[dpr,0,0,dpr,0,0]:null}).promise;
    if(!(tok===this.token||!div.isConnected))return;
    div.prepend(c);
    const tl=document.createElement('div');tl.className='textLayer';tl.style.setProperty('--scale-factor',scale);div.appendChild(tl);
    page.getTextContent().then(tc=>pdfjsLib.renderTextLayer({textContentSource:tc,container:tl,viewport:vp,textDivs:[]}).promise)
      .then(()=>bindTextLayer(tl)).catch(()=>{});
    this.drawMarks(div);
  }
}

// ---------- selección de texto
// Puerto del TextLayerBuilder de pdf.js 3.11: un div «endOfContent» detrás del texto que se mueve
// junto al punto donde va la selección. Sin él, al pasar el cursor por el hueco entre renglones el
// navegador estira la selección hasta el final de la página y parpadea.
const textLayers=new Map();
function resetEnd(end,tl){tl.append(end);end.style.width='';end.style.height='';end.classList.remove('active')}
function bindTextLayer(tl){
  const end=document.createElement('div');end.className='endOfContent';tl.append(end);textLayers.set(tl,end);
  tl.addEventListener('mousedown',()=>end.classList.add('active'));
}
(()=>{let down=false, prev=null;
  const resetAll=()=>{for(const [tl,end] of textLayers){if(!tl.isConnected)textLayers.delete(tl);else resetEnd(end,tl)}};
  document.addEventListener('pointerdown',()=>{down=true});
  document.addEventListener('pointerup',()=>{down=false;resetAll()});
  window.addEventListener('blur',()=>{down=false;resetAll()});
  document.addEventListener('keyup',()=>{if(!down)resetAll()});
  document.addEventListener('selectionchange',()=>{
    const sel=document.getSelection(); if(!sel.rangeCount){resetAll();return}
    const range=sel.getRangeAt(0);
    for(const [tl,end] of textLayers){if(!tl.isConnected){textLayers.delete(tl);continue}
      if(range.intersectsNode(tl))end.classList.add('active');else resetEnd(end,tl)}
    const modStart=prev&&(range.compareBoundaryPoints(Range.END_TO_END,prev)===0||range.compareBoundaryPoints(Range.START_TO_END,prev)===0);
    let a=modStart?range.startContainer:range.endContainer; if(a.nodeType===3)a=a.parentNode;
    const tl=a.parentElement?.closest('.textLayer'), end=tl&&textLayers.get(tl);
    if(end&&a.parentElement){end.style.width=tl.style.width;end.style.height=tl.style.height;
      a.parentElement.insertBefore(end,modStart?a:a.nextSibling)}
    prev=range.cloneRange();
  });
})();
// En huecos y márgenes el navegador no sabe a qué texto apunta el cursor: se lleva la selección al
// punto más cercano del renglón que está a esa altura (como en Preview).
function caretNear(tl,x,y){
  let best=null, bd=1e9;
  for(const sp of tl.querySelectorAll('span')){const t=sp.firstChild; if(!t||t.nodeType!==3||!t.length)continue;
    const r=sp.getBoundingClientRect(); if(!r.width)continue;
    const dy=y<r.top?r.top-y:y>r.bottom?y-r.bottom:0, dx=x<r.left?r.left-x:x>r.right?x-r.right:0, d=dy*1000+dx;
    if(d<bd){bd=d;best={sp,t,r}}}
  if(!best)return null; const {t,r}=best;
  if(x<=r.left)return {node:t,off:0}; if(x>=r.right)return {node:t,off:t.length};
  const c=document.caretRangeFromPoint?.(x,(r.top+r.bottom)/2);
  if(c&&c.startContainer===t)return {node:t,off:c.startOffset};
  return {node:t,off:Math.round(t.length*(x-r.left)/r.width)};
}
const layerAt=(x,y)=>{const pg=document.elementsFromPoint(x,y).find(e=>e.classList?.contains('page'));return pg?.querySelector('.textLayer')};
let selDrag=null;
// El arrastre lo maneja el visor completo (si el navegador y el visor se turnan, la selección
// parpadea); doble y triple clic siguen siendo del navegador.
document.addEventListener('mousedown',e=>{selDrag=null; if(e.button!==0||e.detail>1)return;
  const tl=e.target.closest?.('.textLayer'); if(!tl)return;
  const p=caretNear(tl,e.clientX,e.clientY); if(!p)return;
  e.preventDefault(); selDrag={tl,x:e.clientX,y:e.clientY,sc:tl.closest('.scroll')}; textLayers.get(tl)?.classList.add('active');
  const s=getSelection(); if(e.shiftKey&&s.rangeCount)s.extend(p.node,p.off);else s.collapse(p.node,p.off)});
function selExtend(){const d=selDrag; if(!d)return;
  const tl=layerAt(d.x,d.y)||d.tl; d.tl=tl;
  const p=caretNear(tl,d.x,d.y), s=getSelection(); if(p&&s.rangeCount)s.extend(p.node,p.off)}
document.addEventListener('mousemove',e=>{if(!selDrag)return; if(!(e.buttons&1)){selDrag=null;return}
  selDrag.x=e.clientX; selDrag.y=e.clientY; selExtend()});
// arrastrar hasta el borde desplaza (el navegador ya no lo hace porque el arrastre es del visor)
setInterval(()=>{const d=selDrag; if(!d?.sc)return; const r=d.sc.getBoundingClientRect(), m=40;
  const v=d.y>r.bottom-m?d.y-(r.bottom-m):d.y<r.top+m?d.y-(r.top+m):0; if(!v)return;
  d.sc.scrollTop+=Math.max(-40,Math.min(40,v/2)); selExtend()},30);
document.addEventListener('mouseup',()=>{selDrag=null},true);
// El PDF parte el texto en renglones y trae números de página: se limpia al copiar y al citar.
function cleanSel(s){
  return s.split('\n').filter(l=>!/^\s*\d{1,4}\s*$/.test(l)).join('\n')
    .replace(/(\p{L})-\n(?=\p{Ll})/gu,'$1').replace(/\s*\n\s*/g,' ').replace(/[ \t]{2,}/g,' ').trim();
}
document.addEventListener('copy',e=>{const sel=getSelection(); if(!sel.rangeCount)return;
  const n=sel.anchorNode, el=n&&(n.nodeType===1?n:n.parentElement); if(!el?.closest('.textLayer,.page'))return;
  e.clipboardData.setData('text/plain',cleanSel(sel.toString())); e.preventDefault()});

// posición (en px dentro del scroll) de un destino del índice
Viewer.prototype.yOf=function(it){
  const div=it&&it.page&&this.sc.querySelector(`.page[data-i="${it.page}"]`); if(!div)return null;
  return div.offsetTop+(it.top!=null?Math.max(0,(this.ptH-it.top)*scale):0);
};
Viewer.prototype.goto=function(it){const y=this.yOf(it); if(y!=null)this.sc.scrollTop=Math.max(0,y-24)};

let tab='actual', view='marcado', refs=null, st=null, viewers=[], shown='', noSync=0;

// ---------- diferencias visibles en «lado a lado»
// Se compara el texto que realmente sale en cada PDF, palabra por palabra (Myers). Los números
// sueltos (páginas, llamadas a notas) no cuentan: si la paginación se corre llenarían todo de ruido.
const textCache=new Map();
async function pdfWords(doc,url){
  if(textCache.has(url))return textCache.get(url);
  const toks=[], items={}, p1=await doc.getPage(1), view=p1.view;
  for(let p=1;p<=doc.numPages;p++){
    const tc=await (await doc.getPage(p)).getTextContent(); items[p]=tc.items;
    const pt=[], lastOnLine=new Map();
    tc.items.forEach((it,ii)=>{const s=it.str||'', y=Math.round(it.transform[5]);
      for(const m of s.matchAll(/[\p{L}\p{N}]+/gu)){
        const t={w:m[0].normalize('NFKC').toLowerCase(),p,ii,s:m.index,e:m.index+m[0].length,x:it.transform[4]+it.width*(m.index/Math.max(1,s.length))};
        pt.push(t); const prev=lastOnLine.get(y); if(!prev||t.x>prev.x)lastOnLine.set(y,t)}});
    // números al final de un renglón: páginas al pie y en índice/cuadros/figuras
    const drop=new Set([...lastOnLine.values()].filter(t=>/^\d+$/.test(t.w)));
    for(const t of pt)if(!drop.has(t))toks.push(t);
  }
  const r={toks,items,view}; textCache.set(url,r); if(textCache.size>6)textCache.delete(textCache.keys().next().value); return r;
}
function myers(A,B){ // devuelve [borradoEnA, agregadoEnB] como Uint8Array; null si son demasiado distintos
  const n0=A.length,m0=B.length; let pre=0; while(pre<n0&&pre<m0&&A[pre]===B[pre])pre++;
  let suf=0; while(suf<n0-pre&&suf<m0-pre&&A[n0-1-suf]===B[m0-1-suf])suf++;
  const a=A.slice(pre,n0-suf), b=B.slice(pre,m0-suf), n=a.length, m=b.length, max=n+m;
  const del=new Uint8Array(n0), add=new Uint8Array(m0);
  if(!n||!m){for(let i=0;i<n;i++)del[pre+i]=1;for(let j=0;j<m;j++)add[pre+j]=1;return [del,add]}
  const V=new Int32Array(2*max+3), off=max+1, trace=[]; let done=false;
  for(let d=0;d<=max&&!done;d++){
    if(d>6000)return null;
    trace.push(V.slice(off-d-1,off+d+2));
    for(let k=-d;k<=d;k+=2){
      let x=(k===-d||(k!==d&&V[off+k-1]<V[off+k+1]))?V[off+k+1]:V[off+k-1]+1, y=x-k;
      while(x<n&&y<m&&a[x]===b[y]){x++;y++}
      V[off+k]=x; if(x>=n&&y>=m){done=true;break}
    }
  }
  let x=n,y=m;
  for(let d=trace.length-1;d>=0;d--){
    const v=trace[d], g=k=>v[k+d+1], k=x-y;
    const pk=(k===-d||(k!==d&&g(k-1)<g(k+1)))?k+1:k-1, px=g(pk), py=px-pk;
    while(x>px&&y>py){x--;y--}
    if(d>0){if(x===px)add[pre+y-1]=1;else del[pre+x-1]=1}
    x=px;y=py;
  }
  return [del,add];
}
// Myers solo aguanta pocas diferencias (memoria ~D²). Para capítulos reescritos se ancla primero
// con palabras que salen una sola vez en cada lado (patience diff) y Myers corre en los huecos.
function diffTokens(A,B){
  const del=new Uint8Array(A.length), add=new Uint8Array(B.length), stack=[[0,A.length,0,B.length]];
  const markAll=(a0,a1,b0,b1)=>{for(let i=a0;i<a1;i++)del[i]=1;for(let j=b0;j<b1;j++)add[j]=1};
  while(stack.length){
    let [a0,a1,b0,b1]=stack.pop();
    while(a0<a1&&b0<b1&&A[a0]===B[b0]){a0++;b0++}
    while(a0<a1&&b0<b1&&A[a1-1]===B[b1-1]){a1--;b1--}
    if(a0===a1||b0===b1){markAll(a0,a1,b0,b1);continue}
    let anchors=[];
    if((a1-a0)+(b1-b0)>3000){
      const cA=new Map(), cB=new Map();
      for(let i=a0;i<a1;i++){const v=cA.get(A[i]);cA.set(A[i],v===undefined?i:-1)}
      for(let j=b0;j<b1;j++){const v=cB.get(B[j]);cB.set(B[j],v===undefined?j:-1)}
      const pairs=[]; for(let i=a0;i<a1;i++){const pa=cA.get(A[i]),pb=cB.get(A[i]); if(pa===i&&pb!==undefined&&pb>=0)pairs.push([i,pb])}
      // subsecuencia creciente más larga en posición de B
      const tails=[], prev=new Int32Array(pairs.length).fill(-1), tIdx=[];
      pairs.forEach((p,k)=>{let lo=0,hi=tails.length; while(lo<hi){const m=(lo+hi)>>1; if(tails[m]<p[1])lo=m+1;else hi=m}
        tails[lo]=p[1]; tIdx[lo]=k; prev[k]=lo?tIdx[lo-1]:-1});
      for(let k=tails.length?tIdx[tails.length-1]:-1;k>=0;k=prev[k])anchors.push(pairs[k]);
      anchors.reverse();
    }
    if(anchors.length){
      let pa=a0,pb=b0;
      for(const [i,j] of anchors){stack.push([pa,i,pb,j]);pa=i+1;pb=j+1}
      stack.push([pa,a1,pb,b1]); continue;
    }
    const r=myers(A.slice(a0,a1),B.slice(b0,b1));
    if(!r){markAll(a0,a1,b0,b1);continue}
    r[0].forEach((v,k)=>{if(v)del[a0+k]=1}); r[1].forEach((v,k)=>{if(v)add[b0+k]=1});
  }
  return [del,add];
}
let lado={key:'',hunks:[],cur:-1};
async function computeLado(){
  const [L,R]=viewers; if(view!=='lado'||tab!=='comparar'||!L?.doc||!R?.doc)return;
  const key=L.url+'|'+R.url; if(key===lado.key)return; lado.key=key; $('#navc').textContent='comparando…';
  const [a,b]=await Promise.all([pdfWords(L.doc,L.url),pdfWords(R.doc,R.url)]); if(lado.key!==key)return;
  const ids=new Map(), id=w=>{let v=ids.get(w);if(v===undefined){v=ids.size;ids.set(w,v)}return v};
  const res=diffTokens(a.toks.map(t=>id(t.w)),b.toks.map(t=>id(t.w)));
  if(!res){$('#navc').textContent='demasiados cambios';return}
  const [del,add]=res, hA=new Int32Array(a.toks.length).fill(-1), hB=new Int32Array(b.toks.length).fill(-1), hunks=[];
  let i=0,j=0;
  while(i<a.toks.length||j<b.toks.length){
    if((i<a.toks.length&&del[i])||(j<b.toks.length&&add[j])){
      // un cambio = borrados/agregados seguidos, uniendo los que quedan a ≤3 palabras iguales
      const h={a:i,b:j}; let gap=0;
      while(i<a.toks.length||j<b.toks.length){
        if(i<a.toks.length&&del[i]){hA[i++]=hunks.length;gap=0}
        else if(j<b.toks.length&&add[j]){hB[j++]=hunks.length;gap=0}
        else{let k=0;while(k<4&&i+k<a.toks.length&&j+k<b.toks.length&&!del[i+k]&&!add[j+k])k++;
          if(k<4&&(del[i+k]||add[j+k])){i+=k;j+=k}else break}
      }
      hunks.push(h);
    }else{i++;j++}
  }
  // bloques que solo se movieron (p. ej. una figura que LaTeX reacomodó): mismo texto borrado en
  // un lugar y agregado en otro. No cuentan como cambio.
  const txt=hunks.map(()=>({d:[],a:[]}));
  a.toks.forEach((t,k)=>{if(hA[k]>=0)txt[hA[k]].d.push(t.w)}); b.toks.forEach((t,k)=>{if(hB[k]>=0)txt[hB[k]].a.push(t.w)});
  const pureDel=new Map(), moved=new Set();
  txt.forEach((t,h)=>{if(t.d.length>=3&&!t.a.length){const k=t.d.join(' ');(pureDel.get(k)||pureDel.set(k,[]).get(k)).push(h)}});
  // igual, o uno contenido en el otro (el bloque movido a veces arrastra una palabra vecina)
  const wrap=s=>' '+s+' ';
  txt.forEach((t,h)=>{if(t.a.length<3||t.d.length)return; const A=t.a.join(' ');
    for(const [D,l] of pureDel){if(!l.length)continue;
      if(D===A||wrap(D).includes(wrap(A))||wrap(A).includes(wrap(D))){moved.add(l.shift());moved.add(h);break}}});
  const remap=new Int32Array(hunks.length).fill(-1); let nh=0; hunks.forEach((h,k)=>{if(!moved.has(k))remap[k]=nh++});
  for(let k=0;k<hA.length;k++)if(hA[k]>=0)hA[k]=remap[hA[k]];
  for(let k=0;k<hB.length;k++)if(hB[k]>=0)hB[k]=remap[hB[k]];
  const kept=hunks.filter((h,k)=>!moved.has(k)); hunks.length=0; hunks.push(...kept);
  const marks=(side,hs,cls)=>{const out={}; let last=null;
    side.toks.forEach((t,k)=>{const h=hs[k]; if(h<0){last=null;return}
      if(last&&last.p===t.p&&last.ii===t.ii&&last.h===h){last.e=t.e;return}
      last={p:t.p,ii:t.ii,s:t.s,e:t.e,h,cls}; (out[t.p]=out[t.p]||[]).push(last)});
    return {byPage:out,items:side.items,view:side.view}};
  L.marks=marks(a,hA,'del'); R.marks=marks(b,hB,'add');
  hunks.forEach(h=>{h.pa=a.toks[Math.min(h.a,a.toks.length-1)]; h.pb=b.toks[Math.min(h.b,b.toks.length-1)]});
  lado.hunks=hunks; lado.sides=[a,b]; lado.cur=-1;
  [L,R].forEach(v=>v.sc.querySelectorAll('.page[data-done]').forEach(d=>v.drawMarks(d)));
  navLabel();
}
Viewer.prototype.drawMarks=function(div){
  div.querySelectorAll('.hl').forEach(e=>e.remove());
  const M=this.marks; if(!M||view!=='lado')return; const list=M.byPage[+div.dataset.i]; if(!list)return;
  const [vx,,,vy]=M.view;
  for(const r of list){const it=M.items[r.p][r.ii]; if(!it)continue; const t=it.transform, len=Math.max(1,it.str.length);
    const fh=Math.hypot(t[2],t[3])||it.height||10, x0=t[4]+it.width*r.s/len, x1=t[4]+it.width*r.e/len;
    const el=document.createElement('div'); el.className=`hl ${r.cls}${r.h===lado.cur?' cur':''}`; el.dataset.h=r.h;
    Object.assign(el.style,{left:(x0-vx)*scale-1+'px',top:(vy-t[5]-fh*.9)*scale+'px',width:(x1-x0)*scale+2+'px',height:fh*1.12*scale+'px'});
    div.appendChild(el)}
};
function navLabel(){const n=lado.hunks.length;
  $('#navc').textContent=n?(lado.cur<0?`${n} cambio${n>1?'s':''}`:`${lado.cur+1} / ${n}`):'sin cambios'}
function navGo(dir){
  const n=lado.hunks.length; if(!n||viewers.length<2)return;
  lado.cur=lado.cur<0?(dir>0?0:n-1):(lado.cur+dir+n)%n; const h=lado.hunks[lado.cur];
  noSync=Date.now()+500;
  viewers.forEach((v,s)=>{const t=s?h.pb:h.pa; if(!t)return; const it=lado.sides[s].items[t.p][t.ii];
    v.goto({page:t.p,top:it.transform[5]+Math.hypot(it.transform[2],it.transform[3])*3})});
  document.querySelectorAll('.hl').forEach(e=>e.classList.toggle('cur',+e.dataset.h===lado.cur));
  navLabel();
}
const setHl=on=>{$('#hlon').checked=on;document.body.classList.toggle('nohl',!on);try{localStorage.setItem('hl',on?'1':'0')}catch(e){}};
$('#hlon').onchange=e=>setHl(e.target.checked); try{setHl(localStorage.getItem('hl')!=='0')}catch(e){}
$('#navn').onclick=()=>navGo(1); $('#navp').onclick=()=>navGo(-1);
document.addEventListener('keydown',e=>{if(view!=='lado'||tab!=='comparar'||e.target.closest('input,textarea'))return;
  if(e.key==='c')setHl(!$('#hlon').checked);
  if(e.key==='j')navGo(1); if(e.key==='k')navGo(-1)});
async function outlineOf(doc){
  const out=[]; let ol=null; try{ol=await doc.getOutline()}catch(e){}
  async function walk(items,level){for(const it of items||[]){
    let page=null,top=null;
    try{let d=it.dest; if(typeof d==='string')d=await doc.getDestination(d);
      if(Array.isArray(d)){page=(typeof d[0]==='object'?await doc.getPageIndex(d[0]):d[0])+1;
        const k=d[1]&&d[1].name; if(k==='XYZ'&&typeof d[3]==='number')top=d[3]; else if((k==='FitH'||k==='FitBH')&&typeof d[2]==='number')top=d[2];}}catch(e){}
    out.push({title:(it.title||'').replace(/\s+/g,' ').trim(),level,page,top}); await walk(it.items,level+1)}}
  await walk(ol,0); return out;
}
// el índice sigue al PDF principal: el actual, el de cambios marcados o el derecho en lado a lado
const tocViewer=()=>view==='lado'&&tab==='comparar'?viewers[1]:viewers[0];
function renderToc(){
  const v=tocViewer(), el=$('#tocl');
  if(tab==='comparar'&&view==='fuente'){el.innerHTML='<p class="empty">El índice es para las vistas PDF.</p>';return}
  if(!v||!v.outline){el.innerHTML='<p class="empty">Cargando…</p>';return}
  if(!v.outline.length){el.innerHTML='<p class="empty">Este PDF no trae índice.</p>';return}
  // cambios por sección: propios (punto lleno) o solo en subsecciones (aro)
  const own=v.outline.map(it=>chg?.sections[tkey(it.title)]||0), tot=own.slice();
  for(let i=v.outline.length-1;i>=0;i--)for(let j=i+1;j<v.outline.length&&v.outline[j].level>v.outline[i].level;j++)if(v.outline[j].level===v.outline[i].level+1)tot[i]+=tot[j];
  const n=Object.values(chg?.sections||{}).reduce((a,b)=>a+b,0)+(chg?.outside||0);
  let h='';
  if(chg){h+=n?`<div class="chgleg">${n} cambio${n>1?'s':''} ${tab==='comparar'?`desde ${esc(label(cmpBase))}`:'sin commit'}</div>`
            :`<div class="chgleg" style="opacity:.6">${tab==='comparar'?'sin cambios en las fuentes':'sin cambios sin commit'}</div>`;
          if(chg.outside)h+=`<div class="chgleg">${chg.outside} fuera del índice (portada, resumen…)</div>`}
  h+=v.outline.map((it,i)=>{const c=tot[i]?`<span class="chg${own[i]?'':' sub'}" title="${own[i]?own[i]+' cambio(s) aquí':''}${own[i]&&tot[i]>own[i]?' · ':''}${tot[i]>own[i]?(tot[i]-own[i])+' en subsecciones':''}">${tot[i]}</span>`:'';
    return `<a class="l${Math.min(it.level,3)}" data-i="${i}" title="${esc(it.title)} · p. ${it.page}"><span class="tt">${esc(it.title)}</span>${c}</a>`}).join('');
  el.innerHTML=h;
  hlToc();
}
const tkey=t=>((t||'').normalize('NFKC').toLowerCase().match(/[\p{L}\p{N}_]+/gu)||[]).join(' ');
let chg=null, chgKey='';
async function loadChanges(force){
  const b=tab==='comparar'?cmpBase:'HEAD', t=tab==='comparar'?cmpTarget:'WORKTREE';
  if(!b)return; const key=b+'|'+t+'|'+(st?.actual.v||0)+'|'+(refs?.head||'');
  if(key===chgKey&&!force)return; chgKey=key;
  try{chg=await (await fetch(`/api/changes?base=${b}&target=${t}`)).json(); if(chg.error)chg=null}catch(e){chg=null}
  renderToc();
}
let hlPending=false;
function hlToc(){
  const v=tocViewer(); if(!v||!v.outline)return;
  const y=v.sc.scrollTop+80; let cur=-1;
  v.outline.forEach((it,i)=>{const yy=v.yOf(it); if(yy!=null&&yy<=y)cur=i});
  document.querySelectorAll('#tocl a').forEach((a,i)=>a.classList.toggle('on',i===cur));
  const on=document.querySelector('#tocl a.on'); if(on)on.scrollIntoView({block:'nearest'});
}
// mismo título y misma aparición en el otro PDF (lado a lado); si no está, misma posición en la lista
function matchItem(list,it,src){
  if(!list)return null; const nth=src.slice(0,src.indexOf(it)).filter(x=>x.title===it.title).length;
  return list.filter(x=>x.title===it.title)[nth]||list[src.indexOf(it)]||null;
}
$('#tocl').onclick=e=>{const a=e.target.closest('a'); if(!a)return; const v=tocViewer(); const it=v.outline[+a.dataset.i];
  noSync=Date.now()+500; viewers.forEach(w=>w.goto(w===v?it:matchItem(w.outline,it,v.outline)));};
const setToc=open=>{document.body.classList.toggle('notoc',!open);try{localStorage.setItem('toc',open?'1':'0')}catch(e){}};
$('#tocbtn').onclick=()=>setToc(document.body.classList.contains('notoc'));
try{setToc(localStorage.getItem('toc')!=='0')}catch(e){}

function link(a,b){let lock=false;const f=(x,y)=>x.sc.addEventListener('scroll',()=>{
  if(lock||Date.now()<noSync||!$('#sync').checked)return;lock=true;
  const r=x.sc.scrollTop/Math.max(1,x.sc.scrollHeight-x.sc.clientHeight);y.sc.scrollTop=r*(y.sc.scrollHeight-y.sc.clientHeight);
  requestAnimationFrame(()=>lock=false)});f(a,b);f(b,a)}

let cmpBase=null, cmpTarget='WORKTREE';
function fmtDate(s){const d=new Date(s); if(isNaN(d))return s;
  const o={day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}; if(d.getFullYear()!==new Date().getFullYear())o.year='numeric';
  return d.toLocaleString('es-MX',o)}
const label=sha=>sha==='WORKTREE'?'ahora':(()=>{const r=refs?.refs.find(x=>x.sha===sha);return r?fmtDate(r.date):(sha||'').slice(0,7)})();
function setup(){
  const key=[tab,view,cmpBase,cmpTarget].join('|'); if(key===shown)return; shown=key;
  const m=$('#main'); m.replaceChildren(); viewers=[];
  $('#bar2').style.display=tab==='comparar'?'flex':'none';
  $('#synclbl').style.display=view==='lado'?'':'none'; $('#nav').style.display=view==='lado'?'':'none'; $('#hllbl').style.display=view==='lado'?'':'none'; lado={key:'',hunks:[],cur:-1};
  $('#leg').style.display=view==='marcado'?'':'none';
  $('#cmptitle').textContent=tab==='comparar'?`Cambios desde ${label(cmpBase)} hasta ${label(cmpTarget)}`:'';
  const cap=s=>s.charAt(0).toUpperCase()+s.slice(1);
  if(tab==='actual'){viewers=[new Viewer('Ahora')]}
  else if(view==='marcado'){viewers=[new Viewer('Cambios marcados')]}
  else if(view==='lado'){viewers=[new Viewer(cap(label(cmpBase))),new Viewer(cap(label(cmpTarget)))];link(...viewers)}
  else {const d=document.createElement('div');d.id='src';d.innerHTML='<p class="empty">Cargando…</p>';m.appendChild(d);loadSrc();}
  viewers.forEach(v=>{m.appendChild(v.el);v.sc.addEventListener('scroll',()=>{
    if(v!==tocViewer()||hlPending)return;hlPending=true;requestAnimationFrame(()=>{hlPending=false;hlToc()})})});
  renderToc(); refresh(); loadChanges();
}
async function loadSrc(){
  if(!cmpBase)return;
  const r=await fetch(`/api/source-diff?base=${cmpBase}&target=${cmpTarget}`); const el=$('#src'); if(el) el.innerHTML=await r.text();
}
function pillOf(s){const p=$('#pill');
  if(!s){p.className='pill';p.textContent='…';return}
  if(s.building){p.className='pill run';p.textContent='compilando…'}
  else if(s.ok===false){p.className='pill bad';p.textContent='error de compilación'}
  else if(s.ok){p.className='pill ok';p.textContent='compilado'}
  else{p.className='pill';p.textContent='en cola'}
  $('#took').textContent=s.ok&&!s.building&&s.took?`${s.took}s`:'';
  const e=$('#err'); e.hidden=!(s.ok===false&&!s.building); e.textContent=s.error||'';
}
function refresh(){
  if(!st)return; const a=st.actual, c=st.compare;
  if(tab==='actual'){pillOf(a); viewers[0]?.load(a.v&&a.ok!==null&&(a.ok||a.v>1)?`/pdf/actual.pdf?v=${a.v}`:null);
    if(a.ok===false&&viewers[0]&&!viewers[0].url) viewers[0].sc.innerHTML='<p class="empty">No compila todavía. Mira el error arriba.</p>';
    $('#open').href='/pdf/actual.pdf';return}
  if(!c.base){pillOf(null);return}
  const tgtPdf=c.target==='WORKTREE'?{s:a,u:`/pdf/actual.pdf?v=${a.v}`}:{s:c.target_pdf,u:`/pdf/ref-${c.target}.pdf?v=${c.target_pdf.v}`};
  if(view==='marcado'){pillOf(c.diff);viewers[0]?.load(c.diff.ok?`/pdf/diff.pdf?v=${c.diff.v}`:null);$('#open').href='/pdf/diff.pdf';
    if(c.diff.ok&&c.diff_mode&&c.diff_mode!=='completo')$('#took').textContent+=` · modo ${c.diff_mode}`}
  else if(view==='lado'){const bs=c.base_pdf; pillOf(bs.building||!bs.ok?bs:tgtPdf.s);
    viewers[0]?.load(bs.ok?`/pdf/ref-${c.base}.pdf?v=${bs.v}`:null);viewers[1]?.load(tgtPdf.s.ok?tgtPdf.u:null);
    $('#open').href=`/pdf/ref-${c.base}.pdf`}
  else pillOf({ok:true});
}
async function poll(){
  try{const r=await fetch('/api/status');const prev=st?JSON.stringify([st.actual.v,st.compare.diff.v]):'';st=await r.json();
    refresh(); loadChanges(); if(tab==='comparar'&&view==='fuente'&&prev&&prev!==JSON.stringify([st.actual.v,st.compare.diff.v]))loadSrc();
  }catch(e){$('#pill').className='pill bad';$('#pill').textContent='servidor apagado'}
  setTimeout(poll,1000);
}
// ---------- versiones
async function loadRefs(){
  try{refs=await (await fetch('/api/refs')).json()}catch(e){return}
  renderVersions();
}
function renderVersions(){
  if(!refs)return;
  const cmp=tab==='comparar', n=refs.dirty.length;
  const nowTag=!cmp?'viendo':(cmpTarget==='WORKTREE'?'hasta':'');
  let h='<div class="hint">Clic en una versión: ves lo que cambió desde ella hasta ahora. ⌥clic en otra: comparas esas dos versiones.</div>';
  h+=`<div class="ver now${nowTag?' tgt':''}" data-sha="WORKTREE"><span class="dot"></span>
    <div class="d">Ahora${nowTag?`<span class="tag">${nowTag}</span>`:''}</div><div class="s">Lo que tienes en disco</div>
    <div class="m">${n?`${n} archivo${n>1?'s':''} sin commit`:'sin cambios sin commit'} · rama ${esc(refs.branch)}</div></div>`;
  h+=refs.refs.map(r=>{const b=cmp&&r.sha===cmpBase, t=cmp&&r.sha===cmpTarget;
    return `<div class="ver${b?' base':''}${t?' tgt':''}" data-sha="${r.sha}" title="${esc(r.subject)}"><span class="dot"></span>
      <div class="d">${esc(fmtDate(r.date))}${b?'<span class="tag">desde</span>':''}${t?'<span class="tag">hasta</span>':''}</div>
      <div class="s">${esc(r.subject)}</div><div class="m">${r.short} · ${r.files} archivo${r.files===1?'':'s'}</div></div>`}).join('');
  if(!refs.refs.length)h+='<p class="empty">Todavía no hay commits de la tesis.</p>';
  $('#verl').innerHTML=h;
}
function goActual(){tab='actual';setup();renderVersions()}
async function compare(){
  tab='comparar';
  const r=await fetch('/api/compare',{method:'POST',body:JSON.stringify({base:cmpBase,target:cmpTarget})});
  if(!r.ok){alert((await r.json()).error);return}
  try{st=await (await fetch('/api/status')).json()}catch(e){}
  setup();renderVersions();if(view==='fuente')loadSrc();
}
$('#verl').onclick=e=>{const v=e.target.closest('.ver'); if(!v)return; const sha=v.dataset.sha;
  if(e.altKey&&tab==='comparar'){if(sha!==cmpBase){cmpTarget=sha;compare()}return}
  if(sha==='WORKTREE'){goActual();return}
  cmpBase=sha; if(cmpTarget===sha)cmpTarget='WORKTREE'; compare();};
$('#back').onclick=goActual;
const setSide=s=>{document.querySelectorAll('.stabs button').forEach(b=>b.classList.toggle('on',b.dataset.s===s));
  $('#tocl').hidden=s!=='toc';$('#verl').hidden=s!=='ver';try{localStorage.setItem('side',s)}catch(e){}if(s==='ver')loadRefs()};
document.querySelectorAll('.stabs button').forEach(b=>b.onclick=()=>setSide(b.dataset.s));
try{setSide(localStorage.getItem('side')||'toc')}catch(e){setSide('toc')}
document.querySelectorAll('#views button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#views button').forEach(x=>x.classList.toggle('on',x===b));view=b.dataset.v;setup()});
$('#rebuild').onclick=()=>fetch('/api/build',{method:'POST'});
const zoom=f=>{scale=Math.min(3,Math.max(.6,scale*f));localStorage.setItem('zoom',scale);viewers.forEach(v=>v.layout())};
$('#zin').onclick=()=>zoom(1.15);$('#zout').onclick=()=>zoom(1/1.15);
setInterval(loadRefs,15000);loadRefs();
// ---------- comentarios
const esc=s=>s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let pending=null, comments=[];
function toast(m){const t=$('#toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(()=>t.style.display='none',4000)}
document.addEventListener('mouseup',e=>{
  if(e.target.closest('#cbtn,#cmodal,#cpanel'))return;
  setTimeout(()=>{const sel=getSelection(),q=cleanSel(sel.toString()),b=$('#cbtn');
    const node=sel.anchorNode&&(sel.anchorNode.nodeType===1?sel.anchorNode:sel.anchorNode.parentElement);
    if(!q||!node||!node.closest('.textLayer')){b.style.display='none';return}
    const r=sel.getRangeAt(0).getBoundingClientRect(), pane=node.closest('.pane');
    pending={quote:q,page:node.closest('.page')?.dataset.i||'',view:pane?.querySelector('h2')?.textContent||''};
    b.style.left=Math.min(innerWidth-120,r.right+6)+'px';b.style.top=Math.min(innerHeight-40,r.bottom+6)+'px';b.style.display='block'},0)});
$('#cbtn').onmousedown=e=>e.preventDefault();
$('#cbtn').onclick=()=>{if(!pending)return;$('#cbtn').style.display='none';$('#cquote').textContent=pending.quote;
  $('#ctext').value='';$('#cmodal').style.display='flex';$('#ctext').focus()};
const closeModal=()=>{$('#cmodal').style.display='none'};
$('#ccancel').onclick=closeModal;
$('#cmodal').onclick=e=>{if(e.target.id==='cmodal')closeModal()};
$('#ctext').onkeydown=e=>{if(e.key==='Escape')closeModal();if(e.key==='Enter'&&(e.metaKey||e.ctrlKey))$('#csave').click()};
$('#csave').onclick=async()=>{const text=$('#ctext').value.trim();if(!text)return;
  const r=await fetch('/api/comments',{method:'POST',body:JSON.stringify({...pending,text})});const j=await r.json();
  if(!r.ok){alert(j.error);return}
  closeModal();getSelection().removeAllRanges();
  toast(j.located?`Guardado en ${j.file}:${j.line}`:`No encontré ese texto en las fuentes; quedó en ${j.file}`);loadComments()};
async function loadComments(){
  try{comments=await (await fetch('/api/comments')).json()}catch(e){return}
  $('#cpanelbtn').textContent=`Comentarios (${comments.length})`;
  $('#clist').innerHTML=comments.length?comments.map((c,i)=>`<div class="cm${c.unplaced?' un':''}">
    <button class="loc" data-i="${i}" data-a="open">${esc(c.file)}:${c.line} ↗</button>
    <div class="q">${esc(c.head)}</div><div class="t">${esc(c.text)}</div>
    <div class="acts"><button class="b" data-i="${i}" data-a="resolve">Resolver</button></div></div>`).join('')
    :'<p class="empty">Sin comentarios. Selecciona texto en un PDF y presiona «Comentar».</p>';
}
$('#clist').onclick=async e=>{const b=e.target.closest('button');if(!b)return;const c=comments[+b.dataset.i];
  if(b.dataset.a==='open'){fetch('/api/open',{method:'POST',body:JSON.stringify(c)});return}
  if(!confirm('¿Borrar este comentario del .tex?'))return;
  const j=await (await fetch('/api/comments/resolve',{method:'POST',body:JSON.stringify(c)})).json();
  if(!j.ok)alert(j.error);loadComments()};
const panel=open=>{$('#cpanel').style.display=open?'flex':'none';document.body.classList.toggle('cp',open)};
$('#cpanelbtn').onclick=()=>{panel($('#cpanel').style.display!=='flex');loadComments()};
$('#cclose').onclick=()=>panel(false);
setInterval(loadComments,4000);loadComments();
setup();poll();
</script></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
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
