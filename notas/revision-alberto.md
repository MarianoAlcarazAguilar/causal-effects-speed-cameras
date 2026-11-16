# Revisión de Alberto (asesor de tesis)

*Correo recibido sobre la versión completa de la tesis. Transcrito literal, para
tenerlo presente mientras se rehace la estimación. Los capítulos 1, 2 y la mayor
parte del 3 los da por listos; lo que falta es estimación y discusión de
resultados.*

---

Hola Mariano,

Gracias por el recordatorio. Ya leí esta versión y está mucho mejor. Me parece que los capítulos 1 y 2, y la mayoría del 3, ya están listos. La parte de estimación y la discusión de resultados se quedan un poco cortas aún. Te comparto algunas sugerencias. No sé qué tanto tiempo tengas disponible para dedicarle, así que separo las que me parecen muy importantes de las que me parece que fortalecerían tu tesis pero no veo igualmente cruciales.

## 1. Trimming y lo que el análisis estima

El trimming me parece correcto y útil en todo sentido. Solamente hay que transparentar el hecho de que lo que estás estimando cambia, ya que es un ATT sobre la muestra después del trimming. Esto hace que no sean directamente comparables tus resultados para diferentes distancias, ya que haces diferente trimming.

Yo sugiero que para hacer comparables tus resultados a diferentes distancias, uses el trimming más estricto y luego corras todo a diferentes distancias.

Esto no excluye que, si quieres, luego uses el trimming menos estricto (el que ya usas actualmente) por separado para ver si los resultados son robustos, por ejemplo.

## 2. Tablas

Los cuadros 4.1-4.3 no están aún suficientemente claros. Por favor indica en cada análisis el número de observaciones y la R^2. Ordena tu variable de tratamiento primero y luego la interacción, y hasta el final las variables de efectos fijos. Y reporta la suma de la variable tratamiento más la interacción tratamiento * tiempo con su desviación estándar y sus estrellitas en cada lugar en que sea relevante. También indica el "control mean" en cada columna: la cantidad o tasa de accidentes en el grupo de control, con su desviación estándar. Esto facilita la interpretación de los resultados.

Para las regresiones con tasas, sugiero que transformes la escala de la variable para que los coeficientes sean expresables sin notación científica.

La nota debe explicar qué modelo corres en cada caso y en qué muestra. Debe explicar además las unidades de tal modo que uno pueda interpretar los coeficientes de inmediato, sin tener que regresar al texto. Usa puntos decimales en lugar de comas, es el estándar en México.

Al interpretar los resultados, es necesario hablar en el texto de la magnitud de los coeficientes incluso cuando no son significativos, porque la significancia estadística depende de muchos factores. Esto lo trato en el siguiente punto.

## 3. Errores estándar estimados

En general, los errores estándar del diff in diff después de haber hecho matching no son correctos. Esto puede afectar la significancia estadística de tus resultados en diferentes direcciones, por lo que se vuelve necesario ponerle atención a la magnitud de los coeficientes en primera instancia.

Para mitigar este problema, hay varias vías. La primera es hacer algunos ajustes a tu análisis. La segunda es usar un nuevo método, recomendado en un paper reciente de Sant'Anna y Zhao, para el cual ya hay un algoritmo implementado en R y en STATA.

**a)** PSM + diff in diff. Es correcto hacer clustering por unidad (es decir, por círculo) y que el matching sea sin reemplazo. Eso ya lo haces. Se recomienda también agregar todas las variables que usaste en la estimación del propensity score como controles en el diff in diff, interactuados con un indicador del período pos-tratamiento (o con los efectos fijos de tiempo). Esto es fácil de hacer. También se recomienda usar bootstrap para todo el proceso (es decir, empezando con el cálculo del propensity score), lo cual me suena muy laborioso, por lo que me parece bien si agregas a tu análisis lo que describe el siguiente inciso:

**b)** Sant'Anna y Zhao 2020 (https://arxiv.org/pdf/1812.01723) habla sobre diff in diff condicionando en covariantes pre-tratamiento, y propone un estimador que tiene propiedades estadísticas más deseables que la combinación de PSM + diff in diff. Ya viene implementado en R y en STATA en el paquete "did" (https://bcallaway11.github.io/did/), por lo que no debe ser difícil de que lo corras en tus datos.

## 4. Event study

Posiblemente el event study sería informativo visualmente, y agregaría un mayor nivel de detalle a tus resultados. (Por ejemplo mira la sección 9.7 de este texto: https://mixtape.scunning.com/08a-difference_in_differences). Esto es independiente del método de estimación que uses, ya sea el 3a o el 3b.

---

En resumen, sugiero que hagas 1, 2 y 3a. Tú decide si quieres hacer 3b y/o 4.

Decidas lo que decidas, yo mostraría una variedad mayor de resultados además de los que consideres los principales. Por ejemplo:

- Diff in diff sin matching (en un apéndice)
- Tu análisis principal con el trimming más estricto, para que las distancias sean comparables
- Análisis con el trimming menos estricto por distancia (en un apéndice)
- El análisis principal controlando por las variables que usaste para calcular el propensity score interactuadas con time dummies (menos la variable dependiente pre-tratamiento, esa no la puedes meter como control en el diff in diff)

También ampliaría un poco más la discusión de los resultados. ¿Cuál es el tamaño de los coeficientes? ¿En qué unidades están, y cómo se comparan con los valores pre-cámaras o pos-cámaras en el grupo de control? ¿Hay manera de comparar la magnitud de tus coeficientes con los de los otros análisis de México que citas?

Saludos,
Alberto
