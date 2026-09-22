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
- [x] Caracterización de las 6 unidades que el trimming descarta: ~13.5
      incidentes/mes contra 6.22 las que se quedan

---

## Falta correr — cuatro cosas

- [ ] **1. La especificación principal, en los cinco radios.** Tres columnas,
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

- [ ] **2. Los cinco radios con trimming laxo** (96 / 98 / 99 / 97 / 98 pares).
      Mismo script, cambiando `tratadas_validas`. Va al apéndice.

- [ ] **3. Una columna con las covariables × dummies de tiempo**, solo a 300 m.
      Es el cuarto punto de la lista de Alberto. No va como principal: son 568
      parámetros contra 165 clusters.

- [ ] **4. Bootstrap del proceso completo, solo a 300 m.**
      500 repeticiones. Remuestrear unidades, reajustar la logística, rehacer el
      emparejamiento, reestimar. Las covariables están precalculadas, así que no
      hay que rehacer los cruces espaciales: son segundos por repetición.
      Reporta una sola cosa, el intervalo de confianza del coeficiente principal.

---

## Falta escribir — cuatro cosas

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
      la discusión se apoya en la magnitud. Reportar el intervalo del bootstrap.

- [ ] **8. La discusión.** Magnitud en incidentes por círculo al mes y en
      porcentaje de la media del grupo de control; comparación contra los niveles
      pre y post del control; comparación contra los estudios mexicanos ya citados.

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

Mientras no responda, el plan asume que salen solo `nivel_incidentes` y
`tendencia`, y entran 8 covariables.

---

## Fuera de alcance, y por qué

| | Por qué |
| --- | --- |
| Sant'Anna y Zhao (3b) | *"Tú decide si quieres hacer 3b"*. Necesita R y es un estimador distinto |
| Event study (4) | *"y/o 4"*, explícitamente opcional |
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
