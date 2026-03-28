# Contribuciones a la literatura
Respondamos a la pregunta: **¿qué hace mi análisis diferente al resto que justifica que exista?**

1. Definitivamente hago una muchísima mejor elección de grupo de control.
    - No tomo controles arbitrarios sin comparar de forma explícita ninguno de los atributos de estos (como lo hace madrigal, definitivamente hacen un trabajo muy pobre en su elección de controles)

2. Tomo una unidad de análisis acotada pero que permite realmente analizar el impacto
    - Mi unidad de análisis son áreas circulares alrededor de los radares de velocidad.
    - Hago esta elección porque sé que es robusto a cambios en distancia de análisis y asegura que la creación siempre tenga la cámara en el centro. Cuando hice el análisis con grids cuadriculares era poco robusto y mover ligeramente el grid hacía que los efectos cambiaran erráticamente.
    - Tomo una unidad que hace sentido con la literatura en cuanto al impacto de las cámaras se refiere, pues se ha mostrado que los efectos son locales y nunca generalizados, por lo que evaluar áreas geográficas grandes y no aleatorias resultaría en un análisis poco creíble (como lo hacen quintero al tomar municipios completos, que ahora que lo pienso, ni siquiera controlan por tamaño del área geográfica, solo por número de vehículos registrados, y además no queda claro si lo hacen por registros a nivel municipio o ciudad completa)
    - Además, reporto resultados de efectos causales para áreas de distintos tamaños, y no solo de una longitud determinada (como lo hace madrigal, que solo usan 300 metros en sus resultados estadísticos y se limitan a análisis descriptivos para bandas desde 100 hasta 500 metros antes y después de cada radar)

3. Mejor elección de variables de control
    - La SEMOVI misma identifica que hubo cambios en las conductas viales en la Ciudad durante la pandemia. No controlar por variables que permitan identificar al menos un proxy del flujo vehicular agregaría bias si no se controla.
    - Agrego variables que permiten entender la función de cada área, al incorporar controles por movilidad peatonal como lo son la afluencia en el metro.
    - Controlo por movilidad a nivel espacial y temporal: para la espacial, como no tengo datos de afluencia vehicular, utilizo datos de afluencia en las estaciones del metro, y lo incorporo al momento de hacer el PSM. Para la movilidad temporal, hago uso de los radares de conteo permantenes en la ciudad de méxico.
    - realmente soy el único estudio que se preocupa por la selección de variables de control, al incorporar todas las variables de estructura vial es lo que estoy haciendo. en el análisis a nivel municipio este tipo de cosas se obvian, y solo se controla por número de vehículos registrados y número de vehículos asegurados, mientras que madrigal de plano no controla por nada.

Lo que propone NotebookLM: 
- corrección del sesgo de selección mediante la definición de radios concéntricos granulares (desde 37.5m hasta 250m) combinada con Propensity Score Matching (PSM), superando las limitaciones espaciales (a nivel alcaldía) de estudios como Quintero et al.
- La innovación en el control de la exposición vehicular mediante el uso de datos de afluencia del Metro y radares de la SICT para aislar el choque exógeno de movilidad causado por el COVID-19, algo que la literatura previa sobre la CDMX ignoró

## Resumen de mis aportaciones
Me encanta la forma en cómo se plantea, al explicar que estoy mejorando tres de los problemas que dejaban los estudios anteriores en la CDMX: escala espacial, contrafactual y exposición, con tres decisiones: áreas cirulcares por radio, PSM y controles de movilidad. Además, eso permite reinterpretar la evidencia previa, distinguiendo entre efectos locales y agregados.

## Propuesta detallada para incorporar las contribuciones en la tesis

### 1. Diagnóstico general

Hoy las contribuciones de la tesis ya aparecen, pero de forma dispersa y a veces implícita:

- En la introducción ya se anticipan varias fortalezas del diseño: unidades circulares, matching y controles de movilidad.
- En estrategia empírica se justifica muy bien por qué descartas el grid y por qué eliges áreas circulares.
- En el capítulo de datos sí señalas explícitamente una contribución: el uso de datos de la SICT para controlar el choque de movilidad de la pandemia.
- En resultados comparas tus hallazgos con Madrigal y Quintero, pero más como contraste de resultados que como cierre de una contribución metodológica.

El problema no es que falten ideas, sino que todavía no están articuladas como una agenda clara de contribuciones. Conviene que el lector pueda responder desde la introducción, y luego al cerrar cada capítulo, tres preguntas muy concretas:

