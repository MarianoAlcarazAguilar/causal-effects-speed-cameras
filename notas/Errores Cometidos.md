# Recap de los errores y las decisiones que se tomaron

Transcripción de las 17 páginas manuscritas en `notas/fotos/Errores Cometidos-1.jpg` a `Errores Cometidos-17.jpg`. Se conserva la voz y la secuencia de los apuntes. Las correcciones posteriores en azul se incorporan donde sustituyen texto tachado. Las figuras y tablas se enlazan a su foto original; sus números y rótulos principales también se transcriben.

También voy a dejar los gaps teóricos que tengo que volver a revisar detenidamente.

## Página 1 — Trimming y lo que el análisis estima

[Ver foto 1](<fotos/Errores Cometidos-1.jpg>)

ATT ≠ ATE ⇒ Transparentarlo. No estaba comparando lo mismo entre todas las distancias y por lo tanto, los resultados no son comparables entre sí.

Aquí hubo un cambio metodológico importante:

**Antes.** Para cada radio inicializaba un círculo con centro en cada radar, si había overlap con otra cámara, entonces se movía el centro del área entre ambas y se revisaba que no hubiera más overlap, y así se iteraba hasta tener unidades sin overlap. El problema con esto es que para cada radio este proceso iterativo hacía que termináramos con diferentes ubicaciones de los centros, lo que hacía imposible una comparación consistente entre radios.

**Ahora.** Se hace una definición única de la ubicación de los centros de las unidades tratadas siguiendo una lógica similar a la anterior.

Se empieza con el radio más grande (300 m) y se dibuja un área alrededor de cada una de las 113 cámaras. De ahí se verifica no solo si existe overlap con otra área, sino que se calcula el % de área con overlap. Aquí nace la primera decisión que se toma: ¿a partir de qué % de overlap juntamos dos áreas para que se vuelvan una sola?

Para tomar esa decisión tenemos que recordar que los centros de las unidades serán fijos durante el resto del análisis y tienen que funcionar para todos los radios, incluyendo el más chico (100 m). Con eso en mente, si nos ponemos a fusionar con el más mínimo overlap terminan ocurriendo dos cosas no deseadas: en el mejor de los casos, las cámaras terminan muy al borde del área, y en el peor de los casos, para radios menores, las cámaras ni siquiera están en su respectiva área.

Es así que llegamos a la cota del 60%: si dos cámaras comparten más del 60% de su área a 300 m, entonces se fusionan y se vuelven una sola unidad con centro entre las dos cámaras (equivale a 192 m entre ellas). Esto tiene varias repercusiones con las cuales habrá que tener cuidado más adelante y además nos forza a correr los modelos finales para otro porcentaje de overlap menor para asegurarnos de que ahí no estén los posibles resultados.

## Página 2 — Unidades tratadas y controles

[Ver foto 2](<fotos/Errores Cometidos-2.jpg>)

| umbral_X | distancia_max_m | unidades | camaras_fusionadas | grupo_mayor | dist_max_al_centro_m | fuera_a_100m |
|---:|---:|---:|---:|---:|---:|---:|
| 50% | 242 | 98 | 13 | 3 | 102 | 2 |
| 60% | 192 | 99 | 12 | 3 | 81 | 0 |
| 70% | 143 | 100 | 11 | 3 | 70 | 0 |
| 80% | 95 | 103 | 8 | 3 | 44 | 0 |
| 90% | 47 | 108 | 5 | 2 | 9 | 0 |

Un número que vale la pena tener presente es que del total de los incidentes, 5.5% caen en esas áreas compartidas. Para poder controlar por esto se hacen 2 cosas: el peso de cada incidente vale 1/k donde k es el total de áreas que contabilizan ese accidente, evitando que se infle el total de manera artificial, y segundo, al momento de correr los modelos se clusteriza por componente tratado y no solo por unidad, para que el error estándar no subestime el hecho de que no son del todo independientes.

Considerando todo lo anterior, las 113 cámaras se convierten en 99 unidades tratadas. Esta lista de centros fijos son el universo de posibles unidades que se van a utilizar para todos los radios, haciendo comparables los resultados entre sí, **reforzado por cómo hacemos el trimming tras el matching** [añadido en azul].

[Figura: las 12 unidades fusionadas con X = 60% a 100 m, en la foto 2](<fotos/Errores Cometidos-2.jpg>).

Así se ven las 12 unidades fusionadas a 100 m. Esa es la que está casi al borde, pero el resto quedan definidas razonablemente bien. Si hubiéramos tomado overlap al 50%, la unidad “tratada” ya no tendría cámaras.

[Figura: las mismas unidades con X = 50% a 100 m, en la foto 2](<fotos/Errores Cometidos-2.jpg>).

Hay más pruebas de robustez en el notebook de unit-design y hay que mostrar cómo se ven las unidades donde aún hay mucho overlap. Con esto se soluciona por completo lo que decía Alberto. ツ

Hay otro tema, y es que la construcción de controles también tiene que cambiar.

**Antes.** Se hacía un pool de posibles controles para cada radio. Básicamente era un grid sobre toda la ciudad de círculos y luego se excluían aquellos sin ningún tramo de vialidad y aquellos con overlap con otra cámara.

## Página 3 — Construcción de controles y variables originales

[Ver foto 3](<fotos/Errores Cometidos-3.jpg>)

**Ahora.** Al igual que con las unidades tratadas, el pool de posibles controles se define una única vez en toda la ciudad, asignando puntos aleatorios sobre toda la infraestructura vial y formando inicialmente áreas de radio 300 m. Posteriormente se excluye toda área con overlap con un área de 300 m sobre los radares de velocidad. Para este punto aún no se ha verificado si hay o no overlap entre posibles unidades de control, eso se hará hasta el matching.

