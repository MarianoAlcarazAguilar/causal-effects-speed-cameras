# Insertar la figura en LaTeX

## El bloque

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=\linewidth]{Imagenes/nombre-de-la-figura.pdf}
    \caption{Efecto estimado a 300 metros según el grupo de comparación}
    \label{fig:escalera}
    \begin{minipage}{0.95\linewidth}\linespread{1}\selectfont
        \footnotesize \textit{Nota:} Cada punto es ... ; las líneas son el intervalo de
        confianza al 95\% ... En rojo, el intervalo del \emph{bootstrap} ...
    \end{minipage}
\end{figure}
```

- **`[htbp]`** y nada más restrictivo.
- **`width=\linewidth`**: la figura se hizo al ancho de texto, así que no se escala y la
  letra conserva su tamaño.
- **El caption debajo de la figura** y la nota debajo del caption. El caption es un
  nombre corto ("Efecto por tipo de incidente y por radio"), no una explicación.
- **La nota a renglón sencillo** (`\linespread{1}\selectfont`). Con el interlineado del
  texto (1.25 en la tesis) se ve suelta y empuja la página. En la tesis lo mismo se
  aplicó a los pies de página, en la definición de `\footnote` en `main.tex`.
- **`\label` después del `\caption`.** Se cita con `figura~\ref{fig:...}`, en minúscula
  dentro de la oración.

## Qué va en la nota

La nota permite leer la figura sin volver al texto:

1. Qué es cada marca: "Cada punto es…", "las líneas son el intervalo…", "en rojo…".
2. Qué muestra cada panel, si hay varios.
3. La muestra y las unidades.
4. Lo que no es obvio: un eje cortado, una escala logarítmica, la referencia fija en
   cero, una categoría resaltada.
5. La fuente, si los datos no son propios.

## Cuadros

Las mismas reglas valen para las notas de los cuadros: `\scriptsize` o `\footnotesize`
según el tamaño del cuadro, a renglón sencillo y autocontenidas. Para los cuadros de
regresión: observaciones, R², media y desviación estándar del grupo de control, la suma
tratamiento + interacción donde aplique, qué modelo, qué muestra y qué unidades, y
punto decimal (con babel en español: `\usepackage[spanish,es-nodecimaldot]{babel}`).

## Que no mueva páginas

Una figura más alta, o una línea más en su nota, puede recorrer todo lo que sigue una
página. Después de agregar o agrandar una figura, compila y revisa que el índice no se
haya movido de más y que no haya quedado una página casi vacía.
