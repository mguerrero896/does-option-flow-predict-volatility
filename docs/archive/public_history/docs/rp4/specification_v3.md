# RP4 v3 — especificación del mecanismo de flujo gamma

Registro 2026-09-07; decisión 131, por instrucción explícita de Miguel en esta conversación, sin atribuirle una firma criptográfica. RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false. Etiqueta: **fuera de muestra walk-forward, partición fijada 2026-09-07**.

## 1. Contrato, antecedentes y custodia

Una especificación, una evaluación por ventana, todos los signos. Se preservan byte por byte v1, v2, phase9 y el addendum del commit `23c521367e9af23129d4591f3df67a7f25140615`. Este encargo completo resuelve el contexto que faltaba cuando se registró ese addendum; no reescribe su estado histórico. No se descarga, publica ni activa un colector con v3.

Se hereda el JSON v2 `artifacts/rp4_v2_a1/specification.json`, SHA-256 `08a749049f56a0d1dda09cef1f280328e7c84d59fc39d57e71c48caee81670a5`, excepto las modificaciones expresas de este documento y del JSON v3 generado. El addendum `docs/rp4/v3_addendum_stability_calibration.md`, SHA-256 `81a20523b205e014bd2e910272e280e6c412af120037a6fb1c565e263dd7fce5`, forma parte íntegra del contrato.

Panel base inmutable: `private-input/52abad6fed9842f1a1ba`, SHA-256 `5b7dd5cc4b2b1e64446d305a5ee0de92f6d18e790f94b5840664947da00fd19d`. La unión será uno a uno por `(asset, session_date, origin_minute)`, nunca por posición. Cada columna preexistente, incluido RV30, debe conservar valores y tipos exactos.

Primaria: 2024-08-02 a 2026-07-31, primeras 60 sesiones sólo entrenamiento; referencia de v2: 419 sesiones pronosticadas. Confirmación: 2026-08-03 a 2026-09-04, referencia 25 sesiones. El N ejecutado y sus exclusiones se reportan, no se fuerzan. Activos AAPL, AMZN, META, MSFT, NVDA y TSLA; no se cambian sesiones ni se suman ventanas reutilizadas como replicaciones independientes.

Los resultados ya conocidos motivan este cambio: en v2 LightGBM B1/B0 obtuvo +2.09118% y Holm 0.0264; el promedio ridge también fue positivo, pero su Holm fue 0.1842. Esto no significa rechazo en ambas familias. V3 se diseña con resultados v1/v2 conocidos: fijar ahora el procedimiento evita reajustes adicionales dentro de v3, pero no elimina la selección entre versiones ni convierte las ventanas reutilizadas en evidencia independiente nueva.

## 2. Hipótesis y mecanismo

H1: reducción media de QLIKE B1 sobre B0 > 0. H2: reducción media de QLIKE B2 sobre B1 > 0. La demanda intradía firmada de gamma es una variable de mecanismo, no una identidad observada del cliente ni el inventario real del dealer. El lado agresor y la contrapartida dealer son proxies; tampoco se observa directamente su cobertura en acciones.

