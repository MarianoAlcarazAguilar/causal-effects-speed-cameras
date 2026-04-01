# Formato para tabla de resultados

Esta es la plantilla de CSV que me serviría para convertir tus resultados en una tabla de LaTeX como la del ejemplo incluido en `Chapters/4.Results.tex`.

## Estructura recomendada

- Una fila por combinacion de `radio + outcome + especificacion + variable`.
- `outcome` debe tomar `total` o `rate`.
- `fixed_effects` debe tomar `no` o `yes`.
- `variable` debe tomar uno de estos cuatro valores: `Intersección`, `Tratamiento`, `Tiempo`, `Tratamiento x Tiempo`.
- En los modelos con efectos fijos solo necesitas incluir `Tratamiento x Tiempo`.
- `coef` debe ser el coeficiente correspondiente a esa variable.
- `se` debe ser el error estandar robusto que quieras reportar entre parentesis.
- `p_value` sirve para calcular las estrellas de significancia.
- `stars` puede dejarse vacio si prefieres que yo lo genere a partir de `p_value`.

## Plantilla CSV

```csv
radius_m,outcome,specification,fixed_effects,variable,coef,se,p_value,stars,n_obs,r_squared
50,total,sin_efectos_fijos,no,Intersección,,,,,,
50,total,sin_efectos_fijos,no,Tratamiento,,,,,,
50,total,sin_efectos_fijos,no,Tiempo,,,,,,
50,total,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
50,total,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
50,rate,sin_efectos_fijos,no,Intersección,,,,,,
50,rate,sin_efectos_fijos,no,Tratamiento,,,,,,
50,rate,sin_efectos_fijos,no,Tiempo,,,,,,
50,rate,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
50,rate,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
75,total,sin_efectos_fijos,no,Intersección,,,,,,
75,total,sin_efectos_fijos,no,Tratamiento,,,,,,
75,total,sin_efectos_fijos,no,Tiempo,,,,,,
75,total,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
75,total,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
75,rate,sin_efectos_fijos,no,Intersección,,,,,,
75,rate,sin_efectos_fijos,no,Tratamiento,,,,,,
75,rate,sin_efectos_fijos,no,Tiempo,,,,,,
75,rate,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
75,rate,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
100,total,sin_efectos_fijos,no,Intersección,,,,,,
100,total,sin_efectos_fijos,no,Tratamiento,,,,,,
100,total,sin_efectos_fijos,no,Tiempo,,,,,,
100,total,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
100,total,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
100,rate,sin_efectos_fijos,no,Intersección,,,,,,
100,rate,sin_efectos_fijos,no,Tratamiento,,,,,,
100,rate,sin_efectos_fijos,no,Tiempo,,,,,,
100,rate,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
100,rate,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
150,total,sin_efectos_fijos,no,Intersección,,,,,,
150,total,sin_efectos_fijos,no,Tratamiento,,,,,,
150,total,sin_efectos_fijos,no,Tiempo,,,,,,
150,total,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
150,total,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
150,rate,sin_efectos_fijos,no,Intersección,,,,,,
150,rate,sin_efectos_fijos,no,Tratamiento,,,,,,
150,rate,sin_efectos_fijos,no,Tiempo,,,,,,
150,rate,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
150,rate,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
200,total,sin_efectos_fijos,no,Intersección,,,,,,
200,total,sin_efectos_fijos,no,Tratamiento,,,,,,
200,total,sin_efectos_fijos,no,Tiempo,,,,,,
200,total,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
200,total,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
200,rate,sin_efectos_fijos,no,Intersección,,,,,,
200,rate,sin_efectos_fijos,no,Tratamiento,,,,,,
200,rate,sin_efectos_fijos,no,Tiempo,,,,,,
200,rate,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
200,rate,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
250,total,sin_efectos_fijos,no,Intersección,,,,,,
250,total,sin_efectos_fijos,no,Tratamiento,,,,,,
250,total,sin_efectos_fijos,no,Tiempo,,,,,,
250,total,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
250,total,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
250,rate,sin_efectos_fijos,no,Intersección,,,,,,
250,rate,sin_efectos_fijos,no,Tratamiento,,,,,,
250,rate,sin_efectos_fijos,no,Tiempo,,,,,,
250,rate,sin_efectos_fijos,no,Tratamiento x Tiempo,,,,,,
250,rate,con_efectos_fijos,yes,Tratamiento x Tiempo,,,,,,
```

## Ejemplo de una fila llena

```csv
50,total,sin_efectos_fijos,no,Tiempo,-0.081,0.034,0.019,**,4320,0.214
```

## Regla para estrellas

- `***` si `p_value < 0.01`
- `**` si `p_value < 0.05`
- `*` si `p_value < 0.10`
- vacio en otro caso

## Resultado esperado en LaTeX

Con este formato puedo acomodar automaticamente los resultados en una tabla con:

- columnas por radio,
- paneles separados para `Total de accidentes` y `Tasa de accidentes`,
- distincion entre modelos `Sin EF` y `Con EF`,
- filas para `Intersección`, `Tratamiento`, `Tiempo` y `Tratamiento x Tiempo` cuando no hay efectos fijos,
- una sola fila para `Tratamiento x Tiempo` cuando si hay efectos fijos,
- coeficiente en la primera linea,
- error estandar en la segunda linea,
- y nota al pie con la convencion de significancia.
