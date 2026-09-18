"""
Pool de unidades de control.

Los centros candidatos son puntos aleatorios sobre la red vial, muestreados
proporcionalmente a la longitud de cada segmento. De las construcciones que se
consideraron en `scripts/resume-911/control-design.ipynb` es la que menos
decisiones arrastra: no hay que definir qué cuenta como intersección ni dónde
empieza una rejilla, y cubre tramos y cruces porque unos y otros son parte de la
red.

    from pipeline import Datos, UnidadesTratadas, UnidadesControl

    datos = Datos()
    tratadas = UnidadesTratadas(datos, radio_m=300)
    control = UnidadesControl(datos, tratadas, semilla=0)

Dos restricciones que se aplican en momentos distintos:

- **Control contra tratada**: obligatoria y se aplica al construir el pool.
  Ningún candidato puede traslaparse con un área tratada, así que sus centros
  quedan al menos a dos radios de distancia.
- **Control contra control**: se aplica al seleccionar, con `seleccionar()`.
  Filtrarla desde el pool dejaría unos cientos de candidatos de decenas de miles
  y empeoraría el emparejamiento sin necesidad: solo importa entre los controles
  que terminen en la muestra final.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

if __package__:
    from .limpieza import Datos
    from .unidades import UnidadesTratadas
else:  # ejecutado como script suelto
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline.limpieza import Datos
    from pipeline.unidades import UnidadesTratadas

# Generoso a propósito: el pool alimenta el propensity score y el soporte común,
# y un pool denso da mejores pareos.
N_CANDIDATOS = 20_000

# Atributos de la vía que hereda el centro candidato. Sirven para descartar
# controles sin sentido y alimentan las covariables estructurales.
ATRIBUTOS_VIA = ["ID_VIA", "NOMBRE", "TIPO_VIA", "CARRILES", "CIRCULA", "NIVEL"]


def imponer_separacion(
    puntos: gpd.GeoDataFrame, separacion_m: float, semilla: int = 0
) -> gpd.GeoDataFrame:
    """Subconjunto donde ningún punto queda a menos de `separacion_m` de otro.

    Recorre en orden aleatorio y conserva el punto que respete la distancia
    contra los ya elegidos. Es voraz, así que el resultado depende del orden:
    por eso la semilla es parámetro.
    """
    orden = np.random.default_rng(semilla).permutation(len(puntos))
    coordenadas = np.column_stack([puntos.geometry.x.values, puntos.geometry.y.values])

    elegidos: list[int] = []
    for i in orden:
        if elegidos:
            if np.hypot(*(coordenadas[elegidos] - coordenadas[i]).T).min() < separacion_m:
                continue
        elegidos.append(i)

    return puntos.iloc[sorted(elegidos)]


@dataclass
class UnidadesControl:
    """Pool de controles candidatos: puntos aleatorios sobre la red vial.

    Parameters
    ----------
    datos : Datos
        Fuentes limpias. De aquí sale la red vial.
    tratadas : UnidadesTratadas
        Las unidades a evitar, y de donde se hereda el radio.
    n_candidatos : int
        Cuántos centros sortear antes de filtrar.
    semilla : int
        Semilla del muestreo. Repetir con otra es una prueba de robustez directa.
    separacion_tratada_m : float | None
        Distancia mínima a un centro tratado. Por defecto dos veces el radio de
        decisión, que garantiza traslape cero en el radio más grande. Subirla
        deja colchón contra spillover.
    tipos_via : tuple[str, ...] | None
        Jerarquías elegibles. Por defecto, aquellas donde de hecho hay cámaras:
        un control en una vía donde el programa nunca habría instalado una no
        produce un contrafactual, produce ruido.
    """

    datos: Datos
    tratadas: UnidadesTratadas
    n_candidatos: int = N_CANDIDATOS
    semilla: int = 0
    separacion_tratada_m: float | None = None
    tipos_via: tuple[str, ...] | None = None

    descartes: dict[str, int] = field(default_factory=dict, init=False)

    @property
    def radio_m(self) -> float:
        """El mismo radio que las tratadas: las unidades tienen que ser comparables."""
        return self.tratadas.radio_m

    @property
    def separacion_minima_m(self) -> float:
        if self.separacion_tratada_m is not None:
            return self.separacion_tratada_m
        return 2 * self.tratadas.radio_decision_m

    @cached_property
    def vias_elegibles(self) -> gpd.GeoDataFrame:
        """Segmentos donde puede caer un control."""
        vias = self.datos.vialidades
        tipos = self.tipos_via
        if tipos is None:
            con_camara = gpd.sjoin_nearest(
                self.datos.camaras[["geometry"]], vias[["TIPO_VIA", "geometry"]]
            )
            tipos = tuple(con_camara.TIPO_VIA.unique())

        elegibles = vias[vias.TIPO_VIA.isin(tipos)]
        self.descartes["segmentos de jerarquía no elegible"] = len(vias) - len(elegibles)
        return elegibles

    @cached_property
    def centros(self) -> gpd.GeoDataFrame:
        """Centros sorteados sobre la red, ya filtrados contra las tratadas.

        El muestreo es proporcional a la longitud: cada metro de vía elegible
        tiene la misma probabilidad de recibir un centro. Sortear segmento y
        luego punto le daría el mismo peso a un tramo de 20 m que a una avenida
        de 2 km, y la fragmentación de la capa es una decisión de cartografía,
        no un hecho de la ciudad.
        """
        vias = self.vias_elegibles
        acumulada = np.cumsum(vias.length.values)

        sorteo = np.random.default_rng(self.semilla).uniform(0, acumulada[-1], self.n_candidatos)
        indice = np.searchsorted(acumulada, sorteo)
        offset = sorteo - np.concatenate([[0], acumulada])[indice]

        geometrias = vias.geometry.values
        candidatos = gpd.GeoDataFrame(
            vias.iloc[indice][ATRIBUTOS_VIA].reset_index(drop=True),
            geometry=[geometrias[i].interpolate(d) for i, d in zip(indice, offset)],
            crs=vias.crs,
        )

        centros_tratados = np.column_stack(
            [self.tratadas.centros.geometry.x, self.tratadas.centros.geometry.y]
        )
        coordenadas = np.column_stack([candidatos.geometry.x, candidatos.geometry.y])
        distancia = cKDTree(centros_tratados).query(coordenadas)[0]

        lejos = distancia >= self.separacion_minima_m
        self.descartes["candidatos muy cerca de una tratada"] = int((~lejos).sum())

        candidatos = candidatos[lejos].reset_index(drop=True)
        candidatos.insert(0, "unidad_id", range(len(candidatos)))
        candidatos["dist_tratada_m"] = distancia[lejos]
        return candidatos

    @cached_property
    def unidades(self) -> gpd.GeoDataFrame:
        """Los círculos de control, del mismo radio que las tratadas."""
        centros = self.centros
        unidades = gpd.GeoDataFrame(
            centros.drop(columns="geometry").assign(radio_m=self.radio_m, tratado=0),
            geometry=centros.geometry.buffer(self.radio_m),
            crs=centros.crs,
        )
        unidades["area_ha"] = unidades.area / 1e4
        return unidades

    def seleccionar(self, unidad_ids=None, semilla: int | None = None) -> gpd.GeoDataFrame:
        """Controles separados entre sí por dos radios, para la muestra final.

        Se aplica sobre los controles ya emparejados. Sin `unidad_ids` la aplica
        a todo el pool, que sirve para ver cuántos controles disjuntos caben.
        """
        centros = self.centros
        if unidad_ids is not None:
            centros = centros[centros.unidad_id.isin(unidad_ids)]

        return imponer_separacion(
            centros,
            separacion_m=2 * self.radio_m,
            semilla=self.semilla if semilla is None else semilla,
        )

    def diagnostico(self) -> dict:
        return {
            "radio_m": self.radio_m,
            "semilla": self.semilla,
            "n_candidatos": self.n_candidatos,
            "separacion_tratada_m": self.separacion_minima_m,
            "controles": len(self.centros),
            "tratadas": len(self.tratadas.unidades),
            "controles_por_tratada": len(self.centros) / len(self.tratadas.unidades),
        }

    def resumen(self) -> None:
        d = self.diagnostico()
        print(
            f"radio {self.radio_m} m | semilla {self.semilla} | "
            f"mínimo a una tratada: {d['separacion_tratada_m']:.0f} m"
        )
        print(f"jerarquías elegibles: {sorted(self.vias_elegibles.TIPO_VIA.unique())}")
        print()
        print(f"  candidatos sorteados : {self.n_candidatos:>8,}")
        for motivo, n in self.descartes.items():
            print(f"  descartado, {motivo}: {n:,}")
        print(f"  controles en el pool : {d['controles']:>8,}")
        print(f"  por tratada          : {d['controles_por_tratada']:>8,.0f}")


if __name__ == "__main__":
    datos = Datos()
    UnidadesControl(datos, UnidadesTratadas(datos, radio_m=300)).resumen()
