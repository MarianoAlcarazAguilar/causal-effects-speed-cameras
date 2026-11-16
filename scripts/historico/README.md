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

## Las cuatro versiones

Cada carpeta es una versión del análisis, en el orden en que se hicieron. Un nombre
que se repite entre carpetas (por ejemplo, `data-acquaintance` en la 1 y en la 2) es
el mismo paso rehecho en la versión siguiente. La columna **Hoy** dice qué lo
reemplazó en el análisis actual.

### `1-exploracion-inicial/`

La primera idea, con otras fuentes: accidentes, ingresos de parquímetros, afluencia
del Metrobús y ejes viales. Lee rutas (`../data/clean`, `../thesis-data`) de una
organización de carpetas que ya no existe.

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `data-acquaintance` | Exploración de las fuentes | `scripts/analisis/01-recap-data` |
| `build-propensity-score-features` | Covariables y accidentes ponderados por zona | `scripts/pipeline/features.py` |
| `calculate-propensity-score` | *Propensity score* y emparejamiento | `scripts/pipeline/emparejamiento.py` |
| `calculate-effects` | Primer cálculo del efecto | `scripts/pipeline/estimacion.py` |

### `2-malla-cuadrada-borrador/`

Primer análisis con las fuentes actuales (incidentes del C5, Metro, vialidades y
casetas) sobre una malla de cuadros. Es una serie numerada que se quedó a medias; las
notas de `4-propensity-score` son de agosto de 2025. La limpieza de los incidentes que
hoy usa el pipeline salió de aquí.

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `1-data-acquaintance` | Exploración de las fuentes y series de afluencia del Metro | `scripts/analisis/01-recap-data` |
| `2-data-cleaning` | Limpieza y clasificación de los incidentes en MIN, PIC y FCS | Su resultado es `data/classified-incidents.parquet` |
| `extracting-datos-viales` | Volumen de las casetas de peaje, copiado a mano de los informes de la SICT | Su resultado es `data/volumen-total-mensual.parquet` |
| `3-create-ps-features` | Malla de cuadros y covariables | `scripts/pipeline/features.py` |
| `4-propensity-score` | Por qué emparejar, *propensity score* y primer análisis | `scripts/pipeline/emparejamiento.py` |
| `5-other-stuff` | Datos para la introducción e infracciones | — |

### `3-malla-cuadrada/`

La versión 2 rehecha como un flujo completo, con salidas intermedias guardadas en
`data/`. Elige el tamaño y el desplazamiento de la malla, y estima tanto en conteos
como en tasas.

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `assesing-road-distribution` | Tamaño y desplazamiento de la malla según cómo caen las vialidades y las cámaras | `scripts/analisis/02-unit-design` |
| `ps-features-crafting` | Malla, covariables y variables de resultado | `scripts/pipeline/features.py` |
| `ps-matching` | *Propensity score* y emparejamiento | `scripts/pipeline/emparejamiento.py` |
| `estimating-effects` | Diferencias en diferencias, en conteos y en tasas | `scripts/pipeline/estimacion.py` |
| `comparando-estudiadas-vs-resto` | Cómo cambiaba la tasa de incidentes en las celdas analizadas contra el resto de la ciudad | — |

Estos dos notebooks importaban `build_grid` de un `utils.py` que después se convirtió
en `4-circulos/grid_builder.py`; ya apuntan ahí.

### `4-circulos/`: la versión que revisó Alberto (hasta septiembre de 2026)

Los cuadros se cambiaron por círculos alrededor de cada cámara, y el flujo pasó a
cuatro clases en módulos para que fuera replicable. Es la versión que motivó la
reconstrucción.

**Los módulos**

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `grid_builder.py` | Mallas de cuadros y de círculos, y fusión de cámaras cercanas | `scripts/pipeline/unidades.py` y `controles.py` |
| `ps_features_builder.py` | `PSFeaturesBuilder`: unidades, covariables y variables de resultado | `scripts/pipeline/features.py` |
| `ps_matching.py` | `PSMatching`: *propensity score*, emparejamiento, SMD y soporte común | `scripts/pipeline/emparejamiento.py` |
| `effect_estimation.py` | `EffectEstimation`: diferencias en diferencias | `scripts/pipeline/estimacion.py` |
| `google_places_aggregate.py`, `places_api.py`, `test_response_structure.py` | Clientes de la API de Google Places, para contar establecimientos. La llave se lee de la variable de entorno `GOOGLE_API_KEY` | Los conteos ya consultados están en `data/raw/businesses-cdmx.json` (fuera de git) |
| `road_network_panel.py`, `weekly_incidents_panel.py` | Figuras de la red vial y de los incidentes semanales | Ya no están en la tesis |

**El flujo, en orden**

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `circular-grids-smd` | Círculos en varios radios y su balance | `scripts/pipeline/unidades.py` |
| `best-smd-minimization-columns` | Qué covariables quitar para minimizar el SMD | `scripts/analisis/04-feature-design` |
| `proving-common-support` | Soporte común y balance | `scripts/analisis/05-propensity-score` |
| `acid-test` | Que ningún círculo de control contuviera una cámara | `scripts/pipeline/controles.py` |
| `using-classes-for-effects` | Estimación del efecto con las clases (la segunda de tres versiones; la primera es `3-malla-cuadrada/estimating-effects`) | `scripts/pipeline/estimacion.py` |
| `effects-circular-optimized` | La tercera versión: recorta lo que queda fuera de soporte y usa las covariables que minimizan el SMD | `scripts/pipeline/estimacion.py` |
| `parallel-trends` | Pruebas placebo de tendencias paralelas | El *event study* (`scripts/figuras/capitulo4_figures.py`) |
| `plotting-parallel-trends` | Gráficas de las tendencias antes y después, con y sin emparejamiento | El *event study* |
| `plotting-coefficients-offsets` | Coeficientes al mover la malla | — (la malla se descartó) |

**La evidencia para el texto**

| Archivo | Qué hacía | Hoy |
| --- | --- | --- |
| `fuentes-de-datos` | Documentación de las fuentes de datos | Capítulo 3, sección 3.1 |
| `control-justification` | Por qué los controles van sobre vías primarias | Capítulo 2, sección 2.2.3 |
| `vias-primarias-vs-secundarias` | Hexágonos con y sin vía primaria: incidentes | `scripts/figuras/apendice_figures.py` (apéndice B) |
| `mexico-city-business-density` | Hexágonos con y sin vía primaria: establecimientos de Google Places | `scripts/figuras/apendice_figures.py` (apéndice B) |

## Si hace falta correr algo de aquí

Desde la carpeta de cada versión, las versiones 2 a 4 leen los datos con
`PATH_DATA = '../../../data/'`. Los notebooks de la 4 importan los módulos de su
misma carpeta, y los de la 3 los toman de `../4-circulos`. Muchos dependen de
archivos intermedios que no están en el repo (mallas, emparejamientos y paneles en
pickle), y `ps_matching.py` necesita `seaborn`, que el entorno actual no tiene.

Se quitaron dos notebooks sin contenido propio: `todos` (un pendiente de una figura del *propensity score*,
que hoy es la de soporte común) y `plot-images-points` (una prueba con
datos inventados). Siguen en la historia de git.
