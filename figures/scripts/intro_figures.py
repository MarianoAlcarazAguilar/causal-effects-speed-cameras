"""
Figuras de la introducción: incidentes por año y nivel, accidentes fatales por
año e infracciones por tipo de sanción.

Corre el pipeline de la skill scientific-figure para cada figura: construye el
panel en matplotlib, lo compone al ancho exacto del texto de la tesis, valida
que ninguna fuente quede bajo el mínimo y exporta el PDF que incluye LaTeX. El
SVG final queda en figures/svg/ y el PDF en causal-effects-speed-cameras/Imagenes/.

    python figures/scripts/intro_figures.py

Requiere uv en el PATH, que es como la skill ejecuta svgutils y cairosvg sin
instalarlos.

Los datos están escritos aquí porque no hay otra copia de ellos en el repo. Los
totales y los fatales salen de la base del C5 2014-2023 (incidentes-viales.parquet),
que no está versionada; son los valores que anotaba scripts/auxiliar/5-other-stuff.ipynb
y sus promedios anuales reproducen los de ese notebook (85,150 y 383). Los
lesionados se leyeron de los marcadores de la figura vieja, calibrando el eje
con los totales: el error es de unos cien incidentes y su suma cae a 42 de la
que implica el notebook. Los menores son el residuo, para que las series sumen
el total. Las infracciones las
transcribió Mariano a mano de un PDF de la autoridad.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".claude" / "skills" / "scientific-figure" / "scripts"
SVG_DIR = ROOT / "figures" / "svg"
PDF_DIR = ROOT / "causal-effects-speed-cameras" / "Imagenes"

MM_TO_IN = 1 / 25.4
PT_TO_MM = 25.4 / 72  # el composer trabaja en mm y matplotlib exporta en pt
# Ancho del texto: papel de 170 mm con geometry por defecto (hscale 0.7). Las
# figuras entran con width=\linewidth, así que se imprimen a tamaño real.
WIDTH_MM = 119
HEIGHT_MM = 62
JOURNAL = "science"  # mínimo de 6 pt, holgado para una página de 170 mm

# Misma paleta que weekly_incidents_panel.py, para que las figuras de la tesis
# se lean como un sistema.
INK = "#2F4858"
SAGE = "#86A873"
FATAL = "#BC4B51"
LIGHT = "#A9BCC6"
GRAY = "#6B6B6B"

# La política arranca el 22 de abril de 2019. Con datos anuales, la línea va
# entre 2018 (último año completo previo) y 2019 (primer año con fotocívicas).
POLICY_X = 2018.5

FATALES = pd.Series(
    [482, 457, 351, 316, 295, 345, 303, 330, 491, 464],
    index=range(2014, 2024),
)

INCIDENTES = pd.DataFrame(
    {
        "total": [138_396, 109_620, 77_468, 75_929, 75_853, 75_513, 56_254, 71_922, 87_336, 83_211],
        "lesionados": [52_824, 39_722, 27_126, 30_169, 31_184, 32_198, 28_986, 37_270, 48_429, 48_429],
        "fatales": FATALES.to_list(),
    },
    index=range(2014, 2024),
).assign(menores=lambda df: df.total - df.lesionados - df.fatales)

INFRACCIONES = pd.DataFrame(
    {
        "civica": [500_082, 566_395, 720_718, 667_598, 202_758],
        "economica": [1_598_331, 2_039_552, 3_235_329, 2_773_361, 1_237_133],
    },
    index=range(2019, 2024),
)

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 11,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "lines.linewidth": 0.9,
        "svg.fonttype": "none",  # conserva el texto como <text>, no como paths
    }
)


def new_panel():
    """Lienzo al tamaño físico exacto. layout="constrained" en vez de
    bbox_inches="tight": "tight" recorta el lienzo y cambia sus medidas."""
    fig, ax = plt.subplots(
        figsize=(WIDTH_MM * MM_TO_IN, HEIGHT_MM * MM_TO_IN),
        layout="constrained",
    )
    ax.spines[["top", "right"]].set_visible(False)
    return fig, ax


def mark_policy(ax) -> None:
    ax.axvline(POLICY_X, color="black", linewidth=0.6, linestyle="--", zorder=1)
    ax.annotate(
        "Fotocívicas\n22 abr 2019",
        xy=(POLICY_X, ax.get_ylim()[1]),
        xytext=(4, -2),
        textcoords="offset points",
        va="top",
        ha="left",
        fontsize=8,
    )


def build_incidentes(out: Path) -> None:
    fig, ax = new_panel()

    # Misma asignación de color por nivel que weekly_incidents_panel.py; el total
    # va en negro. Los marcadores distintos sostienen la lectura en gris.
    series = [
        ("total", "Total", "black", "o"),
        ("menores", "Menores", INK, "^"),
        ("lesionados", "Con lesionados", SAGE, "s"),
        ("fatales", "Fatales", FATAL, "X"),
    ]
    for column, label, color, marker in series:
        ax.plot(
            INCIDENTES.index,
            INCIDENTES[column] / 1e3,
            color=color,
            marker=marker,
            markersize=3.5,
            label=label,
        )

    # Tras una caída fuerte, la línea entra por arriba a la izquierda y taparía
    # la etiqueta centrada; ahí se corre a la derecha.
    total = INCIDENTES.total
    lean_right = (total.shift(1) - total > 10_000) & (total.shift(-1) - total < 5_000)
    for year, value in total.items():
        ax.annotate(
            f"{value / 1e3:.1f}",
            xy=(year, value / 1e3),
            xytext=(7, 3) if lean_right[year] else (0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax.set_xticks(INCIDENTES.index)
    ax.set_xlabel("Año")
    ax.set_ylabel("Incidentes (miles)")
    ax.set_ylim(0, 155)
    ax.set_xlim(2013.5, 2023.5)
    ax.legend(frameon=False, loc="upper right", handlelength=1.6, borderaxespad=0.2)
    mark_policy(ax)

    fig.savefig(out, format="svg", transparent=True)
    plt.close(fig)


def build_fatales(out: Path) -> None:
    fig, ax = new_panel()

    ax.plot(FATALES.index, FATALES, color=FATAL, marker="o", markersize=3.5)
    for year, value in FATALES.items():
        ax.annotate(
            f"{value}",
            xy=(year, value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=FATAL,
        )

    ax.set_xticks(FATALES.index)
    ax.set_xlabel("Año")
    ax.set_ylabel("Accidentes fatales")
    ax.set_ylim(0, 560)
    ax.set_xlim(2013.5, 2023.5)
    mark_policy(ax)

    fig.savefig(out, format="svg", transparent=True)
    plt.close(fig)


def build_infracciones(out: Path) -> None:
    fig, ax = new_panel()

    civica = INFRACCIONES.civica / 1e6
    economica = INFRACCIONES.economica / 1e6
    total = civica + economica

    ax.bar(INFRACCIONES.index, civica, width=0.6, color=INK, label="Cívicas")
    ax.bar(
        INFRACCIONES.index,
        economica,
        width=0.6,
        bottom=civica,
        color=LIGHT,
        label="Económicas",
    )

    # El texto cita la proporción de sanciones cívicas, así que es lo que se anota.
    for year, share, height in zip(INFRACCIONES.index, civica / total, total):
        ax.annotate(
            f"{share:.0%} cívicas",
            xy=(year, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=INK,
        )

    ax.set_xticks(INFRACCIONES.index)
    ax.set_xlabel("Año")
    ax.set_ylabel("Infracciones (millones)")
    ax.set_ylim(0, 4.5)
    ax.tick_params(axis="x", length=0)
    ax.legend(frameon=False, loc="upper right", handlelength=1.2, borderaxespad=0.2)

    fig.savefig(out, format="svg", transparent=True)
    plt.close(fig)


def compose(panel: Path, out: Path) -> None:
    """Coloca el panel en un lienzo de WIDTH_MM x HEIGHT_MM, convirtiendo pt a mm."""
    config = panel.with_suffix(".json")
    config.write_text(
        json.dumps(
            {
                "width_mm": WIDTH_MM,
                "height_mm": HEIGHT_MM,
                "journal": JOURNAL,
                "panels": [
                    {
                        "id": "A",
                        "src": panel.name,
                        "x_mm": 0,
                        "y_mm": 0,
                        "scale": PT_TO_MM,
                    }
                ],
            },
            indent=2,
        )
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "uv", "run", "--quiet", "--with", "svgutils", "--with", "lxml",
            "python", str(SKILL / "compose.py"), str(config), "-o", str(out),
        ],
        check=True,
        cwd=panel.parent,
        stdout=subprocess.DEVNULL,
    )


def validate(svg: Path) -> int:
    """Devuelve cuántos textos quedan bajo el mínimo del journal."""
    result = subprocess.run(
        [
            "uv", "run", "--quiet", "--with", "lxml",
            "python", str(SKILL / "validate_fonts.py"), str(svg), "--journal", JOURNAL,
        ],
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    print(
        f"  fuentes: {report['checked_count']} revisadas, "
        f"{report['issue_count']} bajo el mínimo de {report['minimum_pt']} pt "
        f"({report['skipped_count']} omitidas)"
    )
    for issue in report["issues"]:
        print(f"  - {issue['text']!r}: {issue['effective_pt']:.2f} pt")
    return report["issue_count"]


def export(svg: Path, out: Path) -> None:
    """cairosvg necesita libcairo, que en esta máquina solo trae el entorno de
    conda tesis-cameras. Se la señalo con DYLD_FALLBACK_LIBRARY_PATH."""
    env = {**os.environ, "DYLD_FALLBACK_LIBRARY_PATH": str(Path(sys.prefix) / "lib")}
    subprocess.run(
        [
            "uv", "run", "--quiet", "--with", "cairosvg",
            "python", str(SKILL / "export.py"), str(svg), "--out", str(out),
        ],
        check=True,
        env=env,
    )


FIGURES = {
    "yearly-number-of-incidents": build_incidentes,
    "yearly-fatal-number-of-incidents": build_fatales,
    "yearly-number-of-sanctions": build_infracciones,
}


if __name__ == "__main__":
    issues = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, build in FIGURES.items():
            panel = Path(tmp) / f"{name}.svg"
            svg = SVG_DIR / f"{name}.svg"
            pdf = PDF_DIR / f"{name}.pdf"

            build(panel)
            compose(panel, svg)
            print(name)
            issues += validate(svg)
            export(svg, pdf)
            print(f"  escrito: {svg.relative_to(ROOT)} y {pdf.relative_to(ROOT)}")

    sys.exit(1 if issues else 0)
