# Conclusiones

Transcripción de las 6 páginas manuscritas en `notas/fotos/Conclusiones-1.png` a `Conclusiones-6.png`. Se conserva la voz y la secuencia de los apuntes. Las figuras y tablas se enlazan a su foto original; sus rótulos principales también se transcriben. Todas salen de `scripts/resume-911/conclusiones.ipynb`.

Las correcciones posteriores a las notas se marcan así: el texto original ~~tachado~~ y la corrección **[en negritas y entre corchetes]**.

## Página 1 — Unidades excluidas y el inicio de la escalera

[Ver foto 1](<fotos/Conclusiones-1.png>)

### Sobre qué unidades podemos concluir

Estoy estimando el Average Treatment on the Treated (ATT) ~~porque no estoy estimando el efecto de todo el programa, esto se sigue del hecho que hago trimming sobre las unidades tratadas durante el matching para dejar afuera a todas las unidades que no encontraron un control comparable.~~ **[: el efecto sobre las zonas que recibieron cámara, no sobre cualquier zona de la ciudad. Además, el trimming lo restringe a las 93 unidades tratadas que encontraron un control comparable en los cinco radios.]**

Es importante mencionar esto porque de las 99 unidades tratadas, las 6 que se excluyen no son por azar, son de hecho las más peligrosas de toda la ciudad. Aunque pudo ser el caso que encontraran match para algún radio, se busca analizar las mismas unidades en todos, por lo que solo nos quedamos con la intersección.

[Figura: «Múltiplo del valor de las 93 tratadas analizadas (escala logarítmica)». Las 6 excluidas contra las 93 tratadas analizadas: tendencia previa 3.2×, afluencia del metro 3.0×, incidentes al mes 2.2×, al menos un incidente fatal 1.4×, vía de acceso controlado 1.4×, vía a desnivel 1.3×, carriles promedio 1.2×, proporción con lesionados 0.9×. Los 93 controles emparejados quedan cerca de 1. En la foto 1](<fotos/Conclusiones-1.png>).

Antes del programa de Fotocívicas, las 6 áreas excluidas tenían en promedio 2.2x más incidentes mensuales que las 93 analizadas y sus incidentes venían aumentando mucho más rápido, además de ser zonas con 3 veces más afluencia en el metro en comparación. Estructuralmente también son más grandes, con mayor desnivel y con más vías de acceso controlado.

Esto implica también que mis análisis y resultados no nos dicen nada sobre esas unidades, así que si el mayor efecto de las cámaras se da en zonas así, no puedo decir nada al respecto.

### Cómo cambia el resultado conforme aumentamos el rigor

El efecto estimado varía mucho conforme vamos siendo más estrictos con el modelo que utilizamos. Sigamos el caso a 300 metros con todos los incidentes, empezando por la versión más ingenua hasta que lleguemos a la especificación final.

**> Antes y después, solo en zonas tratadas**

Los incidentes bajan 0.94 al mes, 14% de su nivel previo. Con este comparativo podríamos decir que el programa fue todo un éxito, pero estaría obviando cualquier otro cambio tras 2019, incluyendo la pandemia.

## Página 2 — De la comparación contra la ciudad al emparejamiento

[Ver foto 2](<fotos/Conclusiones-2.png>)

**> Tratadas contra controles, solo después.**

Los incidentes aumentaron 67%. Claramente es un error de interpretación, lo que realmente nos está diciendo es que las cámaras están en zonas más peligrosas, así se hizo por construcción.

**> Diff in diff en toda la ciudad**

Si comparamos las 99 unidades tratadas contra los 631 controles sin overlap en toda la red vial, vemos que el efecto estimado es de una disminución de 0.53 incidentes mensuales, lo que equivale a un 13.7% menos con respecto a los controles antes del tratamiento, con un valor p de 0.001. Este cambio está alineado con los rangos que reporta la literatura internacional y es parecido ~~a los resultados que obtienen~~ **[al contrafactual que usan]** Madrigal y Rodríguez (2021) **[, que comparan contra los cruces de la red primaria sin cámaras]**. Agregar efectos fijos de tiempo y unidad no cambian el efecto estimado.

Si quitamos las 6 unidades que están en las zonas más peligrosas de la ciudad y nos quedamos solo con las 93 que sí terminan encontrando match, la reducción baja a 0.39 incidentes mensuales, 10.1% de la media de controles: una cuarta parte del efecto anterior venía solo de esas unidades.

**> Matching**

Cuando realmente comparamos zonas similares, queda claro que el efecto que veníamos observando era el resultado de comparar zonas tranquilas contra peligrosas. Con matching, la reducción observada es de 0.15 incidentes mensuales, lo que representa una disminución del 2.5% de la media de los controles previa al tratamiento (la media previa tras el matching es de 6.02 incidentes mensuales vs 3.84 sin el matching). El efecto también deja de ser significativo.

Cuando además permitimos que las zonas varíen distinto dependiendo de su estructura vial y niveles de afluencia de metro, es decir, agregamos covariables del propensity score interactuadas con post, vemos que el efecto queda en una disminución de 0.11 incidentes al mes, 1.8% de la media previa de control.

