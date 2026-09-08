# RP4 v4 — horizonte del flujo, especificación final

Propietario: Miguel. Decisión 133. Registro nuevo, previo a construir RV15/RV5 y a cualquier ajuste v4; no modifica v1/v2/v3. Etiqueta: «fuera de muestra walk-forward, partición fijada 2026-09-07». RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false.

## Antecedente, disparador y alcance

Se adopta íntegro el prerregistro condicional local `../../artifacts/rp4_v4_prereg/protocol.md`, SHA-256 `6f8ad8d53a8f4336851415a99c25b316bf44db74165e29246110a3bb133eabee`. Su archivo y sidecar coinciden. La fecha del contenido es 2026-09-07 20:20 Sydney; los metadatos locales son anteriores al ajuste primario v3, pero no constituyen un sello temporal independiente. El disparador se cumple: H2 no rechazada en ninguna familia primaria v3 (ridge 0.0525; LightGBM 0.6631).

Único cambio científico respecto de v3: horizonte del objetivo. Primario `rv_15`; secundario registrado `rv_5`. Se excluyen de v4 los endpoints cuantil, salto y recalibración/diagnóstico MZ. No se usa RV30 como objetivo de ningún ajuste v4. Los secundarios QLIKE robustos, temporales y de régimen se conservan.

## Datos, conjuntos y muestra

Panel inmutable: `private-input/1e60e265a1b78b1b0a71`, SHA-256 `a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637`. Se heredan literalmente las listas `feature_sets`, transformaciones, columnas obligatorias y opcionales de la especificación efectiva v3, SHA-256 `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5`. El JSON v4 vuelve a enumerarlas para ejecución: B0/B1/B2 anidados con 29/69/138 predictores. Se mantienen los rezagos `rv_back_*`, HARQ, gamma, NaN, indicadores de presencia y ventana vacía, sin recalcular ni seleccionar predictores.

Se conserva exactamente la elegibilidad v3 por claves `(asset, session_date, origin_minute)`, incluidos sus controles de calidad y RV30 válido ya fijados. También se conservan los límites de disponibilidad del objetivo original de 30 minutos para las máscaras de entrenamiento y validación: es la opción conservadora que aísla el horizonte sin ampliar la muestra ni anticipar entradas al entrenamiento. Los objetivos nuevos deben ser finitos y positivos en todas esas filas; cualquier incumplimiento se censará y se investigará antes de evaluar, nunca se excluirá silenciosamente ni se imputará. Las claves y filas no elegibles permanecen en el archivo de objetivos y en el censo.

Partición 2026-08-01. Primaria: 2024-08-02 a 2026-07-31, primeras 60 sesiones sólo entrenamiento; programación heredada de 419 sesiones evaluables. Confirmación: 2026-08-03 a 2026-09-04, 25 sesiones. No se lee ningún dato nuevo del proveedor. Fase 9 y archivos congelados no se modifican.

## Derivación y validación de objetivos

Para cada clave del panel, construir RV_h = suma de cuadrados de retornos logarítmicos futuros de un minuto, h=15 o 5, con `research.rp2.realized.log_returns/forward_measures`, las mismas barras, rejillas y convenciones de RP4 RV30. Exigir h+1 cierres observados y los controles de calidad heredados; no rellenar precios faltantes. El instante final nuevo es origen+h y debe quedar dentro del límite original origen+30. No ejecutar el CLI Block3 que también ajusta modelos; usar únicamente sus funciones de medición.

Objetivos en archivo nuevo separado, unión uno-a-uno por claves, nunca por posición. Comparar contra `registered_runs/rp2_v3/rp2-v3-20260901-flow-session-loss-registration/rp2_block3_target/target_panel.parquet` (SHA-256 `fdab55c524a6ee2cd94bb3f1f544dec527e1c8813f9a03d6e17ed8029f842831`), columnas rv_15/rv_5, hasta 2026-07-17. «Byte a byte» significa representación Float64 de cada par finito alineado, no bytes del contenedor Parquet: reportar N, máscaras de finitud, diferencias máxima/media, discrepancias y causas. Una diferencia no se pasa por tolerancia sin investigarla antes de evaluar. La confirmación carece de referencia previa y se declara así.

## Modelos y control temporal, sin cambios de procedimiento

Walk-forward expansivo por sesión, seis activos agrupados con efectos fijos, pesos de ajuste iguales por origen. Purga y embargo 60 minutos y últimas diez sesiones de entrenamiento para afinado, con las máscaras causales conservadoras anteriores. Ninguna estadística de evaluación decide transformaciones, hiperparámetros o cotas.

Ridge logarítmica: transformaciones v3, mediana sólo de entrenamiento para opcionales, indicadores de presencia, estandarización media/desviación poblacional de entrenamiento, winsorización ±5, eliminación de varianza cero/colinealidad mediante QR pivoteado con tolerancia 1e-10. Lambda entre [0.0001, 0.01, 1, 100, 10000], QLIKE de validación, empate a mayor lambda; Duan con residuos de entrenamiento. Cotas [0.5 × P1, 2 × P99], cuantiles lineales del objetivo seleccionado en el entrenamiento vigente, no de RV30; reportar contactos de validación y evaluación por sesión/conjunto. Reusar `v3.models.fit_ridge` con el vector objetivo explícito.

