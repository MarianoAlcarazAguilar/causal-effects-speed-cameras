# Tesis: el efecto de las Fotocívicas sobre los incidentes viales

Efecto causal de las cámaras de velocidad del programa Fotocívicas sobre los
incidentes viales en la Ciudad de México, a partir de su entrada en vigor el 22
de abril de 2019. Diferencias en diferencias sobre áreas circulares de 100 a 300
metros alrededor de las cámaras, emparejadas por *propensity score* con zonas
igual de peligrosas de la misma red vial.

Licenciatura en Ciencia de Datos, ITAM. Asesor: Dr. Alberto Simpser.

## Estado

El análisis y la redacción están completos (110 páginas). Falta la dedicatoria,
los agradecimientos, el año de la portada y la fecha del colofón. La revisión del
asesor que motivó la reconstrucción está en
[`notas/revision-alberto.md`](notas/revision-alberto.md).

El resultado principal es un nulo. A 300 metros, el efecto sobre el total de
incidentes es de −1.8% de la media previa del control, con un intervalo del
*bootstrap* de −6.0% a +2.2%, y ningún radio ni tipo de incidente se distingue de
cero.

## Dónde está cada cosa

```
tesis/              La tesis en LaTeX: main.tex, Chapters/, Apendices/, Referencias/
scripts/
  pipeline/         El análisis final como código
  analisis/         Los notebooks que justifican cada paso, numerados en orden
  figuras/          Las figuras de la tesis, un script por capítulo
  visor/            Visor local de la tesis
  historico/        El análisis de septiembre de 2026, como referencia. Ya nada lo usa
data/               Insumos versionados (ver abajo)
notas/              Revisión del asesor, pendientes y apuntes
.claude/skills/
  figuras-tesis/    Estilo, convenciones y ejemplos de las figuras (ver abajo)
nbsetup.py          Arranque de los notebooks
```

### `scripts/pipeline/`

Cada módulo corre solo e imprime sus verificaciones.

| Módulo | Qué hace |
| --- | --- |
| `limpieza.py` | `Datos`: carga y limpia las fuentes, en el CRS métrico |
| `construir_afluencia.py` | Genera `data/afluencia-metro-diaria.parquet` desde el CSV crudo. Se corre una vez |
| `unidades.py` | `UnidadesTratadas`: 113 cámaras → 99 unidades, círculos por radio y reparto de incidentes compartidos |
| `controles.py` | `UnidadesControl`: los candidatos a control sobre la red vial |
| `features.py` | `Features`: las 12 covariables del *propensity score* |
| `emparejamiento.py` | `Emparejamiento` y `muestra_comun`: *propensity score*, emparejamiento y las 93 tratadas comunes a los cinco radios |
| `estimacion.py` | `Panel` y `tabla_resultados`: el panel y las tres especificaciones del modelo |

### `scripts/analisis/`

Lo que el pipeline ejecuta, aquí se justifica. Se leen en orden.

| Notebook | Qué contiene |
| --- | --- |
| `01-recap-data` | Exploración de las fuentes |
| `02-unit-design` | Diseño de las unidades tratadas |
| `03-control-design` | Diseño de los candidatos a control |
| `04-feature-design` | Las 12 covariables y por qué esas |
| `05-propensity-score` | Modelo, emparejamiento, balance, soporte común y tendencias previas |
| `06-did-estimation` | Panel y especificaciones, con la verificación contra el pipeline |
| `07-bootstrap` | *Bootstrap* del proceso completo. Tarda unos 75 minutos y guarda su resultado en `data/bootstrap-coeficientes.parquet` |
| `08-interpretation` | La escalera de comparaciones y las tablas de la tesis |
| `09-efecto-por-anio` | El efecto por año del periodo posterior |
| `10-conclusiones` | Las figuras de los resultados y las conclusiones |
| `11-auxiliary-figures` | Figuras auxiliares |

### `scripts/visor/`

Compila la tesis al guardar, la compara contra cualquier versión de git y guarda
los comentarios que se hacen sobre el PDF como bloques de comentario en los `.tex`.
Necesita `tectonic` y `latexdiff` (`brew install tectonic latexdiff`). Todo lo que
genera vive en `.visor/`, que no está en git.

| Módulo | Qué hace |
| --- | --- |
| `__main__.py` | Arranque: `python3 scripts/visor [--port 9000] [--no-browser]` |
| `config.py` | Rutas y constantes |
| `git_utils.py` | Versiones de la tesis, diff de las fuentes y archivos en un commit |
| `latex.py` | Prepara las fuentes de una versión y compila con tectonic |
| `trabajos.py` | Cola de compilaciones, estado compartido y vigilancia de cambios en disco |
| `secciones.py` | Qué secciones del índice cambiaron entre dos versiones |
| `comentarios.py` | Comentarios guardados en las fuentes |
| `servidor.py` | Servidor HTTP: la página, los PDF y la API |
| `static/` | La interfaz: `index.html`, `visor.css` y `visor.js` |

### `scripts/figuras/`

