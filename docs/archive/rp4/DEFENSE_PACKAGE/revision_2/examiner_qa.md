# Preguntas de examen — evidencia, objeciones y alcance

Las respuestas distinguen resultado primario, diagnóstico descriptivo y prueba prospectiva todavía sin resultado. «Mejor» significa menor pérdida QLIKE con la muestra, ponderación, horizonte y familia indicados. Las tablas conservadas permiten revisar también los signos adversos. Los números de pregunta son referencias editoriales, no resultados.

## 1. ¿Cuál es exactamente la afirmación que defiende este trabajo?

El estado y la superficie de opciones añaden capacidad predictiva media respecto de precios e historia de volatilidad en ambas familias a RV30 y RV15, bajo las pruebas de v3/v4. El flujo añade una mejora más pequeña en la familia lineal a RV15: reducción de QLIKE de +0.6227941 %, delta +0.0011337597 e intervalo del 95 % [0.00033503697, 0.0019321616], con p unilateral 0.0032 después de superar H1. A RV5 la secuencia lineal también rechaza, pero ese horizonte es secundario. En árboles, la media no confirma el incremento de B2.

La afirmación defendible es una jerarquía predictiva condicionada por familia y horizonte. No comprende todos los meses, otros activos, recepción histórica por el cliente, causalidad del mecanismo ni rentabilidad. La ventana final tampoco confirma la secuencia completa.

