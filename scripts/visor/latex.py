"""Preparar las fuentes de una versión de la tesis y compilarlas con tectonic."""
from __future__ import annotations

import io
import re
import shutil
import struct
import subprocess
import tarfile
import zlib
from pathlib import Path

from .config import MAIN, SKIP_COPY, SRC, WORKTREE
from .git_utils import git, src_name_at


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
        name = src_name_at(ref)
        data = git("archive", "--format=tar", ref, name, binary=True)
        tmp = dest.with_name(dest.name + ".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(tmp)
        shutil.move(str(tmp / name), dest)
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
