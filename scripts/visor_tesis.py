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
import html
import io
import json
import re
import shutil
import struct
import subprocess
import tarfile
import threading
import time
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


def job_ref(sha: str, slot_name: str):
    slot = STATE["compare"][slot_name]

    def fn():
        pdf = OUT / f"ref-{sha}.pdf"
        if pdf.exists():
            return True, "", []
        d = WORK / "build" / f"ref-{sha[:12]}"
        missing = materialize(sha, d)
        ok, err = compile_tex(d, MAIN)
        if ok:
            shutil.copy(d / "main.pdf", pdf)
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
                     ["--math-markup=off", "--graphics-markup=none"])]
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
    fmt = "%H%x09%h%x09%ad%x09%s"
    log = git("log", f"--format={fmt}", "--date=format:%Y-%m-%d %H:%M", "-n", "80", "HEAD",
              "--", SRC_NAME)
    refs = [dict(zip(("sha", "short", "date", "subject"), l.split("\t", 3)))
            for l in log.splitlines() if l]
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
                    c["base"], c["target"] = base, target
                enqueue("ref", base, "base_pdf")
                if target != WORKTREE:
                    enqueue("ref", target, "target_pdf")
                enqueue("diff", base, target)
                self.json({"base": base, "target": target})
            else:
                self.send(404, b"", "text/plain")
        except subprocess.CalledProcessError as e:
            self.json({"error": e.stderr.decode("utf-8", "replace")}, 400)


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
button.b{border:1px solid var(--line);background:var(--panel);border-radius:6px;padding:4px 10px;cursor:pointer;font:inherit}
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
.scroll{flex:1;overflow:auto;padding:14px 0}
.page{margin:0 auto 14px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.15);position:relative}
.page canvas{display:block;width:100%;height:100%}
.page .n{position:absolute;right:-34px;top:0;font-size:11px;color:var(--mute)}
.empty{color:var(--mute);text-align:center;padding:40px}
#src{flex:1;overflow:auto;padding:16px 24px;background:var(--panel)}
.file h3{font-size:14px;margin:18px 0 6px;padding-bottom:4px;border-bottom:1px solid var(--line)}
.hunk{font-size:11px;color:var(--mute);margin:10px 0 2px}
.ln{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;white-space:pre-wrap;word-break:break-word;padding:1px 0}
.del{background:var(--del);color:var(--deli);text-decoration:line-through}.add{background:var(--add);color:var(--addi)}
.warn{color:var(--warn)}
.legend{font-size:12px;color:var(--mute)}.legend b{font-weight:500}
</style></head><body>
<header>
  <h1>Tesis</h1>
  <div class="seg" id="tabs"><button data-t="actual" class="on">Actual</button><button data-t="comparar">Comparar</button></div>
  <span class="pill" id="pill">…</span><span class="legend" id="took"></span>
  <span class="sp"></span>
  <span class="legend" id="dirty"></span>
  <button class="b" id="zout" title="Alejar">−</button><button class="b" id="zin" title="Acercar">+</button>
  <button class="b" id="rebuild">Recompilar</button>
  <a id="open" href="/pdf/actual.pdf" target="_blank">Abrir PDF ↗</a>
</header>
<div id="bar2">
  <label>Versión base <select id="base"></select></label>
  <span>contra</span>
  <select id="target"></select>
  <div class="seg" id="views"><button data-v="marcado" class="on">Cambios marcados</button><button data-v="lado">Lado a lado</button><button data-v="fuente">Fuente</button></div>
  <label class="legend" id="synclbl"><input type="checkbox" id="sync" checked> scroll sincronizado</label>
  <span class="legend" id="leg"><b style="color:#00f">azul</b> = agregado · <b style="color:red">rojo tachado</b> = borrado</span>
</div>
<pre class="msg err" id="err" hidden></pre>
<main id="main"></main>
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
  }
  async layout(tok=++this.token){
    const doc=this.doc; if(!doc)return;
    const p1=await doc.getPage(1); const vp=p1.getViewport({scale});
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
    if(tok===this.token||!div.isConnected) div.prepend(c);
  }
}