En total quedamos con 14,656 posibles controles. Si aplicáramos la regla de no overlap entre controles desde este punto, nos quedaríamos con 631 unidades a 300 m. Este número también es importante porque es el que se usará posteriormente como prueba naive del modelo sin matching.

[Figura: pool de control (verde, n = 14,656) y áreas tratadas (rojo) a 300 m, en la foto 3](<fotos/Errores Cometidos-3.jpg>).

Una vez que tenemos definido finalmente cuáles son los pools de tratadas y de control, ahora sí es momento de hacer matching, pero primero hay que calcular los features que vamos a utilizar para poder hacerlo.

**Antes.** Solo se utilizan datos antes del 22 de abril del 2019 (cuando entró en vigor el programa de Fotocívicas). Las variables que se consideraron fueron las siguientes 18:

- Estructurales:
  - Road length → metros de vía.
  - # vialidades → número de vías únicas.
  - Max carriles → el máximo de carriles entre sus vías.
  - Both directions → si tiene tránsito en doble sentido (booleano).
  - Vía acceso controlado → si tiene vialidades de acceso controlado (booleano).
  - Vía primaria → análoga a la anterior.
  - Max nivel → el nivel máximo de sus vías (ej. túnel ⇒ -1, segundo piso ⇒ 1, 2...).

## Página 4 — Metro, siniestralidad y rediseño

[Ver foto 4](<fotos/Errores Cometidos-4.jpg>)

- Metro:
  - Mean afluencia mensual → media mensual de la estación de metro más cercana a cada área.
  - Std afluencia mensual → análoga a la anterior.
  - Distance to station → distancia del centro del área a su respectiva estación considerada.
- Siniestralidad:
  - Media y desviación estándar de los conteos mensuales en 4 niveles: total, min, pic y fcs.

**Ahora.** Propensity score arregla problemas de nivel; DiD no necesita niveles, necesita tendencias (más aún porque además se van a agregar las variables como controles en la especificación del modelo).

⇒ Utilizo el propensity score para poder encontrar unidades que hubiera esperado que tengan comportamientos similares tras una implementación de radar de velocidad. Importante mencionar que DiD asume que sin cámaras, controles y tratadas hubieran evolucionado igual.

**Nota en azul:** ¿Qué supone mi estimador (mi estimador es DiD, no de propensity score)? ¿Qué variables ponen en riesgo ese supuesto?

De ahí se hacen revisiones mecánicas sobre las variables:

- ¿Cuánto varían entre mis unidades? → value counts, histograma.
- ¿Qué otra variable ya dice esto? → matriz de correlaciones, PCA.
- ¿El dato mide lo que dice su nombre? → ¿std realmente es volatilidad?
- ¿Cuánto es señal y cuánto ruido? → confiabilidad por mitades, simular ruido.

**Nota en rojo:** Falta entender bien.

Con esto en mente, el rediseño de las variables termina de la siguiente manera.

Estructurales:

- Road length m: se mantiene igual.
- # vialidades: se mantiene igual.
- Carriles ponderados: max carriles no variaba mucho entre unidades, y esto era especialmente cierto conforme aumentaba el radio. Esta variable pondera el nivel por cuánta vía hay en el área. Es una mejor representación de la forma de la unidad.
- % doble sentido: misma situación que con both_directions del original y max_carriles.
- % acceso controlado: same as the last one, además, dejo afuera vía_primaria porque solo hay 2 tipos de vías ⇒ % vía primaria = 1 - % acceso controlado.
- % desnivel: cuánta vía a desnivel hay. Sustituye max_nivel.
- # niveles: número distinto de niveles. Sustituye max_nivel.

## Página 5 — Variables finales y matching

[Ver foto 5](<fotos/Errores Cometidos-5.jpg>)

Metro:

- Afluencia_nivel: ahora solo mide las estaciones que estén dentro de la unidad.
- × std_afluencia por correlación con nivel.
- × distance to station ya no es necesaria.

Siniestralidad:

- Nivel incidentes: media mensual de incidentes totales.
- % lesionados: fracción de accidentes con lesionados o muertos.
- Tendencia: ∩ / ∪ previo a implementación.
- Hubo_fcs: indicadora de fatalidades.

Una vez que ya tenemos los features que consideramos pertinentes, es momento de calcular el propensity score, balancear grupos y hacer el matching. Aquí también hay diferencias importantes con respecto a la versión anterior, especialmente porque se busca que los resultados sean comparables entre distintos radios.

**Antes.** Mames, neta esto era una porquería. Ni qué decir. Un pool de controles distinto para cada radio, un set de variables distinto para calcular el SMD que minimizaba el SMD de todas las variables.

**Ahora.** El primer cambio y el más importante es que el pool de posibles unidades tanto de tratamiento como de control se mantiene fijo durante todo el proceso de matching.

Para cada radio se calcula el propensity score utilizando una regresión logística sobre las variables estandarizadas, sin penalización y con solver newton-cholesky. [Anotaciones al margen: “permite convergencia”; “no queremos generalizar”; “hay que ver si estandarizando sigue siendo necesario”.]

Para el matching se utiliza vecino más cercano 1:1 sin reemplazo con cuatro reglas:

- Caliper 0.2 desviaciones estándar del logit. Tratada sin control dentro del caliper ⇒ se queda sin pareja.
- Desempate por Mahalanobis: muchísimos controles en el caliper con control casi idéntico. Usar esta distancia baja |SMD| de 0.093 a 0.07.
- 600 m entre controles emparejados, para que no compartan accidentes ni en el radio más grande.

