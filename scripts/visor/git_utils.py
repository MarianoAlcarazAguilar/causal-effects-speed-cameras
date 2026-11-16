"""Comandos de git: versiones de la tesis, diff de las fuentes y archivos en un commit."""
from __future__ import annotations

import html
import re
import subprocess

from .config import REPO, SRC_NAME, SRC_PATHS, WORKTREE


def git(*args: str, binary: bool = False):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def resolve(ref: str) -> str:
    return ref if ref == WORKTREE else git("rev-parse", ref).strip()


def src_name_at(ref: str) -> str:
    """La carpeta de la tesis en `ref`: la actual o, en commits viejos, la anterior."""
    for name in SRC_PATHS:
        if git("ls-tree", "-d", "--name-only", ref, name).strip():
            return name
    return SRC_NAME


def list_refs() -> dict:
    fmt = "@@%H%x09%h%x09%ad%x09%s"
    log = git("log", f"--format={fmt}", "--date=format:%Y-%m-%dT%H:%M", "--shortstat",
              "-n", "80", "HEAD", "--", *SRC_PATHS)
    refs = []
    for l in log.splitlines():
        if l.startswith("@@"):
            refs.append(dict(zip(("sha", "short", "date", "subject"), l[2:].split("\t", 3)),
                             files=0))
        elif refs and "changed" in l:
            m = re.search(r"(\d+) files? changed", l)
            refs[-1]["files"] = int(m.group(1)) if m else 0
    dirty = [l[3:] for l in git("status", "--porcelain", "--", *SRC_PATHS).splitlines()]
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    return {"refs": refs, "dirty": dirty, "branch": branch, "head": resolve("HEAD")}


def diff_spec(base: str, target: str) -> tuple[list[str], str]:
    """Qué comparar con `git diff` y el prefijo de las rutas del lado `target`.

    Si las dos versiones tienen la tesis en la misma carpeta, se compara esa carpeta. Si
    una es anterior al cambio de nombre, se comparan las dos carpetas directamente, árbol
    contra árbol; así git ve los mismos archivos en vez de uno borrado y otro nuevo. Para
    lo que hay en disco se usa `git stash create`, que arma un commit con los cambios sin
    tocar nada (los archivos sin `git add` no entran, igual que en el diff normal).
    """
    name_base = src_name_at(base)
    name_target = SRC_NAME if target == WORKTREE else src_name_at(target)
    if name_base == name_target:
        return [base] + ([] if target == WORKTREE else [target]) + ["--", name_target], name_target + "/"
    commit = target
    if target == WORKTREE:
        commit = git("stash", "create").strip() or "HEAD"
    return [f"{base}:{name_base}", f"{commit}:{name_target}"], ""


def source_diff(base: str, target: str) -> str:
    spec, _ = diff_spec(base, target)
    out = git("diff", "-M", "--no-color", "--word-diff=porcelain", "-U2", *spec)
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
            name = line.split(" b/", 1)[-1]
            for prefix in SRC_PATHS:
                name = name.removeprefix(prefix + "/")
            parts.append(f'<section class="file"><h3>{html.escape(name)}</h3>')
            file_open = True
        elif line.startswith(("index ", "--- ", "+++ ", "new file", "deleted file", "similarity",
                              "rename from", "rename to")):
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
    untracked = [l[3:] for l in git("status", "--porcelain", "--", *SRC_PATHS).splitlines()
                 if l.startswith("??")]
    if untracked and target == WORKTREE:
        parts.insert(0, '<p class="warn">Archivos nuevos sin <code>git add</code> (no salen en este '
                     "diff): " + ", ".join(html.escape(u) for u in untracked) + "</p>")
    return "".join(parts)


def file_at(ref: str, rel: str) -> list[str]:
    if ref == WORKTREE:
        p = REPO / rel
        return p.read_text("utf-8", "replace").splitlines() if p.exists() else []
    try:
        return git("show", f"{ref}:{rel}").splitlines()
    except subprocess.CalledProcessError:
        return []