Fuentes: [comparación primaria y confirmación](../../../../rp4/results_v4.md), [estadísticas y decisiones guardadas](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [resultado final](../../../../rp4/RESULTADO_FINAL.md).

## 2. ¿Por qué hubo cuatro versiones? ¿Se siguió cambiando el estudio hasta obtener significación?

Hubo adaptación y debe decirse expresamente. V1 conserva el diseño inicial y su fallo numérico; v2 cambia cobertura, capacidad y estabilidad; v3 incorpora desbalance y tratamiento de ventanas vacías; v4 cambia el horizonte del objetivo mediante un antecedente condicional local. La última especificación conserva predictores, claves elegibles y reglas de entrenamiento de v3, pero eso no convierte el recorrido completo en una búsqueda libre de adaptación.

Las mismas ventanas fueron evaluadas sucesivamente. Los p de v1/v2 son bilaterales con Holm y los de v3/v4 pertenecen a la secuencia unilateral: no son intercambiables. La búsqueda entre versiones no está corregida y el antecedente local no tiene sello temporal independiente. Conservar todos los resultados permite auditar la evolución; no elimina el sesgo de selección del programa. La réplica prospectiva es la oportunidad de contrastar una regla fijada antes de su nueva muestra.

Fuentes: [tabla completa por versión](../../../../rp4/RESULTADO_FINAL.md), [datos agregados de la comparación](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv), [antecedente y alcance de v4](../../../../rp4/specification_v4.md), [registro prospectivo](../../../../rp4/prospective_confirmation_v1.md), [enmienda vigente](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

## 3. ¿Por qué basta «al menos una familia»? ¿El estudio tiene un error global del 5 %?

La regla de cierre declarada permite concluir que existe un incremento detectado dentro de una de las familias consideradas. H1 contrasta B1 frente a B0; sólo si rechaza se abre H2, B2 frente a B1, con umbral unilateral del 5 % y estimación positiva. Esa secuencia evita abrir H2 cuando no se ha establecido la mejora anterior en la misma familia.

«Al menos una familia» es una regla operativa de cierre, no una corrección entre familias. La especificación declara expresamente que no proporciona control global del 5 % entre familias ni entre versiones. Por ello el resultado se atribuye a la familia lineal y no se presenta como confirmación universal. La nueva réplica fija de antemano la decisión primaria en la familia lineal a RV15, sin permitir escoger después otra familia.

Fuentes: [regla de cierre y límites](../../../../rp4/specification_v4.md), [decisiones primarias](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [decisión prospectiva](../../../../rp4/prospective_confirmation_v1.md), [enmienda vigente](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

## 4. ¿Por qué los árboles no confirman B2 si una parte de sus diagnósticos es favorable?

Porque el estadístico primario es la media de diferencias de pérdida. En RV15, árboles B2/B1 tiene delta −0.00021290307, intervalo [−0.0020441248, 0.0011041695] y p unilateral 0.628. H1 sí abre H2, pero H2 no rechaza. En RV5, H1 tiene p 0.0608 y H2 permanece cerrada: su p nominal 0.1927 es diagnóstico, aunque la estimación de B2/B1 sea positiva.

Los secundarios favorables no sustituyen esas decisiones. Tampoco se concluye que el flujo carezca de información para cualquier árbol, configuración o población: el no rechazo delimita la evidencia de esta prueba. No es una prueba de equivalencia entre B1 y B2 ni de absorción causal del flujo por la superficie.

Dos sesiones ilustran la heterogeneidad, en ventanas distintas y sin excluirlas del cálculo:

- El 2025-04-07 pertenece a la primaria. Las medias de cobertura por activo están alrededor de 20 celdas por origen y la presencia de la celda de opciones cerca del precio y vencimiento inmediato (ATM) es 0 %, con 65 orígenes por activo. El delta RV15 B2/B1 de la sesión es −0.344417 en árboles y +0.011539 en la familia lineal.
- El 2026-08-31 pertenece a la ventana final. Las medias de cobertura por activo van de 20.4 a 24.0 celdas por origen, redondeadas a un decimal, con presencia ATM del 100 % y 65 orígenes por activo. En AMZN, la barra de las 14:00 de Nueva York tiene retorno logarítmico −151.7 puntos básicos y la siguiente +71.3; sus volúmenes son 3.0 y 11.1 veces la mediana de la sesión, respectivamente. El delta RV15 B2/B1 de la sesión agregada es +0.116 lineal y −0.080 en árboles, redondeados a tres decimales.

Los deltas tienen igual ponderación de activos dentro de la sesión; los deltas de agosto no son el efecto exclusivo de AMZN. El rango de celdas compara medias por activo, no mínimos y máximos de cada origen. La celda ATM aquí tiene la definición del censo de cobertura: moneyness 0.97–1.03 y vencimiento de 0–1 días. Su ausencia no equivale a ausencia de toda la superficie. Los agregados son compatibles con fragilidad del incremento de los árboles en extremos; no prueban que el choque cause el deterioro, que todo precio sea correcto ni que exista incapacidad universal de extrapolación. La comprobación de barras acredita consistencia interna del proveedor, no validación externa independiente. Las dos fechas no se tratan como una nueva muestra de inferencia.

Fuentes: [comparación por horizonte y sesiones extremas](../../../../rp4/results_v4.md), [ponderación registrada por activo y sesión](../../../../rp4/specification_v4.md), [p formal, p nominal y estado de hipótesis](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [auditoría de cobertura, barras y límites](../../../../../artifacts/rp4_market_audit/REPORT.md), [transcripción agregada, denominadores y hashes de los ejemplos](additions_evidence.json).

## 5. ¿Puede afirmarse B2 ≥ B1 «en mediana»? ¿Es la misma jerarquía?

Sólo como descripción del estimando secundario: la mediana de las diferencias pareadas por sesión favorece B2 en árboles a RV15 y RV5. Sus p bilaterales son 0.0435 y 0.0038; con Holm son 0.0870 y 0.0096. Por tanto, RV15 no supera ese ajuste, mientras RV5 sí lo supera como secundario. La frase no significa dominancia sesión por sesión ni prueba de no inferioridad.

Una mediana positiva y una media negativa pueden coexistir: pérdidas adversas de mayor magnitud pueden pesar más sobre la media. Aquí no se cambia de estadístico para salvar el resultado primario. Además, mediana de diferencias pareadas no es diferencia de medianas de dos series. El protocolo prospectivo conserva esta distinción para su prueba secundaria de árboles; la enmienda 2 la incluye en Holm junto con A y C, manteniendo su lectura única a 20 sesiones.

Fuentes: [distribuciones secundarias registradas](../../../../../artifacts/rp4_v4_b4/distribution_secondary.csv), [tablas legibles de secundarios](../../../../rp4/results_v4.md), [secundario B y multiplicidad vigente](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

## 6. ¿Cómo puede un intervalo positivo coexistir con un p que no rechaza?

El intervalo y el p guardados no son inversión del mismo procedimiento. El intervalo es percentil bilateral del 95 %; el p usa una distribución bootstrap centrada bajo la nula. Por ejemplo, H1 de árboles RV15 en confirmación tiene intervalo [0.0016443642, 0.016807137] y p 0.0568. La decisión registrada es no rechazo, aunque el intervalo percentil no incluya cero.

No se debe sustituir la regla del p por el signo del intervalo cuando difieren. Se muestran ambos y se identifica su construcción; los diagnósticos asintóticos tampoco reemplazan la prueba primaria. Esta discrepancia de calibración es una limitación de la inferencia empleada, no una autorización para elegir el resultado más favorable.

Fuentes: [intervalos y regla de decisión](../../../../rp4/results_v4.md), [campo `interval` y calibración nula](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [inferencia especificada](../../../../rp4/specification_v4.md).

## 7. Si no está demostrado el mecanismo gamma, ¿qué explica realmente B2?

Lo demostrado es la utilidad incremental del conjunto completo B2 dentro de una representación predictiva concreta. La auditoría encuentra mayor magnitud media absoluta en ciertas participaciones de prima que en el desbalance gamma, pero esa comparación no identifica la contribución marginal de cada variable. Los coeficientes corresponden a entradas transformadas, estandarizadas sólo con entrenamiento y recortadas; además, las columnas están relacionadas entre sí y la salida aplica correcciones y cotas.

La variable `rp4_gamma_imb_signed_trades` cuenta operaciones con dirección identificable: no es un saldo firmado de compra y venta. Las medianas pequeñas de algunas participaciones de prima y sus medias absolutas mayores tampoco describen un efecto estable en cada sesión. Sin ablación, inventarios reales ni identificación causal, no puede afirmarse que la mejora proceda de cobertura de intermediarios, ni que todo sea composición del flujo. La ablación prospectiva registrada compara el bloque completo contra su retirada, sin reescribir esta evidencia histórica.

Fuentes: [escala, signos y límites de los coeficientes](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [resumen por columna y horizonte](../../../../../artifacts/rp4_closeout_audit/b2_coefficient_summary.csv), [definición del secundario A](../../../../rp4/prospective_confirmation_v1_amendment_1.md), [multiplicidad vigente A/B/C](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

## 8. ¿Las interrupciones del proveedor fabricaron la mejora del flujo?

El cierre señala 2025-05-15 y 2025-09-18 como incidencias del instrumento. El censo demuestra ventanas sin operaciones elegibles disponibles; no prueba por sí solo una interrupción de publicación ni distingue su causa económica de cobertura o latencia del proveedor. La regla v3 conserva los conteos de actividad cero, declara indefinidas las formas y razones sin operaciones y añade indicadores. No elimina las filas para favorecer B2. Permanecen 412 ventanas vacías de cinco minutos en la primaria y ninguna en confirmación.

En esas filas, QLIKE lineal B1/B2 pasa de 0.102703519 a 0.202126323 con igual peso por sesión y activo: el daño sigue siendo adverso. La media por origen es diferente, de 0.185885062 a 0.247087047, y no debe intercambiarse con la anterior. La corrección acota un problema de representación; no prueba que toda ausencia sea falta real de actividad ni identifica qué mejora habría sin interrupciones. No se calcula una nueva prueba excluyéndolas.

Fuentes: [incidencias señaladas en el cierre](../../../../rp4/RESULTADO_FINAL.md), [regla y atribución causal pendiente](../../../../rp4/v3_window_empty_addendum.md), [censo de vacíos](../../../../../artifacts/rp4_v4_b4/empty_census.csv), [comparación dentro de vacíos y ponderaciones](../../../../../artifacts/rp4_closeout_audit/REPORT.md).

## 9. ¿Qué ocurrió el 26 de enero? ¿No cambió el mercado que el modelo intentaba aprender?

El censo documenta primera presencia de vencimientos de lunes y miércoles en los seis activos el 2026-01-26, coherente con el anuncio de listado consignado en la auditoría. Los primeros vencimientos de esos días con plazo intradía aparecen el 2026-02-02 y el 2026-02-04. La fecha inicial del listado no se deduce de un aumento posterior de cobertura: conteo de vencimientos y número de celdas son magnitudes diferentes.

La cobertura media global por origen cambia de 20.036718 a 23.095318 celdas antes y después del corte. La confirmación está íntegramente en el régimen nuevo, mientras una parte importante del entrenamiento procede del anterior. Es una limitación de transportabilidad y estabilidad; las comparaciones descriptivas no identifican que ese cambio cause la evolución de QLIKE. La auditoría distingue anuncio, primera presencia observada y primera expiración, y acota el periodo realmente inspeccionado.

Fuentes: [censo, anuncio registrado y límites de interpretación](../../../../../artifacts/rp4_market_audit/REPORT.md), [cobertura por día de semana](../../../../../artifacts/rp4_market_audit/coverage_weekday.csv).

## 10. ¿El periodo de aprendizaje era demasiado corto? ¿Bastaba ampliarlo?

El diseño usa 60 sesiones iniciales sólo para entrenamiento y después entrenamiento expansivo. El tramo evaluado de octubre de 2024 a febrero de 2025 contiene 64 sesiones; en él la ganancia de B1 lineal RV15 es negativa. Es evidencia de dificultad temprana, no una demostración de que otro calentamiento habría corregido el problema.

El tamaño de entrenamiento aumenta junto con el calendario y los regímenes. Los terciles de entrenamiento y el tramo temprano son cortes diferentes. No hay un experimento que mantenga fijo el régimen y cambie únicamente el aprendizaje; ampliar retrospectivamente el calentamiento también excluiría observaciones ya vistas. La defensa conserva ese tramo y los meses adversos.

Fuentes: [reglas de entrenamiento](../../../../rp4/specification_v4.md), [perfil temprano y terciles](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [perfiles descriptivos completos](../../../../../artifacts/rp4_closeout_audit/descriptive_profiles.csv).

## 11. ¿La ridge estaba casi sin penalización? ¿Es correcto llamarla regularizada?

La implementación penaliza la suma de errores cuadrados, sin dividirla por el tamaño de entrenamiento. Por eso la misma lambda no tiene intensidad comparable a una formulación basada en error medio. B2 eligió lambda 0.0001 en 111 de 419 sesiones RV15; la rejilla puede resultar poco restrictiva en muestras grandes. El nombre descriptivo usado en el cierre es «modelo lineal winsorizado con filtro de rango, ridge nominal».

La estabilidad también depende de transformaciones, poda de rango y cotas. En B2 se retiraron entre 88 y 97 columnas, incluidos indicadores de presencia: no eran todas constantes ni se retiró siempre la misma cantidad. Eso no garantiza estabilidad de coeficientes correlacionados. Cambiar la escala de la penalización sería otro diseño; no se hace sobre la muestra cerrada ni se atribuye a esa modificación un resultado no observado.

Fuentes: [regularización y podas](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [selección de lambda](../../../../../artifacts/rp4_closeout_audit/ridge_lambda_counts.csv), [resumen de rango y cotas](../../../../../artifacts/rp4_closeout_audit/ridge_bounds_pruning_summary.csv), [modelo registrado](../../../../rp4/specification_v4.md).

## 12. ¿Qué significa el resultado extremo de v1? ¿Se ocultó un modelo que fallaba?

El resultado permanece visible: la comparación lineal B2/B1 de v1 muestra −167448.32 % de reducción de QLIKE, es decir un empeoramiento extremo, con p Holm 1. La versión inicial usó 418 sesiones y 92261 orígenes; v2–v4 usan otra cobertura y la familia lineal incorpora cambios de estabilidad. El cierre reconoce el fallo numérico, en vez de leer ese valor como una relación económica estructural.

La tabla por versiones no es una ablación controlada que permita adjudicar toda la recuperación a una corrección particular. Conservar el valor adverso y sus denominadores es esencial: mostrar únicamente la versión final escondería la fragilidad que motivó las revisiones. El resultado posterior no vuelve válida retrospectivamente la implementación inicial.

Fuentes: [comparación v1/v2 con denominadores](../../../../rp4/results_v2.md), [comparación agregada sin recorte](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv), [lectura final del fallo](../../../../rp4/RESULTADO_FINAL.md).

## 13. ¿La ventana de 25 sesiones confirma el hallazgo principal?

No. En la familia lineal RV15, H1 tiene p 0.3908, por lo que H2 no se abre; el p nominal de H2 es 0.1758. En árboles RV15, H1 tiene p 0.0568 y también deja H2 cerrada. Un efecto puntual favorable en algún contraste no equivale a superar la secuencia completa.

Además, «confirmación» es el nombre de una ventana de calendario, no garantía de independencia del desarrollo: la partición fue fijada el 2026-09-07 y una ventana parcialmente superpuesta, del 20 de julio al 28 de agosto, ya había sido leída por una evaluación puente previa con otra especificación. Se reportan sus 25 sesiones y 9750 orígenes por separado. Una muestra breve y reutilizada no se rescata sumándola a la primaria ni se convierte su no rechazo en equivalencia.

Fuentes: [confirmación y divulgaciones](../../../../rp4/results_v4.md), [decisiones y tamaños](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [alcance de la lectura previa](../../../../rp4/RESULTADO_FINAL.md).

## 14. Si la partición se fijó después de las fechas evaluadas, ¿en qué sentido es fuera de muestra?

Es fuera de muestra respecto de cada ajuste diario: las predicciones usan entrenamiento anterior a la sesión evaluada, con selección sobre las últimas diez sesiones de entrenamiento, transformación estimada sólo allí y purga/embargo de 60 minutos. Eso limita el uso directo de objetivos futuros en el ajuste.

Es distinto del desconocimiento de la muestra durante el diseño. El calendario se fijó retrospectivamente y las versiones reutilizan ventanas, de modo que el control causal del entrenamiento no elimina la adaptación metodológica. La etiqueta completa es «fuera de muestra walk-forward, partición fijada 2026-09-07». Omitir la segunda parte exageraría el carácter confirmatorio. La réplica nueva conserva el entrenamiento causal y fija la regla antes de incorporar sus sesiones futuras.

Fuentes: [diseño y divulgaciones](../../../../rp4/RESULTADO_FINAL.md), [máscaras temporales y límites de la comprobación](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [especificación v4](../../../../rp4/specification_v4.md), [cohorte prospectiva](../../../../rp4/prospective_confirmation_v1.md), [enmienda vigente](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

## 15. ¿Hay realmente 160832 observaciones independientes? ¿Cómo se trata la dependencia?

No se interpretan los orígenes como ensayos independientes. La primaria v2–v4 tiene 160832 orígenes en 419 sesiones; la pérdida se agrega primero por activo y sesión y después con iguales pesos entre activos y sesiones. La inferencia usa bootstrap circular de bloques de cinco sesiones y 9999 réplicas, manteniendo la unidad temporal registrada.

La superposición intradía, los activos y el régimen motivan distinguir el número de pronósticos del soporte temporal. El remuestreo empleado no demuestra que haya capturado cualquier dependencia de largo plazo o ruptura estructural. La longitud de bloque se conserva; no se escoge otra según el p obtenido. También se conservan los diagnósticos alternativos sin convertirlos en sustitutos de la prueba primaria.

Fuentes: [método de inferencia](../../../../rp4/specification_v4.md), [tamaños y parámetros efectivamente guardados](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [cobertura](../../../../../artifacts/rp4_v4_b4/coverage.csv).

## 16. ¿Una reducción de QLIKE tan pequeña importa? ¿El intervalo está expresado en porcentaje?

El efecto responde a una pregunta de precisión predictiva. La reducción porcentual registrada es 100 × media(delta) / media(QLIKE base), con delta igual a pérdida base menos ampliada y las ponderaciones de sesión y activo fijadas. No es un cambio porcentual de volatilidad ni un retorno. Su utilidad operativa requeriría una evaluación adicional alineada con una decisión concreta; este estudio no la mide.

El intervalo original corresponde a la diferencia de QLIKE. Cuando la figura lo expresa en porcentaje, divide sus extremos por la media base observada y multiplica por 100. Es una reexpresión con denominador fijo, no un nuevo intervalo bootstrap del cociente. En particular, el +0.6227941 % lineal RV15 debe leerse junto al intervalo de delta [0.00033503697, 0.0019321616], la adaptación entre versiones y la falta de confirmación completa en la ventana final.

En la primaria RV15, el incremento lineal B2/B1 es favorable en 249 de 419 sesiones: 100 × 249 / 419 = 59.43 %, redondeado a dos decimales; 59 % es el redondeo entero. Quedan 170 sesiones adversas y ningún empate. La diferencia media también es positiva en 6/6 activos y 3/3 bloques cronológicos. Son descripciones de frecuencia y distribución, no seis pruebas significativas, tres réplicas independientes ni una garantía de rentabilidad.

HARQ ofrece contexto metodológico: Bollerslev, Patton y Quaedvlieg (2016) incorporan cuarticidad para ajustar la persistencia a errores de medición variables. Estudian pronósticos diarios y superiores frente a HAR; los retornos de cinco minutos construyen la medida, no un objetivo RV5. Sus comparadores, muestras y ventanas difieren del incremento intradía B2/B1. Por ello no se utiliza un porcentaje del artículo como umbral comparable ni como validación de la magnitud observada. [Artículo original, secciones 2.3, 3.1, 3.3 y 3.5](https://public.econ.duke.edu/~ap172/BPQ_Exploiting_Errors_JoE_2016.pdf).

Fuentes: [definición, efecto e intervalo original](../../../../rp4/results_v4.md), [estimaciones originales](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [definición explícita del intervalo reescalado](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv), [recuentos agregados y hashes](additions_evidence.json), [identificación bibliográfica en Duke](https://scholars.duke.edu/publication/1072550).

## 17. ¿Por qué no se puede traducir QLIKE en rentabilidad de trading?

QLIKE evalúa el desacuerdo entre variación realizada y pronóstico: `y/f − log(y/f) − 1`. Ninguno de esos términos define una posición, precio de ejecución, horizonte de tenencia o coste. B2 puede mejorar el pronóstico sin ofrecer una operación rentable a los precios disponibles.

Faltan una regla negociable y una evaluación de costes, liquidez, exposición y riesgo de esa regla. No se deducen beneficios, Sharpe, capacidad o retorno de este resultado. La conclusión conservada es investigación predictiva y mantiene `RESEARCH_ONLY`, `NOT INVESTMENT ADVICE` y `capital_go=false`.

Fuentes: [pérdida y alcance del resultado](../../../../rp4/specification_v4.md), [límites expresos de la conclusión](../../../../rp4/RESULTADO_FINAL.md).

## 18. ¿Qué acredita el PIT y qué sigue siendo un proxy?

Se aplica un umbral de tiempo fuente de 120 segundos y se conserva la lógica de disponibilidad temporal registrada. La auditoría distingue los relojes disponibles del proveedor y la selección de sus versiones. Es un control sobre los datos y marcas conservadas, no una observación del instante en que un cliente histórico recibió cada dato.

Por tanto, no puede afirmarse que las señales fueran ejecutables en tiempo real con esa latencia. Descargar prospectivamente después del cierre tampoco transforma esas marcas en recibos históricos del cliente. La nueva réplica mejora la separación entre registro y observación de la muestra, pero conserva esta limitación instrumental y la ausencia de inventarios reales de intermediarios.

Fuentes: [método de relojes y límites](../../../../../artifacts/rp4_market_audit/REPORT.md), [divulgación PIT](../../../../rp4/RESULTADO_FINAL.md), [límites de la adquisición prospectiva](../../../../rp4/prospective_confirmation_v1.md), [enmienda vigente](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

## 19. ¿Los resultados dependen de días extremos o de algunos meses favorables?

La evidencia descriptiva conserva heterogeneidad. Octubre y noviembre de 2025 son negativos para B2 lineal tanto en RV30 como en RV15. En la primaria, el efecto lineal de B2 es positivo en los tres bloques cronológicos de ambos horizontes, pero por activo sólo es positivo en tres de los seis a RV5, frente a los seis a RV15. La media agregada no significa ventaja uniforme.

Los extremos y las acumuladas ayudan a localizar qué sesiones contribuyen a la diferencia. No permiten atribuir un movimiento a un suceso por cercanía temporal ni autorizan excluirlo para mejorar el p. También se distingue la primera hora observable de la primera hora de mercado: sus denominadores y efectos no son intercambiables. Los recortes posteriores se mantienen descriptivos.

Fuentes: [robustez por bloques y activos](../../../../../artifacts/rp4_v4_b4/robustness.csv), [perfiles por mes y hora](../../../../../artifacts/rp4_closeout_audit/descriptive_profiles.csv), [distinción de cortes y ponderaciones](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [síntesis con signos](../../../../rp4/RESULTADO_FINAL.md).

## 20. ¿Las barras extremas son errores de datos que deberían haberse eliminado?

La auditoría de AMZN del 2026-08-31 y TSLA del 2026-08-17 reprodujo los movimientos extremos y sus reversiones en las barras conservadas, comprobando integridad temporal, precios OHLCV y volumen. Los archivos coinciden con sus hashes y recibos históricos. Eso acredita consistencia interna de los datos examinados.

No acredita de forma independiente que esos precios fueran ejecuciones de mercado correctas ni identifica la noticia o causa. Por ello no se eliminan, sustituyen ni se les atribuye un mecanismo económico sin evidencia externa. La defensa expone la anomalía y su límite de validación; no presenta el control de integridad como validación externa del precio.

Fuentes: [barras extremas, comprobaciones y límites](../../../../../artifacts/rp4_market_audit/REPORT.md), [fuentes y hashes del censo](../../../../../artifacts/rp4_market_audit/sources.json), [días de mayor pérdida](../../../../../artifacts/rp4_v4_b4/top_loss_sessions.csv).

## 21. ¿Los fallos de salto y de recalibración MZ invalidan la primaria?

Son endpoints distintos y se mantienen sus estados separados. El cierre final de salto contiene 419 sesiones primarias, no el cierre parcial de 418; combina los componentes válidos conservados con la resolución numérica de los fallos elegibles, sin seleccionar el pase por su AUC. Los agregados no rechazan H1 y no abren H2. La etiqueta `jump30 > 0` representa exceso positivo RV−BPV, no un test formal de salto significativo.

La recalibración MZ permanece no verificable como resultado útil. Ninguno de esos secundarios cambia las pérdidas, máscaras o decisiones primarias guardadas; tampoco puede promoverse un secundario favorable para salvarlas. V4 excluye cuantiles, salto y MZ de sus ajustes. El resultado del clasificador no demuestra ausencia de información sobre saltos económicamente relevantes definidos de otra manera.

Fuentes: [cierre combinado y fallos preservados](../../../../rp4/results_v3_revision2.md), [auditoría de la etiqueta y alcance](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [endpoints de v4](../../../../rp4/specification_v4.md).

## 22. ¿Qué cambiará de verdad con la réplica prospectiva?

Cambiará la muestra y su relación temporal con el registro, manteniendo la prueba primaria v4. La primera adquisición está prevista para el 2026-09-09 a las 10:00 de Australia/Sydney y corresponde a la sesión de mercado 2026-09-08 de Nueva York. Las fechas de muestra son sesiones de mercado, no fechas civiles del equipo. Los hashes y recibos conservan qué se fijó antes de esa adquisición; son constancias locales, no sellos temporales independientes.

La decisión principal se lee una vez al completar las primeras 20 sesiones elegibles: confirma sólo si H1 y H2 rechazan en la familia lineal a RV15 según su secuencia registrada. No permite cambiar a árboles, RV5, mediana o media recortada después del resultado. Las primeras 40 sesiones acumuladas, si se realiza esa lectura, informan estabilidad y no rescatan una primera lectura negativa ni constituyen una réplica independiente. El tamaño registrado no garantiza potencia suficiente; no se ha estimado aquí una probabilidad de éxito.

La enmienda 2 conserva A, ablación, y B, mediana de árboles, y añade C, media pareada recortada de árboles, y D, agrupación de las 25 sesiones históricas finales ya observadas con las primeras 20 nuevas, para un total de 45. A/B/C usan Holm entre tres; D tiene su propia secuencia secundaria H1→H2. A, B, C y D se leen una sola vez cuando se completa la lectura de 20, incluso si el primario no confirma; no se repiten a 40 ni alteran el veredicto principal. La agrupación contiene información histórica conocida y no es una réplica independiente.

Fuentes: [cohorte, lectura y criterio de sesión completa](../../../../rp4/prospective_confirmation_v1.md), [enmienda vigente de secundarios y multiplicidad](../../../../rp4/prospective_confirmation_v1_amendment_2.md), [recibo de la enmienda 2](../../../../rp4/prospective_confirmation_v1_amendment_2_receipt.json), [horario del colector conservado](../../../../rp4/prospective_confirmation_v1_amendment_1.md).

## 23. ¿Qué podrá responder la ablación prospectiva que los coeficientes históricos no responden?

Comparará B2 completo con B2 sin las cuatro columnas registradas de desbalance gamma y sus indicadores de presencia: 138 frente a 134 predictores brutos. Conserva las tres columnas históricas de exposición gamma. Ambos usan las mismas claves, máscaras y reglas; el reducido se ajusta y selecciona con su propio entrenamiento causal. Así se contrasta una contribución predictiva conjunta del bloque dentro de la familia lineal RV15, no sólo la magnitud de sus coeficientes.

A es esa ablación con p unilateral; B es la mediana de los deltas pareados de árboles RV15 con p bilateral; C es la media de esos deltas recortada al 5 % por cada cola, también con p bilateral. A/B/C se calculan en las primeras 20 sesiones prospectivas y las decisiones exigen signo positivo y Holm entre las tres al 5 %. Para C, floor(0.05 × 20) = 1: se retira una observación de cada cola y se promedian las 18 restantes, aplicando la misma receta dentro de cada remuestra. No se recortan las dos series por separado ni se eligen fechas de choque. La enmienda 2 sustituye el Holm de dos de la enmienda 1; no modifica sus recetas nominales A/B.

D responde otra pregunta: si las 25 sesiones históricas finales más las 20 prospectivas apoyan juntas la jerarquía en la familia lineal RV15. Cada una de las 45 sesiones pesa 1/45, sin dar la mitad del peso a cada ventana. Tiene su propia secuencia secundaria unilateral H1→H2 al 5 %, separada de Holm A/B/C; si falla H1, H2 queda sólo nominal. Se reutilizan literalmente las pérdidas históricas congeladas, sin nuevos ajustes históricos ni cambio de sus p originales. Las 25 ya observadas motivan parte de ese análisis, por lo que no puede llamarse confirmación independiente.

Todos los secundarios se leen una sola vez junto a las primeras 20 y no se repiten a 40. No cambian el primario ni se reclama control global sobre su unión. Una ablación favorable no demostraría inventario real ni cobertura causal: el bloque incluye un conteo de operaciones, además de medidas de desbalance; una mediana o media recortada favorable tampoco elimina el riesgo de las colas.

Fuentes: [comparadores originales A/B y entrenamiento](../../../../rp4/prospective_confirmation_v1_amendment_1.md), [reglas vigentes A/B/C, agrupación D y cadena de sellados](../../../../rp4/prospective_confirmation_v1_amendment_2.md), [recibo vigente](../../../../rp4/prospective_confirmation_v1_amendment_2_receipt.json), [límites de los coeficientes históricos](../../../../../artifacts/rp4_closeout_audit/REPORT.md).

## 24. ¿Qué pasa si faltan sesiones o el colector informa éxito con cobertura insuficiente?

La réplica toma las primeras sesiones completas y elegibles en orden cronológico. El éxito de descarga no basta: deben verificarse componentes, hashes, claves, minutos de calendario y elegibilidad bajo v4 antes de consultar pérdidas o signos. Las ausencias se censan con razones objetivas; no se rellenan ni se escogen días por rendimiento. Un modelo reducido no recibe una máscara más permisiva que el completo.

La tarea no despierta el equipo y puede ejecutarse cuando vuelva a estar disponible; el colector obtiene la última sesión cerrada y no promete recuperar automáticamente una interrupción prolongada. Es un riesgo de acumulación y calendario, no motivo para redefinir una sesión completa. Sin las primeras 20 sesiones completas no se abre la lectura principal ni sus secundarios.

Si A, B o C no es computable, conserva su estado y su lugar dentro de Holm de tres con valor administrativo 1; no se reduce la familia ni se presenta ese valor como una estimación científica. Si la unión de 45 sesiones o la inferencia de D falla, se informa no verificable sin excluir fechas, repetir la lectura ni cambiar el criterio. Los secundarios no se rescatan con una lectura a 40.

Fuentes: [criterios de completitud y ausencias](../../../../rp4/prospective_confirmation_v1.md), [limitaciones del colector](../../../../rp4/prospective_confirmation_v1_amendment_1.md), [tratamiento vigente de A/B/C y fallos de D](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

## 25. ¿Qué puede verificar un examinador sin disponer de datos licenciados?

Puede contrastar cada afirmación con las estadísticas agregadas, comparar los signos y denominadores entre versiones, revisar las fórmulas y seguir los hashes de los artefactos. La verificación documental comprueba concordancia de cifras y bytes; no demuestra por sí sola procedencia íntegra de todos los datos, recepción histórica al cliente o ejecución correcta de una estrategia.

Recalcular desde originales licenciados exige esos insumos, el entorno y sus recibos, y es una operación distinta de verificar el paquete. No se declara una reproducción completa desde cero durante esta preparación. Las correcciones documentales se añaden sin sustituir los resultados congelados y las cohortes reservadas quedan fuera del alcance. La evidencia prospectiva permanece pendiente hasta su lectura registrada.

Fuentes: [operaciones de verificación y reproducción](../../../../rp4/OPERATING_GUIDE.md), [manifiesto del informe v4](../../../../../artifacts/rp4_v4_b4/report_manifest.json), [alcance de la auditoría descriptiva](../../../../../artifacts/rp4_closeout_audit/findings.json), [custodia prospectiva](../../../../rp4/prospective_confirmation_v1.md), [enmienda vigente](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

## 26. Multiplicidad entre versiones: ¿resiste el resultado una corrección y qué permite concluir?

Como sensibilidad posterior, se muestra la aritmética de Bonferroni para una familia hipotética fijada: p ajustado = min(1, m × p), con m = 2 o m = 4. El factor dos examina la pareja de horizontes primarios RV30/RV15; el factor cuatro ilustra una cota condicional con cuatro oportunidades. Estos factores no reconstruyen toda la adaptación entre versiones ni crean un nuevo diseño registrado.

| Contraste guardado | p nominal | Sensibilidad ×2 | Sensibilidad ×4 |
| --- | ---: | ---: | ---: |
| H2 lineal RV15 | 0.0032 | 0.0064 | 0.0128 |
| H1 lineal RV15 | 0.0390 | 0.0780 | 0.1560 |
| H1 árboles RV15 | 0.0135 | 0.0270 | 0.0540 |
| H1 árboles RV30 | 0.0053 | 0.0106 | 0.0212 |
| H1 lineal RV5, secundario | 0.0092 | 0.0184 | 0.0368 |

Por ejemplo, 0.0032 × 2 = 0.0064 y 0.0032 × 4 = 0.0128. H2 lineal RV15 queda por debajo de 0.05 en ambos cálculos individuales, pero H1 lineal RV15 pasa de 0.0390 a 0.0780 con el factor dos y no rechaza. Por ello esta sensibilidad no sostiene la secuencia lineal completa al 5 %. H1 de árboles RV15 conserva 0.0270 y H1 de árboles RV30, 0.0106 con el factor dos; ninguna permite abrir H2 lineal. No se mezcla H1 de otra familia, horizonte o muestra con H2 para salvar una jerarquía.

RV5 sigue siendo secundario y queda fuera de la pareja RV30/RV15: su 0.0092 × 2 = 0.0184 se muestra como cálculo ilustrativo separado, no como incorporación retrospectiva a esa familia de dos. Escribir aproximadamente 0.018 supone redondearlo a tres decimales, no otro p ni otro resultado.

Bonferroni ofrece una cota bajo una familia finita fijada y p nominales válidos para sus hipótesis; aquí la elección y reutilización de especificaciones son adaptativas. Estos productos son sensibilidad descriptiva, no prueba de control global entre versiones y familias, ni borrado de la selección previa. Se conservan sin cambios las decisiones originales y la necesidad de una réplica prospectiva con regla fijada antes de sus datos.

Fuentes: [p y estados históricos](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [regla secuencial y límites](../../../../rp4/specification_v4.md), [resultados originales v3/v4](../../../../rp4/results_v4.md), [aritmética, filas fuente y alcance condicional](additions_evidence.json), [decisión prospectiva intacta y enmienda vigente](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