let tab='actual', view='marcado', refs=null, st=null, viewers=[], shown='';
function link(a,b){let lock=false;const f=(x,y)=>x.sc.addEventListener('scroll',()=>{
  if(lock||!$('#sync').checked)return;lock=true;
  const r=x.sc.scrollTop/Math.max(1,x.sc.scrollHeight-x.sc.clientHeight);y.sc.scrollTop=r*(y.sc.scrollHeight-y.sc.clientHeight);
  requestAnimationFrame(()=>lock=false)});f(a,b);f(b,a)}

function setup(){
  const key=tab+'|'+view; if(key===shown)return; shown=key;
  const m=$('#main'); m.replaceChildren(); viewers=[];
  $('#bar2').style.display=tab==='comparar'?'flex':'none';
  $('#synclbl').style.display=view==='lado'?'':'none';
  $('#leg').style.display=view==='marcado'?'':'none';
  if(tab==='actual'){viewers=[new Viewer('Lo que tienes ahora en disco')]}
  else if(view==='marcado'){viewers=[new Viewer('Cambios marcados')]}
  else if(view==='lado'){viewers=[new Viewer('Base'),new Viewer('Contra')];link(...viewers)}
  else {const d=document.createElement('div');d.id='src';d.innerHTML='<p class="empty">Cargando…</p>';m.appendChild(d);loadSrc();}
  viewers.forEach(v=>m.appendChild(v.el)); refresh();
}
async function loadSrc(){
  const b=$('#base').value,t=$('#target').value; if(!b)return;
  const r=await fetch(`/api/source-diff?base=${b}&target=${t}`); const el=$('#src'); if(el) el.innerHTML=await r.text();
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
    refresh(); if(tab==='comparar'&&view==='fuente'&&prev&&prev!==JSON.stringify([st.actual.v,st.compare.diff.v]))loadSrc();
  }catch(e){$('#pill').className='pill bad';$('#pill').textContent='servidor apagado'}
  setTimeout(poll,1000);
}
async function loadRefs(){
  refs=await (await fetch('/api/refs')).json();
  const opt=(r,i)=>`<option value="${r.sha}">${r.short} · ${r.date} · ${r.subject.slice(0,60)}${i===0?' (última)':''}</option>`;
  $('#base').innerHTML=refs.refs.map(opt).join('');
  $('#target').innerHTML='<option value="WORKTREE">Lo que tengo ahora (incluye cambios sin commit)</option>'+refs.refs.map(opt).join('');
  $('#dirty').textContent=refs.dirty.length?`${refs.dirty.length} archivo(s) con cambios sin commit · rama ${refs.branch}`:`sin cambios sin commit · rama ${refs.branch}`;
}
async function compare(){
  const r=await fetch('/api/compare',{method:'POST',body:JSON.stringify({base:$('#base').value,target:$('#target').value})});
  if(!r.ok){alert((await r.json()).error);return}
  viewers.forEach(v=>v.url=null); if(view==='fuente')loadSrc();
}
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=async()=>{
  document.querySelectorAll('#tabs button').forEach(x=>x.classList.toggle('on',x===b));tab=b.dataset.t;
  if(tab==='comparar'){await loadRefs();if(!st?.compare.base)await compare();else{ $('#base').value=st.compare.base; $('#target').value=st.compare.target;}}
  setup()});
document.querySelectorAll('#views button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#views button').forEach(x=>x.classList.toggle('on',x===b));view=b.dataset.v;setup()});
$('#base').onchange=$('#target').onchange=compare;
$('#rebuild').onclick=()=>fetch('/api/build',{method:'POST'});
const zoom=f=>{scale=Math.min(3,Math.max(.6,scale*f));localStorage.setItem('zoom',scale);viewers.forEach(v=>v.layout())};
$('#zin').onclick=()=>zoom(1.15);$('#zout').onclick=()=>zoom(1/1.15);
setInterval(()=>{if(tab==='comparar')loadRefs().then(()=>{if(st?.compare.base){$('#base').value=st.compare.base;$('#target').value=st.compare.target}})},15000);
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
