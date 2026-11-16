# Cambios a la tesis 16 noviembre 2026

*Nota que se le mandó a Alberto el 16 de noviembre de 2026 junto con la versión de
110 páginas, exportada de Google Docs («cambios tesis 16 nov 2026»). Las páginas que
cita son de esa versión. Lo que pidió está en [`revision-alberto.md`](revision-alberto.md).
Abajo de la nota está el correo con el que se mandó.*

Hice los puntos 1, 2, 3a y 4 que me sugirió. El 3b (Sant’Anna y Zhao) no lo hice. También agregué los resultados adicionales que me propuso, sin emparejamiento, con el recorte menos estricto y con dummies de tiempo.

El resultado principal no cambió, las cámaras siguen sin mostrar un efecto que se distinga de cero. Lo que sí cambió es cómo se lee. En la versión anterior interpretaba la caída generalizada de los incidentes (la variable de tiempo) como una posible señal de que el programa había cambiado la conducta en toda la ciudad; ahora esa caída la comparten tratadas y controles e incluye la pandemia, así que no se lo atribuyo al programa. También ahora digo qué magnitudes descarta el resultado, reducciones de más de 6% en el total de incidentes, cuando la literatura reporta entre 10% y 20%. Las conclusiones las reescribí completas con esta lectura.

Casi todos los cambios nacen del primer comentario. Tenía razón en que los resultados no eran comparables entre radios, porque, por construcción, cada radio era un análisis independiente de los demás (no me había dado cuenta que estaba haciéndolo así).

Para mantener la comparabilidad entre radios tuve que hacer varios cambios al diseño. Ahora desde el inicio construyo un solo set de unidades tratadas y uno de posibles controles, se quedan fijos para todos los radios, y de ahí se desprendió todo lo demás. Los radios también cambiaron, ahora son cinco, de 100 a 300 metros cada 50 metros.

Las 113 cámaras se agrupan en 99 unidades tratadas cuando sus círculos se traslapan en su mayor parte, y los incidentes que caen en áreas compartidas se reparten entre las unidades que las contienen para no contar de más (para calcular los errores estándar se clusteriza por “componente tratada”, que es básicamente unidades pegadas que comparten incidentes). Con esto ya no se clusteriza por área, sino por esa componente. Para los controles, que no se traslapan por construcción, es lo mismo que clusterizar por círculo.

Abajo le dejo la figura 3.1 de la tesis para que se vea mejor lo de las componentes. Son las mismas cinco unidades tratadas a 100, 200 y 300 metros. Conforme crece el radio los círculos se empiezan a traslapar, y las unidades que quedan conectadas (las líneas rojas) forman una sola componente, que es la que uso para clusterizar y para remuestrear en el bootstrap.

*[Aquí iba la figura 3.1 de la tesis, `tesis/Imagenes/componente-tratado-100-200-300.pdf`, que genera `scripts/figuras/capitulo3_figures.py`.]*

En la especificación principal de la tesis utilizo solo las unidades de tratamiento que sí encuentran un match en todos los radios, así siempre son las mismas 93 unidades que se comparan en todos los radios, al final igual hago énfasis en que solo se toman esas (las 6 que quedan fuera son las que no encontraron match y son las más peligrosas de toda la ciudad). También cambié las covariables del propensity score que pasaron de 18 a 12, porque había varias que realmente no terminaban de agregar tanto valor.

Reescribí las tablas como me lo pidió, con el número de observaciones, la R cuadrada, la media y la desviación estándar del grupo de control, la suma del tratamiento y la interacción, y ya hay notas que dejan entenderlas sin tener que ir a otro lugar como referencia. Por lo que comentaba de los errores estándar igual ahora discuto sobre todo la magnitud de los coeficientes y cuánto representan en porcentaje con respecto a las medias de los controles antes del tratamiento según sea el caso. En el cuadro 4.2 hago énfasis en que las estrellas se calculan con el error estándar agrupado, porque con el intervalo del bootstrap ningún efecto es significativo.

Las regresiones con tasas por cada 1,000 vehículos que tenía en la versión anterior las quité. La única serie de volumen vehicular que existe es la de las casetas de peaje, que es una sola para toda la ciudad y no distingue entre áreas, así que no decía nada sobre la exposición de cada unidad. Ahora todo está en número de incidentes. La pandemia ahora la reviso con los coeficientes posteriores del event study, y la serie de las casetas solo la uso para describir la caída de la movilidad (sección 4.4).

Respecto a las comparaciones adicionales que me sugirió agregar, ahora están descritas como una escalera de comparaciones que las va agregando una a una. En el análisis de sensibilidad de los resultados se incluyen las comparaciones adicionales que comentaba: sin emparejamiento, con el recorte menos estricto y con las covariables interactuadas con dummies de tiempo, y además una con un umbral distinto para agrupar las cámaras. Las dejé en el texto y no en un apéndice, porque me gustó que quedaran como parte de la línea que va llevando al lector, y además era más fácil irlas construyendo en el análisis mismo.

