# Tesis: el efecto de las Fotocívicas sobre los incidentes viales

Efecto causal de las cámaras de velocidad de la Ciudad de México sobre los
incidentes viales, alrededor de la transición de Fotomultas a Fotocívicas el 22
de abril de 2019. Diferencias en diferencias sobre unidades circulares
emparejadas por propensity score, en cinco radios de 100 a 300 metros.

Actualizado: 2026-11-01.

## Estado

**El análisis está cerrado. Lo que falta es redactar.** La lista única de
pendientes, en orden, está en
[`scripts/resume-911/pendientes.md`](scripts/resume-911/pendientes.md): primero
el capítulo 3, después el 4, una línea del 2, las conclusiones con la
introducción, y la nota para el asesor. La revisión que motivó la reconstrucción
está en [`revision-alberto.md`](scripts/resume-911/revision-alberto.md).

El resultado principal es un nulo: ninguno de los 40 intervalos del bootstrap
excluye el cero. A 300 m, con todos los incidentes, el intervalo va de −6.0% a
+2.2% de la media del grupo de control.

## Dónde está cada cosa

**El análisis final, como código** — `scripts/pipeline/`. Cada módulo corre solo
e imprime sus verificaciones.

| Módulo | Qué hace |
| --- | --- |
| `limpieza.py` | `Datos`: carga y limpia las fuentes, en el CRS métrico |
| `construir_afluencia.py` | Genera `data/afluencia-metro-diaria.parquet` desde el CSV crudo. Se corre una vez |
| `unidades.py` | `UnidadesTratadas`: 113 cámaras → 99 unidades, círculos por radio y reparto de incidentes compartidos |
| `controles.py` | `UnidadesControl`: el pool de controles sobre la red vial |
| `features.py` | `Features`: las 12 covariables del propensity score |
| `emparejamiento.py` | `Emparejamiento` y `muestra_comun`: propensity score, emparejamiento y las 93 tratadas comunes a los cinco radios |
| `estimacion.py` | `Panel` y `tabla_resultados`: el panel y las tres especificaciones del DiD |

**El raciocinio y las pruebas** — `scripts/resume-911/`, en el orden en que se
construyó el análisis. Lo que el pipeline ejecuta, aquí se justifica.

| Notebook | Qué contiene |
| --- | --- |
| `recap-data` | Exploración de las fuentes |
| `unit-design` | Diseño de las unidades tratadas |
| `control-design` | Diseño del pool de controles |
| `feature-design` | Las 12 covariables y por qué esas |
| `propensity-score` | Modelo, emparejamiento, balance y figuras de soporte común y tendencias previas |
| `did-estimation` | Panel y especificaciones del DiD, con la verificación contra el pipeline |
| `bootstrap` | Bootstrap del proceso completo. Tarda unos 75 minutos y guarda su resultado en `data/bootstrap-coeficientes.parquet` |
| `interpretation` | La escalera de modelos, de la comparación ingenua al modelo final, y las tablas de la tesis |
| `efecto-por-anio` | El efecto por año del periodo posterior |
| `conclusiones` | Redacción de las conclusiones, con sus figuras. Al inicio dice a qué capítulo va cada sección |
| `auxiliary-figures` | Figuras auxiliares |

**Lo demás:**

| Ubicación | Qué es |
| --- | --- |
| `causal-effects-speed-cameras/` | Las fuentes en LaTeX (`main.tex`, `Chapters/`). Los capítulos 3 y 4 todavía describen el análisis anterior |
| `figures/` | Las figuras de la tesis, en SVG |
| `notas/` | Transcripción de apuntes: conclusiones y errores cometidos |
| `nbsetup.py` | Arranque de los notebooks |
| `scripts/*.py`, `scripts/auxiliar/`, `scripts/writing/` | La versión anterior del análisis. Quedan como referencia; el análisis actual no los usa. `google_places_aggregate.py`, `places_api.py` y `test_response_structure.py` son del análisis de densidad de negocios |

## Cómo correrlo

El entorno es el de conda `tesis-cameras`. No hay un archivo de entorno fijado.

Cada notebook empieza con `from nbsetup import *`, que deja el directorio de
trabajo en la raíz del repo e importa lo de siempre. Funciona desde cualquier
carpeta gracias a un archivo `.pth` en el entorno, que es local a esta máquina:
en otra, hay que crearlo o agregar la raíz del repo al `PYTHONPATH`.

Los módulos del pipeline corren solos, por ejemplo
`python scripts/pipeline/estimacion.py`. Los notebooks corren de principio a fin
con `jupyter nbconvert --execute`. El único lento es el bootstrap, y como su
resultado está versionado, ningún otro notebook necesita volver a correrlo.

## Insumos versionados

Unos 20 MB en total.

| Archivo | Qué es |
| --- | --- |
| `data/classified-incidents.parquet` | Incidentes viales del C5, clasificados en MIN, PIC y FCS |
| `data/vialidades.json` | Red vial primaria y de acceso controlado |
| `data/fotocivicas-ubicacion-puntos/` | Ubicación de las 113 cámaras |
| `data/stcmetro_shp/` | Estaciones y líneas del Metro. Cada shapefile con sus archivos hermanos: sin el `.prj` se pierde el CRS |
| `data/afluencia-metro-diaria.parquet` | Afluencia diaria del Metro, generada desde el CSV crudo, que no está versionado |
| `data/volumen-total-mensual.parquet` | Volumen de las casetas de peaje. No entra a la estimación; solo a la figura de la pandemia |
| `data/bootstrap-coeficientes.parquet` | Resultado del bootstrap: 80,000 coeficientes |

## Preservar el análisis de densidad de negocios

Notebook: `scripts/writing/mexico-city-business-density.ipynb`. No forma parte de
la reconstrucción y se conserva tal cual, con sus propios insumos:

- `data/raw-data/businesses-cdmx.json`: las respuestas de Google guardadas.
  Volver a consultarlas hoy no reproduciría los conteos históricos.
- `data/localidadurbana/`: el shapefile de cobertura geográfica.
- `data/classified-incidents.parquet`: el análisis lo usa para elegir sus
  hexágonos. No sobrescribirlo con una limpieza nueva.
- `data/vialidades.json`.
- `data/graphs/establecimientos-en-la-cdmx.png` y
  `data/graphs/distribucion-establecimientos-cdmx-hexagonos.png`.

**El JSON de negocios, el shapefile de cobertura y esas figuras no están
versionados.** Un clon trae el notebook pero no todo lo necesario para
reproducirlo. Hay que tener un respaldo externo y no borrar esos archivos
locales.

## Git y respaldos

El remoto es `git@github-personal:MarianoAlcarazAguilar/causal-effects-speed-cameras.git`,
con la cuenta personal. El `.gitignore` es una lista de permitidos: un archivo
nuevo queda fuera hasta que se agrega explícitamente.

Quedan fuera los datos crudos, los grids, emparejamientos y paneles del análisis
anterior, `data/pickle_objects/`, los PDF y los respaldos. Un clon no es un
archivo completo: los datos originales y la extracción manual del volumen
vehicular hay que respaldarlos aparte. Los archivos `.gsheet` son enlaces, no
respaldos de sus hojas.

**Pendiente de seguridad:** en el notebook versionado de densidad de negocios
apareció una llave de la API de Google. Rotarla y quitarla del historial sigue
pendiente hasta confirmarlo.
