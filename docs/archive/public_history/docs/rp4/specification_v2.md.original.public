# RP4 v2 — especificación previa a la evaluación

Fecha de registro: 2026-09-07. Decisión: [130](decision_130_v2.md).
Etiqueta conservada: **fuera de muestra walk-forward, partición fijada 2026-09-07**.
Esta versión se evalúa una sola vez por ventana; v1 conserva sus archivos, resultados y hashes.

## Contrato heredado e insumos

Se hereda el contrato ejecutable v1 `artifacts/rp4_a1/specification.json`, SHA-256
`865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5`, excepto las modificaciones enumeradas abajo.
Las listas exactas y el resto de parámetros se materializan en `artifacts/rp4_v2_a1/specification.json`.
El SHA-256 de este Markdown y del JSON quedan vinculados en `artifacts/rp4_v2_a1/freeze.json` antes de construir el panel v2 o ajustar modelos sobre datos reales.

Insumos locales, sin nuevas descargas:

| Insumo v1 | SHA-256 |
| --- | --- |
| `a2_combined_v2/panel.parquet` | `51f04c5937a7922757f929ef0ca53941b7766719cf2799673669f8545f97a949` |
| `b1_complete_v1/panel.parquet` | `ecb1c6cce76cb6464d3cdf3d4ef409c60e204adf2df22fba6851e32199819d93` |

Sus ubicaciones permanecen bajo la raíz de ejecución RP4 v1. Las fuentes UW, barras, tipos y dividendos son exclusivamente las identificadas por los recibos de v1; se verifican sus hashes. No se descubre un corpus posterior ni se rellena el hueco UW 2025-01-25–2025-02-24.
El panel derivado y todos los pronósticos por origen permanecen bajo `private-input/c153d5c8978c23bc439f`, sin sobrescribir v1.
Claves: `(asset, session_date, origin_minute)`, únicas; todas las uniones son por clave, nunca por posición.
Se conservan exactamente B0, HARQ, RV30, relojes, compuerta `rp4_eligible` y estratos secundarios de los paneles originales.

## Calendario, validación y métrica: sin cambios

Activos: AAPL, AMZN, META, MSFT, NVDA y TSLA; controles SPY y QQQ.
Desarrollo/primaria: 2024-08-02–2026-07-31, primeras 60 sesiones del panel solo entrenamiento.
Confirmación: 2026-08-03–2026-09-04. Partición: 2026-08-01.
Walk-forward expansivo por sesión, activos agrupados con los mismos cinco efectos fijos de activo, ajuste con peso igual por origen.
Cada sesión se pronostica solo con sesiones previas. Purga y embargo de 60 minutos, conservando `causal_masks` de v1.
Las últimas diez sesiones de entrenamiento forman la validación interna; ninguna observación de la sesión pronosticada participa en selección, imputación, escalado, descarte de columnas, límites o calibración.
El ajuste final usa todo el entrenamiento elegible anterior a la sesión, con los hiperparámetros ya seleccionados.

Se conserva la lista de fechas programadas por la ventana y el warmup, no la lista de exclusiones de v1: v1 programó 419 sesiones primarias y ejecutó 418. Si la nueva regla recupera 2025-10-20, se incluye y se declara el N distinto; no se elimina para forzar igualdad con v1.
Dentro de cada versión, todas las familias y conjuntos de información usan la misma máscara elegible.

QLIKE es `y/f - log(y/f) - 1`, con y=RV30 y f=varianza pronosticada, ambas positivas.
La agregación sigue: promedio de orígenes dentro de activo-sesión, promedio igual entre activos disponibles, promedio igual entre sesiones.
Contrastes: `loss(B0)-loss(B1)` y `loss(B1)-loss(B2)`; positivo significa mejora.
Reducción porcentual: `100 * media(delta_por_sesion) / media(perdida_base_por_sesion)`.
La puntuación de validación interna usa la misma agregación por activo/sesión.

## 1. Obligatoriedad y valores ausentes

