# Validación de insumos limpios

Directorio: `data`
Fecha de tratamiento de referencia: 2019-04-22

## Incidentes clasificados — `classified-incidents.parquet`

- Tamaño: 10.0 MB
- Filas: 432,707 | Columnas: 8
- Esquema:

  | Columna | Tipo | Nulos | % nulos | Únicos |
  | --- | --- | ---: | ---: | ---: |
  | `folio` | str | 0 | 0.0% | 432,703 |
  | `timestamp` | datetime64[ns] | 0 | 0.0% | 431,451 |
  | `incident_level` | category | 0 | 0.0% | 3 |
  | `hour` | int8 | 0 | 0.0% | 24 |
  | `weekday` | category | 0 | 0.0% | 7 |
  | `before_treatment` | bool | 0 | 0.0% | 2 |
  | `longitude` | float64 | 0 | 0.0% | 88,302 |
  | `latitude` | float64 | 0 | 0.0% | 91,130 |

- Filas duplicadas exactas: 4
- **Revisar:** 4 filas duplicadas exactas; decidir si se eliminan.
- Longitud: -99.35351 a 0.00000
- Latitud: 0.00000 a 19.57932
- **Revisar:** 5 filas con coordenada en cero.
- Fuera de la caja CDMX: 5 (0.00%)
- **Revisar:** 5 puntos (0.00%) fuera de la caja CDMX; decidir si se recortan antes de agregar a círculos.
- Cobertura `timestamp`: 2016-04-22 a 2022-04-20
- Respecto al 2019-04-22: 226,430 previas, 206,277 posteriores
- Meses con datos: 73 de 73 en el rango
- Distribución de `incident_level`:

  - `MIN`: 239,069 (55.2%)
  - `PIC`: 191,681 (44.3%)
  - `FCS`: 1,957 (0.5%)


## Ubicación de cámaras (Fotocívicas) — `fotocivicas-ubicacion-puntos`

- Tamaño: 0.1 MB
- Filas: 113 | Columnas: 8
- Esquema:

  | Columna | Tipo | Nulos | % nulos | Únicos |
  | --- | --- | ---: | ---: | ---: |
  | `geo_shape` | str | 0 | 0.0% | 110 |
  | `ubi` | float64 | 0 | 0.0% | 111 |
  | `no` | float64 | 0 | 0.0% | 53 |
  | `via_princi` | str | 0 | 0.0% | 80 |
  | `ubicacion` | str | 0 | 0.0% | 111 |
  | `sentido` | str | 0 | 0.0% | 7 |
  | `y` | float64 | 0 | 0.0% | 109 |
  | `x` | float64 | 0 | 0.0% | 110 |

- Filas duplicadas exactas: 0 (solo atributos, sin geometría: 0; esperado en capas segmentadas)
- CRS declarado: EPSG:4326
- Tipos de geometría: {'Point': 113}
- Geometrías vacías: 0 | nulas: 0 | inválidas: 0
- Extensión: lon -99.22076 a -99.01535, lat 19.26593 a 19.51192
- Longitud: -99.22076 a -99.01535
- Latitud: 19.26593 a 19.51192
- Fuera de la caja CDMX: 0 (0.00%)
- Cámaras con coordenada idéntica: 3
- **Revisar:** 3 cámaras comparten coordenada exacta; afecta la definición de centros y el conteo de unidades tratadas.

## Vialidades — `vialidades.json`

- Tamaño: 5.7 MB
- Filas: 10,567 | Columnas: 9
- Esquema:

  | Columna | Tipo | Nulos | % nulos | Únicos |
  | --- | --- | ---: | ---: | ---: |
  | `ID_VIA` | int32 | 0 | 0.0% | 149 |
  | `NOMBRE` | str | 0 | 0.0% | 149 |
  | `ID_NOM` | int32 | 0 | 0.0% | 14 |
  | `NOMENCLAT` | str | 20 | 0.2% | 399 |
  | `TIPO_VIA` | str | 0 | 0.0% | 2 |
  | `CARRILES` | str | 0 | 0.0% | 8 |
  | `NIVEL` | int32 | 0 | 0.0% | 5 |
  | `CIRCULA` | str | 0 | 0.0% | 3 |
  | `ALCALDIA` | str | 0 | 0.0% | 25 |

