# Tendencias paralelas

En esta nota no voy a redactar todavía la versión final de la tesis, sino dejar un plan claro para incorporar el supuesto de tendencias paralelas dentro de la sección `Identificación de supuestos y selección de la muestra`. La idea es que el argumento quede ordenado y que, además, sea consistente con la justificación del `propensity score matching` como mecanismo para construir un grupo de control más comparable.

## Objetivo del cambio

Debo agregar explícitamente el supuesto de tendencias paralelas dentro de la discusión de identificación. Ahí necesito explicar que, en ausencia del tratamiento, la diferencia en los resultados entre el grupo tratado y el grupo de control se habría mantenido constante a lo largo del tiempo. En otras palabras, aunque ambos grupos puedan comenzar en niveles distintos, su trayectoria esperada sin intervención debería evolucionar en paralelo.

También debo dejar claro por qué este supuesto no puede observarse de manera directa: no es posible ver qué le habría ocurrido al grupo tratado si no hubiera recibido el tratamiento. Por eso, la estrategia de diferencia en diferencias usa la evolución del grupo de control como contrafactual para aproximar la trayectoria no observada del grupo tratado. Toda la evidencia que presente en esta sección debe orientarse a defender que esa aproximación es plausible, no a afirmar que el supuesto puede probarse de forma definitiva.

## Propuesta de reordenamiento de la sección

El orden de exposición debe hacer sentido con el uso de `propensity score matching`. La secuencia sugerida es la siguiente:

1. Describir la selección de la muestra y la definición de unidades tratadas y de control.
2. Explicar por qué el `propensity score matching` ayuda a construir un grupo de control más comparable en covariables observables.
3. Aclarar que el matching no sustituye el supuesto de tendencias paralelas, pero sí puede volverlo más plausible al mejorar la similitud entre tratados y controles antes de la intervención.
4. Introducir formalmente el supuesto de tendencias paralelas como condición clave para interpretar causalmente el estimador de diferencia en diferencias.
5. Presentar la evidencia empírica que usaré para respaldar su plausibilidad: inspección visual y prueba placebo.

Con este orden, el argumento queda así: primero justifico cómo selecciono el grupo de comparación; después explico cuál es el supuesto temporal que todavía necesito para que ese grupo funcione como contrafactual.

## Contenido que debo agregar en `Identificación de supuestos y selección de la muestra`

### 1. Definición conceptual del supuesto

Aquí debo incorporar un párrafo que diga, en sustancia, lo siguiente:

- En ausencia del tratamiento, la brecha entre el grupo tratado y el grupo de control habría permanecido estable en el tiempo.
- El problema fundamental es que no puedo observar el contrafactual del grupo tratado, porque esas unidades sí fueron intervenidas.
- La solución empírica consiste en usar la tendencia del grupo de control como aproximación de ese contrafactual.
- La validez del diseño depende de que esa trayectoria de control represente razonablemente lo que le habría pasado al grupo tratado sin cámaras.

Aquí también conviene anticipar una advertencia metodológica: el supuesto no se demuestra, sino que se vuelve más o menos creíble con evidencia previa al tratamiento y con la solidez de la estrategia de construcción del grupo de control.

### 2. Puente explícito con `propensity score matching`

En esta subsección debo justificar que el matching forma parte de la estrategia para reforzar la comparabilidad inicial entre grupos. El punto importante es no sobrerreclamar. El texto debería dejar claro que:

- El `propensity score matching` equilibra características observables relevantes entre unidades tratadas y de control.
- Ese equilibrio no garantiza por sí mismo tendencias paralelas.
- Sin embargo, al seleccionar controles más parecidos a los tratados, el matching puede hacer más plausible que ambos grupos hubieran seguido trayectorias similares sin tratamiento.
- Por eso tiene sentido presentar la evidencia de tendencias paralelas después de haber explicado cómo construyo el grupo de control emparejado.

## Evidencia que debo reportar

### 1. Inspección visual de tendencias pretratamiento

Aquí debo explicar que una forma estándar de evaluar la plausibilidad del supuesto es graficar varios periodos previos a la intervención y comparar la evolución de tratados y controles. El objetivo no es mostrar niveles idénticos, sino trayectorias similares antes del tratamiento.

La lógica de esta parte debe quedar planteada así:

- Gráfica 1: unidades tratadas vs. unidades no tratadas, sin matching.
- Gráfica 2: unidades tratadas vs. unidades no tratadas emparejadas mediante `propensity score matching`.
- La comparación central no cambia a las unidades tratadas; cambia la forma de construir el grupo de control.
- Si las tendencias previas lucen más parecidas en la muestra emparejada, eso fortalece la justificación del matching dentro del diseño empírico.

