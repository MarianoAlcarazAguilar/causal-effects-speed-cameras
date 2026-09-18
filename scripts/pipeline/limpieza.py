"""
Carga y limpieza de las fuentes del análisis.

Un solo objeto, `Datos`, que entrega cada fuente ya limpia, proyectada al CRS
métrico y recortada a la ventana del estudio. Cada fuente se lee una sola vez
y se queda en memoria.

La afluencia se lee de un parquet intermedio que hay que generar antes con
`construir_afluencia.py`; el CSV crudo queda solo como referencia.

    from pipeline.limpieza import Datos

    datos = Datos()
    datos.incidentes      # GeoDataFrame en EPSG:6372
    datos.afluencia       # DataFrame con llaves de join al shapefile
    datos.resumen()       # imprime qué se cargó y cuánto se descartó

Las decisiones de limpieza están documentadas en cada método: qué se descarta,
cuánto, y por qué. Si un supuesto deja de cumplirse (un renombre de estación,
una coordenada nueva en cero), el código truena en vez de seguir con nulos.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# Fotomultas -> Fotocívicas. El día del cambio cuenta como post-tratamiento.
FECHA_TRATAMIENTO = pd.Timestamp("2019-04-22")

# Tres años de cada lado, como en el capítulo 3 de la tesis.
VENTANA_INICIO = pd.Timestamp("2016-04-22")
VENTANA_FIN = pd.Timestamp("2022-04-21")

# México ITRF2008 / LCC, en metros. Las fuentes vienen en grados (EPSG:4326),
# que sirve para guardar pero no para medir: los radios de los círculos y las
# distancias a estaciones se definen en metros.
CRS_METRICO = "EPSG:6372"

# Las dos fuentes del Metro escriben distinto la misma estación. Estos dos casos
# no son de formato, así que no los arregla la normalización: la afluencia usa el
# nombre viejo de Niños Héroes, y el shapefile trae la errata "Mixhiuca". El mapeo
# va hacia la versión del shapefile porque ahí están las coordenadas.
RENOMBRES_ESTACION = {
    "NINOS HEROES": "NINOS HEROES/PODER JUDICIAL CDMX",
    "MIXIUHCA": "MIXHIUCA",
}


def ruta_corta(p: Path) -> str:
    """Ruta relativa al repo cuando se puede, absoluta cuando el archivo vive fuera."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def arreglar_mojibake(s: str) -> str:
    """Deshace 'LÃ­nea' -> 'Línea'. Si la cadena ya está bien, la devuelve igual.

    El CSV de afluencia mezcla codificaciones: el 15% de las filas trae los bytes
    UTF-8 leídos como latin-1. Sin esto aparecen 24 líneas en vez de 12.
    """
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def llave_estacion(s: str) -> str:
    """Clave de join: sin mojibake, sin acentos, sin guiones, en mayúsculas."""
    s = arreglar_mojibake(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.replace("-", " ").split()).upper()


def llave_linea(s: str) -> str:
    """Clave de línea: la afluencia dice 'Línea 1' y el shapefile '01'."""
    s = llave_estacion(s).replace("LINEA ", "")
    return s.zfill(2) if s.isdigit() else s  # '1' -> '01'; 'A' y 'B' se quedan


