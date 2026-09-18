"""
Construcción de las unidades tratadas a partir de las cámaras.

Un objeto `UnidadesTratadas` que encapsula las decisiones de diseño tomadas en
`scripts/resume-911/unit-design.ipynb`. Todas son parámetros con default en el
valor elegido, así que las pruebas de robustez son una instancia distinta y no
un notebook aparte:

    from pipeline import Datos, UnidadesTratadas

    datos = Datos()
    base = UnidadesTratadas(datos, radio_m=300)            # especificación principal
    alt  = UnidadesTratadas(datos, radio_m=300, umbral_overlap=0.50)

    base.resumen()
    base.unidades              # GeoDataFrame de círculos
    base.incidentes_asignados  # cada incidente con su unidad y su peso

Las decisiones, y dónde se justifican en el notebook:

- Unidad = círculo del radio pedido. Mantiene el área constante entre unidades,
  que es lo que permite compararlas y emparejarlas.
- Dos cámaras se fusionan si sus círculos comparten más de `umbral_overlap` del
  área, medido a `radio_decision_m`. Los grupos se calculan una sola vez a ese
  radio y se reusan en todos los demás: así el `unidad_id` significa lo mismo en
  todas las corridas.
- Un incidente en área compartida se reparte en partes iguales entre las
  unidades que lo contienen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

if __package__:
    from .limpieza import Datos
else:  # ejecutado como script suelto: python scripts/pipeline/unidades.py
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline.limpieza import Datos

# Radio donde se deciden las fusiones: el más grande del análisis. Fijarlo aquí
# y no en cada corrida es lo que mantiene estables los ids entre radios.
RADIO_DECISION = 300

# Fracción de área compartida a partir de la cual dos cámaras son una unidad.
# 60% está acotado por los dos lados: con 50% dos cámaras quedan fuera de su
# propio círculo a 100 m, y con 70% reaparece traslape a 100 m.
UMBRAL_OVERLAP = 0.60

RADIOS = (100, 150, 200, 250, 300)


def distancia_para_overlap(pct: float, radio: float) -> float:
    """Distancia entre dos círculos de igual radio que comparten `pct` del área.

    El traslape depende solo de distancia/radio, así que el umbral en porcentaje
    se traduce a uno en distancia. Tenerlo explícito deja claro que la regla
    escala con el radio en el que se aplica.
    """

    def diferencia(d: float) -> float:
        area = (
            2 * radio**2 * np.arccos(d / (2 * radio))
            - (d / 2) * np.sqrt(4 * radio**2 - d**2)
        )
        return area / (np.pi * radio**2) - pct

    return brentq(diferencia, 1e-9, 2 * radio - 1e-9)


@dataclass
class UnidadesTratadas:
    """Unidades tratadas para un radio, con la regla de fusión y reparto elegidas.

    Parameters
    ----------
    datos : Datos
        Fuentes limpias. De aquí salen cámaras e incidentes.
    radio_m : float
        Radio de los círculos de esta corrida.
    radio_decision_m : float
        Radio en el que se decide qué cámaras se fusionan. No cambia entre
        corridas: es lo que mantiene comparables las unidades entre radios.
    umbral_overlap : float
        Fracción de área compartida a partir de la cual dos cámaras se fusionan.
    reparto : {"peso", "cercano", "naive"}
        Qué hacer con un incidente que cae en varios círculos. "peso" lo divide
        en partes iguales; "cercano" se lo da a la unidad con el centro más
        próximo; "naive" lo cuenta entero en cada una, que infla los totales y
        está solo para comparar.
    excluir_borde : float | None
        Si se da, descarta las unidades cuya cámara más lejana pase esa fracción
        del radio. Prueba de robustez: excluir selecciona por densidad de
        cámaras, así que la muestra principal va sin esto.
    """

    datos: Datos
    radio_m: float = RADIO_DECISION
    radio_decision_m: float = RADIO_DECISION
    umbral_overlap: float = UMBRAL_OVERLAP
    reparto: str = "peso"
    excluir_borde: float | None = None

    descartes: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.reparto not in ("peso", "cercano", "naive"):
            raise ValueError(f"reparto desconocido: {self.reparto!r}")

    # =====================================================================
    # Agrupación de cámaras
    # =====================================================================

    @cached_property
    def distancia_fusion_m(self) -> float:
        """Distancia máxima entre dos cámaras para que queden en la misma unidad."""
        return distancia_para_overlap(self.umbral_overlap, self.radio_decision_m)

    @cached_property
    def grupos(self) -> np.ndarray:
        """Etiqueta de unidad por cámara, en el orden del shapefile.

        Componentes conexas: si A se fusiona con B y B con C, las tres son una
        unidad aunque A y C no lleguen al umbral entre sí. Encadenar puede alejar
        el centroide de sus cámaras, que es lo que revisa `camaras_fuera`.
        """
        camaras = self.datos.camaras.geometry
        distancias = np.array([[a.distance(b) for b in camaras] for a in camaras])
        adyacencia = coo_matrix((distancias <= self.distancia_fusion_m).astype(float))
        _, etiquetas = connected_components(adyacencia, directed=False)
        return etiquetas

    @cached_property
    def centros(self) -> gpd.GeoDataFrame:
        """Centroide de cada grupo: el centro del círculo de la unidad."""
        camaras = self.datos.camaras
        puntos = pd.DataFrame(
            {
                "unidad_id": self.grupos,
                "x": camaras.geometry.x.values,
                "y": camaras.geometry.y.values,
            }
        )
        centro = puntos.groupby("unidad_id")[["x", "y"]].mean()

        return gpd.GeoDataFrame(
            {
                "unidad_id": centro.index,
                "n_camaras": puntos.groupby("unidad_id").size().values,
            },
            geometry=gpd.points_from_xy(centro.x, centro.y),
            crs=camaras.crs,
        )

    # =====================================================================
    # Unidades
    # =====================================================================

    @cached_property
    def distancia_camara_centro(self) -> pd.Series:
        """Distancia de cada cámara al centro de su unidad, en metros."""
        centro_de_cada = gpd.GeoSeries(self.centros.geometry.values[self.grupos])
        camaras = self.datos.camaras.geometry
        return pd.Series(
            np.hypot(
                camaras.x.values - centro_de_cada.x.values,
                camaras.y.values - centro_de_cada.y.values,
            ),
            index=self.datos.camaras.index,
        )

    @cached_property
    def camaras_fuera(self) -> int:
        """Cámaras que caen fuera del círculo de su propia unidad.

        Tiene que ser cero: una unidad tratada sin su cámara adentro no es una
        unidad tratada. Es la verificación que descartó centrar los círculos en
        el centroide sin restringir el umbral.
        """
        return int((self.distancia_camara_centro > self.radio_m).sum())

    @cached_property
    def unidades(self) -> gpd.GeoDataFrame:
        """Los círculos tratados, uno por grupo de cámaras."""
        if self.camaras_fuera:
            raise ValueError(
                f"{self.camaras_fuera} cámaras quedan fuera de su unidad con "
                f"radio_m={self.radio_m} y umbral_overlap={self.umbral_overlap}. "
                "Subir el umbral o el radio."
            )

        unidades = gpd.GeoDataFrame(
            {
                "unidad_id": self.centros.unidad_id.values,
                "n_camaras": self.centros.n_camaras.values,
                "radio_m": self.radio_m,
                "tratado": 1,
            },
            geometry=self.centros.geometry.buffer(self.radio_m),
            crs=self.centros.crs,
        )
        unidades["area_ha"] = unidades.area / 1e4

        if self.excluir_borde is not None:
            limite = self.excluir_borde * self.radio_m
            al_borde = (
                self.distancia_camara_centro.groupby(self.grupos).max() > limite
            )
            conservadas = unidades[~unidades.unidad_id.map(al_borde).fillna(False)]
            self.descartes["unidades con la cámara al borde"] = len(unidades) - len(
                conservadas
            )
            unidades = conservadas

        return unidades.reset_index(drop=True)

    # =====================================================================
    # Asignación de incidentes
    # =====================================================================

    @cached_property
    def incidentes_asignados(self) -> gpd.GeoDataFrame:
        """Cada incidente dentro de alguna unidad, con su peso.

        Un incidente en área compartida aparece una vez por unidad que lo
        contiene. `peso` dice con cuánto entra a cada una según `reparto`.
        """
        dentro = gpd.sjoin(
            self.datos.incidentes,
            self.unidades[["unidad_id", "geometry"]],
            predicate="within",
        ).drop(columns="index_right")

        veces = dentro.groupby(dentro.index).size()
        dentro = dentro.assign(n_unidades=veces.reindex(dentro.index).values)

        if self.reparto == "peso":
            dentro["peso"] = 1 / dentro.n_unidades
        elif self.reparto == "naive":
            dentro["peso"] = 1.0
        else:  # "cercano": se lo queda la unidad cuyo centro está más próximo
            centros = self.centros.set_index("unidad_id").geometry
            distancia = [
                punto.distance(centros.loc[unidad])
                for punto, unidad in zip(dentro.geometry, dentro.unidad_id)
            ]
            dentro = dentro.assign(_d=distancia)
            gana = dentro.groupby(dentro.index)._d.transform("min") == dentro._d
            dentro = dentro[gana].drop(columns="_d")
            dentro["peso"] = 1.0

        return dentro

    @cached_property
    def conteos(self) -> pd.DataFrame:
        """Incidentes por unidad: el crudo y el efectivo según el reparto."""
        asignados = self.incidentes_asignados
        conteos = pd.DataFrame(
            {
                "incidentes": asignados.groupby("unidad_id").size(),
                "incidentes_efectivos": asignados.groupby("unidad_id").peso.sum(),
            }
        ).reindex(self.unidades.unidad_id, fill_value=0)

        conteos["pct_compartido"] = 1 - conteos.incidentes_efectivos / conteos.incidentes
        return conteos

    # =====================================================================
    # Diagnóstico
    # =====================================================================

    @cached_property
    def pares_traslapados(self) -> pd.DataFrame:
        """Pares de unidades que comparten área, con cuánta comparten."""
        unidades = self.unidades
        pares = gpd.sjoin(unidades, unidades, predicate="intersects")
        pares = pares[pares.unidad_id_left < pares.unidad_id_right]

        geometria = unidades.set_index("unidad_id").geometry
        area_circulo = np.pi * self.radio_m**2

        return pd.DataFrame(
            {
                "unidad_a": pares.unidad_id_left.values,
                "unidad_b": pares.unidad_id_right.values,
                "pct_overlap": [
                    geometria.loc[a].intersection(geometria.loc[b]).area / area_circulo
                    for a, b in zip(pares.unidad_id_left, pares.unidad_id_right)
                ],
            }
        ).sort_values("pct_overlap", ascending=False)

    def diagnostico(self) -> dict:
        """Una fila con el estado de esta especificación, para comparar variantes."""
        asignados = self.incidentes_asignados
        return {
            "radio_m": self.radio_m,
            "umbral": self.umbral_overlap,
            "reparto": self.reparto,
            "excluir_borde": self.excluir_borde,
            "unidades": len(self.unidades),
            "camaras": int(self.unidades.n_camaras.sum()),
            "camaras_fuera": self.camaras_fuera,
            "pares_traslapados": len(self.pares_traslapados),
            "incidentes": asignados.index.nunique(),
            "incidentes_efectivos": asignados.peso.sum(),
        }

    def resumen(self) -> None:
        """Imprime la configuración y sus verificaciones."""
        d = self.diagnostico()
        print(
            f"radio {self.radio_m} m | fusión: >{self.umbral_overlap:.0%} de área a "
            f"{self.radio_decision_m} m (<= {self.distancia_fusion_m:.0f} m entre cámaras)"
        )
        print(f"reparto de incidentes compartidos: {self.reparto}")
        if self.excluir_borde is not None:
            print(f"excluyendo unidades con la cámara más allá del {self.excluir_borde:.0%} del radio")
        print()
        print(f"  unidades          : {d['unidades']:>8,}  (de {len(self.datos.camaras)} cámaras)")
        print(f"  cámaras incluidas : {d['camaras']:>8,}")
        print(f"  cámaras fuera     : {d['camaras_fuera']:>8,}  <- tiene que ser 0")
        print(f"  pares traslapados : {d['pares_traslapados']:>8,}")
        print(f"  incidentes        : {d['incidentes']:>8,}")
        print(f"  efectivos         : {d['incidentes_efectivos']:>10,.0f}")
        for motivo, n in self.descartes.items():
            print(f"  descartado, {motivo}: {n:,}")


def comparar(datos: Datos, especificaciones: list[dict]) -> pd.DataFrame:
    """Corre varias especificaciones y devuelve sus diagnósticos en una tabla.

        comparar(datos, [
            {"radio_m": r} for r in RADIOS
        ])
    """
    return pd.DataFrame(
        [UnidadesTratadas(datos, **spec).diagnostico() for spec in especificaciones]
    )


if __name__ == "__main__":
    datos = Datos()
    UnidadesTratadas(datos).resumen()
    print()
    print(comparar(datos, [{"radio_m": r} for r in RADIOS]).to_string(index=False))