#### Información pendiente para completar esta parte

- Descripción sustantiva de cada gráfica: qué se observa visualmente en la pendiente, en la separación entre grupos y en la estabilidad pretratamiento.
- Variable graficada, nivel de agregación temporal y número de periodos previos incluidos.
- Ubicación exacta de los archivos de las gráficas para poder citarlas o integrarlas en la tesis.
- Decisión sobre si ambas gráficas irán en el cuerpo principal o si una de ellas se moverá al apéndice.
- Texto breve sobre limitaciones de la inspección visual: sirve como evidencia descriptiva, no como prueba definitiva.

### 2. Prueba placebo con fecha ficticia de tratamiento

Aquí debo explicar que la segunda verificación consiste en tomar solo datos previos a la implementación real, imponer una fecha arbitraria de tratamiento y volver a estimar el modelo como si la intervención hubiera ocurrido antes. La expectativa es que los coeficientes de interacción no sean estadísticamente significativos. Si aparecieran efectos placebo antes del tratamiento real, la credibilidad del supuesto de tendencias paralelas se debilitaría.

#### Información pendiente para completar esta parte

- Ventana exacta de datos pretratamiento que usaré en la prueba.
- Fecha ficticia elegida y justificación de por qué esa fecha es razonable.
- Especificación exacta del modelo placebo y si replica la muestra con matching o la muestra base, o ambas.
- Resultado principal que debo reportar: signo, magnitud y significancia de los coeficientes placebo.
- Comentario interpretativo: si los coeficientes son no significativos, eso respalda la ausencia de diferencias espurias previas; si sí lo son, debo discutir qué implicación tiene para la estrategia empírica.

## Redacción sugerida para cerrar la discusión

Después de presentar la evidencia visual y el placebo, necesito cerrar con una conclusión prudente. La idea no es afirmar que el supuesto queda probado, sino sostener que la evidencia previa al tratamiento es consistente con su validez y que el uso de `propensity score matching` contribuye a construir un contrafactual más creíble en términos observables.

## Lo que ya está cubierto en la tesis

Después de revisar `Chapters/2.Emp.tex`, `Chapters/3.Data.tex`, `Chapters/4.Results.tex` y `Chapters/0.Intro.tex`, queda claro que la tesis ya contiene los elementos centrales de la estrategia empírica. En particular, ya están explicados:

- la motivación para combinar `propensity score matching` con diferencia en diferencias;
- la definición de unidades tratadas y controles elegibles;
- la restricción de la muestra a áreas con traslape con vías primarias;
- el esquema de `nearest neighbor matching` 1:1 sin reemplazo;
- el soporte común y las pruebas de balance mediante SMD;
- la ventana temporal principal de tres años antes y tres años después.

Por lo tanto, en la nueva redacción no conviene repetir cómo se construye el matching ni volver a enumerar las covariables. Eso ya está suficientemente desarrollado. Lo que falta es conectar esa construcción del contrafactual con el supuesto de tendencias paralelas y con la evidencia que respalda su plausibilidad.

## Lo que falta agregar realmente

La revisión muestra que el supuesto de tendencias paralelas ya aparece mencionado en `Chapters/2.Emp.tex:120`, pero solo como una condición enunciada. Todavía no está desarrollado qué significa en este contexto, por qué no puede observarse directamente y qué evidencia concreta se presenta para defenderlo. Ese es el hueco principal que debo llenar.

## Lugar exacto donde conviene hacer el cambio

El mejor lugar para introducir esta discusión es `Chapters/2.Emp.tex`, dentro de la sección `Estrategia de identificación`, inmediatamente después del párrafo en el que explico que el `matching` mejora la comparabilidad entre áreas tratadas y de control, y antes del cierre sobre interpretabilidad y replicación.

La secuencia ideal queda así:

1. Mantener la explicación actual de por qué uso `propensity score matching` + DID.
2. Mantener la discusión actual de soporte común y balance.
3. Insertar un bloque nuevo sobre tendencias paralelas.
4. Cerrar con una conclusión prudente sobre por qué la estrategia de identificación resulta más creíble.

## Ajuste fino del argumento sobre `propensity score matching`

Dado lo que ya está escrito en la tesis, el argumento debe quedar formulado de la siguiente manera:

- el `matching` mejora la comparabilidad en covariables observables y ayuda a construir un grupo de control más defendible;
- esa mejora hace más plausible que la evolución del grupo de control pueda aproximar el contrafactual del grupo tratado;
- sin embargo, el `matching` no sustituye el supuesto de tendencias paralelas;
- por eso la explicación del supuesto debe aparecer después del matching y no antes.

## Evidencia empírica que ya puedo integrar

### 1. Inspección visual