Y la parte más importante para asegurarnos de que seguimos comparando las mismas unidades: nos quedamos solo con la intersección de las...

## Página 6 — Muestra común y diagnósticos

[Ver foto 6](<fotos/Errores Cometidos-6.jpg>)

...unidades tratadas que sí encontraron pareja en todos los radios.

⇒ Solo nos quedamos con **93 unidades de tratamiento**.

❗¿Cómo son las unidades que estamos excluyendo?

Así queda el análisis de SMD para todos los radios: [love plots de 100, 150, 200, 250 y 300 m en la foto 6](<fotos/Errores Cometidos-6.jpg>).

Así se ve el common support: [histogramas antes (14,755 unidades) y después (93 pares) para cada radio en la foto 6](<fotos/Errores Cometidos-6.jpg>).

Y así se ven las tendencias paralelas: [cinco series de tratadas y controles, una por radio, en la foto 6](<fotos/Errores Cometidos-6.jpg>).

Ya por último y solo como referencia, así quedó el mapa de la CDMX con sus unidades de tratamiento y de control a 300 m: [mapa en la foto 6](<fotos/Errores Cometidos-6.jpg>).

## Página 7 — Qué quiere decir DiD

[Ver foto 7](<fotos/Errores Cometidos-7.jpg>)

Antes de pasar a explicar los cambios que hice en el modelado, quiero hacer una pausa para poder internalizar lo que el modelo me quiere decir.

Interpretemos la siguiente información:

| Unidad | Antes | Después |
|---|---:|---:|
| Control | 6.019 | 5.366 |
| Treatment | 6.222 | 5.421 |

Si solo comparara tratamiento antes y después parecería que hubo una disminución de 0.801 (5.421 - 6.222) accidentes mensuales, pero eso estaría obviando el hecho de que **quizá los accidentes ya venían bajando** [subrayado y anotado en azul: “Supuesto de tendencias paralelas”], justo para eso tenemos el grupo de control, los cuales observaron una disminución en el mismo intervalo de tiempo de 0.653 (5.366 - 6.019) incidentes mensuales, así que realmente lo único que podemos atribuir al sistema de Fotocívicas es de 0.148 incidentes mensuales, lo cual representa una disminución del 2.45% con respecto al nivel de las unidades de control antes del tratamiento.

Bien, con eso en mente entonces ahora sí es momento de mostrar las especificaciones de los modelos que se corren:

```text
(1) incidentes ~ treat + post + treat:post
(2) incidentes ~ treat:post + C(uid) + C(t)
(3) incidentes ~ treat:post + [8 covariables]:post + C(uid) + C(t)
```

En los 3 modelos se clusteriza por componente traslapada y no por unidad, pues no olvidemos que por el overlap que existe entre algunas unidades, hay incidentes compartidos por más de un área.

Se incluyen efectos fijos de unidad [texto tachado: “para controlar por cambios específicos dentro de cada unidad”] **para absorber diferencias estables entre áreas** [corrección en azul] y por unidad temporal [texto tachado: “para mitigar el efecto causado por la pandemia”] **para absorber choques comunes a todas** [corrección en azul], lo que permite controlar por cambios que hayan afectado a la ciudad de manera generalizada.

En el último modelo se incluyen todas las variables estructurales y de afluencia del metro interactuadas con una dummy de tiempo para poder controlar por cualquier efecto que el propensity score haya dejado remanente.

Al final se hace bootstrap para poder mitigar un poco el problema que tienen los errores estándar al aplicar PSM + DiD y ver si los resultados nos dicen algo o no.

## Página 8 — De lo más básico al DiD

[Ver foto 8](<fotos/Errores Cometidos-8.jpg>)

Bueno después de tanto desmadre, ahora sí podemos interpretar los resultados y ver qué nos dicen del programa. Vamos a empezar desde lo más básico y vamos a ir construyendo hasta terminar con la especificación principal.

### Antes y después, solo tratadas

Yo creo que esta es la manera más naive que existe de analizar los resultados del programa y es básicamente ver cómo cambiaron las tasas de accidentes mensuales en donde se pusieron los radares. No existen controles, no existe nada. Todo cambio en las tasas se asume que es atribuible exclusivamente a las cámaras (solo analizo a 300 m).

```text
(1) incidentes ~ post
              coef      std err       z       P>|z|     [0.025    0.975]
Intercept    6.6630      0.376     17.734     0.000      5.927     7.399
post        -0.9374      0.161     -5.810     0.000     -1.254    -0.621
```

Antes del tratamiento las unidades tenían en promedio 6.663 accidentes mensuales. El programa redujo los accidentes en 0.9374 cada mes, el programa redujo los incidentes en 14.06%. ⇒ ¡pongamos cámaras en toda la ciudad!

Claramente esta conclusión está obviando cualquier otra cosa que haya hecho que los accidentes bajaran, además de que no tenemos un punto real de referencia más que las mismas unidades tratadas.

### Tratadas vs controles, solo después

Bien, entonces agreguemos controles, ¿cómo se comparan los accidentes en zonas tratadas vs zonas sin radares en toda la ciudad? Para responder esta pregunta haremos uso de las 631 unidades de control sin overlap a un radio de 300 m que resultaban del pool que se construyó.

```text
(2) incidentes ~ tratado | post = 1
              coef      std err       z       P>|z|     [0.025    0.975]
Intercept    3.4295      0.099     34.759     0.000      3.236     3.623
tratado      2.2961      0.310      7.400     0.000      1.688     2.904
```