[Figura: «Efecto estimado, % del nivel previo de la comparación (IC 95%)». Antes y después, solo tratadas: −14.1%; DiD contra toda la ciudad: −13.7%; + solo las 93 con soporte común: −10.1%; + emparejamiento: −2.5%; + covariables × post: −1.8%, con el intervalo del bootstrap debajo. En la foto 2](<fotos/Conclusiones-2.png>).

## Página 3 — Bootstrap, literatura y efectos por tipo de incidente

[Ver foto 3](<fotos/Conclusiones-3.png>)

[Tabla de la escalera en la foto 3](<fotos/Conclusiones-3.png>):

| Paso | Comparación | Tratadas | Controles | Coef. | EE | Base | % | IC bajo % | IC alto % |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Antes y después, solo tratadas | 99 | 0 | −0.937 | 0.161 | 6.663 | −14.069 | −18.814 | −9.324 |
| 2 | Tratadas contra controles, solo después | 99 | 631 | 2.296 | 0.310 | 3.430 | 66.951 | 49.217 | 84.685 |
| 3 | DiD contra toda la ciudad | 99 | 631 | −0.525 | 0.165 | 3.842 | −13.674 | −22.072 | −5.276 |
| 4 | + efectos fijos de unidad y tiempo | 99 | 631 | −0.525 | 0.166 | 3.842 | −13.674 | −22.138 | −5.210 |
| 5 | + solo las 93 con soporte común | 93 | 631 | −0.388 | 0.154 | 3.842 | −10.110 | −17.957 | −2.263 |
| 6 | + emparejamiento | 93 | 93 | −0.148 | 0.198 | 6.019 | −2.452 | −8.902 | 3.998 |
| 7 | + covariables × post | 93 | 93 | −0.106 | 0.181 | 6.019 | −1.766 | −7.653 | 4.121 |

Aplicando bootstrap al modelo final, vemos que el intervalo de confianza va desde una reducción del 6% hasta un aumento del 2.2% contra la media de incidentes de los controles previa. Los datos son compatibles con que las cámaras no hayan tenido efecto y también con una reducción moderada, pero no con una grande.

Vale la pena destacar la posibilidad de una disminución de hasta el 6%, porque con un estimado de esa magnitud podríamos considerarla posible, más si vemos que la literatura internacional reporta disminuciones de entre 12% y 28% en incidentes con lesionados (Li et. al, 2013, 2020; Graham et al., 2019; Mountain et al., 2005), pero ellos analizan el efecto sobre el tramo inmediato posterior al radar, mientras que en este diseño se usan áreas circulares, diluyendo el efecto. ~~Con el intervalo que observamos, hubiera sido necesario ver cambios más grandes, incompatibles con nuestros datos.~~ **[Bajo el supuesto de tendencias paralelas, una reducción del tamaño que reporta esa literatura habría quedado dentro del intervalo, y los datos no la muestran.]**

### Efectos por tipo de incidente

Aún si vemos el efecto separado por tipo de incidente, las conclusiones se mantienen. En la especificación final, todos los intervalos de los cinco radios y los cuatro niveles de incidentes incluyen al cero.

[Figura: «Tratado × Post, % de la media previa del control (IC 95% bootstrap)», un panel por tipo de incidente (todos, MIN, PIC y FCS) con los cinco radios en el eje x. En la foto 3](<fotos/Conclusiones-3.png>).

- **Todos los incidentes:** el estimado puntual a 100 m es positivo y negativo en el resto de los radios. Ninguna reducción puntual supera el 2.6% que es a 250 m.
- **Sin lesionados:** La mayor reducción puntual es de 4% a 150 m y a partir de ahí se va diluyendo.

## Página 4 — Lesionados, fatales y la pandemia

[Ver foto 4](<fotos/Conclusiones-4.png>)

- **Con lesionados:** Parecería que el efecto va disminuyendo conforme aumenta el radio hasta 250 m, para luego volver a subir a 300 m.
- **Fatales:** En ~~toda la base~~ **[el panel emparejado a 300 m, 93 tratadas y 93 controles,]** hay 411 incidentes fatales~~ a 300 m~~, lo que representa 0.5% del total. Los intervalos de confianza van desde reducciones del 17% a 42% hasta aumentos del 37% a 56% según el radio. Con tan pocas observaciones es difícil concluir algo concreto sobre el efecto en muertes.

### La Pandemia

El 23 de marzo del 2020 entró en vigor la Jornada Nacional de Sana Distancia derivado de la pandemia por el coronavirus, la cual limitó la movilidad y forzó a modificar drásticamente el comportamiento en la calle.

El periodo post tratamiento incluye los dos primeros años de las restricciones de movilidad y lo podemos ver en los datos. Entre marzo y mayo de 2020 los incidentes por unidad cayeron de alrededor de 6 mensuales a tan solo 2.5, una caída por encima del 50% y recuperaron su nivel previo hasta finales del 2021. Esto también lo vemos en el volumen vehicular en las casetas en las periferias de la ciudad, cayendo un 46% en abril de 2020, alineado con lo que reportó la SEMOVI de una disminución del 45%.

