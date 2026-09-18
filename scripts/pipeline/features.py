"""
Covariables del propensity score, para tratadas y controles.

Un objeto `Features` que construye la matriz completa a partir de las unidades
de los dos grupos. Las definiciones y sus recortes están justificados en
`scripts/resume-911/feature-design.ipynb`; aquí se documenta la decisión, no se
vuelve a argumentar.

    from pipeline import Datos, UnidadesTratadas, UnidadesControl, Features

    datos = Datos()
    tratadas = UnidadesTratadas(datos, radio_m=300)
    control = UnidadesControl(datos, tratadas, semilla=0)

    features = Features(datos, tratadas, control)
    features.matriz     # una fila por unidad, con la columna `tratado`
    features.resumen()

Doce covariables: siete estructurales, cuatro de siniestralidad y una de Metro.
Todas se miden en los tres años previos al 22 de abril de 2019. Una variable
medida antes de que existiera la cámara no pudo ser causada por ella, así que no
puede ser mediadora ni collider: es la defensa principal del diseño.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

if __package__:
    from .controles import UnidadesControl
    from .limpieza import Datos
    from .unidades import UnidadesTratadas
else:  # ejecutado como script suelto
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline.controles import UnidadesControl
    from pipeline.limpieza import Datos
    from pipeline.unidades import UnidadesTratadas

N_ANIOS = 3

COLUMNAS_ESTRUCTURALES = [
    "road_length_m",
    "n_vialidades",
    "carriles_ponderados",
    "pct_acceso_controlado",
    "pct_doble_sentido",
    "pct_desnivel",
    "n_niveles",
]
COLUMNAS_SINIESTRALIDAD = ["nivel_incidentes", "pct_lesionados", "tendencia", "hubo_fcs"]
COLUMNAS_METRO = ["afluencia_nivel"]

COVARIABLES = COLUMNAS_ESTRUCTURALES + COLUMNAS_SINIESTRALIDAD + COLUMNAS_METRO

DOBLE_SENTIDO = ("Dos sentidos", "Un sentido con carril de contraflujo")


@dataclass
class Features:
    """Matriz de covariables de tratadas y controles.

    Parameters
    ----------
    datos : Datos
        Fuentes limpias.
    tratadas : UnidadesTratadas
        Unidades tratadas; de aquí sale también el reparto de incidentes
        compartidos entre círculos tratados que se traslapan.
    controles : UnidadesControl
        Pool de control. Tiene que venir del mismo radio que las tratadas.
    """

    datos: Datos
    tratadas: UnidadesTratadas
    controles: UnidadesControl

    def __post_init__(self) -> None:
        if self.tratadas.radio_m != self.controles.radio_m:
            raise ValueError(
                f"radios distintos: tratadas {self.tratadas.radio_m} m, "
                f"controles {self.controles.radio_m} m"
            )

    # =====================================================================
    # Ventanas y unidades
    # =====================================================================

    @property
    def ventanas(self) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
        """Los tres años previos, contados hacia atrás desde el tratamiento.

        No son años calendario: así la ventana más reciente termina justo antes
        del 22 de abril de 2019 en vez de mezclar meses tratados.
        """
        corte = self.datos.fecha_tratamiento
        return {
            f"anio_{k}": (corte - pd.DateOffset(years=k), corte - pd.DateOffset(years=k - 1))
            for k in range(1, N_ANIOS + 1)
        }

    @cached_property
    def unidades(self) -> gpd.GeoDataFrame:
        """Tratadas y controles apilados, con `uid` único y la bandera `tratado`.

        Los `unidad_id` de cada grupo empiezan en cero, así que se antepone T o C
        para que la llave no colisione al juntarlos.
        """
        columnas = ["unidad_id", "tratado", "geometry"]
        tratadas = self.tratadas.unidades.assign(tratado=1)[columnas]
        controles = self.controles.unidades[columnas]

        unidades = pd.concat(
            [
                tratadas.assign(uid="T" + tratadas.unidad_id.astype(str)),
                controles.assign(uid="C" + controles.unidad_id.astype(str)),
            ],
            ignore_index=True,
        )
        return gpd.GeoDataFrame(unidades, geometry="geometry", crs=tratadas.crs)

    @cached_property
    def incidentes_asignados(self) -> gpd.GeoDataFrame:
        """Incidentes dentro de cada unidad, con su peso.

        Las tratadas heredan el reparto de `UnidadesTratadas`: un incidente en
        área compartida entre dos círculos tratados cuenta 1/2 en cada uno.

        Los controles cuentan con peso 1. El pool es denso y sus círculos se
        traslapan mucho entre sí, pero son *candidatos*: cada uno representa el
        contrafactual de su propia zona, y la restricción de no traslape entre
        controles se impone al seleccionar los emparejados, no aquí. Repartir
        pesos en el pool haría que el conteo de un control dependiera de cuántos
        otros candidatos cayeron cerca, que es un artefacto del muestreo.
        """
        tratadas = self.tratadas.incidentes_asignados.assign(
            uid=lambda x: "T" + x.unidad_id.astype(str)
        )

        controles = gpd.sjoin(
            self.datos.incidentes,
            self.controles.unidades[["unidad_id", "geometry"]],
            predicate="within",
        ).drop(columns="index_right")
        controles = controles.assign(
            uid="C" + controles.unidad_id.astype(str), peso=1.0
        )

        columnas = ["uid", "timestamp", "incident_level", "peso"]
        return pd.concat([tratadas[columnas], controles[columnas]], ignore_index=True)

    # =====================================================================
    # Bloques de covariables
    # =====================================================================

    @cached_property
    def estructurales(self) -> pd.DataFrame:
        """Composición vial, ponderada por metros de vía dentro del círculo.

        Ponderar en vez de usar máximos y binarias: a 300 m casi cualquier
        círculo contiene una avenida grande, así que `max_carriles` valía lo
        mismo en casi todas las unidades. `pct_desnivel` y `n_niveles` miden la
        ambigüedad vertical, el problema de que un incidente con solo latitud y
        longitud no dice si ocurrió en el segundo piso o en la vía de abajo.
        """
        vialidades = self.datos.vialidades.assign(
            carriles=lambda x: pd.to_numeric(x.CARRILES, errors="coerce"),
            doble=lambda x: x.CIRCULA.isin(DOBLE_SENTIDO),
        )
        unidades = self.unidades

        pares = gpd.sjoin(vialidades, unidades[["uid", "geometry"]], predicate="intersects")
        geometria = unidades.set_index("uid").geometry
        pares["metros"] = [
            via.intersection(geometria.loc[uid]).length
            for via, uid in zip(pares.geometry, pares.uid)
        ]
        pares = pares[pares.metros > 0]

        total = pares.groupby("uid").metros.sum()
        por_uid = pares.groupby("uid")

        estructurales = pd.DataFrame({
            "road_length_m": total,
            "n_vialidades": por_uid.ID_VIA.nunique(),
            "carriles_ponderados": por_uid.apply(
                lambda g: np.average(g.carriles, weights=g.metros), include_groups=False
            ),
            "pct_acceso_controlado": (
                pares[pares.TIPO_VIA == "Vía de acceso controlado"].groupby("uid").metros.sum()
                / total
            ),
            "pct_doble_sentido": pares[pares.doble].groupby("uid").metros.sum() / total,
            "pct_desnivel": pares[pares.NIVEL != 0].groupby("uid").metros.sum() / total,
            "n_niveles": por_uid.NIVEL.nunique(),
        })

        return estructurales.reindex(unidades.uid).fillna(0)

    @cached_property
    def siniestralidad(self) -> pd.DataFrame:
        """Nivel, gravedad, tendencia y presencia de fatales.

        Cuatro y no once: las once medían casi lo mismo, con correlaciones de
        0.75 a 0.94 y el 85.5% de la varianza en un solo componente. Los fatales
        cuentan dentro de `pct_lesionados` —son el 0.5% de los incidentes— y
        aparte como binaria, que no es proxy del nivel (correlación 0.34) y es el
        criterio declarado de ubicación de las cámaras.
        """
        asignados = self.incidentes_asignados
        uids = self.unidades.uid

        por_ventana = {}
        for nombre, (inicio, fin) in self.ventanas.items():
            ventana = asignados[(asignados.timestamp >= inicio) & (asignados.timestamp < fin)]
            por_ventana[nombre] = {
                nivel: (
                    ventana[ventana.incident_level == nivel].groupby("uid").peso.sum()
                    .reindex(uids, fill_value=0) / 12
                )
                for nivel in ("MIN", "PIC", "FCS")
            }

        total = {n: v["MIN"] + v["PIC"] + v["FCS"] for n, v in por_ventana.items()}
        nivel = sum(total.values()) / len(total)
        con_lesionados = sum(v["PIC"] + v["FCS"] for v in por_ventana.values()) / len(por_ventana)
        fatales = sum(v["FCS"] for v in por_ventana.values())

        return pd.DataFrame({
            "nivel_incidentes": nivel,
            "pct_lesionados": (con_lesionados / nivel.replace(0, np.nan)).fillna(0),
            "tendencia": total["anio_1"] - total["anio_3"],
            "hubo_fcs": (fatales > 0).astype(int),
        })

    @cached_property
    def metro(self) -> pd.DataFrame:
        """Afluencia mensual promedio de las estaciones dentro del área.

        Una y no cuatro: las cuatro correlacionaban entre 0.984 y 1.000, con el
        99.5% de la varianza en un solo componente. El cero significa "no hay
        estación dentro", que es informativo y no un dato faltante.
        """
        unidades = self.unidades
        dentro = gpd.sjoin(
            self.datos.estaciones, unidades[["uid", "geometry"]], predicate="within"
        )
        afluencia = self.datos.afluencia.merge(
            dentro[["uid", "linea_key", "estacion_key"]], on=["linea_key", "estacion_key"]
        )

        corte = self.datos.fecha_tratamiento
        pre = afluencia[
            (afluencia.fecha >= corte - pd.DateOffset(years=N_ANIOS)) & (afluencia.fecha < corte)
        ]

        return pd.DataFrame({
            "afluencia_nivel": (
                pre.groupby("uid").afluencia.sum().reindex(unidades.uid, fill_value=0)
                / (12 * N_ANIOS)
            )
        })

    @cached_property
    def crecimiento_metro(self) -> pd.Series:
        """Crecimiento relativo de la afluencia. Solo para robustez.

        NaN donde no hay estación: ahí el crecimiento no es cero, es indefinido,
        y confundirlos le diría al propensity score que "sin estación" es lo
        mismo que "estación con afluencia estable". Solo el 14% de las unidades
        lo tiene definido, por eso no entra en la muestra principal.
        """
        unidades = self.unidades
        dentro = gpd.sjoin(
            self.datos.estaciones, unidades[["uid", "geometry"]], predicate="within"
        )
        afluencia = self.datos.afluencia.merge(
            dentro[["uid", "linea_key", "estacion_key"]], on=["linea_key", "estacion_key"]
        )

        por_ventana = {}
        for nombre, (inicio, fin) in self.ventanas.items():
            ventana = afluencia[(afluencia.fecha >= inicio) & (afluencia.fecha < fin)]
            por_ventana[nombre] = ventana.groupby("uid").afluencia.sum() / 12

        nivel = sum(por_ventana.values()) / len(por_ventana)
        crecimiento = (por_ventana["anio_1"] - por_ventana["anio_3"]) / nivel
        return crecimiento.reindex(unidades.uid)

    # =====================================================================
    # Salida
    # =====================================================================

    @cached_property
    def matriz(self) -> pd.DataFrame:
        """Una fila por unidad: las doce covariables más `tratado`."""
        unidades = self.unidades.set_index("uid")
        return pd.concat(
            [
                unidades[["tratado", "unidad_id"]],
                self.estructurales,
                self.siniestralidad,
                self.metro,
            ],
            axis=1,
        )

    def resumen(self) -> None:
        """Medias por grupo y diferencia estandarizada, antes de emparejar."""
        matriz = self.matriz
        tratadas = matriz[matriz.tratado == 1]
        controles = matriz[matriz.tratado == 0]

        print(f"radio {self.tratadas.radio_m} m | "
              f"{len(tratadas)} tratadas, {len(controles):,} controles")
        print()
        print(f"{'covariable':<24} {'tratadas':>12} {'controles':>12} {'SMD':>8}")
        for columna in COVARIABLES:
            t, c = tratadas[columna], controles[columna]
            pooled = np.sqrt((t.var() + c.var()) / 2)
            smd = (t.mean() - c.mean()) / pooled if pooled else 0.0
            print(f"{columna:<24} {t.mean():>12,.2f} {c.mean():>12,.2f} {smd:>8.2f}")


if __name__ == "__main__":
    datos = Datos()
    tratadas = UnidadesTratadas(datos, radio_m=300)
    Features(datos, tratadas, UnidadesControl(datos, tratadas)).resumen()