Increíble, gracias a los radares de velocidad aumentamos los incidentes mensuales en 2.2961, es decir un incremento del 66%. Claramente este resultado es absurdo y refleja más bien el hecho que ya sabíamos: las cámaras se colocaron en zonas con altos índices de accidentes.

## Página 9 — DiD sin emparejar y muestra común

[Ver foto 9](<fotos/Errores Cometidos-9.jpg>)

Si comparar controles y tratadas de esta forma nos lleva a resultados tan absurdos, es necesario encontrar una manera de compararlos entre sí, pero entendiendo las diferencias que existen entre ellos.

### Diferencias en diferencias, sin emparejar

Veamos cómo cambió la ciudad antes y después del tratamiento y comparemos ese cambio con el observado en las zonas tratadas.

```text
(3) incidentes ~ treat + post + treat:post
                  coef      std err       z       P>|z|     [0.025    0.975]
Intercept        3.8416      0.115     33.380     0.000      3.616     4.067
tratado          2.8214      0.391      7.218     0.000      2.055     3.587
post            -0.4121      0.037    -11.086     0.000     -0.485    -0.339
tratado:post    -0.5253      0.165     -3.191     0.001     -0.848    -0.203
```

Como podemos observar, la ciudad tenía en promedio 3.8416 incidentes cada mes (en radios de 300 m), y tras la implementación se redujeron en 0.4121 a 3.4295. Por otro lado, las unidades tratadas mostraban una tasa de incidentes mensuales de 6.663 y se redujeron a 5.7256, **lo que significó una caída adicional de 0.5253 tras tratamiento vs controles post** [añadido en azul].

Esta reducción implica que las cámaras ayudaron a reducir los incidentes en un 13.67% con respecto a la media de los controles. Sin embargo, hay algo que vale la pena resaltar, y es el hecho de que estamos asumiendo que toda la ciudad se iba a comportar exactamente igual a las zonas donde se pusieron radares, pero ya sabemos que estos últimos eran sistemáticamente más peligrosos.

Ya sabíamos que hay unidades que son tan peligrosas que simplemente no son nada comparables al resto de la ciudad. No es realmente válido incluirlas en el comparativo.

### Muestra común de 93 tratadas

Consideremos solo aquellas unidades que sabemos que son comparables con al menos alguna otra zona en la ciudad. Aquí se consideran solo las 93 unidades que sabemos que encuentran un match en los 5 radios, pero por ahora solo las vamos a comparar contra el resto de la ciudad. Se incluyen también efectos fijos de unidad y tiempo.

```text
(4) incidentes ~ treat:post + C(uid) + C(t)
tratadas  controles      N      coef       EE    sig       p    base del %       base    % de la base
      93        631  52,128   -0.3884   0.1538    **   0.0116   controles, antes  3.8416     -10.1101
```

El punto de referencia para los controles sigue siendo la misma media de 3.8416, y en este caso vemos que la reducción fue de 0.3884 incidentes al mes, lo que...

## Página 10 — Emparejamiento y covariables × post

[Ver foto 10](<fotos/Errores Cometidos-10.jpg>)

...equivale a una disminución de 10.11%. Notamos que el efecto disminuyó, y esto era de esperarse, porque las unidades que excluimos eran las más peligrosas de la ciudad, y para las cuales no encontramos un control similar. Esto también nos obliga a dejar claro que el análisis, por lo tanto, no podrá decir nada respecto a este tipo de unidades.

### Emparejamiento

Veamos pues qué pasa cuando el grupo de control contra el que comparamos sí es representativo del tipo de unidades tratadas. Aquí nos quedamos con las mismas 93 unidades de tratamiento y sus respectivos controles matcheados.

```text
(5) incidentes ~ treat:post + C(uid) + C(t)
tratadas  controles      N      coef       EE    sig       p    base del %       base    % de la base
      93         93  13,392   -0.1476   0.1981         0.4565   controles, antes  6.0194      -2.4512
```

Ahora sí vemos una caída en el efecto estimado, siendo de 0.1476 incidentes mensuales, pero en esta ocasión el grupo de control tiene una media mensual de 6.0194, reflejando el efecto que tuvo el matching para elegir unidades más peligrosas. Con este cambio, el efecto se traduce en una disminución de tan solo 2.45%, muy lejos de lo que habíamos estado viendo antes.

### Covariables × post

No asumamos que el matching solucionó todas las diferencias entre unidades de control y tratamiento e introduzcamos ahora las variables que usamos en el propensity score como controles en la regresión, permitiendo que lugares estructuralmente distintos varíen distinto tras la implementación. Se excluyen de manera explícita todas las covariables que representaban el nivel y tendencia de siniestralidad (nivel incidentes, % lesionados, tendencia, hubo_fcs).

```text
(6) incidentes ~ treat_post + road_length_m_post + n_vialidades_post
    + carriles_ponderados_post + pct_acceso_controlado_post
    + pct_doble_sentido_post + pct_desnivel_post + n_niveles_post
    + afluencia_nivel_post + C(uid) + C(t)

variable                      coef      std err      z       P>|z|    [0.025    0.975]
treat_post                  -0.1063       0.181   -0.588     0.557    -0.461     0.248
road_length_m_post          -0.3469       0.164   -2.115     0.034    -0.668    -0.025
n_vialidades_post           -0.1138       0.142   -0.802     0.423    -0.392     0.164
carriles_ponderados_post    -0.0607       0.111   -0.548     0.584    -0.278     0.156
pct_acceso_controlado_post   0.0613       0.100    0.613     0.540    -0.135     0.257
pct_doble_sentido_post       0.2486       0.099    2.506     0.012     0.054     0.443
pct_desnivel_post            0.1048       0.226    0.464     0.643    -0.338     0.547
n_niveles_post              -0.0606       0.255   -0.237     0.813    -0.561     0.440
afluencia_nivel_post        -0.0444       0.122   -0.365     0.715    -0.283     0.194
```

