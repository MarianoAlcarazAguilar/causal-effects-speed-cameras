"""
Construye el parquet limpio de afluencia del Metro a partir del CSV crudo.

Se corre una vez; después el pipeline lee el parquet y el CSV queda solo como
referencia de la fuente original.

    python scripts/pipeline/construir_afluencia.py

Qué hace, y por qué no se puede leer el crudo directo:

- El CSV mezcla dos codificaciones. 171,795 filas (15%) traen los bytes UTF-8 de
  'Línea' leídos como latin-1, o sea 'LÃ­nea'. Sin corregirlo aparecen 24 líneas
  en vez de 12 y 395 pares estación-línea en vez de 195.
- Los nombres no empatan con el shapefile del STC: acentos, guiones y el formato
  del número de línea. Aquí se generan las llaves normalizadas del join.

Lo que NO hace, a propósito: recortar a la ventana del estudio ni calcular
`before_treatment`. Eso depende de parámetros de `Datos` y se aplica al cargar,
para que el archivo sirva con cualquier ventana.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.limpieza import (  # noqa: E402
    RENOMBRES_ESTACION,
    ROOT,
    llave_estacion,
    llave_linea,
    ruta_corta,
)

ORIGEN = ROOT / "data" / "raw" / "raw-afluencia-metro.csv"
DESTINO = ROOT / "data" / "afluencia-metro-diaria.parquet"


def construir(origen: Path = ORIGEN, destino: Path = DESTINO) -> pd.DataFrame:
    crudo = pd.read_csv(origen)

    limpio = crudo.assign(
        linea_key=lambda x: x.linea.map(llave_linea),
        estacion_key=lambda x: x.estacion.map(llave_estacion).replace(
            RENOMBRES_ESTACION
        ),
        fecha=lambda x: pd.to_datetime(x.fecha),
    )[["fecha", "linea_key", "estacion_key", "afluencia"]]

    destino.parent.mkdir(parents=True, exist_ok=True)
    limpio.to_parquet(destino, index=False)

    print(f"origen : {ruta_corta(origen)} ({origen.stat().st_size / 1e6:,.0f} MB)")
    print(f"destino: {ruta_corta(destino)} ({destino.stat().st_size / 1e6:,.1f} MB)")
    print()
    print(f"filas            : {len(limpio):,}")
    print(f"rango de fechas  : {limpio.fecha.min():%Y-%m-%d} a {limpio.fecha.max():%Y-%m-%d}")
    print(f"líneas           : {limpio.linea_key.nunique()} (crudo: {crudo.linea.nunique()})")
    print(f"estaciones       : {limpio.estacion_key.nunique()} (crudo: {crudo.estacion.nunique()})")
    print(f"pares línea-est. : {limpio.groupby(['linea_key', 'estacion_key']).ngroups}")

    return limpio


if __name__ == "__main__":
    construir()