La motivación es compatible con la demanda de cobertura y el comportamiento intradía estudiados por [Baltussen, Da, Lammers y Martens (2021)](https://pure.eur.nl/en/publications/hedging-demand-and-market-intraday-momentum/). Su estudio no valida directamente esta variable para RV30 de estos seis activos. [Ni, Pan y Poteshman (2008)](https://www.mit.edu/~junpan/npp.pdf) estudian demanda informativa de volatilidad ponderada por vega y datos de participantes no creadores de mercado; no es la misma exposición gamma de este protocolo. Una ausencia de efecto detectado limitará esta especificación y su precisión, no probará que todo flujo posible esté absorbido ni que éste sea el único mecanismo.

## 3. A2: derivación independiente, comparación y variables nuevas

Candidato entregado: `private-input/d01207654cb6c67c17c4`, SHA-256 `edc0263c8d8a76c897fc6d8e54462fd3ffb8f3aa475eb7ee4b55551b4a7fdfcc`; manifiesto SHA-256 `8619bfd4191e80d14e7c025dc7f3358d9d0f881eb65f55a341fc16bddaae645d`. La derivación propia se escribió antes de inspeccionar su productor; no se usa el candidato como predictor sin la rederivación.

Se utilizan los mismos archivos de `materialize.tape_index`, incluida la clave `__ALL__` de 2026-07-13 a 17; fuentes FMP y exógenas ya fijadas por v2. No se repara el hueco aceptado 2025-01-25 a 2025-02-24.

Reglas por operación:

1. Apertura 09:30 America/New_York; origen apertura + origin_minute. Corte inclusivo origen menos 120 s. Sólo ejecución dentro de la rejilla de sesión y DTE calendario entre 0 y 90, inclusive; los filtros de validez de `build_new_option_features` se mantienen. IV finita entre 0.03 y 3 inclusive, filtrada antes de agregar.
2. Spot `mark_price(minute_of_trade, closes, opens)` de `build_session_grid` y `load_rp4_bars`: cierre del minuto anterior, o apertura para minuto cero; nunca cierre del minuto de la operación. Tenor entre ejecución y cierre de vencimiento de `expiry_close_timestamps`, con `time_to_expiry_years`, año de 365.25 días. Tasa y dividendo de `exogenous_sources` / `carry_for_session`, sin r=q=0; rendimiento dividendo = efectivo anual previo / spot de la operación.
3. Gamma Black–Scholes con carry: `exp(-q*T)*phi(d1)/(S*IV*sqrt(T))`, `d1=(log(S/K)+(r-q+IV²/2)*T)/(IV*sqrt(T))`. Rechazar resultados no finitos, no fabricarlos. Exposición firmada = dirección × size × 100 × gamma × S²; el signo no depende de call/put.
4. ask_side solamente: +1; bid_side solamente: −1; ninguno o ambos: 0. Si `_multileg_size > 0`, dirección 0. La detección incremental de multileg conserva sus limitaciones, incluida la primera observación de un contrato; se cuentan ambigüedades y entradas no finitas, sin afirmar identificación perfecta.
5. Exigir **created_at y executed_at <= corte**. Ordenar historia multileg por `max(created_at, executed_at)`, con desempate por orden fuente fijado: una operación aún no disponible no cambia la clasificación anterior. Esa intersección no es una nueva marca de recepción del cliente. Por ID se conserva la primera versión disponible en ese orden; duplicados exactos se eliminan y revisiones contradictorias posteriores se auditan sin borrar ni actualizar la versión inicial. Contradicciones simultáneas en el primer instante se resuelven por el orden fuente fijado y se cuentan como ambigüedad. No se usa un conflicto futuro para excluir una operación pasada.
6. Prefijo sin operaciones válidas disponibles: NaN. Prefijo válido sin operaciones firmadas: cero, incluido conteo cero. Una operación futura no convierte retrospectivamente un prefijo NaN en cero. Rejilla ausente: NaN. No hay imputación de cinta.

Columnas, como acumulados desde apertura hasta corte:

| Columna | Acumulado |
|---|---|
| rp4_gamma_imb_total | Exposición firmada de todos los strikes |
| rp4_gamma_imb_near_spot | Exposición con abs(K/S−1) <= 0.05 + 1e-12 |
| rp4_gamma_imb_near_short | Lo anterior y DTE <= 7 |
| rp4_gamma_imb_signed_trades | **Número** de operaciones válidas de dirección no cero; no suma de signos |

Se compara por claves con el candidato: número de filas, diferencia máxima y media absoluta por columna, discrepancias numéricas con `atol=1e-8, rtol=1e-10`, discrepancias de ausencia y causas. Un puente independiente reproduce su definición histórica (IV [0.01,5], sólo created_at, prioridad ask si ambos tags y disponibilidad evaluada al nivel de día); otro cambia sólo IV. La versión de producción añade los controles causales anteriores. Esos puentes son auditoría de construcción, **nunca** entradas o evaluaciones alternativas de modelos. Se registran filtros y cobertura por activo/sesión/variable. Si persisten discrepancias, se conserva el candidato y se utiliza la derivación propia documentada, sin elegir según QLIKE.

Para el secundario de salto se reconstruye `jump30=max(RV30−BPV30,0)` con `forward_measures` del productor RP2 bloque 3, desde las mismas barras y máscara de 31 cierres observados positivos del productor RP4 de RV30. Se compara RV30 reconstruido contra el existente sin cambiar éste. Jump ausente sigue NaN y afecta sólo al clasificador. `jump30>0` es el componente positivo RV−BPV solicitado, no una prueba estadística formal de salto.

## 4. Conjuntos y entrenamiento causal

B0 y B1 son exactamente las listas v2: 29 y 69 predictores anidados. B2 son sus 132 predictores v2 más las cuatro columnas anteriores: 136. El JSON enumera todas las columnas, incluyendo las exclusiones v2; ningún objetivo, latencia o indicador de ventana vacía se introduce en X. Se conservan cinco efectos de activo e intercepto donde corresponda.

Los nuevos tres importes reciben `sign(x)*log1p(abs(x))` y el nuevo conteo `log1p(x)`, exactamente una vez, también al alimentar árboles; los predictores anteriores conservan sus transformaciones específicas de familia v2. El parquet conserva magnitudes crudas. Todos los opcionales admiten NaN: nativo en LightGBM; indicadores y mediana de entrenamiento en la familia lineal. Sólo B0+HARQ son obligatorios. Las máscaras son comunes a los tres conjuntos y dos familias de cada estimando; el estimando de salto añade únicamente disponibilidad de jump30.

Walk-forward expansivo por sesión. Cada objetivo de entrenamiento debe terminar al menos 60 minutos antes del primer origen pronosticado. Afinado exclusivamente en las últimas diez sesiones elegibles de entrenamiento, con el mismo corte de 60 minutos entre inner_fit y validación; refit sólo con todo el pasado permitido. Peso igual por origen al ajustar y selección por promedio de pérdidas dentro de activo-sesión, después activo y sesión iguales. No se escoge configuración usando pérdidas del día pronosticado.

### Familia lineal primaria y addendum

Ridge de log RV30, suma de cuadrados + lambda por suma de pendientes al cuadrado; intercepto no penalizado. Lambda `[0.0001,0.01,1,100,10000]`, selección QLIKE, empate lambda mayor. Medianas, presencia, eliminación de columnas sin datos/varianza, media y desviación poblacional exclusivamente de entrenamiento. Winsorización ±5 de cada pendiente estandarizada, incluidos indicadores y efectos de activo; intercepto intacto, sin reestandarizar. QR con pivote después del recorte, tolerancia relativa 1e-10, contemplando dependencia con intercepto.

Duan sólo con residuos de entrenamiento. Pronóstico acotado en log antes de exponenciar, a `[0.5*P1,2*P99]` de RV30 positivo del entrenamiento de ese ajuste, percentiles lineales, pesos por origen. Cada inner_fit usa sus propios percentiles y cada refit los del pasado completo. Reportar lambda, columnas, recortes de X y hits inferiores/superiores de pronóstico, separando validación y evaluación. No se acota el objetivo ni se garantiza una cota de QLIKE.

### LightGBM primario y MZ secundario

Se conserva QLIKE sobre pronóstico logarítmico, inicialización log(media RV30 entrenamiento), hojas 15/31/63, learning_rate 0.05, min_data_in_leaf 100, max_bin 63, hasta 2000 rondas, paciencia 50, semilla 20260907, cuatro hilos, determinismo y desempate menos hojas/menos rondas. Se registra la ronda elegida por sesión/conjunto; el score inicial se suma exactamente una vez en la predicción externa. Clip log [-30,30], piso 1e-12.

Se ejecuta íntegramente el addendum MZ: coeficientes en niveles sobre diez pares de medias de sesión de validación, con las predicciones del candidato **inner_fit**, no del refit que ya incorporó esos objetivos. Aplicación por origen al pronóstico final; piso 1e-12 y conteos. Degeneración determinada con entrenamiento: identidad de sesión. Fallo numérico de aplicación: identidad únicamente de ese origen, no cambio de los anteriores. No se descarta una calibración finita por mal resultado. Se informan QLIKE original/recalibrado por conjunto y contrastes pareados aparte, nunca se sustituye el primario.

## 5. Estimandos de cola, exclusivamente secundarios

Mismas variables, fechas, máscaras causales y bloque interno de diez sesiones. Cada familia produce:

- Cuantil 0.90 de log RV30 y pérdida pinball `u*(0.90−I[u<0])`, con u=log RV30 menos cuantil pronosticado. Delta positivo = pérdida base menos ampliada. Familia lineal: regresión cuantílica convexa con penalización L2 de pendientes (suma pinball + lambda L2), mismo preprocesado y rejilla lambda, selección por pinball igual-activo/sesión, empate lambda mayor; sin Duan; mismas cotas percentiles lineales traducidas a log. LightGBM: objetivo nativo quantile, alpha 0.90, misma rejilla hojas/rounds/paciencia y selección pinball; sin Duan, clip log [-30,30].
- Clasificación `jump30>0`: logit L2 con intercepto no penalizado y preprocesado/rejilla lambda lineales; LightGBM binary con la misma rejilla y controles. Selección por logloss igual-activo/sesión, no por AUC de evaluación. Sin pesos de clase. Si el entrenamiento sólo contiene una clase, pronóstico de frecuencia empírica de entrenamiento; probabilidades limitadas a [1e-12,1−1e-12], con diagnóstico. AUC se calcula fuera de muestra por conjunto, pooling de orígenes con peso uno y empate 0.5; delta positivo = AUC ampliado menos base.

Se utilizan los [objetivos nativos documentados de LightGBM](https://lightgbm.readthedocs.io/en/latest/Parameters.html), sin instalar dependencias. Logit: L-BFGS-B de SciPy, gradiente exacto, maxiter 1000, gtol 1e-8, ftol 1e-12. Cuantil lineal: ADMM del objetivo pinball exacto, no suavizado, rho inicial 1 en escala suma, máximo 5000 iteraciones, tolerancia absoluta 1e-5 y relativa 1e-4; residual dual/tolerancia expresados para el objetivo dividido por N (mismo minimizador). Balance residual cada 25 iteraciones, razón 10/factor 2. Warm start determinista entre lambdas descendentes sólo dentro del mismo inner_fit; refit independiente iniciado en el cuantil incondicional de entrenamiento. Se conservan iteraciones, rho, residuales, tolerancias y convergencia.

Un fallo de cálculo/convergencia no es un ajuste válido: se documenta sin seleccionar según pérdida. Se preservan componentes ya calculados; el estimando afectado no produce una falsa cifra y una sesión incompleta se excluye de la comparación común de ese estimando, contada como NO VERIFICABLE. Eso no elimina una sesión válida de otros estimandos. Errores de implementación se reparan y verifican sin retocar esta metodología ni reejecutar componentes válidos.

## 6. Inferencia fijada

QLIKE por origen `RV/f−log(RV/f)−1`; media dentro de activo-sesión, luego igual peso a los activos presentes y a sesiones. Cada contraste es pareado sobre exactamente las mismas filas. Reducción porcentual = 100 × media de delta de sesión / media de pérdida base de sesión. La media QLIKE es el único estimando principal.

Bootstrap circular de bloques de cinco sesiones cronológicas, 9999 réplicas, semilla 20260907, mínimo diez sesiones. Intervalo percentil bilateral 95%; p principal unilateral de nulidad centrada: `(1 + count(T*−T >= T))/(9999+1)`. El signo positivo corresponde siempre a la mejora. El intervalo percentil y ese p no son procedimientos duales exactos.

Por cada familia y ventana: H1 se rechaza si delta>0 y p<=0.05; sólo entonces H2 se prueba formalmente con la misma regla. Si H1 no rechaza, se puede mostrar el p nominal de H2 como diagnóstico, con estado NO_PROBADA_POR_SECUENCIA, nunca como rechazo formal. La afirmación conjunta exige H1 y H2 rechazadas **en ambas familias**; no se elige una familia ganadora. El control de error fijo-secuencial es nominal dentro de la familia y ventana bajo los supuestos del bootstrap; no ajusta toda la búsqueda histórica entre v1/v2/v3.

Secundarios separados: mediana y media recortada simétricamente 5% de cada cola (`floor(.05*N)`), con sus propios estadísticos/bootstrap; p bilateral centrado y Holm de cuatro contrastes (dos por familia) para comparabilidad con v1/v2. DM normal bilateral HAC5, GW con constante y delta de sesión anterior HAC5 como diagnóstico asintótico, y MZ diagnóstico HAC5 de v2 se conservan. Ningún secundario rescata un primario adverso.

Probabilidad posterior delta>0: modelo de trabajo para la media m, `m|delta ~ Normal(delta, HAC5_long_run_variance/N)` y previo plano de delta; `Phi(m/SE_HAC5)`. Es una probabilidad condicional/asintótica plug-in a ese modelo y varianza, no una posterior libre de supuestos ni la proporción de réplicas bootstrap positivas. Varianza no positiva/no finita o menos de diez sesiones: NO VERIFICABLE.

Pinball y AUC usan su propia secuencia unilateral H1→H2 por familia, etiquetada secundaria/no promovible. Para AUC se remuestrean bloques enteros de sesión y las mismas multiplicidades para los tres conjuntos; se recalcula el AUC agrupado en cada réplica, incluyendo comparaciones entre sesiones. El cálculo equivalente por matriz de pares positivos/negativos de sesiones se admite. AUC de muestra de una sola clase es NO VERIFICABLE; si una réplica es monoclase se cuentan esas réplicas y no se finge un intervalo/p válido mediante redibujos o descarte oculto.

## 7. Estratos y estabilidad, sin promoción

Se conservan primera hora, alto flujo (premium medio del día previo por activo, tercil superior aprendido sólo del entrenamiento y mismas reglas de elegibilidad v2), earnings, FOMC y vencimiento mensual; calendario no disponible no se sustituye por falso cero.

Se añaden última hora por `origin_minute>=300`; viernes calendario (proxy del vencimiento semanal, no identificación de vencimiento de cada contrato); tercer viernes con día del mes 15–21. No se desplazan a otra fecha por conveniencia ni se incluyen orígenes inexistentes en sesiones cortas. Desbalance alto: abs(rp4_gamma_imb_near_spot) disponible al inicio de cada ventana pronosticada y mayor que el percentil 2/3 de valores absolutos finitos del **entrenamiento previo del mismo activo**, interpolación lineal. Umbral vacío: estrato no disponible. Se compara descriptivamente alto frente al resto, con hipótesis de mayor aporte B2; no se define umbral mirando la evaluación.

Reportar por activo, tres bloques cronológicos, retirada de cada bloque y últimas 30 sesiones como v2. Tabla de diez días de mayor pérdida por familia/conjunto, desempate fecha ascendente, con signo de ambos contrastes en esos días. No se retiran los días extremos de la media principal.

## 8. Etapas, verificaciones y divulgación

A1 registra este MD, JSON, decisión y hashes antes de materializar/evaluar v3. A2 congela código, insumos, comparación gamma, jump, panel ampliado, cobertura y manifiestos. B2/B3 fijan release de código/datos/configuración y producen checkpoints con escritura exclusiva y hashes por sesión/componente. Reiniciar sólo verifica/reutiliza componentes válidos; no vuelve a afinarlos. Agregación de checkpoints no es nueva evaluación. Pruebas sintéticas de causalidad, transformaciones, convergencia, MZ, bootstrap y secuencia preceden a la evaluación real. Ninguna prueba sintética cuenta como éxito empírico.

B4 presenta v1/v2/v3 lado a lado, N, media/intervalo/p unilateral v3 y bilateral/Holm comparable, porcentaje QLIKE, coberturas, secundarios, AUC/pinball, cotas, extremos, dos figuras de pérdidas acumuladas por contraste y todas las limitaciones efectivamente encontradas. Cada etapa registra comando exacto, exit code y hashes de artefactos nuevos, con commit local. Fuentes licenciadas y predicciones por origen permanecen en la raíz privada de RP4 v3. Nada se publica con esta autorización.

Divulgación solicitada: La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 con otra especificación. El PIT es proxy de tiempo fuente a 120 s, no prueba de disponibilidad histórica para el cliente.

Se declara además el hueco UW 2025-01-25 a 2025-02-24, la reutilización/adaptación entre versiones, las limitaciones del lado agresor/multileg, el jump RV−BPV y la inferencia condicionada a dependencia y momentos adecuados. Un resultado adverso no se oculta ni prueba equivalencia sin margen registrado.
