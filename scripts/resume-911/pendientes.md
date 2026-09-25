# Pendientes para cerrar la estimación

*Lo mínimo indispensable para cumplir lo que pidió Alberto en [`revision-alberto.md`](revision-alberto.md) y que los resultados sean defendibles. Todo lo que no está aquí se decidió dejar fuera, y abajo está por qué.*

---

## Ya está hecho

- [x] Panel de unidad × periodo, verificado (descuadre 0)
- [x] Emparejamiento de los cinco radios sobre la muestra común de 93
- [x] **DiD sin matching** → apéndice de Alberto. −0.525 con 99 tratadas,
      −0.388 con 93, contra 631 controles disjuntos (lo corrió claude, pero falta generar bien el resultado e interpretarlo)
- [x] **Clustering por componente traslapada**: +7% al error estándar a 300 m,
      0% a 100 m 
- [x] **Robustez X = 50%**: −0.2532 contra −0.2293 del X = 60% libre. Un octavo
      del error estándar; el umbral no carga el resultado
- [x] **Robustez reparto cercano**: idéntica al reparto por pesos, exactamente.
      Ver la nota al final
- [x] **Las 60 estimaciones**: 5 radios × 4 niveles × 3 especificaciones, en el
      notebook y en `pipeline/estimacion.py`, verificadas una contra otra
- [x] **Bootstrap del proceso completo**, 500 repeticiones. Los dos intervalos
      cruzan cero: a 300 m [-6.2%, +1.7%], y PIC a 100 m [-4.2%, +13.9%]. El
      único resultado significativo de las 60 **no sobrevive**: el estimado
      original queda en el percentil 84 de su propia distribución bootstrap y la
      repetición típica da la mitad del efecto. A 300 m el error estándar del
      bootstrap es 0.69x el analítico, o sea que la fórmula era conservadora —la
      dirección que predicen Abadie e Imbens
- [x] Caracterización de las 6 unidades que el trimming descarta: ~13.5
      incidentes/mes contra 6.22 las que se quedan

---

## Falta correr — cuatro cosas

- [x] **1. La especificación principal, en los cinco radios.** Tres columnas,
      en progresión:

  ```
  (1)  incidentes ~ tratado + post + tratado:post
  (2)  incidentes ~ tratado:post + C(uid) + C(t)
  (3)  incidentes ~ tratado:post + [8 covariables]:post + C(uid) + C(t)
  ```

  Todas con `cov_type="cluster"`, agrupando por componente traslapada.

  **La (1) es la que contesta lo que pidió Alberto**: ahí sobreviven `tratado`,
  `post` y la interacción, así que se puede reportar la suma
  `tratado + tratado:post` con su error estándar y sus estrellitas. Sus cuatro
  coeficientes son literalmente la tabla 2x2 de medias.

  **La (2) y la (3) son el resultado.** Con efectos fijos de unidad, `tratado` y
  `post` son colineales y desaparecen; el intercepto queda pero es un artefacto
  de qué dummy se omitió, así que no se reporta ni se interpreta. Queda un solo
  coeficiente que leer, la interacción, y significa lo mismo que en la (1).

  Dummies de tiempo y no un simple `post`, porque la ventana incluye la pandemia.

  En las tres hay que reportar N, R² y el *control mean* con su desviación
  estándar: los efectos fijos se comen la información de niveles y esa columna es
  lo que la repone. El R² salta de 0.01 a 0.51 al meter los efectos fijos, pero
  eso solo refleja que los círculos y los meses difieren entre sí, no calidad del
  modelo. Los indicadores de efectos fijos van hasta abajo de la tabla.

- [x] **1b. Cuatro variables de resultado, no una.** Como estaba pensado
      originalmente y como probablemente son los cuadros 4.1-4.3 que Alberto
      revisó:

