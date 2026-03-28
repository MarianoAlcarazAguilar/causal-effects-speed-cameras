# El efecto de las fotoinfracciones en la Ciudad de México

> Madrigal Montes de Oca, A., Rodríguez, A. (2021). El efecto de las fotoinfracciones en la Ciudad de México. *Revista Espacialidades UAM*, 11(1), 83-97.

Análisis del efecto de las fotoinfracciones en la Ciudad de México, tanto del programa de Fotomultas como del de Fotocívicas. 

### Notas
- Utiliza datos del C5 desde el 2014 hasta el 2020
- Análisis descriptivo 
    - En la primera parte del trabajo, se contaron los incidentes viales ocurridos en las *inmediaciones* de las cámaras de fotomultas y de fotocívicas un año antes y uno después de la implementación de cada una. Estiman la variación porcentual alrededor de los dispositivos. 
    - La contabilización de incidentes se hacen en bandas sobre las vialidades en las que están ubicadas las cámaras de velocidad. Estas bandas aumentan en múltiplos de 50 antes y después hasta llegar a los 500 metros en total (antes y después, lo que implica que el máximo evaluado es de 1km lineal con la cámara en el medio)
    - Este análisis de bandas crecientes cada 50 metros solo se utiliza de manera descriptiva. Para el análisis de diff in diff solo evalúan el impacto que tienen en bandas de 300 metros antes y después de cada radar. 
- Método de inferencia: diff in diff.
    - Unidades de control: "Áreas aledañas a los cruces de vialidades primarias [...] que no contaban con cámaras. [...] Se decidió utilizar los cruces de vías primaras sin dispositivos como el grupo control, debido a que es en este tipo de vialidades donde se colocan las cámaras; sin embargo, existen otras formas de establecer la contrparte con la que se compara el grupo de tratamiento". Hasta ahí llega su justificación. Claramente es muy deficiente.
    - Unidades de tratamiento: bandas sobre las vialidades que tienen un radar de velocidad de 300 metros antes y después de cada cámara. No hay explicación detrás de esta decisión.
    - Ventana temporal: evaluaciones mensuales. Para fotomultas usan desde septiembre del 2014 hasta agosto del 2017, considerando que el tratamiento empezó en diciembre del 2015. Para Fotocívicas se analiza desde enero del 2018 hasta diciembre del 2020, considerando que el tratamiento empezó en abril del 2019. En total, para cada programa, consideran 15 meses antes y 21 meses después, respectivamente.
    - Controles empleados: ninguno
    - Pruebas de robustez: ninguna 
- Consideraciones importantes:
    - Asume que no hay cambios en la movilidad, pero toma meses en los que hubo un lockdown por la pandemia de Covid 19 para el análisis de las Fotocívicas. No demuestra que esto no tuvo impacto.
- Resultados: 
    - Fotomultas: el único impacto estadísticamente significativo es en hechos fatales donde encuentra un aumento de casi el 50% en el número total de incidencias. No encuentra significancia estadísitca en hechos totales o con lesionados. La variable del tiempo es signficativa en los tres casos (total, lesionados y fatales) y negativa, pero no es atribuible a los radares de velocidad.
    - Fotocívicas: solo encuentra singificancia estadística al 10% en hechos fatales con una dismunición también aproximada del 46%. En sus palabras: "el programa no mostró efecto de reducción sobre los hechos de tránsito generales, pero sí lo hizo en los casos de siniestros con personas lesionadas y fallecidas, a pesar de la tendencia al alza de estos últimos". Realmente no discuten porcentajes en sus resultados, solo descripciones. 