Es un hecho que modificó los patrones de movilidad, pero es manejable cuando vemos que golpeó por igual tanto controles como tratadas. Además los efectos fijos de tiempo nos ayudan a absorber cualquier cambio que haya afectado a todas las unidades el mismo mes, así que la caída en 2020 no se confunde con el efecto de las cámaras.

El conteo vehicular de las casetas en la periferia de la ciudad queda fuera de los modelos en cuanto es la misma serie para toda la ciudad, el mismo número para todas las unidades en cada mes. Incluirla como denominador para calcular tasas de incidentes no aportaba tanto para la interpretación ni como control.

[Figura: arriba, incidentes por unidad al mes de tratadas y controles de 2016 a 2022, con la entrada de Fotocívicas marcada y el primer año de pandemia sombreado; abajo, volumen en casetas (media previa = 100). En la foto 4](<fotos/Conclusiones-4.png>).

## Página 5 — Efecto por año, tendencias paralelas y limitaciones

[Ver foto 5](<fotos/Conclusiones-5.png>)

Para revisar si el año de la pandemia está sesgando los resultados, separo en el modelo final la variable post en 3 intervalos de un año cada uno.

```text
incidentes ~ tratado:año1 + tratado:año2 + tratado:año3
             + [8 covariables]:año_i + C(uid) + C(t)
```

Los años van del 22 de abril al 21 de abril.

[Figura: «Tratado × año, % de la media previa del control (IC 95%)», un panel por tipo de incidente con los tres años: abr 2019–abr 2020, abr 2020–abr 2021 y abr 2021–abr 2022. En la foto 5](<fotos/Conclusiones-5.png>).

A 300 m, con todos los incidentes, las reducciones puntuales estimadas son de 4.4% el primer año, 1.2% el segundo y prácticamente cero el tercero. Ningún año puede distinguirse realmente de cero, además, el patrón decreciente en los estimados puntuales coincide con lo encontrado por Li et. al (2020): efectos que se diluyen con el tiempo.

Es cierto que la pandemia pudo haber afectado los resultados de otras maneras, especialmente al permitir que el tránsito fluyera a velocidades más altas precisamente por haber menos tráfico, tal como lo reporta la SEMOVI. El emparejamiento trata de mitigar este riesgo al incorporar variables estructurales, pero sin datos de afluencia vehicular dentro de la ciudad y velocidades de tránsito es complicado afirmarlo con mayor certeza.

### Tendencias Paralelas

[Anotación en rojo: «Tengo que entender bien cómo es que hizo esto.»]

Mejor dejarlo para la sección de resultados o supuestos.

### Limitaciones

Estimo el efecto local de una cámara, no el del programa y no puedo decir nada de las zonas más peligrosas de la ciudad, pues al no encontrar un control comparable, tuvieron que quedar excluidas.

~~Las tendencias previas no son exactamente paralelas, la diferencia es pequeña y...~~

## Página 6 — Limitaciones y conclusión

[Ver foto 6](<fotos/Conclusiones-6.png>)

~~...no significativa, pero es del mismo tamaño que el efecto estimado.~~ **[La prueba de tendencias previas tiene poca potencia. El event study no encuentra diferencias entre tratadas y controles antes del tratamiento, pero sus intervalos son de ±6% a ±8% por año: una diferencia de tendencias del tamaño del efecto estimado no se habría detectado.]**

Los errores estándar no son correctos por el diseño que seleccioné. El modelo de diferencias en diferencias toma como dados los pares que se construyeron durante el emparejamiento. El bootstrap de todo el proceso ayuda un poco a contrarrestar este efecto, pero por eso se prestó más atención en magnitudes sobre significancias.

No puedo observar la exposición vehicular ni velocidades de tránsito dentro de la ciudad.

### Conclusión

Con el diseño más riguroso que se pudo construir, no se identificó evidencia que muestre que ~~el programa~~ **[las cámaras]** de Fotocívicas ~~haya~~ **[hayan]** reducido el número de incidentes viales en su entorno. El efecto estimado a 300 metros es una reducción de 1.8% de la media previa de los controles, aunque los datos son compatibles con una reducción del 6% y un aumento del 2.2%. Cambiar el radio, estimar por severidad o ver por años separados no cambia la conclusión.

No se puede afirmar que las cámaras no hayan tenido efecto, pero **[, bajo el supuesto de tendencias paralelas,]** sí se vuelve razonable descartar efectos por encima del 10% como los que encuentra la literatura internacional o mi hipótesis inicial.

También se puede decir que comparar las zonas donde se colocaron los radares con el resto de la ciudad no es válido: por construcción son estructuralmente distintas, con niveles de incidentes más altos. Hacerlo puede llevar a sobreestimar el efecto real de las cámaras.

Estas conclusiones solo aplican a las 93 zonas analizadas y no a las 6 que se excluyeron.