Son **cuatro**, no tres: la tesis ya tiene `tab:results-main-general`,
      `-min`, `-pic` y `-fcs`.

  | Tabla | Variable de resultado | Definición (capítulo 3) | En el panel a 300 m |
  | --- | --- | --- | --- |
  | general | MIN + PIC + FCS | todos | 77,102 |
  | min | MIN | sin lesionados ni fallecidos, daños materiales | ~42,500 |
  | pic | PIC | alarma clasificada como Urgencias Médicas | ~34,200 |
  | fcs | FCS | se registró un cadáver en el lugar | 411 |

  Se cambia `NIVELES` en la celda del panel: `None`, `("MIN",)`, `("PIC",)`,
  `("FCS",)`.

  **Ojo con las tasas.** El capítulo 3 dice que los incidentes se analizan "tanto
  en números absolutos como en tasas por cada 1,000 vehículos". Quitar las tasas
  no elimina una tabla: le quita la mitad a las cuatro. Sigue siendo defendible
  —el denominador son casetas en la periferia— pero es un cambio visible y tiene
  que ir en la nota para Alberto.

  **La de FCS necesita una nota de potencia, y no es opcional.** Con 411 eventos
  en 13,392 observaciones y 80% de potencia, solo detectaría reducciones
  superiores al **47%** de la media del control; el intervalo del efecto estimado
  va de **-22% a +44%**. Sin esa frase el cuadro se lee como "no hubo efecto sobre
  las muertes", que es lo contrario de lo que permite concluir. Redacción:

  > La especificación sobre incidentes fatales tiene 411 eventos en 13,392
  > observaciones. Con 80% de potencia solo permitiría detectar reducciones
  > superiores al 47% de la media del grupo de control, y el intervalo de
  > confianza abarca desde -22% hasta +44%. No es informativa y se reporta
  > únicamente por completitud.

  Nota técnica: 40 de los 431 FCS caen en área compartida y llevan peso
  fraccionario, así que Poisson tampoco es una salida directa para este cuadro.

  **Estructura de la presentación**, para que no se vuelvan 45 columnas: un
  cuadro por variable de resultado con los cinco radios como columnas, en la
  especificación (3); más un cuadro aparte a 300 m con las tres columnas de
  progresión, que es donde va lo que pidió Alberto sobre `tratado` y la suma.

- [x] **2. Los cinco radios con trimming laxo** (96 / 98 / 99 / 97 / 98 pares).
      Mismo script, cambiando `tratadas_validas`. Va al apéndice.

- [x] **3. Una columna con las covariables × dummies de tiempo**, solo a 300 m.
      Es el cuarto punto de la lista de Alberto. No va como principal: son 568
      parámetros contra 165 clusters.

- [x] **4. Bootstrap del proceso completo.** Hecho en `bootstrap.ipynb`, 500
      repeticiones, sobre 300 m con todos los incidentes y sobre 100 m con PIC.
      Pendiente menor: subirlo a 2,000 repeticiones para estabilizar los
      percentiles, y decidir si se corre en más combinaciones.

---

## Falta escribir

- [ ] **10. Reescribir el capítulo 3. Va primero.** Alberto lo dio casi por bueno,
      pero describe unidades, covariables, modelo y trimming que ya no existen, e
      incluso menciona un radio de 50 m que ya no se analiza. Es el cambio más
      grande que va a encontrar, y sin él los resultados del capítulo 4 no tienen
      de dónde salir. Por secciones de `Chapters/3.Data.tex`:

  | Sección | Qué cambia |
  | --- | --- |
  | Tratamiento | Las 113 cámaras se agrupan en **99 unidades**: dos se fusionan si sus círculos comparten más de 60% del área a 300 m. Los grupos se fijan una vez y se reusan en los cinco radios. Sale de `unit-design.ipynb` |
  | Atributos físicos de la red vial | Los máximos y binarias (`max_carriles`, `both_directions`, `via_acc_cont`, `max_nivel`) pasan a proporciones ponderadas por metros de vía; `via_primaria` sale porque es 1 menos `% acceso controlado`. Sale de `feature-design.ipynb` |
  | Proxies de movilidad | La afluencia se mide con las estaciones **dentro** del círculo, no la más cercana, y sin dividir entre el volumen de las casetas. Salen `std_afluencia_mensual` y `distance_to_station` |
  | Construcción de variables para el matching | Las 12 covariables con sus ventanas de tres años contadas desde el 22 de abril |
  | Estaciones de conteo permanente | El volumen de las casetas ya no se usa, ni como tasa ni como control: los efectos fijos de tiempo absorben el choque de movilidad. Hay que decir por qué |
  | Uso de la siniestralidad | Las 8 variables de media y desviación estándar pasan a 4, con la tendencia como variable explícita. Quitar la mención de tasas por cada 1,000 vehículos |
  | Soporte común y recorte | Los umbrales de score por radio se reemplazan por el caliper de 0.2 sd del logit más la intersección de los cinco radios: **93 de 99**. Las 6 que se caen son 2.2 veces más peligrosas |
  | Evaluación del balance | Las tablas de SMD nuevas, con las mismas 12 covariables en todos los radios. \|SMD\| medio después entre 0.045 y 0.065 |

  Y agregar lo que el capítulo viejo no tenía: el control pool sobre la red vial
  con separación de 600 m, el modelo por máxima verosimilitud con el método de Newton, sin penalización y sobre covariables estandarizadas —Newton es el estándar para la logística, el que usan por defecto R y Stata; el default de sklearn cambia hasta 18 de 99 pares—, el
  desempate por Mahalanobis, y la separación entre controles emparejados.

  Lo que hay que poder explicar del modelo viejo, ordenado por peso:

  1. **Los radios no eran comparables.** El grid se reconstruía en cada radio y el
     recorte usaba un umbral de score distinto por radio, así que cada columna
     estimaba el efecto sobre unidades distintas. Es el punto 1 de Alberto.
  2. **Ninguna covariable medía la tendencia previa.** El balance se revisaba sobre
     las 18, pero ninguna decía si la zona venía subiendo o bajando, que es la
     dimensión de la que depende el supuesto de tendencias paralelas. Con las
     definiciones viejas, el SMD de la tendencia queda en 0.216.
  3. **Pares de peor calidad:** sin caliper, y con la distancia en escala 0–1, que
     no discrimina cuando casi todos los scores están pegados a cero.
  4. **`LogisticRegression()` por default** penaliza y no converge sobre variables
     sin estandarizar; el score que produce correlaciona 0.38 con el correcto. Pesa
     poco: si el balance salía bien, los pares servían igual.

  **Lo que NO era un problema, y no hay que presentarlo como tal:** elegir un
  subconjunto de covariables por radio según el SMD. El SMD se calculaba sobre las
  18 variables, incluidas las que se quitaban del score (`calculate_smd` en
  `scripts/ps_matching.py`), así que la tabla no salía bien por construcción.
  Elegir la especificación del score por el balance que produce, revisado sobre
  todas las variables, es práctica estándar. En la versión nueva la lista es fija
  por otras razones —redundancia y ruido medidos—, no porque la anterior estuviera
  mal.

  **Pendiente de verificar antes de escribirlo:** la comparación de las 18
  covariables originales contra las 12 no está en el repo. Se corrió en un
  scratchpad y se perdió. Si se va a citar, hay que volver a correrla y guardarla.

