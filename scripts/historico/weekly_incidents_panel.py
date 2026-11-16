"""
Figura: incidentes semanales por nivel de gravedad, 2016-2022.

Corre el pipeline completo de la skill scientific-figure en un solo paso:
construye el panel en matplotlib, lo compone al tamaño exacto de journal,
valida que ninguna fuente quede bajo el mínimo, y escribe el SVG final en
figures/svg/. Los archivos intermedios (panel suelto, config de composición)
viven en un directorio temporal y se borran solos.

    python figures/scripts/weekly_incidents_panel.py

Requiere uv en el PATH, que es como la skill ejecuta svgutils sin instalarlo.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".claude" / "skills" / "scientific-figure" / "scripts"
OUT = ROOT / "figures" / "svg" / "weekly-incidents.svg"

TREATMENT_DATE = pd.Timestamp("2019-04-22")

MM_TO_IN = 1 / 25.4
PT_TO_MM = 25.4 / 72  # el composer trabaja en mm y matplotlib exporta en pt
WIDTH_MM = 183  # Nature, dos columnas
HEIGHT_MM = 75
JOURNAL = "nature"

# Paleta sobria: azul tinta, verde salvia y ladrillo. Segura para daltonismo y
# distinguible en escala de grises. El orden sigue la frecuencia de cada nivel.
COLORS = {"MIN": "#2F4858", "PIC": "#86A873", "FCS": "#BC4B51"}
LABELS = {
    "MIN": "Menor (MIN)",
    "PIC": "Con lesionados (PIC)",
    "FCS": "Fatal (FCS)",
}

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


def weekly_counts() -> pd.DataFrame:
    """Conteo semanal por nivel, sin folios repetidos y con semanas vacías en cero."""
    incidentes = pd.read_parquet(ROOT / "data" / "classified-incidents.parquet")
    incidentes = incidentes.drop_duplicates(subset="folio")

    return incidentes.pivot_table(
        index=pd.Grouper(key="timestamp", freq="W"),
        columns="incident_level",
        values="folio",
        aggfunc="count",
        fill_value=0,
        observed=False,
    )


def build_panel(counts: pd.DataFrame, out: Path) -> None:
    """Escribe el panel como SVG al tamaño físico exacto que espera la composición.

    layout="constrained" en vez de bbox_inches="tight" al guardar: "tight" recorta
    el lienzo al contenido, y entonces el panel deja de medir WIDTH_MM x HEIGHT_MM.
    """
    fig, ax = plt.subplots(
        figsize=(WIDTH_MM * MM_TO_IN, HEIGHT_MM * MM_TO_IN),
        layout="constrained",
    )

    for level in ("MIN", "PIC", "FCS"):
        if level in counts.columns:
            ax.plot(
                counts.index,
                counts[level],
                color=COLORS[level],
                label=LABELS[level],
            )

    ax.axvline(TREATMENT_DATE, color="black", linewidth=0.6, linestyle="--", zorder=1)
    ax.annotate(
        "Fotocívicas\n22 abr 2019",
        xy=(TREATMENT_DATE, ax.get_ylim()[1]),
        xytext=(6, -2),
        textcoords="offset points",
        va="top",
        ha="left",
        fontsize=8,
    )

    ax.set_xlabel("Semana")
    ax.set_ylabel("Incidentes por semana")
    ax.set_ylim(bottom=0)
    ax.margins(x=0.01)

    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right", handlelength=1.4, borderaxespad=0.2)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="svg", transparent=True)
    plt.close(fig)


def compose(panel: Path, out: Path) -> None:
    """Coloca el panel en un lienzo de WIDTH_MM x HEIGHT_MM, convirtiendo pt a mm."""
    config = panel.parent / "panels-config.json"
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
        f"fuentes: {report['checked_count']} revisadas, "
        f"{report['issue_count']} bajo el mínimo de {report['minimum_pt']} pt "
        f"({report['skipped_count']} omitidas)"
    )
    for issue in report["issues"]:
        print(f"  - {issue['text']!r}: {issue['effective_pt']:.2f} pt")
    return report["issue_count"]


if __name__ == "__main__":
    counts = weekly_counts()
    print(
        f"{len(counts)} semanas, "
        f"{counts.index.min():%Y-%m-%d} a {counts.index.max():%Y-%m-%d}"
    )

    with tempfile.TemporaryDirectory() as tmp:
        panel = Path(tmp) / "weekly-incidents.svg"
        build_panel(counts, panel)
        compose(panel, OUT)

    issues = validate(OUT)
    print(f"escrito: {OUT.relative_to(ROOT)}")
    sys.exit(1 if issues else 0)