1. Qué limitación de la literatura previa corrige esta tesis.
2. Qué decisión metodológica o de datos tomas para corregirla.
3. Qué implicación tiene eso para interpretar tus resultados.

### 2. Cambio de tono recomendado

En el documento final conviene evitar una formulación demasiado confrontativa del tipo "definitivamente hago una muchísimo mejor elección" o "el trabajo previo es muy pobre". Esa intuición es correcta como nota de trabajo, pero en la tesis debe traducirse a un tono más académico:

- En vez de decir que estudios previos "eligen mal" sus controles, decir que "la comparabilidad entre unidades tratadas y de control queda menos justificada".
- En vez de decir que una unidad de análisis "no hace sentido", decir que "puede diluir efectos intrínsecamente locales".
- En vez de decir que otros trabajos "no controlan por pandemia", decir que "no incorporan controles explícitos para cambios exógenos en la exposición vehicular".

La tesis gana mucho si presentas tus contribuciones como una respuesta precisa a vacíos identificables en la literatura de CDMX.

### 3. Cómo conviene redefinir tus contribuciones

Te conviene agruparlas en cuatro contribuciones principales, no en una lista larga de decisiones técnicas.

#### Contribución 1: una evaluación verdaderamente local del efecto de los radares

La primera contribución no es solo usar círculos, sino reubicar la pregunta empírica en la escala espacial correcta. La idea central es:

> Esta tesis evalúa el efecto de las cámaras de velocidad en áreas centradas directamente en cada radar y a distintos radios de distancia, en lugar de utilizar unidades espaciales amplias o arbitrarias que pueden diluir un efecto que, según la literatura, es eminentemente local.

Esto te permite contrastarte con ambos antecedentes:

- frente a Quintero: porque ellos capturan un efecto agregado de política a nivel alcaldía;
- frente a Madrigal: porque tú no impones un solo tramo lineal de 300 metros como único espacio relevante, sino que pruebas sistemáticamente varios radios.

Lo valioso aquí no es solo la forma geométrica del área, sino que conviertes la distancia al radar en una dimensión del análisis.

#### Contribución 2: una mejor construcción del contrafactual

La segunda contribución debe formularse como una mejora de identificación causal:

> La tesis construye un grupo de comparación explícitamente comparable mediante Propensity Score Matching, usando siniestralidad previa, atributos físicos de la red vial y medidas de exposición, lo que fortalece la credibilidad del contrafactual frente a evaluaciones previas de la Ciudad de México.

Aquí la idea importante no es solo "uso PSM", sino por qué eso importa:

- las cámaras no se asignaron aleatoriamente;
- la autoridad las reubicó hacia zonas con mayor riesgo;
- por tanto, comparar tratadas contra cualquier zona sin cámara introduce sesgo de selección.

Esta es probablemente tu contribución metodológica más fuerte frente a Madrigal.

#### Contribución 3: control explícito de la exposición y del choque de movilidad por COVID-19

La tercera contribución es de datos y de medición:

> La tesis incorpora proxies de movilidad y exposición vehicular ausentes en la literatura previa para la CDMX, combinando afluencia del Metro y estaciones permanentes de conteo de la SICT, con el fin de separar el efecto de los radares de los cambios sistémicos de movilidad inducidos por la pandemia.

Esta contribución es especialmente importante porque fortalece tu argumento contra resultados previos estimados en años que incluyen COVID sin controlar de forma explícita ese choque.

#### Contribución 4: reinterpretación de la evidencia previa para la CDMX

La cuarta contribución no es solo metodológica, sino sustantiva:

> Al distinguir entre efectos localizados alrededor de las cámaras y reducciones agregadas en la siniestralidad de la ciudad, la tesis ofrece una reinterpretación de por qué estudios previos llegan a conclusiones distintas sobre las fotocívicas.

Esta contribución aparece ya en tus resultados y conclusiones, pero hoy no está anunciada desde el inicio. Vale la pena elevarla porque ayuda a responder la pregunta "para qué importa esta tesis si ya existen dos estudios previos".

### 4. Propuesta de redacción para la introducción

Lo más recomendable es agregar, al final de la introducción o justo después de presentar la estrategia empírica, un párrafo explícito de contribuciones. Idealmente debe aparecer después de la pregunta de investigación, la hipótesis y una breve descripción del método. No conviene esconderlo dentro de la descripción técnica.