Cada script genera los PDF de un capítulo en `tesis/Imagenes/`. Con `--png` deja
además una vista previa en `scripts/figuras/png/`, que no entra a git. El estilo lo importan de la skill
`figuras-tesis` (abajo).

| Script | Figuras |
| --- | --- |
| `intro_figures.py` | Introducción |
| `capitulo3_figures.py` | Capítulo 3 y soporte común del apéndice A |
| `capitulo4_figures.py` | Capítulo 4 (lee el *bootstrap* versionado; no lo recalcula) |
| `apendice_figures.py` | Apéndice B. Necesita `data/raw/businesses-cdmx.json`, que no está versionado |

### `.claude/skills/figuras-tesis/`

Una skill de Claude Code del proyecto: todo lo necesario para que una figura nueva se
vea como las de la tesis. Claude la carga sola cuando, trabajando en este repo, se le
pide una figura; también se puede leer como documentación.

| Ruta | Qué es |
| --- | --- |
| `SKILL.md` | Cuándo usarla, el flujo para agregar una figura y las reglas que más se olvidan |
| `assets/` | `tesis.mplstyle` y las fuentes Latin Modern |
| `scripts/estilo_tesis.py` | Registra las fuentes y aplica el estilo; los colores (`OSCURO`, `CLARO`, `ACENTO`…), el ancho de la figura y utilidades como `cero()`, `pct()` y `guardar()` |
| `references/convenciones.md` | Las reglas de las figuras, cada una con el caso de la tesis del que salió |
| `references/tipos-de-figura.md` | Qué figura usar para qué, y lo que se probó y no funcionó |
| `references/latex.md` | Cómo insertarlas: caption, nota a renglón sencillo y cómo evitar que muevan páginas |
| `examples/` | Cinco ejemplos que corren solos, con su PNG: escalera de coeficientes, *event study*, distribuciones, *love plot* y mapa resaltado |

**Los scripts de `scripts/figuras/` importan el estilo de aquí:** cambiar
`estilo_tesis.py`, `tesis.mplstyle` o las fuentes cambia todas las figuras de la tesis.
La skill pasa el validador oficial de skills; no hace falta empaquetarla como `.skill`,
porque Claude Code la lee como carpeta (el `.skill` es solo para compartirla o
instalarla en claude.ai).

## Cómo correrlo

El entorno es el de conda `tesis-cameras`. No hay un archivo de entorno fijado;
el apéndice B necesita además `h3` (v4).

- **La tesis:** `python3 scripts/visor` abre el visor en
  http://127.0.0.1:8765, compila al guardar y compara contra cualquier versión de
  git. Para compilar a mano: `tectonic -X compile tesis/main.tex`.
- **Las figuras:** `python scripts/figuras/<script>.py` (con `--png` para la vista
  previa). Para una figura nueva, partir de `.claude/skills/figuras-tesis/`.
- **Los notebooks:** empiezan con `from nbsetup import *`, que deja el directorio
  de trabajo en la raíz del repo y pone `scripts/` en el path. Funciona desde
  cualquier carpeta gracias a un archivo `.pth` en el entorno, que es local a esta
  máquina: en otra, hay que agregar la raíz del repo al `PYTHONPATH`.

## Insumos versionados

| Archivo | Qué es |
| --- | --- |
| `data/classified-incidents.parquet` | Incidentes viales del C5, clasificados en MIN, PIC y FCS (en la tesis, FSC) |
| `data/vialidades.json` | Red vial primaria y de acceso controlado |
| `data/fotocivicas-ubicacion-puntos/` | Ubicación de las 113 cámaras |
| `data/stcmetro_shp/` | Estaciones y líneas del Metro. Cada shapefile con sus archivos hermanos: sin el `.prj` se pierde el CRS |
| `data/afluencia-metro-diaria.parquet` | Afluencia diaria del Metro, generada desde el CSV crudo, que no está versionado |
| `data/volumen-total-mensual.parquet` | Volumen de las casetas de peaje. Solo describe la caída de la movilidad en la pandemia |
| `data/bootstrap-coeficientes.parquet` | Resultado del *bootstrap* |
| `data/localidadurbana/` | Contorno de la Ciudad de México, para los hexágonos del apéndice B |

**No versionado:** `data/raw/businesses-cdmx.json`, los conteos de Google Places del
apéndice B. Los términos de Google no permiten publicarlos y volver a consultarlos
hoy no reproduciría los conteos. Hay que respaldarlo aparte.

## Git

El remoto es `git@github-personal:MarianoAlcarazAguilar/causal-effects-speed-cameras.git`,
con la cuenta personal. El `.gitignore` es una lista de permitidos: un archivo
nuevo queda fuera hasta que se agrega explícitamente. Las imágenes de
`tesis/Imagenes/` no están versionadas; se regeneran con los scripts de
`scripts/figuras/`. La skill `figuras-tesis` sí está versionada (su `.md`, `.py`,
`.mplstyle`, fuentes y PNG de ejemplo), así que un clon puede regenerar las figuras.

Hasta el 16 de noviembre de 2026 la tesis vivía en `causal-effects-speed-cameras/`.
El visor busca ahí las versiones anteriores, así que sigue pudiendo comparar contra
cualquier commit.