Obligatorios: exclusivamente los 22 predictores B0 registrados y siete HARQ de v1 (29 entradas), además de un RV30 positivo/finito, claves/relojes válidos y compuerta de calidad original.
Se eliminan `b1_implied_rate`, `b1_implied_dividend_yield` y `b1_pcp_residual` de cualquier diseño v2; el último ya estaba excluido del diseño activo v1.
Todos los demás predictores activos admiten NaN. Los valores no finitos opcionales se codifican como ausentes; no se fabrican datos de mercado.
LightGBM conserva su manejo nativo de NaN. La familia lineal agrega un indicador de presencia por predictor opcional e imputa por mediana de entrenamiento, después de las transformaciones puntuales de v1 y antes del escalado.
Si una columna no tiene ningún valor finito en entrenamiento, se elimina en ese ajuste y se registra: no se inventa su mediana. Su indicador constante también se elimina.

## 2. LightGBM QLIKE con parada temprana

La familia y el objetivo QLIKE en log-varianza son los de v1. Se conserva el init-score `log(media_RV30_entrenamiento)`, `max_bin=63`, semilla 20260907, cuatro hilos, determinismo, columnas completas, sin bagging y `zero_as_missing=false`.
Nueva rejilla de hojas: 15, 31, 63; `learning_rate=0.05`, `min_data_in_leaf=100`.
Cada candidato se entrena con tope de 2.000 rondas y paciencia de 50 rondas sin mejora estricta de QLIKE en las diez sesiones internas; se conserva su mejor ronda.
El callback de validación usa el mismo desplazamiento inicial que el objetivo, sin sumarlo dos veces.
Se eligen hojas y ronda por QLIKE de validación mínimo; empate: menos hojas, luego menos rondas.
Se reajusta sobre todo el entrenamiento exactamente hasta la ronda elegida. Se registran candidatos, mejor ronda y puntuación por sesión/conjunto de información.
Se mantienen los límites numéricos v1 exclusivos de esta familia: log-pronóstico [-30,30] y piso de varianza 1e-12.

## 3. Diagnósticos fuera del diseño y fe de erratas

Se excluyen expresamente los nueve nombres:

`b2_5m_late_arrival_share`, `b2_30m_late_arrival_share`,
`b2_5m_mean_provider_latency_s`, `b2_30m_mean_provider_latency_s`,
`b2_5m_is_empty_window`, `b2_30m_is_empty_window`,
`b2_5m_observed_span_s`, `b2_30m_observed_span_s`, `b1_median_quote_age_s`.

Las exclusiones adicionales ya fijadas por v1 siguen vigentes; no se reincorpora ningún predictor.
Verificación del diseño ejecutado: de estos nueve, solo los dos `observed_span_s` estaban activos; los otros siete figuraban en listas nominales, pero estaban excluidos antes del ajuste.
La fe de erratas adjunta al informe v2 corrige la frase absoluta de v1 sobre ausencia de diagnósticos: sí entraron ambos `observed_span_s`. No se modifica el informe v1 ni se afirma que se usaron columnas que el ejecutor excluyó.
Conjuntos anidados v2: B0=29; B1=69 (29+14 B1 activos+25 celdas+conteo); B2=132 (69+60 B2 activos+3 dealers), más los mismos efectos fijos de activo. Los indicadores lineales no se cuentan como variables económicas nuevas.

## 4. Familia lineal log-ridge HARQ

Se sustituye OLS por ridge; esta es la única sustitución de familia solicitada. Identificador v2: `log_ridge_harq`. Se conservan objetivo log(RV30), transformaciones por predictor y corrección de retransfomación de Duan calculada solo con residuos de entrenamiento.
Medianas, medias y escalas se ajustan en el subconjunto que se está entrenando; pendientes estandarizadas con desviación poblacional, intercepto separado y no penalizado.
Se eliminan columnas de varianza cero y dependencias lineales mediante QR con pivote sobre pendientes estandarizadas, tolerancia relativa 1e-10; se registra la selección de columnas por ajuste.
Objetivo: suma de errores cuadrados en log(RV30) más `lambda * suma(coeficientes_pendiente^2)`.
Rejilla lambda fijada: 0.0001, 0.01, 1, 100, 10000; cubre escalas logarítmicas sin elegirla a partir de resultados v2.
Selección en las diez sesiones internas por QLIKE; empate exacto: lambda mayor.
Pronóstico acotado a `[0.1 * min(RV30_entrenamiento), 10 * max(RV30_entrenamiento)]`, con RV30 positivo/finito del ajuste correspondiente. Esto interpreta «0.1 y 10 veces el rango» como límites inferior/superior del intervalo observado, no como su amplitud.
El acotamiento se aplica en log-escala antes de exponenciar para evitar desbordamiento. La selección interna usa sus propios límites, no los del refit posterior.
Se reportan límites, cantidad de pronósticos que alcanzan cada cota, lambda y columnas eliminadas por sesión/conjunto de información.

