"""Servidor HTTP: la página, los PDF y la API que usa la interfaz."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .comentarios import add_comment, list_comments, resolve_comment, safe_src_path
from .config import OUT, STATIC, WORKTREE
from .git_utils import list_refs, resolve, source_diff
from .secciones import changed_sections
from .trabajos import LOCK, STATE, enqueue


# Solo estos archivos se sirven desde static/.
STATIC_TYPES = {
    "index.html": "text/html; charset=utf-8",
    "visor.css": "text/css; charset=utf-8",
    "visor.js": "text/javascript; charset=utf-8",
}


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
                self.send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif u.path.startswith("/static/"):
                name = Path(u.path).name
                f = STATIC / name
                if name not in STATIC_TYPES or not f.is_file():
                    return self.send(404, b"no existe", "text/plain")
                self.send(200, f.read_bytes(), STATIC_TYPES[name])
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
