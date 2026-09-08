fuera de muestra walk-forward, partición fijada 2026-09-07.

# ¿Las opciones mejoran el pronóstico de volatilidad intradía?

Sí para el estado de opciones; para el flujo, la respuesta depende del horizonte,
la familia y el estadístico. La regla de cierre de RP4 se cumplió en RV15 con la
familia lineal. El programa científico termina en v4, sin una v5.

## Pregunta y prueba

Se pronostica la variación realizada de AAPL, AMZN, META, MSFT, NVDA y TSLA con
barras de un minuto y operaciones de opciones. Los tres conjuntos son anidados:
B0 usa precios e historia de volatilidad; B1 añade estado y superficie de opciones;
B2 añade composición, actividad y desbalance firmado del flujo. En v3/v4 tienen
29, 69 y 138 predictores, respectivamente, más los efectos de activo y los
indicadores de presencia que corresponden a cada familia.

El desarrollo abarca 2024-08-02–2026-07-31. La partición de calendario es
2026-08-01, fijada el 2026-09-07. Cada sesión se predice con entrenamiento
expansivo exclusivamente anterior, después de 60 sesiones de calentamiento,
con selección en las últimas diez sesiones de entrenamiento y purga/embargo de
60 minutos. La primaria v2–v4 tiene 419 sesiones y 160.832 orígenes; la ventana
denominada confirmación, 2026-08-03–2026-09-04, tiene 25 sesiones y 9.750 orígenes.

Se comparan una familia lineal y LightGBM. En v3/v4 la lineal es un **modelo
lineal winsorizado con filtro de rango (ridge nominal)**. La pérdida QLIKE mide
error de pronóstico, no rentabilidad. En v3/v4, H1 prueba B1 sobre B0 al 5 %
unilateral; sólo si rechaza se prueba H2, B2 sobre B1, también al 5 %. La regla
de cierre exige la secuencia en al menos una familia, no en ambas. El bootstrap
usa bloques de cinco sesiones; los p no corrigen la búsqueda entre versiones.

## Resultado primario de cada versión

Cada celda muestra **reducción porcentual de QLIKE (p)**. Un signo negativo
significa empeoramiento. En v1/v2, p es bilateral con Holm; en v3/v4 es unilateral
secuencial. Por tanto, los p de distintas versiones no son intercambiables.

| Versión / objetivo | Lineal B1/B0 | Lineal B2/B1 | Árboles B1/B0 | Árboles B2/B1 | Sesiones |
| --- | ---: | ---: | ---: | ---: | ---: |
| v1 · RV30 | +0,290 % (1,000) | −167.448,32 % (1,000) | +1,204 % (0,4724) | −0,073 % (1,000) | 418 |
| v2 · RV30 | +1,715 % (0,1842) | −8,714 % (0,3752) | +2,091 % (0,0264) | −0,063 % (0,8858) | 419 |
| v3 · RV30 | +1,729 % (0,0439) | +0,554 % (0,0525) | +2,091 % (0,0053) | −0,159 % (0,6631) | 419 |
| v4 · RV15, primario | +0,880 % (0,0390) | +0,623 % (0,0032) | +1,170 % (0,0135) | −0,115 % (0,6280) | 419 |
| v4 · RV5, secundario | +0,377 % (0,0092) | +0,256 % (0,0172) | +0,536 % (0,0608) | +0,160 % (no abierta; nominal 0,1927) | 419 |

v1 conserva su fallo numérico adverso y sus 92.261 orígenes. Las versiones
cambian cobertura y especificación; esta tabla no es una comparación controlada
que aísle el efecto de cada corrección. [v1](results_v1.md), [v2](results_v2.md),
[v3](results_v3.md) y [v4 con intervalos, N y ambas ventanas](results_v4.md)
conservan todos los signos.

## Conclusión en tres frases

El estado y la superficie de opciones mejoran el pronóstico medio de RV30 y RV15
en ambas familias bajo las pruebas registradas de v3/v4, sin que ello signifique
mejora en todos los meses ni confirmación independiente en las 25 sesiones finales.
El flujo añade una mejora pequeña en la familia lineal a 15 minutos (+0,623 %,
IC95 % de la diferencia QLIKE [0,000335; 0,001932]) y a 5 minutos (+0,256 %,
secundario): es positiva en los tres bloques de ambos horizontes y en los seis
activos a 15 minutos, **pero sólo en tres de los seis a 5 minutos**.
En árboles, B2 no supera la prueba de la media; la mediana pareada es positiva
a 15 y 5 minutos, con p bilateral 0,0435/0,0038 y Holm 0,0870/0,0096, un
secundario que no sustituye la prueba primaria.

## Qué explica el resultado y qué no