@dataclass
class Datos:
    """Las fuentes del análisis, limpias y en un mismo CRS.

    Parameters
    ----------
    data_dir : Path
        Carpeta de datos. Por defecto `data/` en la raíz del repo.
    crs : str
        CRS de salida de las capas geográficas.
    ventana : tuple[pd.Timestamp, pd.Timestamp]
        Rango de fechas al que se recortan las series temporales.
    fecha_tratamiento : pd.Timestamp
        Corte para `before_treatment`, con `<` estricto.
    """

    data_dir: Path = field(default_factory=lambda: ROOT / "data")
    crs: str = CRS_METRICO
    ventana: tuple[pd.Timestamp, pd.Timestamp] = (VENTANA_INICIO, VENTANA_FIN)
    fecha_tratamiento: pd.Timestamp = FECHA_TRATAMIENTO

    # Lo que se descartó, para poder reportarlo sin volver a leer los archivos.
    descartes: dict[str, int] = field(default_factory=dict, init=False)

    # =====================================================================
    # Fuentes
    # =====================================================================

    @cached_property
    def incidentes(self) -> gpd.GeoDataFrame:
        """Incidentes viales del C5, un punto por folio.

        Ya viene filtrado desde su origen a código de cierre A y a eventos de
        tránsito. Aquí solo se quitan folios repetidos y cinco registros del
        2018-12-31 cuya coordenada es cero: al proyectarlos se van a 10,000 km
        de la ciudad y arruinan cualquier sjoin o cálculo de extensión.
        """
        crudo = pd.read_parquet(self.data_dir / "classified-incidents.parquet")

        limpio = crudo.drop_duplicates(subset="folio")
        self.descartes["incidentes: folios repetidos"] = len(crudo) - len(limpio)

        con_coord = limpio.query("longitude != 0 and latitude != 0")
        self.descartes["incidentes: coordenada en cero"] = len(limpio) - len(con_coord)

        return gpd.GeoDataFrame(
            con_coord,
            geometry=gpd.points_from_xy(con_coord.longitude, con_coord.latitude),
            crs="EPSG:4326",
        ).to_crs(self.crs)[
            ["folio", "timestamp", "incident_level", "before_treatment", "geometry"]
        ]

    @cached_property
    def vialidades(self) -> gpd.GeoDataFrame:
        """Red vial primaria y de acceso controlado, un registro por segmento.

        Los 149 `ID_VIA` se reparten en miles de segmentos: eso es la estructura
        de la capa, no un duplicado. Lo que sí se quita son los segmentos que se
        repiten con todo y geometría.
        """
        crudo = gpd.read_file(self.data_dir / "vialidades.json").to_crs(self.crs)

        limpio = crudo.drop_duplicates()  # compara también la geometría
        self.descartes["vialidades: segmentos repetidos"] = len(crudo) - len(limpio)

        return limpio

    @cached_property
    def camaras(self) -> gpd.GeoDataFrame:
        """Ubicación de las cámaras de Fotocívicas: los centros del tratamiento.

        Se entregan las 113 sin deduplicar. Tres pares comparten coordenada
        exacta y generarían círculos idénticos, pero descartar uno de cada par
        aquí sería arbitrario: dos de esos pares son ubicaciones distintas a las
        que la fuente asignó la misma coordenada (dos puntos de la Autopista
        Urbana Norte; Eje 5 Sur contra Universidad, que están a kilómetros), y el
        tercero son dos cámaras reales en la misma esquina en sentidos opuestos.

        El traslape entre círculos, incluido el caso extremo de los que se
        superponen al 100%, se resuelve al construir las unidades de análisis y
        no aquí: es una regla de diseño del muestreo, no de limpieza.
        """
        return gpd.read_file(self.data_dir / "fotocivicas-ubicacion-puntos").to_crs(
            self.crs
        )

    @cached_property
    def estaciones(self) -> gpd.GeoDataFrame:
        """Estaciones del Metro, una fila por estación y línea.

        195 filas para 163 nombres: los 28 transbordos tienen un andén por línea,
        separados entre sí por 173 m en mediana y hasta 634 m. Para distancia a la
        estación más cercana conviene conservar los 195; para contar estaciones
        dentro de un área, agrupar por `estacion_key` evita inflar los transbordos.
        """
        gdf = gpd.read_file(self.data_dir / "stcmetro_shp" / "estaciones").to_crs(
            self.crs
        )
        return gdf.assign(
            linea_key=lambda x: x.LINEA.map(llave_linea),
            estacion_key=lambda x: x.NOMBRE.map(llave_estacion),
        )[["linea_key", "estacion_key", "NOMBRE", "ALCALDIAS", "geometry"]]

    @cached_property
    def lineas_metro(self) -> gpd.GeoDataFrame:
        """Trazo de las 12 líneas del Metro.

        Ojo con esta carpeta: los dos shapefiles se llaman `utm14n`, pero solo las
        líneas lo están (EPSG:32614); las estaciones vienen en grados. Cada `.prj`
        declara lo correcto, así que `to_crs` las alinea, pero mezclarlas sin
        reproyectar las manda a escalas distintas.
        """
        gdf = gpd.read_file(self.data_dir / "stcmetro_shp" / "lineas").to_crs(self.crs)
        return gdf.assign(linea_key=lambda x: x.LINEA.map(llave_linea))

    @cached_property
    def afluencia(self) -> pd.DataFrame:
        """Afluencia diaria del Metro por estación y línea.

        Lee `afluencia-metro-diaria.parquet`, que ya trae el encoding corregido y
        las llaves normalizadas. Ese archivo lo genera
        `scripts/pipeline/construir_afluencia.py` desde el CSV crudo, que se
        conserva solo como referencia de la fuente original.

        El parquet guarda el rango completo (2010-2026); la ventana y
        `before_treatment` se aplican aquí porque son parámetros de esta clase.

        Verifica que todo par (línea, estación) exista en el shapefile: si un
        renombre futuro rompe el join, truena aquí en vez de meter nulos.
        """
        ruta = self.data_dir / "afluencia-metro-diaria.parquet"
        if not ruta.exists():
            raise FileNotFoundError(
                f"falta {ruta_corta(ruta)}. "
                "Generarlo con: python scripts/pipeline/construir_afluencia.py"
            )

        crudo = pd.read_parquet(ruta)

        limpio = crudo.assign(
            before_treatment=lambda x: x.fecha < self.fecha_tratamiento
        )
        limpio = self._recortar(limpio, "fecha")
        self.descartes["afluencia: fuera de la ventana"] = len(crudo) - len(limpio)

        self._verificar_join_metro(limpio)

        return limpio[
            ["linea_key", "estacion_key", "fecha", "before_treatment", "afluencia"]
        ]

    @cached_property
    def volumen(self) -> pd.DataFrame:
        """Volumen vehicular mensual: el denominador de las tasas de incidentes.

        La mediana ronda 15,500, consistente con miles de vehículos y no con
        vehículos. Verificar contra la fuente antes de reescalar coeficientes.
        """
        crudo = pd.read_parquet(self.data_dir / "volumen-total-mensual.parquet")

        limpio = crudo.assign(
            before_treatment=lambda x: x.timestamp < self.fecha_tratamiento
        )
        limpio = self._recortar(limpio, "timestamp")
        self.descartes["volumen: fuera de la ventana"] = len(crudo) - len(limpio)

        return limpio

    # =====================================================================
    # Auxiliares
    # =====================================================================

    def _recortar(self, df: pd.DataFrame, columna: str) -> pd.DataFrame:
        """Deja solo las filas dentro de la ventana del estudio, extremos incluidos."""
        inicio, fin = self.ventana
        return df[df[columna].between(inicio, fin)]

    def _verificar_join_metro(self, afluencia: pd.DataFrame) -> None:
        """Truena si la afluencia tiene pares que el shapefile no reconoce."""
        pares_afluencia = set(
            map(tuple, afluencia[["linea_key", "estacion_key"]].drop_duplicates().values)
        )
        pares_estaciones = set(
            map(
                tuple,
                self.estaciones[["linea_key", "estacion_key"]].drop_duplicates().values,
            )
        )
        huerfanos = sorted(pares_afluencia - pares_estaciones)
        if huerfanos:
            raise ValueError(
                f"{len(huerfanos)} pares de afluencia sin estación en el shapefile: "
                f"{huerfanos[:5]}. Revisar RENOMBRES_ESTACION."
            )

    def cargar_todo(self) -> None:
        """Materializa las siete fuentes. Útil para validar de una sola vez."""
        for nombre in (
            "incidentes",
            "vialidades",
            "camaras",
            "estaciones",
            "lineas_metro",
            "afluencia",
            "volumen",
        ):
            getattr(self, nombre)

    def resumen(self) -> None:
        """Imprime qué se cargó y qué se descartó."""
        self.cargar_todo()

        inicio, fin = self.ventana
        print(f"ventana   : {inicio:%Y-%m-%d} a {fin:%Y-%m-%d}")
        print(f"tratamiento: {self.fecha_tratamiento:%Y-%m-%d} (el día cuenta como post)")
        print(f"crs        : {self.crs}")
        print()

        print(f"{'fuente':14s} {'filas':>10s}")
        for nombre in (
            "incidentes",
            "vialidades",
            "camaras",
            "estaciones",
            "lineas_metro",
            "afluencia",
            "volumen",
        ):
            print(f"{nombre:14s} {len(getattr(self, nombre)):>10,}")

        if self.descartes:
            print()
            print("descartado:")
            for motivo, n in self.descartes.items():
                print(f"  {motivo}: {n:,}")


if __name__ == "__main__":
    Datos().resumen()
