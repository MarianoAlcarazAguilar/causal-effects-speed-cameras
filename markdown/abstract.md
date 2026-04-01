# Abstract

## Resumen

Esta tesis analiza el efecto causal de las cámaras de velocidad sobre los incidentes viales en la Ciudad de México a partir de la transición de Fotomultas a Fotocívicas en abril de 2019. El objetivo es evaluar si este cambio redujo los accidentes, en particular aquellos con víctimas mortales. Para ello, se estudia la Ciudad de México en una ventana de tres años antes y tres años después de la implementación del programa, utilizando datos de incidentes del C5, información sobre la ubicación de las cámaras de velocidad de la Secretaría de Seguridad Ciudadana y proxies de movilidad, como los conteos de radares permanentes y la afluencia en el Metro. La estrategia empírica se basa en un modelo de diferencias en diferencias, complementado con propensity score matching para construir un grupo de control comparable a las unidades tratadas. El análisis se realiza en áreas circulares de distintos radios, desde 37.5 hasta 250 metros, en línea con la literatura que sugiere que los efectos de este tipo de intervenciones son altamente locales. Los resultados no muestran evidencia de un efecto causal de las cámaras de velocidad ni sobre el número ni sobre las tasas de incidentes viales en ninguno de los radios analizados. Aunque la variable de tiempo resulta significativa de forma sistemática, lo que sugiere una disminución generalizada de accidentes tras la implementación del programa, esta reducción no puede atribuirse a la presencia de los radares. La tesis aporta una definición espacial más congruente con la literatura, un contrafactual más sólido y controles de exposición asociados a cambios de movilidad antes y después de la pandemia. En términos de política pública, los hallazgos sugieren que este tipo de medidas, al menos en su implementación observada, debe complementarse con estrategias de educación vial y cambios en la infraestructura urbana que promuevan una movilidad más segura.

## Abstract 

This thesis analyzes the causal effect of speed cameras on traffic incidents in Mexico City following the transition from *Fotomultas* to *Fotocívicas* in April 2019. The main objective is to evaluate whether this change reduced crashes, particularly those involving fatalities. To do so, the study examines Mexico City over a three-year window before and a three-year window after the program's implementation, using traffic incident data from the C5, information on the location of speed cameras from the Secretariat of Citizen Security (SSC), and mobility proxies such as counts from permanent traffic counters and Metro ridership data. The empirical strategy is based on a difference-in-differences model, complemented by propensity score matching to construct a control group comparable to the treated units. The analysis is conducted within circular areas of different radii, ranging from 37.5 to 250 meters, in line with the literature suggesting that the effects of this type of intervention are highly localized. The results show no evidence of a causal effect of speed cameras on either the number or the rates of traffic incidents at any of the radii analyzed. Although the time variable is systematically significant, suggesting a general decline in crashes after the program's implementation, this reduction cannot be attributed to the presence of the cameras. This thesis contributes a spatial definition more consistent with the literature, a stronger counterfactual, and exposure controls associated with changes in mobility before and after the pandemic. In terms of public policy, the findings suggest that this type of measure, at least as implemented in practice, should be complemented with road safety education strategies and changes in urban infrastructure that promote safer mobility.

## Notes

- Tema general y contexto del problema:
    Estoy analizando el efecto causal de las cámaras de velocidad sobre los incidentes viales en la Ciudad de México a raíz del cambio que hubo del programa de Fotomultas al programa de Fotocívicas, que trajo consigo un reacomodo de los radares de velocidad a zonas con mayor siniestralidad en la ciudad y un cambio de enfoque, pasando de un programa con fines recaudatorios a uno con fines cívicos, buscando un cambio en las conductas de manejo.
- Pregunta de investigacion u objetivo principal:
    Quiro evaluar si dicho cambio tuvo el efecto esperado en accidentes, pensando en encontrar una posible disminución de accidentes, en especial en aquellos con víctimas mortales.
- Caso de estudio / ambito geografico / periodo analizado:
    Solo analizo el impacto en la Ciudad de México, en una ventana de 3 años antes y 3 años después a partir de la implementación del programa en abril del 2019
- Datos utilizados:
    Utilizo datos de diferentes fuentes con diferentes objetivos.
    - accidentes: datos del C5
    - cámaras de velocidad: datos de la secretaría de seguridad ciudadana
    - utilizo además proxies de movilidad como lo son los conteos de los radares permanentes de la ciudad de méxico, y los datos de alfuencia en el metro de la ciudad
- Metodologia o estrategia empirica:
    El método que utilizo para estimar el efecto es diferencia en diferencias. Utilizo propensity score matching para crear un grupo de control que sea comparable a las unidades tratadas. Hago el análisis en áreas circulares de distintos radios, que van desde 37.5 metros hasta 250 metros de radio.
- Principal hallazgo 1:
    No encuentro evidencia de que las cámaras de velocidad hayan tenido un efecto causal en el número ni en tasas de incidentes viales, en ninguno de los radios analizados.
- Principal hallazgo 2 (si aplica):
    La variable del tiempo resulta ser significativa en todos los casos, indicando que hubo una disminución generalizada de accidentes tras la implementación del programa, pero no atribuible a los radares de velocidad.
- Magnitud o direccion del efecto estimado:
    No aplica, no lo hubo
- Contribucion de la tesis:
    Ya se habían realizado análisis en la ciudad de méxico, pero habían quedado huecos que trato de resolver en esta ocasión. Mis aportaciones se encuentran en cada una de las siguientes esferas: 
        - escala espacial: construyo unidades de análisis congruentes con la literatura, que ha mostrado que el efecto de los radares de velocidad es local, y no generalizado, en una vecindad del radar
        -  contrafactual: construyo un grupo de control utilizando propensity score, controlando por variables estructurales y de siniestralidad para poder tener un punto de referencia válido en la comparación
        - exposición: la implementación de los radares de velocidad fue meses antes de que la pandemia por el coronavirus modificara drásticamente nuestros patrones de movilidad. Agrego controles y proxies que permiten tener más control sobre el impacto que esto pudo haber tenido.
- Implicacion de politica publica / relevancia practica:
    Vale la pena resaltar que a pesar de que el objetivo último del sistema de Fotocívicas era migrar de multas económicas a cívicas, en la práctica esto no fue así, pues la mayor parte de las multas seguían siendo económicas, ya que solo se aplican sanciones cívicas a placas de la cdmx, valdría la pena evaluar si esto valió realemnte la pena, porque no tuvieron un impacto en accidentes. Quizá hizo falta acompañar esta medida con algún tipo de educación adicional, o pensar en mejorar no solo las medidas coercitivas que promuevan un manejo más controlado, sino que la estructura vial misma lo promueva, y pensar en cambiar de una estructura que facilita el tránsito a altas velocidades, a una que promueva el uso de otros medios de transporte y tener una mejor educación vial
- Palabras clave:
    Diff-in-Diff
    Propensity Score Match
    Speed cameras
    Area analysis
    Fotocívicas
