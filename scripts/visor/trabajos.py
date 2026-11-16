"""Cola de compilaciones, estado compartido con la interfaz y vigilancia de cambios en disco."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import threading
import time

from .config import MAIN, OUT, PACKAGE, SRC, WATCH_EXT, WORK, WORKTREE
from .latex import compile_tex, flatten, materialize


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
    parts = [hashlib.sha1(b"".join(p.read_bytes() for p in sorted(PACKAGE.glob("*.py")))).hexdigest()]
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