#### Versión breve sugerida

> Esta tesis contribuye a la literatura sobre cámaras de velocidad en la Ciudad de México en cuatro dimensiones. Primero, evalúa el efecto de los radares en una escala espacial estrictamente local, mediante áreas circulares centradas en cada dispositivo y estimaciones para distintos radios, en lugar de unidades agregadas que pueden diluir su impacto. Segundo, fortalece la identificación causal mediante la construcción de un grupo de control emparejado con Propensity Score Matching a partir de siniestralidad previa, atributos de la infraestructura vial y características de exposición. Tercero, incorpora controles explícitos para los cambios en movilidad asociados a la pandemia de COVID-19 usando afluencia del Metro y estaciones permanentes de conteo vehicular de la SICT, un elemento ausente en la evidencia previa para la ciudad. Finalmente, al comparar efectos locales con cambios agregados en la siniestralidad, la tesis ofrece una reinterpretación de los resultados divergentes reportados por estudios anteriores sobre fotomultas y fotocívicas en la CDMX.

#### Versión un poco más ambiciosa

> Más allá de estimar si las fotocívicas redujeron los incidentes viales, esta tesis busca mejorar la forma en que ese efecto se identifica en la Ciudad de México. Su primera contribución consiste en estudiar el impacto de los radares en el entorno donde la literatura internacional espera encontrarlo: áreas locales centradas en cada cámara y observadas a distintos radios. La segunda es metodológica: dado que las cámaras fueron reubicadas hacia tramos con mayor riesgo, construyo el contrafactual mediante Propensity Score Matching para comparar las zonas tratadas con áreas observacionalmente similares. La tercera es de medición: incorporo proxies de movilidad y exposición vehicular para aislar el choque exógeno provocado por la pandemia, combinando información de afluencia del Metro y estaciones permanentes de conteo de la SICT. La cuarta es interpretativa: los resultados permiten distinguir entre reducciones agregadas en la siniestralidad de la ciudad y efectos causalmente atribuibles a la presencia local de las cámaras, lo que ayuda a reconciliar la evidencia previa para la CDMX.

### 5. Cómo distribuir las contribuciones durante el resto de la tesis

La mejor estrategia no es repetir la misma lista idéntica en todos lados, sino hacer que cada capítulo desarrolle una pieza de esa promesa inicial.

#### En revisión de literatura (`Chapters/1.Rev.tex`)

Al final de la sección sobre evidencia en CDMX conviene cerrar con un párrafo de "brecha". No basta con resumir Quintero y Madrigal; hace falta decir exactamente qué dejan abierto. Ese párrafo debería decir, en sustancia:

- que Quintero identifica efectos agregados de política, pero no efectos locales alrededor de cámaras específicas;
- que Madrigal busca efectos locales, pero con un contrafactual menos justificado y sin controles explícitos para cambios de movilidad por pandemia;
- que tu tesis entra justamente en esa intersección: efecto local + mejor contrafactual + control de exposición.

Fórmula útil:

> En conjunto, la evidencia para la CDMX deja abierta una pregunta central: si las fotocívicas generaron un efecto causal localizado en el entorno inmediato de los radares una vez que se corrige explícitamente el sesgo de selección en la ubicación de las cámaras y los cambios exógenos en la movilidad. Esta tesis aborda precisamente ese vacío.

#### En estrategia empírica (`Chapters/2.Emp.tex`)

Aquí no necesitas una subsección llamada "contribuciones", pero sí conviene insertar frases de cierre al final de las secciones clave.

- Después de explicar por qué descartas el grid: remarcar que la contribución no es solo técnica, sino de credibilidad empírica. La tesis no adopta un área arbitraria, sino una unidad consistente con el mecanismo local de la intervención.
- Después de presentar los radios circulares: enfatizar que esto permite evaluar la sensibilidad espacial del efecto, en vez de depender de un único umbral ad hoc.
- Después de explicar el PSM: señalar que el aporte central es convertir un problema evidente de selección en una comparación explícitamente defendible.

Lenguaje sugerido:

> Esta decisión metodológica constituye una contribución central del estudio, pues permite alinear la unidad espacial de análisis con el carácter local del tratamiento y evita que los resultados dependan de particiones espaciales arbitrarias.

Y más adelante:

> En este sentido, la combinación de emparejamiento y diferencias en diferencias no es solo una elección econométrica conveniente, sino el mecanismo mediante el cual esta tesis fortalece la credibilidad del contrafactual respecto de la evidencia previa para la Ciudad de México.

#### En datos (`Chapters/3.Data.tex`)

Aquí ya tienes un párrafo de contribución, pero conviene ampliarlo para que no parezca una nota aislada. Lo ideal es presentar las fuentes de datos como parte de una contribución más amplia de medición.

La idea sería conectar tres cosas:

- uso del C5 para captar severidades y una ventana temporal amplia;
- construcción propia de coordenadas de Metro y uso de afluencia como proxy espacial de movilidad;
- extracción y uso de datos SICT para control agregado de exposición vehicular durante COVID.

Es decir, el aporte de datos no es solo "uso SICT", sino la integración de varias fuentes para medir mejor riesgo y exposición.

Fórmula sugerida:

> En términos de datos, esta tesis contribuye a la evidencia sobre seguridad vial en la CDMX al integrar fuentes administrativas y geoespaciales que permiten medir con mayor precisión tanto la siniestralidad local como los cambios en exposición vehicular y movilidad. En particular, la combinación de registros del C5, afluencia del Metro y estaciones permanentes de conteo de la SICT hace posible distinguir mejor entre cambios atribuibles a la presencia de radares y cambios sistémicos asociados a la pandemia.

#### En resultados (`Chapters/4.Results.tex`)

Aquí conviene ordenar la discusión alrededor de la contribución interpretativa. Tus resultados no solo dicen "no encuentro efecto"; dicen algo más interesante:

- que sí hay caída general de la siniestralidad;
- que esa caída no parece localizarse alrededor de las cámaras cuando se compara con controles emparejados;
- que esta diferencia ayuda a explicar por qué estudios agregados y estudios locales pueden arrojar conclusiones distintas.

En otras palabras, el aporte de resultados es ayudar a separar "efecto del programa en la ciudad" de "efecto local de la cámara".

#### En conclusiones (`Chapters/5.Conc.tex`)

Aquí te conviene incluir un cierre explícito de contribuciones antes del párrafo de limitaciones o de agenda futura. Algo como:

> Más allá de sus hallazgos sustantivos, esta tesis deja tres aportes para la evaluación de políticas de control de velocidad en la Ciudad de México: una unidad espacial de análisis alineada con el carácter local del tratamiento, un contrafactual más creíble construido mediante emparejamiento y una estrategia de medición que incorpora cambios exógenos en movilidad y exposición durante la pandemia. En conjunto, estos elementos permiten reinterpretar la evidencia previa y distinguir con mayor claridad entre efectos agregados del programa y efectos localizados de los radares.

Si quieres conservar cuatro contribuciones, aquí también puede entrar la parte de reinterpretación de la literatura previa.

### 6. Una estructura narrativa que puede ayudarte

Una forma muy limpia de presentar todo es usar la misma lógica en toda la tesis:

- La literatura previa deja tres problemas: escala espacial, contrafactual y exposición.
- La tesis responde a esos tres problemas con tres decisiones: áreas circulares por radio, PSM y controles de movilidad.
- Los resultados permiten una cuarta contribución: reinterpretar la evidencia previa distinguiendo entre efectos locales y agregados.

Esa arquitectura hace que la tesis se lea como una respuesta coherente a vacíos específicos, no como una colección de decisiones metodológicas sueltas.

### 8. Qué evitar

- No presentar cada decisión técnica como si fuera una contribución independiente.
- No pelearte con Madrigal o Quintero; conviene mostrar sus límites con precisión, no con adjetivos.
- No dejar la contribución de reinterpretación solo en resultados; debe anunciarse desde la introducción.
- No reducir la contribución de datos únicamente a la SICT si en realidad tu aporte es la integración de varias fuentes.

### 9. Mi recomendación concreta

Si tuviera que escoger una sola manera de reorganizar tus contribuciones, sería esta:

1. Contribución espacial: evaluación local con radios alrededor de cada cámara.
2. Contribución de identificación: mejor contrafactual mediante PSM.
3. Contribución de medición: control explícito de movilidad y exposición durante COVID.
4. Contribución interpretativa: reconciliación de la evidencia previa distinguiendo efectos locales y agregados.

Esa es la versión más clara, más defendible y más fácil de insertar tanto en la introducción como a lo largo de toda la tesis.


