"""
Propensity score y emparejamiento.

    from pipeline import Datos, UnidadesTratadas, UnidadesControl, Features, Emparejamiento

    datos = Datos()
    tratadas = UnidadesTratadas(datos, radio_m=300)
    control = UnidadesControl(datos, tratadas)
    emp = Emparejamiento(Features(datos, tratadas, control))

    emp.resumen()
    emp.pares          # tratada, control, distancias
    emp.balance        # SMD antes y después, por covariable
    love_plot(emp.balance)

Las decisiones, justificadas en `scripts/resume-911/propensity-score.ipynb`:

- **Logit por máxima verosimilitud con el método de Newton, sin penalización y
  sobre covariables estandarizadas.** El propensity score no busca predecir
  fuera de muestra sino balancear covariables en esta muestra, así que
  regularizar deja desbalance a propósito. Newton (`newton-cholesky`) es el
  método estándar para la regresión logística —el que usan por defecto `glm` en
  R y `logit` en Stata— y converge en 7 iteraciones. El solver por defecto de
  sklearn no sirve aquí: sin estandarizar no converge y da un score con
  correlación 0.38 contra el correcto; estandarizado converge, pero su
  tolerancia deja un error en el logit de hasta 0.54 —casi tres veces el ancho
  del caliper— y cambia hasta 18 de 99 pares. Con la tolerancia apretada a
  `1e-10` reproduce los pares de Newton en la muestra original, pero en el
  bootstrap diverge en un remuestreo con cuasi-separación, donde Newton no.
- **Vecino más cercano 1:1 sin reemplazo**, con caliper de 0.2 desviaciones
  estándar del logit del score.
- **Desempate por distancia de Mahalanobis** entre los controles dentro del
  caliper. Suele haber cientos con score casi idéntico —la distancia mediana es
  0.0002— así que elegir por score es elegir al azar. Usar esa holgura baja el
  |SMD| medio de 0.093 a 0.070 sin perder pares.
- **Dos radios de separación entre controles emparejados.** Dos controles que se
  traslapan comparten incidentes y no son observaciones independientes. La
  restricción se impone aquí, sobre los seleccionados, no sobre el pool.

Para comparar radios, ver `muestra_comun`: el emparejamiento se rehace en cada
radio —las covariables cambian con el radio, y reusar los pares dispara el |SMD|
a 0.59 en el más chico— pero la muestra tratada se restringe a la intersección.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.linear_model import LogisticRegression

if __package__:
    from .controles import UnidadesControl
    from .features import COVARIABLES, Features
    from .limpieza import Datos
    from .unidades import RADIOS, UnidadesTratadas
else:  # ejecutado como script suelto
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline.controles import UnidadesControl
    from pipeline.features import COVARIABLES, Features
    from pipeline.limpieza import Datos
    from pipeline.unidades import RADIOS, UnidadesTratadas

CALIPER_SD = 0.2

ETIQUETAS = {
    "road_length_m": "Metros de vía",
    "n_vialidades": "Vialidades distintas",
    "carriles_ponderados": "Carriles (ponderado)",
    "pct_acceso_controlado": "% acceso controlado",
    "pct_doble_sentido": "% doble sentido",
    "pct_desnivel": "% a desnivel",
    "n_niveles": "Niveles distintos",
    "nivel_incidentes": "Incidentes/mes",
    "pct_lesionados": "% con lesionados",
    "tendencia": "Tendencia previa",
    "hubo_fcs": "Hubo fatal",
    "afluencia_nivel": "Afluencia Metro",
}


def smd(muestra: pd.DataFrame, covariables=COVARIABLES) -> pd.Series:
    """Diferencia de medias estandarizada por la desviación combinada."""
    tratadas = muestra[muestra.tratado == 1]
    controles = muestra[muestra.tratado == 0]
    return pd.Series({
        v: (tratadas[v].mean() - controles[v].mean())
        / np.sqrt((tratadas[v].var() + controles[v].var()) / 2)
        for v in covariables
    })


@dataclass
class Emparejamiento:
    """Propensity score y pareo 1:1 para un radio.

    Parameters
    ----------
    features : Features
        Matriz de covariables de tratadas y controles.
    caliper_sd : float
        Ancho del caliper, en desviaciones estándar del logit del score.
    separacion_m : float | None
        Distancia mínima entre controles emparejados. Por defecto dos radios,
        que es lo que garantiza que sus círculos no se traslapen.
    tratadas_validas : set | None
        Restringe la muestra a estas tratadas después de emparejar. Se usa para
        fijar la muestra común entre radios; ver `muestra_comun`.
    """

    features: Features
    caliper_sd: float = CALIPER_SD
    separacion_m: float | None = None
    tratadas_validas: set | None = None

    descartes: dict[str, int] = field(default_factory=dict, init=False)

    @property
    def radio_m(self) -> float:
        return self.features.tratadas.radio_m

    @property
    def separacion(self) -> float:
        if self.separacion_m is not None:
            return self.separacion_m
        return 2 * self.radio_m

    # =====================================================================
    # Propensity score
    # =====================================================================

    @cached_property
    def X(self) -> pd.DataFrame:
        return self.features.matriz[COVARIABLES]

    @cached_property
    def Z(self) -> pd.DataFrame:
        """Covariables estandarizadas.

        No cambia el modelo —la logística es equivariante a reescalamientos—
        pero sí la convergencia: `afluencia_nivel` llega a 10 millones mientras
        `pct_lesionados` vive entre 0 y 1.
        """
        return (self.X - self.X.mean()) / self.X.std()

    @cached_property
    def modelo(self) -> LogisticRegression:
        return LogisticRegression(
            max_iter=5000, C=np.inf, solver="newton-cholesky"
        ).fit(self.Z, self.features.matriz.tratado)

    @cached_property
    def datos_ps(self) -> pd.DataFrame:
        """La matriz con el propensity score, su logit y las coordenadas del centro."""
        centros = pd.concat([
            self.features.tratadas.centros.assign(
                uid="T" + self.features.tratadas.centros.unidad_id.astype(str)
            ),
            self.features.controles.centros.assign(
                uid="C" + self.features.controles.centros.unidad_id.astype(str)
            ),
        ]).set_index("uid")

        ps = self.modelo.predict_proba(self.Z)[:, 1]
        return self.features.matriz.assign(
            ps=ps,
            logit_ps=np.log(ps / (1 - ps)),
            x=centros.geometry.x,
            y=centros.geometry.y,
        )

    # =====================================================================
    # Emparejamiento
    # =====================================================================

    @cached_property
    def caliper(self) -> float:
        return self.caliper_sd * self.datos_ps.logit_ps.std()

    @cached_property
    def _resultado(self) -> tuple[pd.DataFrame, list]:
        """Pareo voraz: las tratadas más difíciles eligen primero."""
        datos = self.datos_ps
        inv_cov = np.linalg.pinv(np.cov(self.Z.to_numpy().T))

        tratadas = datos[datos.tratado == 1].sort_values("ps", ascending=False)
        controles = datos[datos.tratado == 0]
        c_xy = controles[["x", "y"]].to_numpy()
        c_logit = controles.logit_ps.to_numpy()
        c_id = controles.index.to_numpy()
        c_z = self.Z.loc[controles.index].to_numpy()

        disponible = np.ones(len(controles), dtype=bool)
        ocupados: list = []
        pares: list[dict] = []
        sin_pareja: list[str] = []

        for uid, fila in tratadas.iterrows():
            distancia_ps = np.abs(c_logit - fila.logit_ps)
            elegibles = disponible & (distancia_ps <= self.caliper)
            if ocupados:
                elegibles &= cKDTree(np.array(ocupados)).query(c_xy)[0] >= self.separacion

            if not elegibles.any():
                sin_pareja.append(uid)
                continue

            indices = np.where(elegibles)[0]
            diferencia = c_z[indices] - self.Z.loc[uid].to_numpy()
            mahalanobis = np.einsum("ij,jk,ik->i", diferencia, inv_cov, diferencia)
            elegido = indices[np.argmin(mahalanobis)]

            pares.append({
                "tratada": uid,
                "control": c_id[elegido],
                "dist_ps": distancia_ps[elegido],
                "dist_mahalanobis": np.sqrt(mahalanobis.min()),
            })
            ocupados.append(c_xy[elegido])
            disponible[elegido] = False

        return pd.DataFrame(pares), sin_pareja

    @cached_property
    def pares(self) -> pd.DataFrame:
        pares, sin_pareja = self._resultado
        self.descartes["tratadas sin control dentro del caliper"] = len(sin_pareja)

        if self.tratadas_validas is not None:
            antes = len(pares)
            pares = pares[pares.tratada.isin(self.tratadas_validas)]
            self.descartes["fuera de la muestra común entre radios"] = antes - len(pares)

        return pares.reset_index(drop=True)

    @cached_property
    def sin_pareja(self) -> list:
        return self._resultado[1]

    @cached_property
    def emparejados(self) -> pd.DataFrame:
        """Las unidades que quedan en la muestra final, tratadas y controles."""
        pares = self.pares
        return self.datos_ps.loc[list(pares.tratada) + list(pares.control)]

    # =====================================================================
    # Balance
    # =====================================================================

    @cached_property
    def balance(self) -> pd.DataFrame:
        """SMD antes y después, con las medias del grupo emparejado."""
        emparejados = self.emparejados
        return pd.DataFrame({
            "media_tratadas": emparejados[emparejados.tratado == 1][COVARIABLES].mean(),
            "media_controles": emparejados[emparejados.tratado == 0][COVARIABLES].mean(),
            "smd_antes": smd(self.datos_ps),
            "smd_despues": smd(emparejados),
        })

    def diagnostico(self) -> dict:
        balance = self.balance
        return {
            "radio_m": self.radio_m,
            "pares": len(self.pares),
            "sin_pareja": len(self.sin_pareja),
            "smd_medio_antes": balance.smd_antes.abs().mean(),
            "smd_medio_despues": balance.smd_despues.abs().mean(),
            "smd_max_despues": balance.smd_despues.abs().max(),
            "sobre_0.1": int((balance.smd_despues.abs() > 0.1).sum()),
        }

    def resumen(self) -> None:
        d = self.diagnostico()
        print(f"radio {self.radio_m} m | caliper {self.caliper:.4f} "
              f"({self.caliper_sd} sd del logit) | separación {self.separacion:.0f} m")
        print()
        print(f"  pares formados     : {d['pares']:>6}")
        for motivo, n in self.descartes.items():
            if n:
                print(f"  descartado, {motivo}: {n}")
        print(f"  |SMD| medio        : {d['smd_medio_antes']:.3f} -> {d['smd_medio_despues']:.3f}")
        print(f"  |SMD| máximo       : {d['smd_max_despues']:.3f}")
        print(f"  covariables > 0.1  : {d['sobre_0.1']}")


def muestra_comun(
    datos: Datos, radios=RADIOS, semilla: int = 0, **kwargs
) -> tuple[dict[float, Emparejamiento], set]:
    """Emparejamiento por radio, restringido a las tratadas que sobreviven en todos.

    El pareo se rehace en cada radio porque las covariables cambian con él:
    reusar los pares del radio mayor en el menor dispara el |SMD| de 0.07 a 0.21.
    Lo que se mantiene fijo es la muestra **tratada**, que es lo que define el
    estimando; los controles son el instrumento para estimar el contrafactual y
    tienen que ser comparables a cada escala.

    Devuelve un emparejamiento por radio y el conjunto de tratadas comunes.
    """
    primera_pasada = {}
    for radio in radios:
        tratadas = UnidadesTratadas(datos, radio_m=radio)
        control = UnidadesControl(datos, tratadas, semilla=semilla)
        primera_pasada[radio] = Emparejamiento(
            Features(datos, tratadas, control), **kwargs
        )

    comunes = set.intersection(*[set(e.pares.tratada) for e in primera_pasada.values()])

    final = {
        radio: Emparejamiento(e.features, tratadas_validas=comunes, **kwargs)
        for radio, e in primera_pasada.items()
    }
    return final, comunes


def love_plot(
    balance: pd.DataFrame,
    ax=None,
    umbral: float = 0.1,
    titulo: str | None = None,
    orden: str = "nombre",
):
    """Love plot: SMD de cada covariable, antes y después del emparejamiento.

    Una línea une los dos puntos de cada variable, para que el movimiento se lea
    como movimiento y no como dos nubes sueltas.

    `orden="nombre"` ordena alfabéticamente, que es lo que permite comparar las
    figuras de los cinco radios: ordenar por SMD pone cada variable en distinta
    posición en cada radio y vuelve imposible seguirla de una figura a otra.
    `orden="smd"` ordena por magnitud, útil para una figura suelta.
    """
    import matplotlib.pyplot as plt

    ANTES, DESPUES, GRIS, TINTA = "#BC4B51", "#7BA34A", "#C4CACE", "#2F4858"

    if orden == "smd":
        variables = balance[["smd_antes", "smd_despues"]].abs().max(axis=1).sort_values().index
    else:
        # descendente porque el eje y crece hacia arriba
        variables = sorted(balance.index, reverse=True)
    posicion = np.arange(len(variables))

    if ax is None:
        _, ax = plt.subplots(figsize=(6.5, 4.2), layout="constrained")

    ax.axvline(0, color=GRIS, lw=.8, zorder=1)
    for signo in (-1, 1):
        ax.axvline(signo * umbral, color=GRIS, lw=.8, ls="--", zorder=1)

    for i, v in enumerate(variables):  # la línea que une el antes con el después
        ax.plot([balance.smd_antes[v], balance.smd_despues[v]], [i, i],
                color=GRIS, lw=.8, zorder=2)

    ax.scatter(balance.loc[variables, "smd_antes"], posicion, s=34, color=ANTES,
               label="antes de emparejar", zorder=3)
    ax.scatter(balance.loc[variables, "smd_despues"], posicion, s=34, color=DESPUES,
               label="después", zorder=3)

    ax.set_yticks(posicion, [ETIQUETAS.get(v, v) for v in variables])
    ax.set_xlabel("Diferencia de medias estandarizada (SMD)")
    if titulo:
        ax.set_title(titulo, fontsize=9, loc="left", color=TINTA)
    ax.annotate(f"umbral convencional  ±{umbral}", xy=(umbral, len(variables) - 0.4),
                fontsize=7, color=TINTA, ha="left")
    ax.legend(frameon=False, loc="lower right", fontsize=8)

    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRIS)
    ax.tick_params(colors=TINTA, labelsize=8)
    return ax


if __name__ == "__main__":
    datos = Datos()
    emparejamientos, comunes = muestra_comun(datos)

    print(f"tratadas comunes a los {len(emparejamientos)} radios: {len(comunes)}")
    print()
    print(pd.DataFrame([e.diagnostico() for e in emparejamientos.values()])
          .round(3).to_string(index=False))
