# Convenciones de las figuras

Cada regla salió de una corrección concreta en la tesis. El porqué importa más que la
regla: si un caso nuevo no encaja, decide con el porqué.

## La figura no se titula a sí misma

- **Sin título dentro de la figura.** El título va en el `\caption` de LaTeX, y lo que
  hace falta para leerla, en la nota debajo. Un título dentro duplica el caption y
  roba altura.
- **Paneles con letra y nombre corto, a la izquierda:** `(a) Incidentes`,
  `(b) 200 m, después`. El texto y la nota se refieren a "el panel (a)".
- **Etiquetas de eje que se entienden solas, con unidades:** "Efecto estimado, % del
  nivel previo de la comparación (IC 95%)", no "efecto".

## Tamaño

- **Ancho = ancho de texto del documento** (`ANCHO`, 12 cm en la tesis). La figura se
  inserta a `\linewidth` sin escalar, y así la letra mide en el PDF lo que mide en
  matplotlib (9 pt el cuerpo, 8 los ticks, 7–7.5 anotaciones).
- **Altura según lo que muestra**, no fija: 2.1–2.9 in para uno o dos paneles en
  renglón, 3.6–3.9 in para cuadrículas de 2×2 o 2×3.
- **Nunca más de ~5.7 in de alto si la figura lleva nota.** En la tesis, una de 8 in
  empujó el caption y la nota debajo del número de página.
- **Dos mapas lado a lado y no apilados:** con la altura de la página como límite,
  apilarlos no los agranda.

## Color

- **Escala de grises con un solo acento.** `OSCURO` (#333333) es el grupo principal o
  el estimado; `CLARO` (#A6A6A6) es la comparación o el fondo; `ACENTO` (#8C2D2D)
  solo para lo que el texto señala: el intervalo del bootstrap, una referencia, un
  grupo aparte. Si todo resalta, nada resalta.
- **Capas encima de datos en `ACENTO_CLARO`** (#D9A3A3), delgadas (0.15–0.6 pt). La
  red vial en rojo oscuro sobre un mapa lo saturaba hasta no verse nada.
- **Grupo de comparación relleno, grupo principal en contorno** cuando se enciman
  (histogramas): así se ve el traslape.
- **Fondo de mapas y categoría "resto" en `FONDO`** (#E3E3E3).

## Escalas

- **Colas largas: no uses una escala continua lineal.** Unos cuantos valores extremos
  se llevan el rango y el resto queda del mismo tono. La raíz cuadrada y los quintiles
  tampoco bastaron en mapas con miles de polígonos; lo que funcionó fue resaltar el 20%
  más alto en negro sobre gris.
- **Valores amontonados cerca de cero: eje en log10**, y el eje lo dice
  (`$\log_{10}$ del propensity score`).
- **Comparar dos distribuciones con colas: distribución acumulada** antes que
  histograma. Si se corta el eje para ver la forma, la proporción se calcula con todos
  los datos y la nota lo dice.
- **Ejes compartidos cuando la escala es comparable** (`sharey` entre radios,
  `sharex="row"` entre antes y después). La excepción va explícita: los incidentes
  fatales, con intervalos diez veces más anchos, en su propia escala.

## Referencias y marcas

- **Cero punteado, delgado y debajo de los datos** (`cero(ax)`).
- **Punto + intervalo como línea** para coeficientes: punto de 4 de tamaño, intervalo de
  1.2 pt. El valor anotado a la derecha, con signo y fondo blanco (`pct(v)`).
- **La referencia del event study como punto hueco fijo en cero**, y la nota lo dice.
- **Periodos sombreados en gris claro** (`axvspan`, alpha .25) en vez de una línea
  vertical; "antes" y "después" escritos arriba.
- **Signo menos tipográfico (−)**, no guion, en etiquetas y anotaciones (`menos()`).
- **Eje y de categorías sin línea ni ticks** (`spines["left"]` fuera,
  `tick_params(length=0)`).

## Leyenda

- **Sin marco.** Dentro del eje si cabe en una esquina vacía; si tapa datos, afuera:
  `fig.legend(..., loc="outside upper center", ncol=2)` con `layout="constrained"`.
  Una sola leyenda para todos los paneles.

## Consistencia

- **Figuras paralelas, mismo formato.** El soporte común de los otros radios se hizo con
  la misma función que el de 300 m; el love plot sigue el orden del cuadro de balance.
- **Los números de la figura coinciden con los del texto y los cuadros.** Antes de dar
  una figura por buena, verifica uno contra el texto.
- **Variables con su nombre de código en monoespaciada** cuando el cuadro de al lado las
  nombra así.

## Código

- **Un script por capítulo** (`intro_figures.py`, `capitulo3_figures.py`…). Cada figura
  es una función que devuelve una `Figure`; el `__main__` arma un diccionario
  `nombre → figura` y llama a `guardar()`.
- **PDF vectorial al directorio de imágenes del documento** (`pdf.fonttype 42`, fuentes
  incrustadas), nombres en kebab-case. Con `--png`, una vista previa para revisarla sin
  compilar.
- **No recalcular lo caro.** El bootstrap se lee de su archivo guardado.
- **Si dejas de usar una figura, quita su función.** Si no, se sigue generando y se
  acumulan archivos que nadie usa.

## Revisión antes de darla por buena

1. Ver el PNG.
2. Compilar el documento y ver la página: que el caption y la nota quepan, y que la
   figura no empuje el texto a otra página (una figura más alta puede mover todo lo
   que sigue).
3. Comparar un número de la figura con el texto.
