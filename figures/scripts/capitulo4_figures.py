"""
Figuras del capítulo 4 (resultados), con el estilo de la tesis
(figures/tesis.mplstyle).

Port de las figuras de `scripts/resume-911/conclusiones.ipynb`:

1. conclusion-escalera: el efecto a 300 m conforme la comparación se vuelve
   más rigurosa. Los siete pasos se estiman en `interpretation.ipynb` (Parte I)
   y aquí, como en el notebook, solo se grafican.
2. conclusion-por-nivel: la especificación (3) por radio y tipo de incidente.
3. conclusion-brecha: tratadas menos controles antes y después, modelo (1).
4. conclusion-pandemia: serie mensual de tratadas y controles y volumen en casetas.
5. conclusion-por-anio: un coeficiente por año posterior.
6. conclusion-event-study: años previos y posteriores contra el año -1.

(conclusion-excluidas ya está en capitulo3_figures.py como unidades-excluidas.)

Y de `scripts/resume-911/interpretation.ipynb`, una por nivel de severidad:

7. efecto-por-radio[-min|-pic|-fcs]: Tratado × Post por radio, (1) y (3).
8. brecha-posterior[-min|-pic|-fcs]: Tratado + Tratado × Post por radio.

Los intervalos del bootstrap se leen de data/bootstrap-coeficientes.parquet;
no se recalculan.

    python figures/scripts/capitulo4_figures.py [--png]

Los PDF van a causal-effects-speed-cameras/Imagenes/; con --png queda además
una vista previa en figures/png/.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
PDF_DIR = ROOT / "causal-effects-speed-cameras" / "Imagenes"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from estilo_tesis import ACENTO, ANCHO, CLARO, OSCURO  # noqa: E402
from pipeline import NIVELES_TESIS, Datos, Panel, muestra_comun, tabla_resultados  # noqa: E402

RADIO = 300
NOMBRE_NIVEL = {"general": "Todos los incidentes", "MIN": "Sin lesionados (MIN)",
                "PIC": "Con lesionados (PIC)", "FCS": "Fatales (FCS)"}
ESPEC = {"(1) sin efectos fijos": "(1)", "(2) + EF unidad y tiempo": "(2)",
         "(3) + covariables x post": "(3)"}
PANDEMIA = pd.Timestamp("2020-03-23")   # Jornada Nacional de Sana Distancia


def cero(ax):
    ax.axhline(0, color="black", lw=.6, ls=":", zorder=1)


def resultados_con_bootstrap(emparejamientos, boot) -> pd.DataFrame:
    """tabla_resultados con el IC 95% percentil del bootstrap, como interpretation.ipynb."""
    r = tabla_resultados(emparejamientos)
    r["espec"] = r.especificacion.map(ESPEC)
    ic = (boot.groupby(["radio", "nivel", "especificacion"]).coef
          .agg(ic_bajo=lambda c: np.percentile(c, 2.5),
               ic_alto=lambda c: np.percentile(c, 97.5))
          .reset_index().rename(columns={"especificacion": "espec"}))
    r = r.merge(ic, on=["radio", "nivel", "espec"], how="left")
    r["ic_bajo %"] = 100 * r.ic_bajo / r.media_control
    r["ic_alto %"] = 100 * r.ic_alto / r.media_control
    return r


# =========================================================================
# conclusiones.ipynb
# =========================================================================

def escalera(boot) -> plt.Figure:
    """Los pasos a 300 m con todos los incidentes. IC analítico agrupado por
    componente; el último paso lleva además el del bootstrap del proceso completo."""
    pasos = pd.DataFrame([
        (1, "Antes y después,\nsolo tratadas",           -0.9374, 0.1613, 6.6630),
        (2, "Tratadas contra controles,\nsolo después",   2.2961, 0.3103, 3.4295),
        (3, "DiD contra toda la ciudad",                 -0.5253, 0.1646, 3.8416),
        (4, "+ efectos fijos de\nunidad y tiempo",        -0.5253, 0.1659, 3.8416),
        (5, "+ solo las 93 con\nsoporte común",           -0.3884, 0.1538, 3.8416),
        (6, "+ emparejamiento",                          -0.1476, 0.1981, 6.0194),
        (7, "+ covariables × post",                      -0.1063, 0.1808, 6.0194),
    ], columns=["paso", "comparacion", "coef", "EE", "base"]).set_index("paso")
    pasos["pct"] = 100 * pasos.coef / pasos.base
    pasos["bajo"] = 100 * (pasos.coef - 1.96 * pasos.EE) / pasos.base
    pasos["alto"] = 100 * (pasos.coef + 1.96 * pasos.EE) / pasos.base

    b = boot.query("radio == @RADIO and nivel == 'general' and especificacion == '(3)'").coef
    ic_boot = 100 * np.percentile(b, [2.5, 97.5]) / pasos.loc[7, "base"]

    # el paso 2 (+67%) no es un DiD y aplastaría la escala; el 4 es idéntico al 3
    g = pasos.loc[[1, 3, 5, 6, 7]]
    fig, ax = plt.subplots(figsize=(ANCHO, 2.7), layout="constrained")
    y = np.arange(len(g))[::-1]
    ax.axvline(0, color="black", lw=.6, ls=":")
    ax.hlines(y, g.bajo, g.alto, color=OSCURO, lw=1.2)
    ax.plot(g.pct, y, "o", color=OSCURO, ms=4)
    ax.hlines(y[-1] - .32, *ic_boot, color=ACENTO, lw=1.2)
    ax.text(ic_boot[0], y[-1] - .32, "bootstrap ", ha="right", va="center",
            fontsize=7.5, color=ACENTO)
    for yi, (_, fila) in zip(y, g.iterrows()):
        ax.text(fila.alto + .6, yi, f"{fila.pct:+.1f}%".replace("-", "−"), va="center",
                fontsize=7.5, bbox={"facecolor": "white", "edgecolor": "none", "pad": .5})
    ax.set_yticks(y, g.comparacion)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_ylim(-.65, len(g) - .5)
    ax.set_xlabel("Efecto estimado, % del nivel previo de la comparación (IC 95%)")
    return fig


def por_nivel(resultados) -> plt.Figure:
    principal = resultados.query("espec == '(3)'")
    fig, axes = plt.subplots(2, 2, figsize=(ANCHO, 3.8), sharex=True, layout="constrained")
    axes = axes.ravel()
    for ax in axes[1:3]:
        ax.sharey(axes[0])   # FCS va en su propia escala: sus intervalos son diez veces más anchos
    for ax, nivel, letra in zip(axes, NOMBRE_NIVEL, "abcd"):
        d = principal.query("nivel == @nivel").sort_values("radio")
        cero(ax)
        ax.vlines(d.radio, d["ic_bajo %"], d["ic_alto %"], color=OSCURO, lw=1.2)
        ax.plot(d.radio, d["% del control"], "o", color=OSCURO, ms=4)
        ax.set_title(f"({letra}) {NOMBRE_NIVEL[nivel]}")
        ax.set_xticks(d.radio)
        ax.tick_params(labelleft=True)
    for ax in axes[2:]:
        ax.set_xlabel("Radio (m)")
    fig.supylabel("Tratado × Post, % de la media previa del control\n(IC 95% bootstrap)",
                  fontsize=9)
    return fig


def brecha(resultados) -> plt.Figure:
    """Modelo (1): `tratado` es la brecha antes; `tratado + tratado:post`, después."""
    uno = resultados.query("espec == '(1)' and nivel == 'general'").sort_values("radio")
    fig, ax = plt.subplots(figsize=(ANCHO, 2.5), layout="constrained")
    cero(ax)
    for desplazamiento, columna, ee, estilo, etiqueta in [
            (-6, "tratado", "EE_tratado", dict(mfc="white", mec=OSCURO), "Antes"),
            (6, "suma", "EE_suma", dict(color=OSCURO), "Después")]:
        x = uno.radio + desplazamiento
        ax.vlines(x, uno[columna] - 1.96 * uno[ee], uno[columna] + 1.96 * uno[ee],
                  color=OSCURO, lw=1.2)
        ax.plot(x, uno[columna], "o", ms=4, label=etiqueta, **estilo)
    ax.set_xticks(uno.radio, [f"{r} m" for r in uno.radio])
    ax.set_ylabel("Tratadas menos controles\n(incidentes al mes, IC 95%)")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1), ncols=2)
    return fig


def pandemia(datos, e300) -> plt.Figure:
    panel = Panel(e300)
    serie = (panel.tabla.groupby(["t", "tratado"]).incidentes.mean().unstack()
             .rename(columns={0: "controles", 1: "tratadas"})
             .join(panel.periodos.set_index("t").inicio))
    volumen = datos.volumen.set_index("timestamp").volumen_mensual
    indice = 100 * volumen / volumen[volumen.index < datos.fecha_tratamiento].mean()

    fig, (arriba, abajo) = plt.subplots(2, 1, figsize=(ANCHO, 3.6), sharex=True,
                                        height_ratios=[2, 1], layout="constrained")
    for ax in (arriba, abajo):
        ax.axvline(datos.fecha_tratamiento, color="black", lw=.6, ls="--")
        ax.axvspan(PANDEMIA, PANDEMIA + pd.DateOffset(years=1), color=CLARO, alpha=.25, lw=0)
    for columna, color, etiqueta in [("tratadas", OSCURO, "Tratadas"),
                                     ("controles", CLARO, "Controles")]:
        arriba.plot(serie.inicio, serie[columna], color=color, lw=1.2, label=etiqueta)
    arriba.legend(loc="lower left", ncols=2)
    arriba.set_ylim(bottom=0)
    arriba.set_ylabel("Incidentes por\nunidad al mes")
    arriba.set_title("(a) Incidentes en tratadas y controles a 300 m")
    arriba.text(datos.fecha_tratamiento, arriba.get_ylim()[1], " Fotocívicas", va="top")
    arriba.text(PANDEMIA, 0.4, " primer año\n de pandemia")
    abajo.plot(indice.index, indice, color=OSCURO, lw=1.2)
    abajo.set_ylabel("Índice\n(media previa = 100)")
    abajo.set_title("(b) Volumen vehicular en casetas de peaje")
    return fig


ANIOS = {"año 1": (0, 11), "año 2": (12, 23), "año 3": (24, 35)}


def efecto_por_anio(emparejamiento, niveles=None) -> pd.DataFrame:
    """El DiD de la especificación (3), con un coeficiente por año posterior."""
    p = Panel(emparejamiento, niveles=niveles)
    tabla = p.tabla.copy()
    for k, (desde, hasta) in enumerate(ANIOS.values(), start=1):
        anio = tabla.t.between(desde, hasta).astype(int)
        tabla[f"trat_a{k}"] = tabla.tratado * anio
        for c in p.covariables:
            tabla[f"{c}_a{k}"] = tabla[f"z_{c}"] * anio
    formula = ("incidentes ~ trat_a1 + trat_a2 + trat_a3 + "
               + " + ".join(f"{c}_a{k}" for k in (1, 2, 3) for c in p.covariables)
               + " + C(uid) + C(t)")
    r = smf.ols(formula, data=tabla).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(tabla.cluster)[0]})
    base = tabla[(tabla.tratado == 0) & (tabla.t < 0)].incidentes.mean()
    return pd.DataFrame([{
        "año": anio,
        "%": 100 * r.params[f"trat_a{k}"] / base,
        "IC bajo %": 100 * (r.params[f"trat_a{k}"] - 1.96 * r.bse[f"trat_a{k}"]) / base,
        "IC alto %": 100 * (r.params[f"trat_a{k}"] + 1.96 * r.bse[f"trat_a{k}"]) / base,
    } for k, anio in enumerate(ANIOS, start=1)])


def por_anio(e300) -> plt.Figure:
    tabla = pd.concat({nivel: efecto_por_anio(e300, niveles)
                       for nivel, niveles in NIVELES_TESIS.items()}, names=["nivel"])
    fig, axes = plt.subplots(2, 2, figsize=(ANCHO, 3.9), sharex=True, layout="constrained")
    for ax, nivel, letra in zip(axes.ravel(), NOMBRE_NIVEL, "abcd"):
        d = tabla.loc[nivel]
        x = np.arange(len(d))
        cero(ax)
        ax.vlines(x, d["IC bajo %"], d["IC alto %"], color=OSCURO, lw=1.2)
        ax.plot(x, d["%"], "o", color=OSCURO, ms=4)
        ax.set_xticks(x, ["abr 2019–\nabr 2020", "abr 2020–\nabr 2021", "abr 2021–\nabr 2022"])
        ax.set_xlim(-.5, 2.5)
        ax.set_title(f"({letra}) {NOMBRE_NIVEL[nivel]}")
    fig.supylabel("Tratado × año, % de la media previa del control\n(IC 95%)", fontsize=9)
    return fig


EVENTO = {-3: (-36, -25), -2: (-24, -13), 1: (0, 11), 2: (12, 23), 3: (24, 35)}


def event_study(emparejamiento, niveles=None) -> pd.DataFrame:
    p = Panel(emparejamiento, niveles=niveles)
    tabla = p.tabla.copy()
    terminos, nombres = [], {}
    for k, (desde, hasta) in EVENTO.items():
        sufijo = f"m{-k}" if k < 0 else f"p{k}"
        anio = tabla.t.between(desde, hasta).astype(int)
        tabla[f"trat_{sufijo}"] = tabla.tratado * anio
        nombres[k] = f"trat_{sufijo}"
        terminos.append(f"trat_{sufijo}")
        for c in p.covariables:
            tabla[f"{c}_{sufijo}"] = tabla[f"z_{c}"] * anio
            terminos.append(f"{c}_{sufijo}")
    r = smf.ols("incidentes ~ " + " + ".join(terminos) + " + C(uid) + C(t)", data=tabla).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(tabla.cluster)[0]})
    base = tabla[(tabla.tratado == 0) & (tabla.t < 0)].incidentes.mean()
    filas = [{"año": -1, "coef": 0.0, "EE": 0.0}] + [
        {"año": k, "coef": r.params[n], "EE": r.bse[n]} for k, n in nombres.items()]
    d = pd.DataFrame(filas).sort_values("año").set_index("año")
    for c in ("coef", "EE"):
        d[f"{c} %"] = 100 * d[c] / base
    return d


def evento(emparejamientos) -> plt.Figure:
    tabla = pd.concat({radio: event_study(e) for radio, e in emparejamientos.items()},
                      names=["radio"])
    fig, axes = plt.subplots(2, 3, figsize=(ANCHO, 3.6), sharey=True, layout="constrained")
    axes = axes.ravel()
    axes[-1].set_axis_off()
    for ax, radio, letra in zip(axes, emparejamientos, "abcde"):
        d = tabla.loc[radio]
        x = d.index.to_numpy()
        # el periodo posterior va sombreado, en lugar de una línea vertical
        ax.axvspan(0, 3.6, color=CLARO, alpha=.25, lw=0)
        cero(ax)
        ax.vlines(x, d["coef %"] - 1.96 * d["EE %"], d["coef %"] + 1.96 * d["EE %"],
                  color=OSCURO, lw=1.2)
        ax.plot(x[x != -1], d.loc[x != -1, "coef %"], "o", color=OSCURO, ms=4)
        ax.plot([-1], [0], "o", mfc="white", mec=OSCURO, ms=4)   # referencia, fija en cero
        ax.set_xticks(x, [f"{k:+d}".replace("-", "−") for k in x], fontsize=7)
        ax.set_xlim(-3.6, 3.6)
        ax.set_title(f"({letra}) {radio} m")
    for ax in axes[:-1]:
        ax.text(-2, ax.get_ylim()[1], "antes", ha="center", va="top", fontsize=7.5)
        ax.text(2, ax.get_ylim()[1], "después", ha="center", va="top", fontsize=7.5)
    fig.supylabel("Tratado × año, % de la media previa del control\n(IC 95%)", fontsize=9)
    fig.supxlabel("Años desde la entrada de Fotocívicas (año −1 = referencia, punto hueco)",
                  fontsize=9)
    return fig


# =========================================================================
# interpretation.ipynb
# =========================================================================

def datos_para_figuras(resultados, nivel, n_radios):
    """Las especificaciones (1) y (3) de un nivel. (1) y (2) tienen el mismo
    coeficiente, así que (1) toma el IC del bootstrap de (2)."""
    d = resultados[resultados.nivel.eq(nivel)]
    base_1 = d[d.espec.eq("(1)")].set_index("radio").sort_index()
    base_2 = d[d.espec.eq("(2)")].set_index("radio").sort_index()
    assert base_1.index.equals(base_2.index) and len(base_1) == n_radios
    np.testing.assert_allclose(base_1.coef, base_2.coef, rtol=0, atol=1e-10)

    grafica = (d[d.espec.isin(["(1)", "(3)"])]
               [["radio", "espec", "coef", "ic_bajo", "ic_alto", "media_control"]]
               .sort_values(["espec", "radio"]).copy())
    sin_ef = grafica.espec.eq("(1)")
    for limite in ("ic_bajo", "ic_alto"):
        grafica.loc[sin_ef, limite] = grafica.loc[sin_ef, "radio"].map(base_2[limite])
    grafica["coef_pct"] = 100 * grafica.coef / grafica.media_control
    grafica["bajo_pct"] = 100 * grafica.ic_bajo / grafica.media_control
    grafica["alto_pct"] = 100 * grafica.ic_alto / grafica.media_control
    return base_1, grafica


def efecto_por_radio(resultados, nivel, n_radios) -> plt.Figure:
    base_1, grafica = datos_para_figuras(resultados, nivel, n_radios)
    radios = base_1.index.to_numpy()
    dec = 3 if nivel == "FCS" else 2
    # tres renglones para que la media (DE) del control quepa entre radios
    etiquetas = [f"{int(r)} m\n{m:.{dec}f}\n({sd:.{dec}f})"
                 for r, m, sd in zip(radios, base_1.media_control, base_1.sd_control)]
    series = [("(1)", "Sin EF ni covariables"), ("(3)", "EF + covariables × post")]
    escalas = [("coef", "ic_bajo", "ic_alto"), ("coef_pct", "bajo_pct", "alto_pct")]

    fig, axes = plt.subplots(2, 2, sharex="col", sharey="row", figsize=(ANCHO, 4.4),
                             layout="constrained")
    for columna, (espec, nombre) in enumerate(series):
        d = grafica[grafica.espec.eq(espec)]
        x = d.radio.to_numpy()
        for fila, (valor, bajo, alto) in enumerate(escalas):
            ax = axes[fila, columna]
            y, lo, hi = (d[c].to_numpy() for c in (valor, bajo, alto))
            con_ic = np.isfinite(lo) & np.isfinite(hi)
            cero(ax)
            ax.plot(x, y, "o", color=OSCURO, ms=3.5, zorder=3)
            ax.vlines(x[con_ic], lo[con_ic], hi[con_ic], color=OSCURO, lw=.8, zorder=2)
            for extremo in (lo, hi):
                ax.hlines(extremo[con_ic], x[con_ic] - 4, x[con_ic] + 4, color=OSCURO, lw=.8)
            for radio, estimado in zip(x, y):
                texto = (f"{estimado:+.{3 if nivel == 'FCS' else 2}f}" if fila == 0
                         else f"{estimado:+.1f}")   # el eje ya dice que es %
                # a la derecha del punto, entre su intervalo y el del radio siguiente
                ax.annotate(texto.replace("-", "−"), (radio, estimado),
                            xytext=(4, 0), textcoords="offset points",
                            ha="left", va="center", fontsize=7, zorder=4,
                            bbox={"facecolor": "white", "edgecolor": "none", "pad": .3})
            ax.set_xlim(80, 340)
            ax.margins(y=.12)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
            letra = "abcd"[2 * fila + columna]
            ax.set_title(f"({letra}) {espec} {nombre}"
                         + (", %" if fila else ""))
        axes[1, columna].set_xticks(radios, etiquetas, fontsize=7)
    axes[0, 0].set_ylabel("Incidentes mensuales\npor unidad")
    axes[1, 0].set_ylabel("% de la media previa\ndel control")
    fig.supxlabel("Radio; debajo, media (DE) previa del control en incidentes por unidad al mes",
                  fontsize=8)
    return fig


def brecha_posterior(resultados, nivel, n_radios) -> plt.Figure:
    base_1, _ = datos_para_figuras(resultados, nivel, n_radios)
    radios = base_1.index.to_numpy()
    dec = 4 if nivel == "FCS" else 2
    fig, ax = plt.subplots(figsize=(ANCHO, 2.5), layout="constrained")
    cero(ax)
    ax.errorbar(radios, base_1.suma, yerr=base_1.EE_suma, fmt="o", color=OSCURO,
                lw=.8, capsize=2.5, ms=3.5)
    for radio, valor, sig in zip(radios, base_1.suma, base_1.sig_suma):
        ax.annotate(f"{valor:+.{dec}f}{sig}".replace("-", "−"), (radio, valor),
                    xytext=(5, 0), textcoords="offset points", va="center", fontsize=7,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": .5})
    ax.set_xlim(80, 335)
    ax.set_xticks(radios)
    ax.set_xlabel("Radio (m)")
    ax.set_ylabel("Tratado + Tratado × Post\n(incidentes al mes, ±1 EE)")
    ax.margins(y=.15)
    return fig


if __name__ == "__main__":
    datos = Datos()
    emparejamientos, comunes = muestra_comun(datos)
    e300 = emparejamientos[RADIO]
    boot = pd.read_parquet(DATA / "bootstrap-coeficientes.parquet")
    resultados = resultados_con_bootstrap(emparejamientos, boot)

    figuras = {
        "conclusion-escalera": escalera(boot),
        "conclusion-por-nivel": por_nivel(resultados),
        "conclusion-brecha": brecha(resultados),
        "conclusion-pandemia": pandemia(datos, e300),
        "conclusion-por-anio": por_anio(e300),
        "conclusion-event-study": evento(emparejamientos),
    }
    for nivel in NOMBRE_NIVEL:
        sufijo = "" if nivel == "general" else f"-{nivel.lower()}"
        n = len(emparejamientos)
        figuras[f"efecto-por-radio{sufijo}"] = efecto_por_radio(resultados, nivel, n)
        figuras[f"brecha-posterior{sufijo}"] = brecha_posterior(resultados, nivel, n)

    vista = "--png" in sys.argv
    for nombre, fig in figuras.items():
        fig.savefig(PDF_DIR / f"{nombre}.pdf")
        if vista:  # para revisar sin compilar la tesis
            fig.savefig(ROOT / "figures" / "png" / f"{nombre}.png", dpi=200)
        plt.close(fig)
