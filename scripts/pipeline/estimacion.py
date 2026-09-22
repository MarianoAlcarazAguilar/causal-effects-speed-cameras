"""
Panel de estimación y diferencias en diferencias.

Convierte un emparejamiento en el panel de unidad × periodo y corre las
especificaciones de la tesis. Las decisiones están justificadas en
`scripts/resume-911/did-estimation.ipynb`; aquí se documentan, no se argumentan.

    from pipeline import Datos, muestra_comun, Panel, tabla_resultados

    datos = Datos()
    emparejamientos, comunes = muestra_comun(datos)

    Panel(emparejamientos[300]).resumen()
    tabla_resultados(emparejamientos)     # 5 radios × 4 niveles × 3 especificaciones

## Los periodos no son meses de calendario

Van del 22 al 22, porque las Fotocívicas entraron en vigor el 22 de abril de
2019. Así el corte cae exacto en la frontera entre `t = -1` y `t = 0`, no hay mes
partido, la ventana queda simétrica con 36 periodos de cada lado, y `t` es
directamente tiempo de evento.

## Los ceros y los pesos

Un mes sin incidentes es un cero, no una fila ausente: el panel se arma sobre el
producto completo unidad × periodo. Y un incidente en área compartida entre dos
círculos tratados entra con 1/k en cada uno, como lo decidió `UnidadesTratadas`.
Por eso el conteo es flotante y el panel no sirve para Poisson sin replantear el
reparto.

## Las tres especificaciones

El coeficiente de interés es el mismo en las tres y significa lo mismo. La (1)
existe porque es la única donde `tratado` y `post` sobreviven, y por lo tanto la
única donde se puede reportar la suma `tratado + tratado:post` que pidió el
asesor. Con efectos fijos de unidad las dos son colineales y desaparecen; el
intercepto queda pero es un artefacto de qué dummy se omitió.

Que la (1) y la (2) den idéntico no es casualidad: con panel balanceado,
tratamiento simultáneo y los dos grupos en los dos periodos, el regresor
residualizado vale ±0.25 según el cuadrante y es ortogonal a los efectos fijos.

## El clustering

Por componente traslapada, no por unidad. Dos círculos que comparten área
registran los mismos eventos: la correlación de sus residuales es 0.19 en mediana
y llega a 0.58. Las dos particiones están anidadas, así que se usa la más gruesa;
a 100 m no hay traslape y la componente es la unidad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

if __package__:
    from .emparejamiento import Emparejamiento
    from .features import COVARIABLES
else:  # ejecutado como script suelto
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline.emparejamiento import Emparejamiento
    from pipeline.features import COVARIABLES

# Las cuatro que derivan de la variable de resultado. Meter el nivel previo
# interactuado con post afirma que el nivel previo determina la evolución
# posterior, que es lo que el supuesto de tendencias paralelas supone que no
# pasa. El asesor dijo "menos la variable dependiente pre-tratamiento": el
# criterio literal saca dos, el estricto saca estas cuatro.
COVARIABLES_FUERA = ("nivel_incidentes", "tendencia", "pct_lesionados", "hubo_fcs")

# Las cuatro tablas de resultados de la tesis.
NIVELES_TESIS = {"general": None, "MIN": ("MIN",), "PIC": ("PIC",), "FCS": ("FCS",)}


def estrellas(p: float) -> str:
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


@dataclass
class Panel:
    """Panel de unidad × periodo para un emparejamiento.

    Parameters
    ----------
    emparejamiento : Emparejamiento
        De aquí salen los pares, las covariables y el traslape entre tratadas.
    niveles : tuple[str, ...] | None
        Qué incidentes cuenta la variable de resultado. `None` los cuenta todos.
    covariables_fuera : tuple[str, ...]
        Las que no entran interactuadas con post.
    """

    emparejamiento: Emparejamiento
    niveles: tuple[str, ...] | None = None
    covariables_fuera: tuple[str, ...] = COVARIABLES_FUERA

    def __post_init__(self) -> None:
        desconocidos = set(self.niveles or ()) - {"MIN", "PIC", "FCS"}
        if desconocidos:
            raise ValueError(f"niveles desconocidos: {sorted(desconocidos)}")

    @property
    def datos(self):
        return self.emparejamiento.features.datos

    @property
    def radio_m(self) -> float:
        return self.emparejamiento.radio_m

    @property
    def covariables(self) -> list[str]:
        return [c for c in COVARIABLES if c not in self.covariables_fuera]

    @property
    def interacciones(self) -> list[str]:
        return [f"{c}_post" for c in self.covariables]

    # =====================================================================
    # Ejes
    # =====================================================================

    @cached_property
    def cortes(self) -> pd.DatetimeIndex:
        """Fronteras de los periodos: el día 22 hace las veces de primero de mes."""
        corte, (inicio, fin) = self.datos.fecha_tratamiento, self.datos.ventana

        k_min = 0
        while corte + pd.DateOffset(months=k_min - 1) >= inicio:
            k_min -= 1
        k_max = 0
        while corte + pd.DateOffset(months=k_max + 1) <= fin + pd.Timedelta(days=1):
            k_max += 1
        k_max -= 1

        self._t = np.arange(k_min, k_max + 1)
        return pd.DatetimeIndex(
            [corte + pd.DateOffset(months=int(k)) for k in range(k_min, k_max + 2)]
        )

    @cached_property
    def periodos(self) -> pd.DataFrame:
        cortes = self.cortes
        return pd.DataFrame({
            "t": self._t,
            "inicio": cortes[:-1],
            "post": (self._t >= 0).astype(int),
        })

    @cached_property
    def unidades(self) -> pd.DataFrame:
        """Una fila por unidad emparejada. `par` dice qué control le tocó a quién."""
        pares = self.emparejamiento.pares
        return pd.concat([
            pd.DataFrame({"uid": pares.tratada, "par": pares.index, "tratado": 1}),
            pd.DataFrame({"uid": pares.control, "par": pares.index, "tratado": 0}),
        ], ignore_index=True)

    @cached_property
    def clusters(self) -> pd.Series:
        """Cluster por unidad: las tratadas que comparten área van juntas."""
        pares = self.emparejamiento.pares
        ids = sorted(int(u[1:]) for u in pares.tratada)

        traslapes = self.emparejamiento.features.tratadas.pares_traslapados
        traslapes = traslapes[
            traslapes.unidad_a.isin(ids) & traslapes.unidad_b.isin(ids)
        ]

        posicion = {u: i for i, u in enumerate(ids)}
        adyacencia = coo_matrix(
            (np.ones(len(traslapes)),
             ([posicion[a] for a in traslapes.unidad_a],
              [posicion[b] for b in traslapes.unidad_b])),
            shape=(len(ids),) * 2,
        )
        _, etiqueta = connected_components(adyacencia, directed=False)

        # cada control conserva su cluster: no comparte incidentes con nadie
        componente = {f"T{u}": f"G{c}" for u, c in zip(ids, etiqueta)}
        return self.unidades.uid.map(componente).fillna(self.unidades.uid)

    # =====================================================================
    # Panel
    # =====================================================================

    @cached_property
    def incidentes(self) -> pd.DataFrame:
        """Incidentes de las unidades emparejadas, con su periodo asignado."""
        inc = self.emparejamiento.features.incidentes_asignados
        inc = inc[inc.uid.isin(self.unidades.uid)]
        if self.niveles is not None:
            inc = inc[inc.incident_level.isin(self.niveles)]

        cortes = self.cortes
        indice = np.searchsorted(cortes, inc.timestamp, side="right") - 1
        dentro = (indice >= 0) & (indice < len(self.periodos))
        return inc[dentro].assign(t=self._t[indice[dentro]])

    @cached_property
    def tabla(self) -> pd.DataFrame:
        """El panel, con clusters e interacciones listos para estimar."""
        unidades, periodos = self.unidades, self.periodos

        malla = pd.MultiIndex.from_product(
            [unidades.uid, periodos.t], names=["uid", "t"]
        )
        panel = (
            self.incidentes.groupby(["uid", "t"]).peso.sum()
            .reindex(malla, fill_value=0.0).rename("incidentes").reset_index()
            .merge(unidades, on="uid")
            .merge(periodos[["t", "inicio", "post"]], on="t")
        )

        if abs(panel.incidentes.sum() - self.incidentes.peso.sum()) > 1e-6:
            raise ValueError("el panel no suma lo que entró")

        panel["cluster"] = panel.uid.map(
            dict(zip(unidades.uid, self.clusters))
        )

        # las covariables se estandarizan para no dejar mal condicionada la
        # matriz; no cambia el ajuste y sus coeficientes no se reportan
        cov = self.emparejamiento.features.matriz.loc[unidades.uid, self.covariables]
        z = (cov - cov.mean()) / cov.std()
        panel = panel.merge(
            z.rename(columns=lambda c: f"z_{c}"), left_on="uid", right_index=True
        )
        for c in self.covariables:
            panel[f"{c}_post"] = panel[f"z_{c}"] * panel.post

        panel["treat_post"] = panel.tratado * panel.post
        return panel.sort_values(["uid", "t"]).reset_index(drop=True)

    # =====================================================================
    # Estimación
    # =====================================================================

    @property
    def especificaciones(self) -> dict[str, str]:
        return {
            "(1) sin efectos fijos": "incidentes ~ tratado + post + tratado:post",
            "(2) + EF unidad y tiempo": "incidentes ~ treat_post + C(uid) + C(t)",
            "(3) + covariables x post": (
                "incidentes ~ treat_post + "
                + " + ".join(self.interacciones)
                + " + C(uid) + C(t)"
            ),
        }

    def estimar(self, formula: str) -> dict:
        """Una regresión, con todo lo que pide el cuadro de resultados."""
        tabla = self.tabla
        r = smf.ols(formula, data=tabla).fit(
            cov_type="cluster", cov_kwds={"groups": tabla.cluster}
        )
        interaccion = "tratado:post" if "tratado:post" in r.params else "treat_post"
        control = tabla[(tabla.tratado == 0) & (tabla.post == 0)]

        fila = {
            "tratado": r.params.get("tratado", np.nan),
            "EE_tratado": r.bse.get("tratado", np.nan),
            "post": r.params.get("post", np.nan),
            "EE_post": r.bse.get("post", np.nan),
            "coef": r.params[interaccion],
            "EE": r.bse[interaccion],
            "sig": estrellas(r.pvalues[interaccion]),
            "t": r.tvalues[interaccion],
        }

        if "tratado" in r.params:  # la brecha que queda después del tratamiento
            suma = r.t_test(f"tratado + {interaccion} = 0")
            fila |= {
                "suma": float(suma.effect[0]),
                "EE_suma": float(np.sqrt(suma.sd[0, 0])),
                "sig_suma": estrellas(float(suma.pvalue)),
            }
        else:
            fila |= {"suma": np.nan, "EE_suma": np.nan, "sig_suma": ""}

        fila |= {
            "media_control": control.incidentes.mean(),
            "sd_control": control.incidentes.std(),
            "N": int(r.nobs),
            "R2": r.rsquared,
            "clusters": tabla.cluster.nunique(),
        }
        fila["% del control"] = 100 * fila["coef"] / fila["media_control"]
        return fila

    @cached_property
    def resultados(self) -> pd.DataFrame:
        """Las tres especificaciones de este panel."""
        return pd.DataFrame(
            {n: self.estimar(f) for n, f in self.especificaciones.items()}
        ).T

    def resumen(self) -> None:
        tabla, periodos = self.tabla, self.periodos
        nivel = "todos" if self.niveles is None else "+".join(self.niveles)
        print(f"radio {self.radio_m} m | incidentes: {nivel}")
        print(f"periodos: t de {periodos.t.min()} a {periodos.t.max()}, "
              f"del {periodos.inicio.iloc[0]:%Y-%m-%d} "
              f"al {self.cortes[-1] - pd.Timedelta(days=1):%Y-%m-%d}")
        print()
        print(f"  unidades      : {tabla.uid.nunique():>8,}  ({len(self.unidades) // 2} pares)")
        print(f"  filas         : {len(tabla):>8,}")
        print(f"  incidentes    : {tabla.incidentes.sum():>10,.1f}")
        print(f"  filas en cero : {(tabla.incidentes == 0).mean():>9.1%}")
        print(f"  clusters      : {tabla.cluster.nunique():>8,}")
        print(f"  covariables   : {len(self.covariables):>8,}")


def tabla_resultados(
    emparejamientos: dict, niveles: dict | None = None, **kwargs
) -> pd.DataFrame:
    """Un renglón por radio, nivel de severidad y especificación.

        emparejamientos, comunes = muestra_comun(datos)
        tabla_resultados(emparejamientos)
    """
    niveles = NIVELES_TESIS if niveles is None else niveles

    filas = []
    for radio, emparejamiento in emparejamientos.items():
        for etiqueta, nivel in niveles.items():
            panel = Panel(emparejamiento, niveles=nivel, **kwargs)
            for nombre, formula in panel.especificaciones.items():
                filas.append(
                    {"radio": radio, "nivel": etiqueta, "especificacion": nombre}
                    | panel.estimar(formula)
                )
    return pd.DataFrame(filas)


if __name__ == "__main__":
    from pipeline.emparejamiento import muestra_comun
    from pipeline.limpieza import Datos

    datos = Datos()
    emparejamientos, comunes = muestra_comun(datos)

    Panel(emparejamientos[300]).resumen()
    print()

    tabla = tabla_resultados(emparejamientos)
    principal = tabla.query("especificacion == '(3) + covariables x post'")
    print("efecto como % de la media del grupo de control:")
    print(principal.pivot(index="nivel", columns="radio", values="% del control")
          .reindex(list(NIVELES_TESIS)).round(2).to_string())
    print()
    print(f"significativas: {(tabla.sig != '').sum()} de {len(tabla)}")