La composición del flujo tiene mayor peso en la representación lineal que las
exposiciones gamma: en RV15, las tres shares de prima tienen coeficientes medios
absolutos de 0,250–0,312, frente a 0,00489 para desbalance gamma total; el conteo
de operaciones con dirección identificada tiene pendiente media −0,04271; cuenta
operaciones, no su saldo firmado. Esto no identifica una contribución causal
ni reemplaza una ablación: el mecanismo de cobertura de dealers no queda probado.
[Coeficientes por columna y horizonte](../../artifacts/rp4_closeout_audit/b2_coefficient_summary.csv).
Los perfiles intradía, meses y tamaños de entrenamiento son descriptivos: se
distingue la primera hora de mercado del primer tramo observable, y el bloque
registrado `origin_minute >= 300` de la última hora real, `>= 330`.

Las interrupciones de publicación del proveedor de 2025-05-15 y 2025-09-18
son hallazgos del instrumento. La regla v3 conserva actividad cero, vuelve
indefinidas las formas/ratios sin operaciones y añade indicadores; acota el daño
sin eliminarlo. Quedan 412 ventanas vacías de cinco minutos en la primaria y
ninguna en confirmación. No se excluyen para mejorar el resultado.
En esas filas, el QLIKE lineal pasa de 0,103 en B1 a 0,202 en B2 con igual peso
por sesión/activo; la reparación limita el daño, no lo elimina.

Existe una ruptura de estructura de mercado documentada: Nasdaq anunció el
inicio de vencimientos de lunes y miércoles para estos nombres el **2026-01-26**.
La cinta verifica esa primera presencia en los seis activos; el salto de celdas
se observa el 29 de enero y los primeros lunes/miércoles 0DTE el 2/4 de febrero.
La cobertura media por origen pasa de 20,04 a 23,10 celdas antes/después del 26.
La confirmación está enteramente en el régimen nuevo, con entrenamiento en gran
parte del anterior: no es una réplica bajo una estructura de mercado estable.
[Aviso de Nasdaq del 16 de enero](https://www.nasdaqtrader.com/MicroNews.aspx?id=OTA2026-2)
y [censo diario y cobertura por día de semana](../../artifacts/rp4_market_audit/REPORT.md).

La penalización lineal se aplica a suma de errores, sin dividirla por N; la rejilla
es poco restrictiva en muestras grandes y no garantiza estabilidad de coeficientes
correlacionados. B2 eligió lambda 0,0001 en 111/419 sesiones; las podas fueron
88–97 columnas, incluidas presencias, no 88 constantes. Las cotas superiores tocaron 223/324/302 pronósticos RV15 de
B0/B1/B2: más contactos en conjuntos ricos no prueban por sí solos la dirección
del sesgo. Cambiar la escala de penalización, adaptar la rejilla al ciclo de
vencimientos y distinguir indisponibilidad del proveedor de actividad nula quedan
como trabajo futuro, sin reejecutar esta prueba.

El tramo octubre de 2024–febrero de 2025 contiene 64 sesiones evaluadas (15,27 %),
no 84: la ganancia temprana de B1 lineal RV15 es negativa. El tiempo de aprendizaje
y el régimen de mercado cambian juntos; no se identifica por separado que ampliar
el calentamiento causaría una ventaja mayor. Se conservan los meses negativos.
Los [perfiles por mes y tercil de entrenamiento](../../artifacts/rp4_closeout_audit/descriptive_profiles.csv)
incluyen octubre/noviembre de 2025, negativos para B2 lineal tanto en RV30 como
en RV15. La [auditoría descriptiva](../../artifacts/rp4_closeout_audit/REPORT.md)
separa también los 288 orígenes de la primera hora **observable** de la semana
arancelaria (0,18 % de la muestra, contraste B2 de árboles −0,3221 por origen)
de la primera hora de mercado, que tiene otro denominador. No se excluye ninguno.

Los movimientos extremos de AMZN (31 de agosto, −152/+71 puntos básicos desde
las 14:00 ET; volumen siguiente 11 veces la mediana) y TSLA (17 de agosto) se
reprodujeron en barras de un minuto y volumen. Es consistencia interna de FMP,
no validación independiente del precio; la causa no está identificada.

El secundario de saltos final usa 419 sesiones, no el cierre parcial de 418;
su etiqueta `jump30 > 0` no es un test de salto significativo. Sus AUC cercanas a
0,52 no demuestran ausencia de información sobre saltos económicamente importantes.
La recalibración MZ permanece NO VERIFICABLE como resultado útil; no afecta la
primaria. [Cierre corregido de secundarios](results_v3_revision2.md).

## Cuatro divulgaciones

Esta es la cuarta evaluación de las mismas ventanas: v1 inicial; v2 corrige
cobertura/capacidad/estabilidad; v3 añade desbalance y regla de ventanas vacías;
v4 cambia el horizonte mediante un antecedente condicional predeclarado. RV5 es
secundario, no una réplica adicional; la búsqueda entre versiones no está corregida.

La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8
con otra especificación. El PIT es proxy de tiempo fuente a 120 s, como en la
literatura; no prueba la disponibilidad histórica al cliente.

El hueco UW 2025-01-25–2025-02-24 se acepta y se declara, sin relleno.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