Como ya le adelantaba, agregué un event study para evaluar el supuesto de tendencias paralelas, incluí en el modelo de diferencias en diferencias las covariables del propensity score interactuadas con el periodo posterior (dejé fuera las de siniestralidad previa) y calculé los intervalos de confianza con un bootstrap de todo el proceso. De siniestralidad previa dejé fuera las cuatro covariables (nivel de incidentes, proporción con lesionados, tendencia y si hubo algún incidente fatal) y no solo la variable dependiente, para no asumir que eso afecta en cómo van a cambiar tras la implementación del programa. El event study reemplaza a las gráficas de tendencias paralelas y a las pruebas placebo que estaban en el apéndice.

No implementé el estimador doblemente robusto que me dejó de Sant’Anna y Zhao. Lo consideré, pero al final decidí mejor no incorporarlo porque me estaba tomando más tiempo del que había planeado.

Además de lo que me comentó, hice otros cambios. Reescribí la introducción para que dijera el diseño y los resultados con palabras y con menos cifras (especialmente al inicio había muchos números). También reescribí el resumen, para reflejar lo que ahora se hace.

Quité la explicación de la malla de cuadrículas, porque ya no queda nada de ese enfoque en la tesis y sentía que podía hacer que el lector esperara ver algo de ese análisis, y moví la evidencia de hexágonos y Google Places a un apéndice, porque solo sirve para justificar que los controles estén sobre vías primarias. Agregué en un apéndice el soporte común y el balance de los otros cuatro radios. También quité del capítulo 2 la revisión de ventanas temporales, que repetía la del capítulo 1.

Le dejo igual una lista con la referencia a dónde están los cambios que hice,

* Unidades tratadas fijas en los cinco radios y reparto de los incidentes compartidos: sección 3.2.1 (pp. 52-53).
* Radios de 100 a 300 metros: secciones 2.2.3 (p. 32) y 3.2 (p. 50).
* Recorte más estricto, con las 93 unidades comunes a los cinco radios, y lo que estima el efecto: secciones 2.3.1 (pp. 35-36), 3.2.3 (p. 55) y 3.3.5 (p. 59).
* Covariables del propensity score: sección 3.1 (p. 43) y cuadro 3.1 (p. 51).
* Emparejamiento y balance: sección 3.3 (p. 56), cuadro 3.2 (p. 60) y soporte común y balance de los demás radios en el apéndice A (pp. 84-88).
* Especificaciones, covariables interactuadas con el periodo posterior y por qué quedan fuera las de siniestralidad previa: sección 2.3.4 (pp. 39-40).
* Clusters por componente y bootstrap de todo el proceso: sección 2.3.5 (p. 41).
* Tablas con el formato que me pidió: cuadros 4.1 (p. 66), 4.2 (p. 74) y 4.3 (p. 78).
* Escalera de comparaciones: sección 4.1 y figura 4.1 (pp. 65-68).
* Event study: el diseño está en la sección 2.3.6 (p. 42) y resultados en la sección 4.2 y la figura 4.2 (pp. 69-70).
* Comparaciones adicionales (sin emparejamiento, recorte menos estricto, dummies de tiempo y umbral para agrupar cámaras): sección 4.5 y cuadro 4.3 (pp. 75-78).
* Magnitud de los efectos y medias del control antes y después del programa: sección 4.1 (pp. 65-67).
* Comparación con los estudios sobre la Ciudad de México: conclusiones (p. 80).
* Limitaciones del bootstrap: conclusiones (p. 82).
* Evidencia de hexágonos y Google Places: apéndice B (p. 89).

---

## El correo

*Enviado el 16 de noviembre de 2026 a la 1:36 p.m., en respuesta al hilo «Propuesta de
tesis basada en proyecto sobre cámaras de velocidad». Adjuntos: `cambios tesis 16 nov
2026.pdf` (esta nota) y `tesis version 16 nov 2026.pdf`. Esa versión de la tesis
es la del commit `30f0082`; los commits posteriores en `tesis/` solo movieron la
carpeta y partieron los apéndices en un archivo cada uno, sin cambiar el texto. Con el
visor (`python3 scripts/visor`) se puede compilar o comparar contra ese commit.*

Hola profesor,

Una disculpa por la tardanza, los cambios me tomaron más tiempo del que pensaba, pero ya quedaron listos. Le comparto la nueva versión a partir de sus comentarios. Hice los puntos 1,2, 3a y 4 que me sugirió y agregué los resultados adicionales que me propuso; el 3b no lo hice.

Como fueron bastantes cambios, le dejo también una nota con lo que cambió y por qué, así como en qué sección y página quedó cada cosa. El resultado principal se mantuvo, solo que cambian algunas interpretaciones. Igual eso viene en la nota más desarrollado.

Me encantaría saber qué le parece y si cree que ya está lista . Aún me queda pendiente la dedicatoria y los agradecimientos pero el resto ya está completo.

Muchas gracias por todos sus comentarios, me ayudaron mucho a mejorar la tesis.

Saludos,
Mariano