| tratadas | controles | N | coef | EE | p | base del % | base | % de la base |
|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 93 | 93 | 13,392 | -0.1063 | 0.1808 | 0.5566 | controles, antes | 6.0194 | -1.7664 |

## Página 11 — Resumen de los pasos e incertidumbre

[Ver foto 11](<fotos/Errores Cometidos-11.jpg>)

Efectivamente, las covariables absorben parte del efecto observado. [Anotación en azul: “realmente estamos mostrando que es sensible moderadamente al ajuste”.] Las cámaras parecen haber reducido los incidentes en 0.1063 accidentes mensuales, equivalente a una reducción del 1.76% de la media de los controles.

Aquí queda el resumen sobre todos los modelos que llevan al modelo final, aplicado solo sobre el radio a 300 metros.

| Paso | Se introduce | Tratadas | Controles | N | Coef. | EE | Sig. | p | Base del % | Base | % de la base |
|---:|---|---:|---:|---:|---:|---:|:---:|---:|---|---:|---:|
| 1 | antes y después, solo tratadas | 99 | 0 | 7,128 | -0.9374 | 0.1613 | *** | 0.0000 | tratadas, antes | 6.6630 | -14.0691 |
| 2 | tratadas contra controles, solo después | 99 | 631 | 26,280 | 2.2961 | 0.3103 | *** | 0.0000 | controles, después | 3.4295 | 66.9501 |
| 3 | diferencia en diferencias | 99 | 631 | 52,560 | -0.5253 | 0.1646 | *** | 0.0014 | controles, antes | 3.8416 | -13.6750 |
| 4 | efectos fijos de unidad y tiempo | 99 | 631 | 52,560 | -0.5253 | 0.1659 | *** | 0.0015 | controles, antes | 3.8416 | -13.6750 |
| 5 | muestra común de 93 tratadas | 93 | 631 | 52,128 | -0.3884 | 0.1538 | ** | 0.0116 | controles, antes | 3.8416 | -10.1101 |
| 6 | emparejamiento | 93 | 93 | 13,392 | -0.1476 | 0.1981 | | 0.4565 | controles, antes | 6.0194 | -2.4512 |
| 7 | covariables × post | 93 | 93 | 13,392 | -0.1063 | 0.1808 | | 0.5566 | controles, antes | 6.0194 | -1.7664 |

### Cómo se administra la desconfianza sobre el último modelo

Hasta ahora no se había hecho explícito, pero es necesario mencionar que el último modelo clusteriza por componente traslapada. Veamos ahora cómo se ve el modelo si tomamos otros caminos. La media de los controles contra la que comparamos sigue siendo 6.0194.

Primero, asumamos que todas las observaciones son independientes entre sí, y no apliquemos ningún tipo de cluster.

| Se introduce | Coef. | EE | p | Clusters | IC bajo | IC alto | IC bajo % | IC alto % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sin agrupar | -0.1063 | 0.0935 | 0.2553 | — | -0.2895 | 0.0769 | -4.8097 | 1.2769 |

El coeficiente no cambió, se sigue manteniendo en una disminución de 0.1063 incidentes mensuales, pero sí lo hizo el error estándar, disminuyendo a 0.0935. El modelo se muestra más seguro de su resultado y nos dice que el efecto pudo haber estado entre una disminución de 4.8% y un aumento de 1.2%. Nótese el 0 en ese intervalo.

Sabemos que las observaciones del modelo no son independientes entre sí del todo, tenemos 72 observaciones mensuales de las mismas 186 unidades. Clusterizemos por unidad.

| Se introduce | Coef. | EE | p | Clusters | IC bajo | IC alto | IC bajo % | IC alto % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| agrupado por unidad | -0.1063 | 0.1722 | 0.537 | 186 | -0.4439 | 0.2312 | -7.3739 | 3.8411 |

Nuevamente vemos que el coeficiente no cambia, pero sí lo hace su error estándar y con él, el intervalo de confianza que se tiene sobre el efecto, pasando a estar entre -7.3739% y 3.8411%; nótese nuevamente el 0 en el intervalo.

## Página 12 — Clustering por componente y proceso de bootstrap

[Ver foto 12](<fotos/Errores Cometidos-12.jpg>)

Y finalmente, llegamos al modelo que utilizamos, clusterizando no por unidad, sino por componente traslapada, reconociendo así el hecho de que hay unidades que comparten área y, por lo tanto, incidentes entre ellas. En total son 72 componentes tratadas y 93 unidades de control (por construcción no hay traslape entre controles).

| Se introduce | Coef. | EE | p | Clusters | IC bajo | IC alto | IC bajo % | IC alto % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| agrupado por componente traslapada | -0.1063 | 0.1808 | 0.5566 | 165 | -0.4608 | 0.2481 | -7.6547 | 4.1218 |

Este es el modelo final, manteniendo el mismo coeficiente pero con un intervalo de confianza entre -7.6547% y 4.1218%, nuevamente con el 0 incluido.

### Bootstrap

Se hizo además bootstrap para poder dar un poco más de claridad sobre los efectos que estamos observando.

El proceso de bootstrap toma como dados las 99 unidades tratadas y los 14,656 controles. A continuación se describe el proceso seguido para cada una de las iteraciones.

