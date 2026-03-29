# Tendencias paralelas

En esta sección responderé al segundo comentario de mi profesor sobre la tesis. Dado que la estrategia empírica que estoy utilizando es una diferencia en diferencias, necesito explicitar con mayor claridad los supuestos que sostienen la interpretación causal de los resultados.

El supuesto que todavía debo desarrollar es el de tendencias paralelas. Este supuesto no puede demostrarse de manera directa, porque no es posible observar qué habría ocurrido en ausencia de la instalación de las cámaras. Sin embargo, sí puedo presentar evidencia indirecta que haga más plausible su cumplimiento y, al mismo tiempo, señalar con transparencia sus limitaciones.

Para ello, las tareas que necesito completar son las siguientes:

1. Prueba placebo
   Debo trabajar únicamente con información previa a la implementación del programa de Fotocívicas y definir una fecha ficticia de intervención. Con esa fecha artificial, estimaré nuevamente el modelo como si el tratamiento hubiera ocurrido antes. La tarea central consiste en verificar que el coeficiente asociado al periodo "postratamiento" placebo sea estadísticamente indistinguible de cero. Si encuentro un efecto significativo antes de la intervención real, eso debilitaría la plausibilidad del supuesto de tendencias paralelas.

2. Pruebas visuales con y sin propensity score matching
   Debo comparar gráficamente la evolución de las unidades tratadas y de control antes de la intervención, tanto en la muestra sin emparejamiento como en la muestra emparejada mediante propensity score matching. Para poder hacerlo bien, primero tengo que revisar cómo estoy construyendo las unidades de control artificiales, porque su definición puede introducir arbitrariedad. En particular, necesito establecer criterios mínimos de depuración para evitar traslapes entre unidades de control cuando se considera todo el grid y para excluir unidades que no pertenezcan a una vialidad principal. Después, debo organizar la estimación de los distintos modelos de manera replicable, de modo que la comparación entre especificaciones sea clara y sistemática. El objetivo final de esta parte es evaluar si el propensity score matching mejora, empeora o no modifica la similitud de las tendencias previas al tratamiento.
