"""
Figuras: red vial de la CDMX con las cámaras de Fotocívicas, en tres versiones.

Un mismo mapa con distintos criterios de color y capas:

- por tipo de vía (primaria vs acceso controlado) -> svg/road-network-tipo.svg
- por nivel de elevación (de -2 a +2)              -> svg/road-network-nivel.svg
- por nivel, más líneas y estaciones del Metro     -> svg/road-network-nivel-metro.svg

Corre el pipeline de la skill scientific-figure para cada una: construye el
panel en matplotlib, lo compone al tamaño exacto de journal, valida fuentes y
escribe el SVG final. Los intermedios viven en un directorio temporal.

    python figures/scripts/road_network_panel.py                # todas
    python figures/scripts/road_network_panel.py nivel-metro   # solo una

Requiere uv en el PATH, que es como la skill ejecuta svgutils sin instalarlo.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".claude" / "skills" / "scientific-figure" / "scripts"
SVG_DIR = ROOT / "figures" / "svg"

# CRS métrico para México: mantiene las distancias, así que la escala gráfica
# y la forma del mapa son correctas. Los datos vienen en EPSG:4326.
METRIC_CRS = "EPSG:6372"

MM_TO_IN = 1 / 25.4
PT_TO_MM = 25.4 / 72  # el composer trabaja en mm y matplotlib exporta en pt
WIDTH_MM = 89  # Nature, una columna
HEIGHT_MM = 94  # sigue el aspecto real de la extensión (35.9 x 37.7 km)
JOURNAL = "nature"

SCALEBAR_KM = 10

# Negro con halo blanco: neutro frente a las dos paletas, que ya usan tinta y
# ladrillo. Así las cámaras se leen igual en ambas versiones.
CAMERA_COLOR = "black"

# El color ya lo ocupa la variable de la vía, así que el Metro se distingue por
# forma: líneas punteadas, estaciones en cuadro hueco, cámaras en círculo lleno.
# Un gris neutro las agrupa como una sola capa sin competir con la divergente.
METRO_COLOR = "#3B3B3B"

# Cada esquema define con qué columna se colorea, en qué orden se dibujan las
# capas (las primeras quedan al fondo) y en qué orden aparecen en la leyenda.
SCHEMES = {
    # Categórico: dos clases sin orden entre ellas, paleta sobria.
    "tipo": {
        "column": "TIPO_VIA",
        "out": "road-network-tipo.svg",
        "colors": {
            "Vía de acceso controlado": "#2F4858",
            "Vía primaria": "#86A873",
        },
        "labels": {
            "Vía de acceso controlado": "Acceso controlado",
            "Vía primaria": "Vía primaria",
        },
        "linewidths": {"Vía de acceso controlado": 0.35, "Vía primaria": 0.35},
        # Las primarias son mayoría y sirven de fondo para el resto.
        "draw_order": ["Vía primaria", "Vía de acceso controlado"],
        "legend_order": ["Vía de acceso controlado", "Vía primaria"],
        "background": "Vía primaria",
        "metro": False,
    },
    # NIVEL es la elevación de la vía: negativo bajo tierra, 0 a nivel de calle,
    # positivo elevado. Variable ordenada y centrada en cero, así que la paleta
    # es divergente: tinta hacia abajo, ladrillo hacia arriba, gris neutro en
    # medio. El gris además funciona como fondo, que conviene porque el nivel 0
    # es el 91% de la red.
    "nivel": {
        "column": "NIVEL",
        "out": "road-network-nivel.svg",
        "colors": {-2: "#1F3A4D", -1: "#2F4858", 0: "#C4CACE", 1: "#BC4B51", 2: "#7E2E32"},
        "labels": {
            -2: "Dos niveles abajo",
            -1: "Un nivel abajo",
            0: "A nivel de calle",
            1: "Un nivel arriba",
            2: "Dos niveles arriba",
        },
        # Los desniveles van más gruesos: son pocos y son lo que la figura
        # quiere mostrar. Con el mismo grosor que el nivel 0 casi no se ven.
        "linewidths": {-2: 0.6, -1: 0.6, 0: 0.3, 1: 0.6, 2: 0.6},
        "draw_order": [0, -1, 1, -2, 2],
        "legend_order": [2, 1, 0, -1, -2],
        "background": 0,
        "metro": False,
    },
}

# La versión con Metro es la de nivel más una capa; se deriva para que ambas no
# se puedan desincronizar en colores o grosores.
SCHEMES["nivel-metro"] = {
    **SCHEMES["nivel"],
    "out": "road-network-nivel-metro.svg",
    "metro": True,
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.linewidth": 0.6,
        "svg.fonttype": "none",  # conserva el texto como <text>, no como paths
    }
)


def load_layers() -> dict[str, gpd.GeoDataFrame]:
    """Todas las capas, proyectadas al CRS métrico.

    El Metro sale del shapefile del STC, no del parquet geocodificado: trae las
    195 estaciones con línea y alcaldía, más las geometrías de las 12 líneas.

    Ojo con esos dos shapefiles: los dos se llaman `utm14n`, pero solo las líneas
    lo están (EPSG:32614). Las estaciones vienen en grados (EPSG:4326) pese al
    nombre. Cada `.prj` declara lo correcto, así que `to_crs` las alinea; lo que
    no se puede es ponerlas juntas sin reproyectar.
    """
    metro_dir = ROOT / "data" / "stcmetro_shp"

    capas = {
        "roads": gpd.read_file(ROOT / "data" / "vialidades.json"),
        "cameras": gpd.read_file(ROOT / "data" / "fotocivicas-ubicacion-puntos"),
        "metro_stations": gpd.read_file(metro_dir / "estaciones"),
        "metro_lines": gpd.read_file(metro_dir / "lineas"),
    }
    return {nombre: capa.to_crs(METRIC_CRS) for nombre, capa in capas.items()}


def add_scalebar(ax, km: int) -> None:
    """Barra de escala arriba a la izquierda, en coordenadas del mapa (metros).

    Va arriba porque la leyenda ocupa la franja inferior; abajo se encimaban.
    """
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    pad_x = (x1 - x0) * 0.06
    pad_y = (y1 - y0) * 0.06

    start = x0 + pad_x
    y = y1 - pad_y
    ax.plot(
        [start, start + km * 1000],
        [y, y],
        color="black",
        linewidth=1.0,
        solid_capstyle="butt",
    )
    ax.annotate(
        f"{km} km",
        xy=(start + km * 1000 / 2, y),
        xytext=(0, 2),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=8,
    )


def build_panel(capas: dict, scheme: dict, out: Path) -> None:
    """Escribe el panel como SVG al tamaño físico exacto que espera la composición."""
    roads = capas["roads"]
    cameras = capas["cameras"]
    fig, ax = plt.subplots(
        figsize=(WIDTH_MM * MM_TO_IN, HEIGHT_MM * MM_TO_IN),
        layout="constrained",
    )

    column = scheme["column"]
    for value in scheme["draw_order"]:
        subset = roads[roads[column] == value]
        if subset.empty:
            continue
        subset.plot(
            ax=ax,
            color=scheme["colors"][value],
            linewidth=scheme["linewidths"][value],
            zorder=2 if value == scheme["background"] else 3,
        )

    # El Metro va debajo de las cámaras: es contexto, no el objeto de estudio.
    # Punteado para que no se confunda con las vías, que ya usan línea continua.
    if scheme["metro"]:
        capas["metro_lines"].plot(
            ax=ax,
            color=METRO_COLOR,
            linewidth=0.5,
            linestyle=(0, (2.5, 1.2)),
            zorder=4,
        )
        capas["metro_stations"].plot(
            ax=ax,
            facecolor="white",
            edgecolor=METRO_COLOR,
            markersize=3.5,
            marker="s",
            linewidth=0.35,
            zorder=5,
        )

    cameras.plot(
        ax=ax,
        color=CAMERA_COLOR,
        markersize=3,
        marker="o",
        linewidth=0.3,
        edgecolor="white",
        zorder=6,
    )

    ax.set_aspect("equal")
    ax.set_axis_off()
    add_scalebar(ax, SCALEBAR_KM)

    presentes = [v for v in scheme["legend_order"] if (roads[column] == v).any()]
    handles = [
        Line2D([], [], color=scheme["colors"][v], linewidth=0.9, label=scheme["labels"][v])
        for v in presentes
    ] + [
        Line2D(
            [], [], color=CAMERA_COLOR, marker="o", markersize=3,
            markeredgecolor="white", markeredgewidth=0.3,
            linewidth=0, label=f"Cámara ({len(cameras)})",
        )
    ]
    if scheme["metro"]:
        handles += [
            Line2D(
                [], [], color=METRO_COLOR, linewidth=0.7,
                linestyle=(0, (2.5, 1.2)),
                label=f"Línea de Metro ({capas['metro_lines'].LINEA.nunique()})",
            ),
            Line2D(
                [], [], marker="s", markersize=3.5, markerfacecolor="white",
                markeredgecolor=METRO_COLOR, markeredgewidth=0.35,
                linewidth=0, label=f"Estación ({len(capas['metro_stations'])})",
            ),
        ]
    # Fondo blanco semiopaco y esquina inferior derecha. A partir de cinco
    # entradas la leyenda se parte en dos columnas: en una sola quedaba tan
    # alta que invadía la mancha urbana.
    ax.legend(
        handles=handles,
        loc="lower right",
        ncols=2 if len(handles) > 4 else 1,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        framealpha=0.85,
        borderaxespad=0.0,
        handlelength=1.2,
        columnspacing=1.0,
        handletextpad=0.5,
    )

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
        f"  fuentes: {report['checked_count']} revisadas, "
        f"{report['issue_count']} bajo el mínimo de {report['minimum_pt']} pt "
        f"({report['skipped_count']} omitidas)"
    )
    for issue in report["issues"]:
        print(f"    - {issue['text']!r}: {issue['effective_pt']:.2f} pt")
    return report["issue_count"]


def render(capas: dict, name: str) -> int:
    scheme = SCHEMES[name]
    out = SVG_DIR / scheme["out"]

    with tempfile.TemporaryDirectory() as tmp:
        panel = Path(tmp) / scheme["out"]
        build_panel(capas, scheme, panel)
        compose(panel, out)

    issues = validate(out)
    print(f"  escrito: {out.relative_to(ROOT)} ({out.stat().st_size / 1024:,.0f} KB)")
    return issues


if __name__ == "__main__":
    pedidos = sys.argv[1:] or list(SCHEMES)
    desconocidos = [p for p in pedidos if p not in SCHEMES]
    if desconocidos:
        sys.exit(f"esquema desconocido: {', '.join(desconocidos)}. Opciones: {', '.join(SCHEMES)}")

    capas = load_layers()
    bounds = capas["roads"].total_bounds
    print(
        f"{len(capas['roads']):,} segmentos, {len(capas['cameras'])} cámaras, "
        f"{len(capas['metro_stations'])} estaciones, "
        f"{len(capas['metro_lines'])} líneas | "
        f"extensión {(bounds[2] - bounds[0]) / 1000:.1f} x "
        f"{(bounds[3] - bounds[1]) / 1000:.1f} km"
    )

    issues = 0
    for name in pedidos:
        print(f"[{name}]")
        issues += render(capas, name)

    sys.exit(1 if issues else 0)