1. Para cada radio, se sortean tantas componentes como las haya. Recordemos que una componente es un conjunto de unidades tratadas que comparten área entre ellas. Por construcción, no existe overlap entre unidades a 100 m, por lo que en ese radio una componente es lo mismo que una tratada. A 300 m sí hay overlap entre unidades, convirtiendo las 99 unidades en 77 componentes.

| Radio | Componentes |
|---:|---:|
| 100 m | 99 |
| 150 m | 96 |
| 200 m | 92 |
| 250 m | 84 |
| 300 m | 77 |

En cada radio se hace un muestreo aleatorio del número de componentes con reemplazo. Ej. a 100 m se muestrean 99 componentes; a 200 m se muestrean 92 componentes.

2. Se muestrean los 14,656 controles con reemplazo.
3. Se ajusta la regresión logística sobre el pool muestreado de tratadas y controles y se calcula el propensity score para las unidades.
4. Se hace el matching entre las unidades tratadas y los controles, excluyendo aquellas tratadas que no hayan encontrado un buen control.

## Página 13 — Bootstrap y resumen de incertidumbre

[Ver foto 13](<fotos/Errores Cometidos-13.jpg>)

5. De las unidades tratadas que hayan sobrevivido al matching, se filtran solo aquellas que estén dentro de las 93 del análisis original. No se hizo antes del matching porque en el original las 99 entran al matching a tomar su mejor control.

Sobre las unidades que resulten se calculan los modelos siguientes:

```text
(a) incidentes ~ treat:post + C(uid) + C(t)
(b) incidentes ~ treat:post + [8 covariables]:post + C(uid) + C(t)
```

Clusterizando por componentes tratadas.

Se hacen 2,000 muestreos por cada uno de los 5 radios. Cada modelo se calcula para los 4 niveles de incidentes (total, MIN, PIC y FCS). En total se calcularon 80,000 coeficientes.

```text
80,000 = 2,000 muestreos × 5 radios × 4 niveles × 2 modelos
```

El bootstrap nos muestra lo siguiente:

| Se introduce | Coef. | EE | IC bajo | IC alto | IC bajo % | IC alto % | Media bootstrap | Percentil del estimado | Repeticiones |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bootstrap del proceso completo | -0.1063 | 0.1294 | -0.3637 | 0.1322 | -6.0415 | 2.1963 | -0.1155 | 52.9 | 2,000 |

El error estándar disminuyó a **0.1294** [corregido en azul] con una media en el bootstrap de -0.1155 incidentes mensuales, aunque el 0 sigue en el intervalo de confianza de entre -0.3637 y 0.1322, lo que se traduce entre una disminución del 6.0415% y un aumento de 2.1963% con respecto a la media de los controles antes del tratamiento. [Texto original “Reforzando la idea de un efecto nulo” tachado; corrección en azul: **“es compatible con efecto cero”**.]

| Paso | Se introduce | Coef. | EE | p | Clusters | IC bajo | IC alto | IC bajo % | IC alto % | Media bootstrap | Percentil del estimado | Repeticiones | Cruza cero |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 8 | sin agrupar | -0.1063 | 0.0935 | 0.2553 | — | -0.2895 | 0.0769 | -4.8097 | 1.2769 | — | — | — | sí |
| 9 | agrupado por unidad | -0.1063 | 0.1722 | 0.537 | 186 | -0.4439 | 0.2312 | -7.3739 | 3.8411 | — | — | — | sí |
| 10 | agrupado por componente traslapada | -0.1063 | 0.1808 | 0.5566 | 165 | -0.4608 | 0.2481 | -7.6547 | 4.1218 | — | — | — | sí |
| 11 | bootstrap del proceso completo | -0.1063 | 0.1294 | — | — | -0.3637 | 0.1322 | -6.0415 | 2.1963 | -0.1155 | 52.9 | 2,000 | sí |

Y así queda el resumen sobre el modelo final y cómo se fue ajustando su incertidumbre.

Y con esto entonces ahora sí podemos analizar los resultados en todos los radios y en todos los niveles de incidentes. Se muestran los resultados del modelo sin efectos fijos ni covariables y con efectos fijos y covariables.

## Página 14 — Interpretación de los resultados

[Ver foto 14](<fotos/Errores Cometidos-14.jpg>)

Antes de entrar en el análisis específico por nivel de incidentes, merece la pena hacer un resumen de los efectos que estamos estimando: es el Average Treatment on the Treated pues estamos analizando el efecto en la muestra resultante tras hacer trimming, recordemos que tuvimos que excluir aquellas unidades para las que no encontramos un control comparable y que luego nos aseguramos de que las unidades resultantes encontraran match en todos los radios, así que el modelo no podrá decirnos nada de ellas, que justamente eran las más peligrosas en toda la ciudad. Si bien esto último nos obligó a descartar más unidades, es valioso en cuanto nos permite comparar los resultados entre radios pues las unidades tratadas (los centros tratados) se mantuvieron constantes en todos los casos (las 93 sobrevivientes).

Se analizarán además dos modelos: Dif-in-Dif sin covariables ni efectos y con EF y las covariables interactuadas con una dummy temporal post.

También vale la pena mencionar que como estamos corriendo un modelo de diff-in-diff sobre parejas matcheadas con PSM, no podemos confiar del todo en los errores estándar calculados en el modelo final ni necesariamente en su significancia. Precisamente con el objetivo de mitigar esa incertidumbre fue que se hizo el bootstrap sobre todo el proceso. El IC usado es el de este último. Esto nos obliga también a tener más presente el tamaño de los efectos al interpretarlos.