- [ ] **5. Las tablas como las pidió Alberto.** Número de observaciones y R² por
      columna; orden tratamiento → interacción → efectos fijos al final; la suma
      `tratado + tratado:post` con su error estándar y sus estrellitas; el
      *control mean* con su desviación estándar en cada columna; puntos decimales
      y no comas; y una nota que explique modelo, muestra y unidades de forma que
      los coeficientes se interpreten sin volver al texto.

- [ ] **6. El estimando, dos párrafos.** Entran 99 unidades, se reportan 93. Las
      6 que se caen no encuentran control dentro del caliper porque no se parecen
      a ningún lugar sin cámara de la ciudad, y son **2.2 veces más peligrosas**
      que las que sí entran. El estimando es el ATT sobre las unidades tratadas
      con soporte común en las cinco escalas, y excluye los cruces más peligrosos.

- [ ] **7. La inferencia, un párrafo.** Los errores estándar del DiD después de
      matching no son válidos, y el sesgo puede ir en cualquier dirección. Por eso
      la discusión se apoya en la magnitud. Los números ya están: intervalo de
      [-6.2%, +1.7%] a 300 m, y el aumento aparente de lesionados a 100 m no
      sobrevive. Declarar también que el bootstrap no es formalmente válido para
      vecino más cercano (Abadie e Imbens, 2008) y que la intersección de los
      cinco radios no se remuestrea.

- [ ] **8. La discusión.** Magnitud en incidentes por círculo al mes y en
      porcentaje de la media del grupo de control; comparación contra los niveles
      pre y post del control; comparación contra los estudios mexicanos ya citados.

  **Una frase obligatoria sobre las tendencias previas.** En las figuras 3 y 3b, la
  pendiente previa de los controles es un poco mayor que la de las tratadas en
  los cinco radios (entre 0.4% y 1.6% de la media del control por año). Es chica,
  pero del mismo signo en todas las columnas y del mismo orden que el efecto
  estimado, y apunta en la dirección de una reducción aparente: si hubiera seguido
  después de 2019, por sí sola daría un DiD negativo. Refuerza el nulo en vez de
  contradecirlo. Redacción sugerida:

  > Las pendientes previas muestran una diferencia pequeña y del mismo signo en
  > los cinco radios: los controles venían creciendo ligeramente más rápido que
  > las unidades tratadas. Su magnitud es comparable a la de los efectos
  > estimados y su dirección es la de una reducción aparente, por lo que las
  > pequeñas reducciones puntuales a 250 y 300 metros no pueden distinguirse de
  > la continuación de esa diferencia previa.

- [ ] **9. Media cuartilla para Alberto** con lo que cambió además de lo que pidió:
      unidades fusionadas por traslape con grupos fijos a 300 m (que es su punto 1),
      covariables de 18 a 12 con la medición que lo respalda, y reparto de
      incidentes compartidos. Sin esto, los puntos 1–8 le llegan sin contexto.

---

## Pregunta pendiente para Alberto

El correo es ambiguo sobre el bootstrap: en 3a lo recomienda pero ofrece el 3b
como sustituto, y luego en el resumen dice "haz 3a" y deja el 3b a criterio.
Se resuelve con una línea:

> Sobre el punto 3a: el bootstrap del proceso completo sí es factible en mi caso
> porque las covariables están precalculadas. ¿Lo consideras imprescindible, o
> basta con declarar la limitación si no corro el 3b?

Una segunda, más chica, sobre qué covariables excluir del DiD:

> Dices que van todas las del propensity score menos la dependiente
> pre-tratamiento. `nivel_incidentes` y `tendencia` salen claramente.
> ¿`pct_lesionados` y `hubo_fcs` también, por venir de los mismos incidentes
> previos, o solo las dos primeras?

Mientras no responda, el plan aplica el criterio estricto —nada derivado del
outcome— y saca las cuatro: entran **8 covariables**, las 7 estructurales más
`afluencia_nivel`. La versión con 10, que solo saca `nivel_incidentes` y
`tendencia`, queda como sensibilidad de una línea en el notebook.

---

## Fuera de alcance, y por qué

| | Por qué |
| --- | --- |
| Sant'Anna y Zhao (3b) | *"Tú decide si quieres hacer 3b"*. Necesita R y es un estimador distinto |
| Event study (4) | *"y/o 4"*, explícitamente opcional. Se reconsideró al ver la diferencia de pendientes previas —es la herramienta que diría si es distinguible de cero— y se dejó fuera por alcance: basta con declararla |
| Regresiones en tasas | El denominador son casetas de peaje en la periferia: no mide exposición del círculo. Los efectos fijos de tiempo ya absorben el choque de movilidad. En su lugar, el efecto en % de la media del control |
| Robustez con las unidades de borde, un solo nivel vial, y otras semillas | Las dos robusteces que tocaban el diseño de unidades ya están cerradas |

---

## Nota: el reparto cercano no puede cambiar el resultado

Se corrió y salió **idéntico a ocho decimales** al reparto por pesos, con el
panel sí cambiando. La razón es exacta:

- **El coeficiente** no puede moverse porque los dos repartos conservan el total
  del grupo tratado en cada periodo, y el DiD con efectos fijos sobre un panel
  balanceado depende solo de esos totales.
- **El error estándar** tampoco, si se clusteriza por componente: la reasignación
  ocurre solo entre unidades que se traslapan, y esas están en el mismo cluster
  por construcción.

Comprobado: clusterizando por unidad, que separa a las unidades traslapadas, el
error estándar sí se mueve (0.18544 → 0.18664).

Hay que corregir la línea de `unit-design.ipynb` que dice *"si los resultados
aguantan, el reparto no estaba cargando nada"*. No es que aguanten: no pueden
cambiar. Es una afirmación más fuerte y hay que escribirla así.

---

## Nota: tres especificaciones que no pueden mover el coeficiente

En un panel balanceado con tratamiento simultáneo, todos los regresores se
factorizan en una parte de unidad por una parte de tiempo, y el regresor del
tratamiento solo distingue pre de post. Eso vuelve al coeficiente **invariante por
construcción** frente a tres elecciones:

| Cambio | Por qué no puede moverlo |
| --- | --- |
| Agregar efectos fijos de unidad y tiempo, (1) → (2) | El regresor residualizado vale ±0.25 por cuadrante y es ortogonal a las dummies |
| Reparto cercano en vez de pesos 1/k | Conserva el total del grupo tratado en cada periodo |
| Covariables × dummies de tiempo en vez de × post, (3) → (4) | Las interacciones extra varían *dentro* del pre y del post, que es ortogonal a un regresor que solo distingue pre de post |

Verificado en los datos: idénticos a cuatro decimales o más en todos los casos.

**Cómo redactarlo:** no como "el resultado es robusto a…", porque no hubo prueba
—el número no podía cambiar—. Sí como "es invariante por construcción, porque…".
Presentarlo como robustez es un error que un examinador que conozca el diseño va a
notar.

Lo que sí es una prueba de robustez con contenido: el trimming laxo, X = 50%, y
agregar las covariables de la (2) a la (3), que es la única que mueve el
coeficiente (−0.148 → −0.106).

---

## Números que ya tenemos, a 300 m

| Especificación | Pares | Coef | EE | p | % del control |
| --- | --- | --- | --- | --- | --- |
| Sin matching, 99 tratadas | 99 vs 631 | −0.525 | 0.150 | 0.001 | −8.3% |
| Sin matching, 93 tratadas | 93 vs 631 | −0.388 | 0.137 | 0.005 | −6.1% |
| Con matching, libre | 98 | −0.229 | 0.208 | 0.270 | −3.6% |
| **Con matching, muestra común** | **93** | **−0.148** | **0.198** | 0.457 | **−2.5%** |

Todas con efectos fijos de unidad y tiempo, clusterizadas por componente. Sin
las 8 covariables todavía: eso es el pendiente 1.

Las cuatro medias de la especificación principal: control 6.019 → 5.366,
tratadas 6.222 → 5.421.
