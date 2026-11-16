# Histórico: el análisis antes de la reconstrucción

Aquí está el código de las versiones anteriores del análisis. **Ya nada de la tesis lo
usa**: se conserva para poder ver cómo se llegó al diseño actual y de dónde salió cada
decisión. No se garantiza que corra; algunos insumos que leía ya no existen.

## Por qué se archivó

En septiembre de 2026, Alberto revisó la versión completa de la tesis
([`notas/revision-alberto.md`](../../notas/revision-alberto.md)). Su primer punto
mostró que **los resultados no eran comparables entre radios**: en cada radio las
unidades tratadas se construían otra vez (los centros se movían al resolver traslapes)
y el recorte por soporte común dejaba fuera unidades distintas, así que cada radio
estimaba el efecto sobre otro conjunto de zonas. Corregirlo cambió el diseño de raíz,
y el análisis se rehízo desde cero en `scripts/pipeline/` y `scripts/analisis/`. Los
errores y las decisiones de esa transición están en
[`notas/Errores Cometidos.md`](../../notas/Errores%20Cometidos.md) y en
[`notas/bitacora-del-analisis.md`](../../notas/bitacora-del-analisis.md).

## Qué hay y qué lo reemplazó

### `auxiliar/`: el primer intento (mayo de 2025)

Una serie numerada que se quedó a medias: exploración, limpieza, covariables y
*propensity score*. La limpieza de los incidentes que hoy usa el pipeline salió de
`2-data-cleaning`.

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `1-data-acquaintance` | Exploración de las fuentes | `scripts/analisis/01-recap-data` |
| `2-data-cleaning` | Limpieza y clasificación de los incidentes en MIN, PIC y FCS | Su resultado es `data/classified-incidents.parquet` |
| `3-create-ps-features` | Primeras covariables del *propensity score* | `scripts/pipeline/features.py` |
| `4-propensity-score` | Primer modelo de *propensity score* | `scripts/pipeline/emparejamiento.py` |
| `5-other-stuff` | Exploraciones sueltas | — |
| `extracting-datos-viales` | Volumen de las casetas de peaje, copiado a mano de los informes de la SICT | Su resultado es `data/volumen-total-mensual.parquet` |
| `plot-images-points` | Prueba de una figura con imágenes como puntos | — |
| `initial-research/` | Cuatro notebooks de la investigación inicial (exploración, covariables, *propensity score* y efectos) | — |

### `writing/`: la versión que revisó Alberto (hasta septiembre de 2026)

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `fuentes-de-datos` | Documentación de las fuentes de datos | Capítulo 3, sección 3.1 |
| `vias-primarias-vs-secundarias` | Hexágonos con y sin vía primaria: incidentes | `scripts/figuras/apendice_figures.py` (apéndice B) |
| `mexico-city-business-density` | Hexágonos con y sin vía primaria: establecimientos de Google Places | `scripts/figuras/apendice_figures.py` (apéndice B) |
| `assesing-road-distribution` | Cómo se distribuyen las vialidades y las cámaras | `scripts/analisis/02-unit-design` |
| `control-justification` | Por qué los controles van sobre vías primarias | Capítulo 2, sección 2.2.3 |
| `acid-test` | Que ningún círculo de control contuviera una cámara | `scripts/pipeline/controles.py` |
| `circular-grids-smd` | Mallas de círculos en varios radios y su balance | `scripts/pipeline/unidades.py` |
| `comparando-estudiadas-vs-resto` | Cómo cambiaba la tasa de incidentes en las celdas analizadas contra el resto de la ciudad | — |
| `ps-features-crafting` | Las covariables del *propensity score* (eran 18) | `scripts/pipeline/features.py` (ahora 12) |
| `best-smd-minimization-columns` | Qué covariables quitar para minimizar el SMD | `scripts/analisis/04-feature-design` |
| `ps-matching` | *Propensity score* y emparejamiento | `scripts/pipeline/emparejamiento.py` |
| `proving-common-support` | Soporte común y balance | `scripts/analisis/05-propensity-score` |
| `estimating-effects`, `using-classes-for-effects`, `effects-circular-optimized` | Tres versiones sucesivas de la estimación del efecto | `scripts/pipeline/estimacion.py` |
| `parallel-trends`, `plotting-parallel-trends` | Tendencias paralelas: gráficas y pruebas placebo | El *event study* (`scripts/figuras/capitulo4_figures.py`) |
| `plotting-coefficients-offsets` | Gráfica de coeficientes al mover la malla | — (la malla se descartó) |
| `todos` | Lista de pendientes de esa versión | [`notas/bitacora-del-analisis.md`](../../notas/bitacora-del-analisis.md) |

### Módulos sueltos

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `grid_builder.py` | Mallas de celdas y de círculos sobre la ciudad | `scripts/pipeline/unidades.py` y `controles.py` |
| `ps_features_builder.py` | Covariables y variables de resultado | `scripts/pipeline/features.py` |
| `ps_matching.py` | *Propensity score* y emparejamiento | `scripts/pipeline/emparejamiento.py` |
| `effect_estimation.py` | Diferencias en diferencias | `scripts/pipeline/estimacion.py` |
| `google_places_aggregate.py`, `places_api.py`, `test_response_structure.py` | Clientes de la API de Google Places, para contar establecimientos. La llave se lee de la variable de entorno `GOOGLE_API_KEY` | Los conteos ya consultados están en `data/raw/businesses-cdmx.json` (fuera de git) |
| `road_network_panel.py`, `weekly_incidents_panel.py` | Figuras de la red vial y de los incidentes semanales | Ya no están en la tesis |

## Si hace falta correr algo de aquí

Los notebooks de `writing/` y `auxiliar/` leen los datos con rutas relativas a su
carpeta (`PATH_DATA = '../../../data/'`) e importan los módulos de esta carpeta con
`sys.path.insert(1, '../')`. Muchos dependen de archivos intermedios del análisis
anterior (mallas, emparejamientos y paneles en pickle) que no están en el repo.