Algo que tampoco podemos olvidar es que estamos clusterizando por componente tratada y no por unidad. Una componente tratada incluye a todas las unidades tratadas que tengan overlap entre sí para reflejar el hecho de que comparten algunos incidentes y no subestimar el error estándar. La cantidad de clusters varía con cada radio y por construcción la cantidad de componentes tratadas es igual al total de unidades tratadas a 100 metros.

En la figura muestro una componente de 5 tratadas a 300 m para ilustrar cómo cambia con los radios. En estas 5 unidades tratadas, las componentes pasan de 5 → 4 → 1 conforme incrementamos el radio, esto a su vez se refleja en el número total de componentes, que pasan de 93 → 86 → 72 respectivamente. Recordemos que por construcción, no hay traslape entre controles, así que los 93 controles siempre son 93 componentes.

[Figura: «Las mismas cinco unidades tratadas en tres radios», 100 m = 5 componentes; 200 m = 4 componentes; 300 m = 1 componente. Círculos: unidades tratadas; líneas ocres: traslape directo. En la foto 14](<fotos/Errores Cometidos-14.jpg>).

## Página 15 — Incidentes en general

[Ver foto 15](<fotos/Errores Cometidos-15.jpg>)

También es importante tener presente que los efectos que estamos midiendo se entienden como número de incidentes al mes en un área determinada, y que cuando hacemos comparaciones porcentuales es tomando como referencia la media de incidentes mensuales del grupo de control antes del tratamiento. En cada caso se especifica tanto la media como su desviación estándar.

### Incidentes en general

[Figura: «Tratado × Post por radio | todos los incidentes», con (1) Sin EF ni covariables y (3) EF + covariables × post; dos escalas: incidentes mensuales por unidad y % de la media del control antes. En la foto 15](<fotos/Errores Cometidos-15.jpg>).

| Radio | Media (DE) del control antes | (1) Coef. | (1) % | (3) Coef. | (3) % |
|---:|---:|---:|---:|---:|---:|
| 100 m | 2.22 (2.52) | +0.094 | +4.2% | +0.125 | +5.6% |
| 150 m | 2.95 (2.70) | -0.064 | -2.2% | -0.040 | -1.4% |
| 200 m | 3.87 (3.02) | -0.083 | -2.1% | -0.091 | -2.4% |
| 250 m | 5.03 (3.43) | -0.129 | -2.6% | -0.131 | -2.6% |
| 300 m | 6.02 (3.86) | -0.148 | -2.5% | -0.106 | -1.8% |

Notemos que a 100 m el estimado puntual es positivo; en el resto de los radios es negativo, y tampoco es obvio que haya una disminución de incidentes sostenida conforme aumenta el radio: a 300 m el efecto es menor que a 250 m en magnitud.

Todos los intervalos del bootstrap incluyen el cero. En el caso específico de 300 m podemos observar que con respecto a la media de los controles antes del tratamiento, los datos pudieron haber mostrado desde un aumento del 2.2% hasta una reducción de 6.04%.

Notemos también que con respecto a los intervalos del valor estimado del DiD, tanto la especificación 1 como la 3, el intervalo crece, mientras que lo contrario es cierto para el porcentaje de la media.

Recordemos que es importante prestar atención al tamaño de los coeficientes sobre la certeza estadística que tenemos de ellos. Con eso en mente podemos ver que...

## Página 16 — Brecha posterior e incidentes menores

[Ver foto 16](<fotos/Errores Cometidos-16.jpg>)

...independientemente del radio que evaluemos, ninguna reducción puntual supera el 2.61%, que es la de 250 m.

[Figura: «Brecha posterior: Tratado + Tratado × Post | modelo (1)». Puntos por radio: 100 m +0.16; 150 m -0.03; 200 m -0.06; 250 m -0.08; 300 m +0.05. Todos los intervalos cruzan cero. En la foto 16](<fotos/Errores Cometidos-16.jpg>).

Y en cuanto a la brecha que quedó tras el tratamiento podemos notar lo siguiente: para el caso específico de 300 m, los controles tenían una media de incidentes mensual de 6.019 y las tratadas de 6.222, una diferencia de 0.203, mientras que después del tratamiento quedaron controles con 5.366 y tratadas con 5.421, reduciendo la brecha a 0.055, Pero ese cierre de 0.148 es exactamente el coeficiente DiD, no una evidencia adicional, y no es distinguible de cero. Tampoco se repite en los demás radios: a 100 m la brecha se abre (de +0.06 a +0.16) y entre 150 y 250 m cambia de signo, con las tratadas pasando de estar ligeramente arriba a ligeramente abajo de sus controles. Lo que sí se puede decir es que después del tratamiento la brecha entre tratadas y controles no es distinguible de cero en ningún radio.

```text
incidentes = media controles antes + treatment + post + treat:post
             6.019                 + 0.203     - 0.653   - 0.148

media tratamiento antes = 6.222
controles tras tratamiento = 5.366
tratadas tras tratamiento = 5.421
```

A 300 m, sin embargo, el estimado final del efecto fue de -0.106 incidentes al mes por unidad, equivalente a -1.77% de la media previa del control, una reducción pequeña con respecto a los 6.019 incidentes mensuales antes del tratamiento.

### Incidentes menores

[Figura: «Tratado × Post por radio | incidentes sin lesionados (MIN)», (1) Sin EF ni covariables y (3) EF + covariables × post; dos escalas: incidentes mensuales por unidad y % de la media del control antes. En la foto 16](<fotos/Errores Cometidos-16.jpg>).