La evidencia visual ya tiene insumos suficientes para ser incorporada al cuerpo principal:

- Ruta de las figuras: `Imagenes/mean_accidents_trends`.
- Archivos disponibles: `trend_mean_accidents_37.png`, `trend_mean_accidents_50.png`, `trend_mean_accidents_100.png`, `trend_mean_accidents_150.png`, `trend_mean_accidents_200.png` y `trend_mean_accidents_250.png`.
- Las gráficas están agregadas por mes.
- Cubren tres años antes y tres años después de la implementación.
- Reportan promedios de accidentes para total, `MIN`, `PIC` y `FCS`.
- Comparan, en dos columnas, la muestra sin matching y la muestra emparejada.

La lectura sustantiva que debo integrar es la siguiente: antes del matching, las áreas tratadas muestran niveles promedio de accidentes más altos que las de control, aunque en general las trayectorias pretratamiento son similares. Después del matching, el traslape entre curvas aumenta de manera importante y la similitud mejora tanto en niveles como en tendencias. La excepción visual más clara aparece en accidentes `MIN` para el radio de 50 metros, donde persiste una ligera discrepancia alrededor de año y medio antes del tratamiento, aunque menor que en la muestra sin emparejar. Las gráficas deben quedarse en el cuerpo principal.

### 2. Prueba placebo

La evidencia placebo también ya está suficientemente definida para el plan:

- La muestra usa exclusivamente los tres años previos a la implementación real.
- Se utilizan tres fechas ficticias de tratamiento: un año y medio, un año, y medio año antes de la implementación real.
- La especificación replica el modelo principal.
- Se utilizan los mismos `matches` que en la estimación final.
- Se reportan 144 coeficientes placebo en total.
- 143 de 144 no son estadísticamente significativos.
- La única excepción corresponde al placebo de un año y medio previo para la tasa de accidentes `MIN` en el radio de 50 metros, con significancia al 95%.

La forma correcta de presentar este resultado es decir que la evidencia es ampliamente consistente con el supuesto de tendencias paralelas, aunque existe una excepción puntual que obliga a interpretar con cautela esa especificación específica. No conviene enmarcarlo como un fracaso del diseño, sino como una limitación acotada que se reconoce explícitamente.

## Checklist para convertir este plan en texto final

1. Insertar en `Chapters/2.Emp.tex` un bloque específico que desarrolle el supuesto de tendencias paralelas.
2. Hacer explícito que el `matching` mejora la comparabilidad observable, pero no reemplaza el supuesto temporal de DID.
3. Explicar por qué el contrafactual del grupo tratado no es observable y por qué se usa la trayectoria del control emparejado como aproximación.
4. Integrar una discusión breve de la inspección visual usando las figuras de `Imagenes/mean_accidents_trends`.
5. Incorporar un párrafo sobre las pruebas placebo resaltando que 143 de 144 coeficientes no son significativos y comentando con cautela la única excepción.
6. Cerrar la sección dejando claro que estas verificaciones refuerzan la plausibilidad del supuesto, pero no lo prueban de manera definitiva.

## Inputs que ya me compartiste

Los comentarios añadidos al final de este archivo ya resolvieron casi todos los insumos necesarios para redactar la versión del cuerpo principal.

### Inspección visual

- La ruta exacta de las gráficas que quieres usar
    '/Users/mariano/Documents/itam/tesis/speed-cameras/causal-effects-speed-cameras/Imagenes/mean_accidents_trends'
    Aquí encontrarás las gráficas correspondientes que hice de las tendencias del promedio de accidentes para cada uno de los radios evaluados en la tesis. Desde 37.5 metros hasta los 250 metros de radio (500 metros de diámetro)
- Una breve descripción de cada gráfica: qué variable muestra, cuál es la unidad temporal y cuántos periodos pretratamiento incluye.
    Para las gráficas agrupo por mes, considerando 3 años antes y 3 años después de la implementación de las cámaras de velocidad. Calculo el promedio de accidentes para cada tipo, es decir, agrupo por total de accidentes, para min, pic y fcs. Las gráficas están hechas en dos columnas, en la primera columna se encuentran los plots para accidentes en los que no incorporo el propensity score matching, es decir, tomo todos los posibles controles y los comparo con todas las unidades tratadas.
