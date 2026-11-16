# Qué figura usar para qué

Cada fila es una figura que funcionó en la tesis. El ejemplo correspondiente en
`examples/` reproduce el patrón con datos sintéticos.

| Para mostrar | Figura | Ejemplo | En la tesis |
| --- | --- | --- | --- |
| Cómo cambia un efecto según la especificación o la comparación | Coeficientes en horizontal, un renglón por especificación, valor anotado; el intervalo que el texto discute, en el acento | `coeficientes.py` | Figura 4.1, la escalera |
| Tendencias previas y efecto por periodo | Event study: un panel por grupo, referencia hueca en cero, periodo posterior sombreado | `event_study.py` | Figura 4.2 |
| Efecto por grupo y tipo de resultado | Punto + intervalo por radio, una cuadrícula de paneles por tipo de incidente; eje compartido salvo el que tiene otra escala | (igual que `event_study.py`, con radios en x) | Figura 4.3 |
| Soporte común | Histogramas antes y después de emparejar, en log10; comparación rellena y principal en contorno | `distribuciones.py` | Figura 3.2 y figura A.1 (todos los radios) |
| Balance de covariables | Love plot: vacío antes, relleno después, umbrales de ±0.1 | `love_plot.py` | Figura 3.3 |
| Dos grupos con colas largas | Distribución acumulada | `distribuciones.py` | Figura B.2 |
| Una variable espacial con cola larga | Mapa con el 20% más alto en negro sobre gris, capa de contexto en `ACENTO_CLARO` | `mapa_resaltado.py` | Figura B.1 |
| Unidades excluidas frente a las analizadas | Puntos en escala log del múltiplo del promedio de referencia, una fila por variable | — | Figura 3.4 |
| Ejemplo de cómo se construyen las unidades | Mapa a escala real, mismo encuadre en todos los paneles, barra de escala, conexiones en el acento | — | Figura 3.1, componentes |
| Una serie en el tiempo con un choque | Serie mensual de los grupos, el inicio del programa marcado y el periodo del choque sombreado; un segundo panel con la serie de contexto | — | Figura 4.4, pandemia |

## Lo que se probó y no funcionó

- **Mapas con escala continua, raíz cuadrada o quintiles** sobre miles de hexágonos: a
  tamaño de página todo se veía gris. Funcionó resaltar el 20% más alto.
- **La red vial en rojo oscuro encima del mapa:** tapaba los hexágonos. Funcionó en rojo
  claro y delgada.
- **Apilar dos mapas para agrandarlos:** la altura de la página los dejó del mismo
  tamaño.
- **Histogramas con la cola recortada con `clip`:** dibujan un pico falso en el límite.
  Si hay que cortar, corta el eje y calcula la densidad con todos los datos.
- **Una figura por año además del event study:** repetía lo mismo. Si dos figuras dicen
  lo mismo, deja la que el texto usa.