## 5. Colas y secundarios: sin sustituir la media primaria

Se conservan primera hora, alto flujo por prima del día anterior y eventos de v1 con sus estados de disponibilidad; no se recalculan los estratos para que cambie su pertenencia debido al filtro IV.
Se añaden como secundarios, por ventana/familia/contraste, la mediana de los contrastes pareados por sesión y la media recortada simétrica al 5 %: ordenar los N contrastes y retirar `floor(0.05*N)` de cada cola.
Se distinguen expresamente mediana de diferencias y diferencia de medianas; no son el mismo estimando.
Se presentan diez sesiones de mayor QLIKE por familia y conjunto de información, orden descendente de pérdida y fecha ascendente para empates, incluyendo las pérdidas B0/B1/B2 y el valor/signo de ambos contrastes en cada día.
No se elimina ninguna sesión extrema de la evaluación ni se cambia el estimando primario, bootstrap, Holm o umbral de decisión por estos secundarios.

## Filtro IV por operación antes de agregar

IV debe ser finita y pertenecer al intervalo cerrado [0.03,3]. Se descartan las filas que incumplen antes de la agregación de las tres rutas: superficie B1, flujo B2 y nuevas rejilla/dealers.
Se conservan todas las demás reglas del productor original, relojes de 120 s sobre `created_at`, ventanas, pesos y deduplicación; se computan las salidas solo sobre las fuentes de v1 verificadas por hash.
Como el filtro actúa sobre filas, también puede cambiar primas, conteos e intensidad agregada: es una consecuencia declarada del universo filtrado, no un nuevo método ni una redefinición de sus fórmulas.
Se reportan por activo/sesión: filas originales, IV ausente/no finita, fuera del intervalo, aceptadas y porcentaje descartado; también descarte incremental respecto al intervalo anterior [0.01,5]. No se deducen esos porcentajes solo de las celdas finales.
Las griegas históricas B2 conservan su fórmula original; los nuevos dealers conservan tasas/dividendos exógenos reales de v1. No se introduce una corrección adicional de carry histórico.
La reconstrucción comprueba por clave que objetivos, B0/HARQ, tiempos, compuerta de calidad y estratos no cambiaron. No se abre otra fuente o ventana.

## Inferencia y entrega: sin cambios

Bootstrap circular de bloques de cinco sesiones, 9.999 replicaciones, semilla 20260907, intervalo percentil 95 % y p bilateral bajo nulo centrado con corrección +1.
Holm: cuatro contrastes por ventana (dos incrementos por dos familias), alpha=0.05, sin cambio respecto a v1. DM con HAC5; GW con constante y contraste rezagado, diagnóstico asintótico; Mincer-Zarnowitz sobre medias de sesión, prueba conjunta intercepto=0/pendiente=1, HAC5.
Se conservan los desgloses v1 por activo, tres bloques temporales, retiro de un bloque y últimas 30 sesiones.
La inferencia reutiliza las funciones v1 sin cambiar su matemática; el adaptador solo identifica explícitamente la familia lineal nueva.

Entregas sucesivas: registro/hash; materialización IV y cobertura; primaria v2; confirmación v2 sin alterar la especificación; `results_v2.md` con tablas v1/v2 lado a lado, cobertura por activo/ventana, secundarios, cotas, rondas y fe de erratas.
Se informa cada comando, código de salida y SHA-256 de artefactos. Los checkpoints completos no se reemplazan: reanudar tras interrupción solo puede cargar los mismos bytes/pins, sin recalcular sesiones completadas. Correcciones de un error de implementación se registran antes de cualquier reanudación afectada; no se cambia el método por un resultado adverso.
No se cambian v1, phase9, el colector, main ni el PR existente; no se publica v2 en esta ejecución.

Limitación: v2 responde a una auditoría de resultados ya observados; un nuevo hash y una sola ejecución no eliminan esa selección adaptativa, y Holm por versión no controla la búsqueda entre v1 y v2 ni demuestra disponibilidad histórica más allá del proxy temporal.

RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false.
