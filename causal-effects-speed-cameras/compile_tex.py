#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


AUX_EXTENSIONS = {
    ".aux",
    ".bbl",
    ".bcf",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".lof",
    ".log",
    ".lot",
    ".nav",
    ".out",
    ".run.xml",
    ".snm",
    ".synctex.gz",
    ".toc",
    ".xdv",
}

TARGET_SUBDIRS = {
    "Apendices",
    "Chapters",
    "Referencias",
    "Imagenes",
}

ICON_FILENAMES = {"Icon", "Icon\r"}


def run_pdflatex(tex_file: Path, runs: int) -> None:
    for i in range(1, runs + 1):
        print(f"[compile] Run {i}/{runs}: {tex_file.name}")
        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_file.name,
        ]
        result = subprocess.run(cmd, cwd=tex_file.parent)
        if result.returncode != 0:
            raise RuntimeError(f"pdflatex failed on run {i} with code {result.returncode}")


def is_auxiliary(path: Path) -> bool:
    suffixes = path.suffixes
    full_suffix = "".join(suffixes) if suffixes else path.suffix
    return path.suffix in AUX_EXTENSIONS or full_suffix in AUX_EXTENSIONS


def clean_aux_files(root_dir: Path) -> int:
    removed = 0

    search_roots = [root_dir]
    for subdir in TARGET_SUBDIRS:
        candidate = root_dir / subdir
        if candidate.is_dir():
            search_roots.append(candidate)

    seen: set[Path] = set()
    for search_root in search_roots:
        for path in search_root.rglob("*"):
            if path in seen or not path.is_file():
                continue
            seen.add(path)

            if is_auxiliary(path) or path.name in ICON_FILENAMES:
                path.unlink(missing_ok=True)
                removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compila un archivo .tex y elimina archivos auxiliares.",
    )
    parser.add_argument(
        "tex_file",
        nargs="?",
        default="main.tex",
        help="Archivo .tex principal (default: main.tex)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Numero de corridas de pdflatex (default: 2)",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Solo elimina auxiliares, no compila",
    )
    args = parser.parse_args()

    tex_file = Path(args.tex_file).resolve()
    if tex_file.suffix != ".tex":
        print("[error] El archivo debe terminar en .tex", file=sys.stderr)
        return 2
    if not tex_file.exists():
        print(f"[error] No existe: {tex_file}", file=sys.stderr)
        return 2
    if args.runs < 1:
        print("[error] --runs debe ser >= 1", file=sys.stderr)
        return 2

    try:
        if not args.clean_only:
            run_pdflatex(tex_file, args.runs)

        removed = clean_aux_files(tex_file.parent)
        print(f"[clean] Archivos auxiliares eliminados: {removed}")
        print("[done] Proceso completado")
        return 0
    except RuntimeError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