- **Revisar:** `NOMENCLAT` tiene 20 nulos (0.2%).
- Filas duplicadas exactas: 64 (solo atributos, sin geometría: 8,769; esperado en capas segmentadas)
- **Revisar:** 64 filas duplicadas exactas; decidir si se eliminan.
- CRS declarado: EPSG:4326
- Tipos de geometría: {'LineString': 10567}
- Geometrías vacías: 0 | nulas: 0 | inválidas: 0
- Extensión: lon -99.30069 a -98.95785, lat 19.19625 a 19.54030
- Valores de `TIPO_VIA`: ['Vía de acceso controlado', 'Vía primaria']
- Valores de `CIRCULA`: ['Dos sentidos', 'Un sentido', 'Un sentido con carril de contraflujo']
- `CARRILES`: min 1, max 8, mediana 3.0
- `ID_VIA` duplicados: 10,418

## Coordenadas de estaciones del Metro — `metro-station-coordinates.parquet`

- Tamaño: 0.0 MB
- Filas: 167 | Columnas: 3
- Esquema:

  | Columna | Tipo | Nulos | % nulos | Únicos |
  | --- | --- | ---: | ---: | ---: |
  | `estacion` | str | 0 | 0.0% | 167 |
  | `latitude` | float64 | 0 | 0.0% | 136 |
  | `longitude` | float64 | 0 | 0.0% | 134 |

- Filas duplicadas exactas: 0
- Longitud: -99.25795 a -98.99351
- Latitud: 19.25266 a 19.56711
- Fuera de la caja CDMX: 0 (0.00%)
- `estacion` duplicadas: 0

## Afluencia semanal del Metro — `afluencia-metro-semanal.parquet`

- Tamaño: 2.9 MB
- Filas: 130,564 | Columnas: 6
- Esquema:

  | Columna | Tipo | Nulos | % nulos | Únicos |
  | --- | --- | ---: | ---: | ---: |
  | `fecha` | datetime64[ns] | 0 | 0.0% | 801 |
  | `estacion` | str | 0 | 0.0% | 167 |
  | `afluencia_total` | int64 | 0 | 0.0% | 101,662 |
  | `media_diaria` | float64 | 0 | 0.0% | 102,581 |
  | `std_diaria` | float64 | 2 | 0.0% | 123,778 |
  | `before_treatment` | bool | 0 | 0.0% | 2 |

- **Revisar:** `std_diaria` tiene 2 nulos (0.0%).
- Filas duplicadas exactas: 0
- Cobertura `fecha`: 2010-01-03 a 2025-05-04
- Respecto al 2019-04-22: 79,218 previas, 51,346 posteriores
- Meses con datos: 185 de 185 en el rango
- Estaciones distintas: 167
- `afluencia_total`: min 0.00, mediana 123,486.50, max 2,704,417.00
- `media_diaria`: min 0.00, mediana 15,553.43, max 148,561.86
- `std_diaria`: min 0.00, mediana 4,186.99, max 67,418.19

## Volumen vehicular mensual — `volumen-total-mensual.parquet`

- Tamaño: 0.0 MB
- Filas: 120 | Columnas: 2
- Esquema:

  | Columna | Tipo | Nulos | % nulos | Únicos |
  | --- | --- | ---: | ---: | ---: |
  | `timestamp` | datetime64[ns] | 0 | 0.0% | 120 |
  | `volumen_mensual` | float64 | 0 | 0.0% | 120 |

- Filas duplicadas exactas: 0
- Cobertura `timestamp`: 2015-01-01 a 2024-12-01
- Respecto al 2019-04-22: 52 previas, 68 posteriores
- Meses con datos: 120 de 120 en el rango
- `volumen_mensual`: min 8,699.86, mediana 15,525.90, max 19,799.51
- Magnitud mediana sugiere unidades en miles de vehículos (verificar contra la fuente antes de reescalar coeficientes).

## Resumen

7 puntos requieren revisión o decisión:

1. 4 filas duplicadas exactas; decidir si se eliminan.
2. 5 filas con coordenada en cero.
3. 5 puntos (0.00%) fuera de la caja CDMX; decidir si se recortan antes de agregar a círculos.
4. 3 cámaras comparten coordenada exacta; afecta la definición de centros y el conteo de unidades tratadas.
5. `NOMENCLAT` tiene 20 nulos (0.2%).
6. 64 filas duplicadas exactas; decidir si se eliminan.
7. `std_diaria` tiene 2 nulos (0.0%).