LightGBM QLIKE sobre log-pronóstico: hojas 15/31/63, tasa 0.05, mínimo 100 por hoja, max_bin 63, máximo 2.000 rondas, paciencia 50, últimas diez sesiones, empate a menos hojas y rondas. Inicialización log de la media del objetivo seleccionado de entrenamiento; una sola aplicación de la escala inicial. Semilla 20260907, determinista, cuatro hilos. Se reutiliza el primario v2, idéntico al primario v3, sin invocar el secundario MZ. Reportar ronda y hojas elegidas por sesión.

## Inferencia y secundarios

QLIKE = y/f − log(y/f) − 1. Media de orígenes por activo/sesión, luego media igual de activos y sesiones. Delta = pérdida base − ampliada. Reducción porcentual = 100 × media(delta) / media(pérdida base). Por familia y ventana: H1 B1/B0 > 0 al 5%; H2 B2/B1 > 0 sólo si H1 rechaza, también al 5%; se exige estimación positiva. H2 cerrada conserva p nominal diagnóstico, no p formal. Se mantienen bootstrap circular de bloques de cinco sesiones, 9.999 réplicas, semilla 20260907, prueba unilateral con nula centrada y corrección +1, IC95% percentil bilateral y mínimo diez sesiones.

Secundarios no promovibles: mediana pareada y media recortada 5% por cada cola (floor), con su bootstrap; p bilateral/Holm de cuatro contrastes por ventana para comparabilidad; posterior gaussiana condicional de la media con previo plano y varianza HAC5 plug-in; DM y GW diagnósticos de sesión heredados; activos, tres bloques cronológicos, retirada de cada bloque y últimas treinta sesiones. Ninguno sustituye la decisión primaria.

Regímenes heredados: primera hora, última hora origen≥300, viernes calendario como proxy de vencimiento semanal, tercer viernes, alto flujo según prima del día anterior y tercil calculado sólo en entrenamiento, alto desbalance gamma absoluto disponible al origen con umbral de entrenamiento, earnings/FOMC/vencimiento mensual. Calendario desconocido no equivale a ausencia. Censo de ventanas vacías 5/30 minutos y contraste dentro/fuera, sin exclusión por vacío; contraste alto gamma frente al resto. Diez días de mayor pérdida por familia/conjunto, con signos de ambos contrastes y desempate por fecha. Todos los signos se reportan.

## Orden, rendimiento y custodia

Una evaluación lógica por ventana y horizonte: RV15 primaria, RV15 confirmación, RV5 primaria, RV5 confirmación. Ocho shards disjuntos por sesión y cuatro hilos cada uno (máximo 32 hilos), cada shard con acceso al pasado completo permitido; no ocho modelos distintos ni partición del entrenamiento. Se adopta directamente la configuración autorizada, sin ensayo adicional sobre ventanas evaluadas. Resumir tiempo real y recursos; cinco horas es objetivo operativo, no promesa de resultado o duración.

Reanudar sólo componentes cuyo checkpoint íntegro coincide con especificación, código, objetivo, panel y claves, sin repetir ajustes completos; raíz y binding separados por horizonte/ventana. Release con hashes antes de ajustar, comandos y códigos de salida por etapa. Los arreglos de secundarios v3 quedan fuera del release v4, con prioridad baja y máximo dos hilos, sin cambiar el presupuesto de v4. No publicación, descargas, colectores ni v5.

## Cierre y límites

Si RV15 primaria rechaza H2 en al menos una familia tras H1, se reporta como resultado de esa familia y RV5 sólo como secundario. Se informa además si ambas familias rechazan; «al menos una» no tiene por sí solo control global 5% entre familias, ni entre versiones. Si ninguna rechaza, se cierra la investigación de este mecanismo con B1>B0 como resultado principal observado a 30 minutos y B2 no detectado a 30/15/5 según cada estimación e intervalo. No rechazo no establece equivalencia a cero ni absorción causal; «nulo informativo» describe el cierre, no una prueba de ausencia.

El informe compara v3 y v4 y declara la cuarta evaluación de las mismas ventanas: v1 diseño inicial; v2 cobertura/capacidad/regularización; v3 mecanismo y ventanas vacías; v4 horizonte condicional predeclarado. Las comparaciones de horizontes son descripciones de estimandos distintos, no replicaciones independientes.

La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 con otra especificación. El PIT es proxy de tiempo fuente a 120 s, como en la literatura.

Hueco UW aceptado: 2025-01-25 a 2025-02-24, sin relleno. La fijación local de v4 no elimina la búsqueda adaptativa previa ni demuestra disponibilidad histórica al cliente o inventarios reales de dealers.