| Radio | Media (DE) del control antes | (1) Coef. | (1) % | (3) Coef. | (3) % |
|---:|---:|---:|---:|---:|---:|
| 100 m | 1.32 (1.77) | +0.020 | +1.5% | +0.041 | +3.1% |
| 150 m | 1.71 (1.92) | -0.094 | -5.5% | -0.069 | -4.0% |
| 200 m | 2.33 (2.18) | -0.064 | -2.7% | -0.068 | -2.9% |
| 250 m | 3.03 (2.44) | -0.069 | -2.3% | -0.052 | -1.7% |
| 300 m | 3.68 (2.76) | -0.090 | -2.4% | -0.045 | -1.2% |

En este caso la mayor reducción la observamos a 150 m, con una reducción de 0.069 incidentes mensuales, equivalente a una disminución porcentual del 4% con respecto a la media de los controles antes del tratamiento de 1.71.

Merece la pena mencionar que el cero está en todos los intervalos reportados.

También se observa que el efecto tiene su mínimo a 150 m y de ahí el efecto parece irse diluyendo. Honestamente a 100 m me suena más a ruido.

## Página 17 — Incidentes con lesionados, fatales y conclusión

[Ver foto 17](<fotos/Errores Cometidos-17.jpg>)

### Incidentes con lesionados

[Figura: «Tratado × Post por radio | incidentes con lesionados (PIC)», (1) Sin EF ni covariables y (3) EF + covariables × post; dos escalas: incidentes mensuales por unidad y % de la media del control antes. En la foto 17](<fotos/Errores Cometidos-17.jpg>).

| Radio | Media (DE) del control antes | (1) Coef. | (1) % | (3) Coef. | (3) % |
|---:|---:|---:|---:|---:|---:|
| 100 m | 0.89 (1.20) | +0.076 | +8.5% | +0.085 | +9.5% |
| 150 m | 1.22 (1.38) | +0.030 | +2.4% | +0.028 | +2.3% |
| 200 m | 1.52 (1.53) | -0.015 | -1.0% | -0.020 | -1.3% |
| 250 m | 1.97 (1.75) | -0.065 | -3.3% | -0.085 | -4.3% |
| 300 m | 2.30 (1.90) | -0.062 | -2.7% | -0.065 | -2.8% |

Aquí se ve algo interesante porque para los efectos puntuales estimados sí se ve una tendencia a que el efecto disminuía más accidentes conforme aumentaba el radio con el caveat enorme de que para 100 y 150 m el efecto estimado es positivo y en todos los intervalos está el cero. El mayor efecto es a 250 m con una disminución de 4.3% con respecto a la media de controles previa al tratamiento de 1.97 incidentes con lesionados.

### Incidentes con fallecidos

[Figura: «Tratado × Post por radio | incidentes fatales (FCS)», (1) Sin EF ni covariables y (3) EF + covariables × post; dos escalas: incidentes mensuales por unidad y % de la media del control antes. En la foto 17](<fotos/Errores Cometidos-17.jpg>).

| Radio | Media (DE) del control antes | (1) Coef. | (1) % | (3) Coef. | (3) % |
|---:|---:|---:|---:|---:|---:|
| 100 m | 0.014 (0.120) | -0.0015 | -10.6% | -0.0011 | -7.7% |
| 150 m | 0.018 (0.134) | +0.0003 | +1.6% | +0.0006 | +3.4% |
| 200 m | 0.019 (0.139) | -0.0042 | -22.6% | -0.0032 | -17.4% |
| 250 m | 0.032 (0.182) | +0.0051 | +15.7% | +0.0060 | +18.6% |
| 300 m | 0.036 (0.193) | +0.0039 | +10.9% | +0.0041 | +11.6% |

Honestamente esto suena más a ruido que nada, en especial considerando que en el total de accidentes que estamos utilizando solo hay 411 incidentes fatales a 300 m, el 0.53% de los 77,102 del panel.

Se ve más obvio en la tabla, donde vemos que los datos son compatibles con una reducción del 17.45% hasta un incremento de 37.09% en incidentes fatales al mes.

| | 100 m | 150 m | 200 m | 250 m | 300 m |
|---|---:|---:|---:|---:|---:|
| Tratado × Post | -0.001 | 0.001 | -0.003 | 0.006 | 0.004 |
| (EE) | (0.004) | (0.005) | (0.005) | (0.006) | (0.006) |
| IC 95% bootstrap | [-0.006, 0.007] | [-0.006, 0.009] | [-0.008, 0.010] | [-0.006, 0.012] | [-0.006, 0.013] |
| Media del control, antes | 0.014 | 0.018 | 0.019 | 0.032 | 0.036 |
| (DE) | (0.120) | (0.134) | (0.139) | (0.182) | (0.193) |
| % de la media del control | -7.71 | 3.42 | -17.40 | 18.61 | 11.62 |
| IC 95% bootstrap (%) | [-42.14, 51.26] | [-33.35, 51.01] | [-42.29, 55.87] | [-19.37, 36.70] | [-17.45, 37.09] |
| Observaciones | 13,392 | 13,392 | 13,392 | 13,392 | 13,392 |
| R² | 0.035 | 0.032 | 0.029 | 0.029 | 0.029 |
| Clusters | 186 | 183 | 179 | 171 | 165 |

### Conclusión

Dentro de lo que se pudo observar, no se puede descartar que las cámaras no hayan tenido impacto, pero el efecto observado fue muy bajo. No olvidemos que no podemos decir nada de las zonas más peligrosas de la ciudad (esas 6 unidades que dejamos fuera tras el matching).

**Nota final en azul:** Las estimaciones puntuales son pequeñas y sus intervalos incluyen cero ツ.