- Qué observas en cada una: si las pendientes son similares, si hay separación constante entre grupos o si hay divergencias visibles.
    Antes de hacer propensity score matching: claramente las unidades tratadas tienen en promedio más accidentes mensuales. El promedio de todos los accidentes siempre es más alto en las unidades tratadas, independientemente del tamaño del área estudidada. Algo que vale la pena resaltar es que los datos de accidentes fatales parecen ser muy ruidosos, quizá esto sea porque hay menos observaciones para poder ver tendencias claras. En cuanto a tendencas se refiere, en general se ven tendencias similares.
    Después del propensity score matching: como ya adelantaba, si bien las tendencias eran similares, tras hacer el matching, hay un overlap casi total de las curvas, además, ya no son solo similares en tendencias sino también en niveles (algo que era de esperarse al usar el método de propensity score matching) Defintivamente el match ayudó a elegir un grupo de control que se comporta muy similar al de tratamiento. Visualemnte, donde identifico mayor diferencia en tendencias tras hacer el matching es para accidentes min en radios de 50 metros, donde parece ser que año y medio antes de la implementación parece haber una ligera diferencia de niveles. Si se observa la gráfica sin propensity score matching, se puede ver que la tendencia de accidentes menores en radios de 50 metros tenía una ligera tendencia a la baja, mientras que para los controles se mantenía constante. Tras hacer el matching esa diferencia de tendencias se ve reducida.
- Si quieres que ambas gráficas queden en el cuerpo principal o si alguna debe ir al apéndice.
    Me gustaría que las gráficas estuvieran en el cuerpo principal de la tesis.

### `Propensity score matching`

- Una descripción breve de cómo construiste el grupo de control emparejado.
    esto no es necesario explicarlo, ya se hace en capítulos de la tesis
- Las covariables que usaste para el matching.
    tampoco es necesario explicarlo, ya se hace en la tesis
- Si quieres que lo presente como parte central de la estrategia empírica o como un refinamiento adicional de comparabilidad.
    El propoensity score matching es fundamental en la creación de un grupo de control creíble, pero esto ya está detallado en otras partes de la tesis

### Prueba placebo

- La ventana exacta de datos pretratamiento que utilizaste.
    tomo 3 años antes de la implementación del programa de fotocívicas.
    no le doy datos posteriores a la implementación
- La fecha ficticia de tratamiento que escogiste.
    se usan 3 ventanas de tiempo distintas: año y medio, un año, y medio año antes de la implementación del programa como pruebas placebo.
- La especificación del modelo placebo: si replica exactamente el modelo principal y si corre sobre la muestra sin matching, con matching o ambas.
    Se utiliza la misma especificación que uso para el modelo final. utilizo los mismos matches que para el modelo final.
- El resultado principal: signo, magnitud aproximada y significancia estadística del coeficiente placebo.
    tengo que correr muchísimos modelos porque son un montón de radios y porque son para 4 outcomes distintos, no vale la pena reportar cada uno de ellos (al menos en el cuerpo de la tesis, en los apéndices voy a agregar una tabla con los coeficientes reportados de cada una de las evaluaciones, así como su significancia estadística), en total estoy reportando 144 coeficientes y sus respectivos valores-p. De esos 144 coeficientes, todos, excepto 1, carecen de signicancia estadística en las 3 pruebas que hago. Ese coeficiente que presenta significancia estadística corresponde al modelo que evalúa como prueba placebo un año y medio el impacto sobre tasas de accidentes min en radios de 50 metros, con significancia estadística del 95%. Fuera de eso, el resto sí cumple con el supesto. aquí creo que hay que encontrar la forma de framear esto para que no parezca que se pierde poder de inferencia.
- Tu lectura sustantiva del resultado: qué crees que demuestra o qué limitación quieres reconocer.
    - Creo que en cuanto a tendencias se refiere, no se gana tanto como me encantaría, creo que se cumple el supuesto de tendencias paralelas, con esa ligera excepción, y creo que la implementación del psm nos permite tener un grupo de control mucho mejor comparable con tendnecias muy similares, capaz de captar efectos que sean efectivametne atribuibles a las cámaras de velocidad.

### Tono e integración en la tesis

- El fragmento o archivo donde está la sección `Identificación de supuestos y selección de la muestra`, para que la redacción quede bien integrada con el resto del capítulo.
    '/Users/mariano/Documents/itam/tesis/speed-cameras/causal-effects-speed-cameras/Chapters/2.Emp.tex' ahí es donde está la estrategia empírica. necestio que leas la tesis.
- Si quieres un tono más técnico-formal o más explicativo.
    necesito que mantengas el mismo tono que tengo en la tesis, recuerda que soy un egresado de la licenciatura, así que el tono y tipo de palabras deben de reflejar eso
- Si prefieres que deje una versión breve para el cuerpo principal y una versión más extensa para notas o apéndice.
    Necesito que trabajes exclusivamente en la versión para el cuerpo principal.

## Estado actual del plan

Con la información ya añadida en este archivo y con la revisión de los capítulos relevantes de la tesis, el plan quedó suficientemente aterrizado para pasar después a la redacción del cuerpo principal.
