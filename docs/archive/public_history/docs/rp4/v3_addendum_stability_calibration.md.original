# RP4 v3 — addendum registrado de estabilidad y recalibración

Fecha: 2026-09-07. Autoridad: los dos cambios solicitados explícitamente por el propietario en esta conversación. Este registro no constituye una firma criptográfica.

## Alcance y estado

Se registran estos cambios para integrar en v3, sin modificar la especificación, código, paneles ni resultados de v1/v2. La referencia comprobada es [specification_v2.md](specification_v2.md), SHA-256 `3f360466d5730defbf14e4d16b9904cdf381624f33215d5ff611f55ea0d2e54c`, y su JSON ejecutable `artifacts/rp4_v2_a1/specification.json`, SHA-256 `08a749049f56a0d1dda09cef1f280328e7c84d59fc39d57e71c48caee81670a5`.

Estado: **ADICIONES REGISTRADAS; ESPECIFICACIÓN COMPLETA V3 NO VERIFICABLE**. El encargo anterior de v3 al que se refiere «además de lo ya enviado» no aparece en el historial recuperado ni en los documentos RP4 inspeccionados. No se interpreta un panel candidato como autorización o como especificación completa. Este documento no sustituye ese encargo ni habilita una evaluación incompleta.

Su hash se fija en `artifacts/rp4_v3_addendum_v1/receipt.json`. No se han implementado ni evaluado estos cambios sobre datos reales durante este registro. No hay valores nuevos de QLIKE ni conteos observados de cotas v3.

## 1. Ridge: winsorización de predictores y cotas por percentiles

Para cada sesión pronosticada y cada conjunto B0/B1/B2:

1. Conservar las transformaciones puntuales, codificación de ausencias, mediana de entrenamiento e indicadores de presencia de v2. No winsorizar el objetivo RV30 ni los datos fuente.
2. Estimar media y desviación estándar poblacional exclusivamente en el entrenamiento del ajuste correspondiente, antes de winsorizar. Excluir columnas sin datos o de varianza cero conforme a v2.
3. Para cada predictor estandarizado, aplicar `z_acotado = min(5, max(-5, z))`. Incluye columnas económicas, indicadores y efectos de activo que formen parte de las pendientes; excluye el intercepto. La misma transformación, con las mismas estadísticas de entrenamiento, se aplica al entrenamiento y a las filas que ese ajuste pronostica. No volver a estandarizar después del recorte.
4. Comprobar colinealidad sobre el diseño ya winsorizado antes del ridge, conservando la tolerancia QR relativa `1e-10` y un intercepto no penalizado. Registrar las columnas retenidas y eliminadas; el control debe contemplar dependencias con el intercepto.
5. Sustituir las cotas basadas en mínimo/máximo por `L = 0.5 * P1(RV30_entrenamiento)` y `U = 2 * P99(RV30_entrenamiento)`, con observaciones positivas y finitas, peso igual por origen y percentiles con interpolación lineal (`numpy.quantile(..., [0.01, 0.99], method="linear")`). No se calculan percentiles por conjunto de evaluación ni sobre el panel completo.
6. Aplicar `[L,U]` al pronóstico con corrección de Duan: recortar primero en log-escala a `[log(L),log(U)]`, exponenciar y respetar los extremos lineales para evitar desbordamiento y redondeo fuera de las cotas.

Durante la selección de lambda, medianas, escalas, QR, winsorización, residuos de Duan y percentiles proceden solo de `inner_fit`; las últimas diez sesiones internas reciben esa transformación. Después de seleccionar lambda, se recalculan estos parámetros usando todo el entrenamiento previo para pronosticar la siguiente sesión. Se conservan la rejilla lambda, su criterio QLIKE, desempate, purga y embargo de v2. La sesión pronosticada nunca aporta estadísticas ni objetivos al ajuste.

Registro obligatorio por sesión/conjunto: N de entrenamiento y predicción, P1, P99, L, U, lambda, columnas eliminadas y conteos separados de pronósticos que alcanzan la cota inferior y superior. Se cuenta el pronóstico previo al recorte con `<= L` y `>= U` (o equivalentes logarítmicos), incluyendo igualdades. El informe suma esos conteos y porcentajes por ventana y conjunto; distingue validación interna de evaluación. Se conservan además los conteos de valores de predictores recortados por columna y partición.

## 2. LightGBM: recalibración Mincer–Zarnowitz exclusivamente secundaria

No sustituye el LightGBM primario ni selecciona entre resultados primarios y recalibrados. Se produce una salida secundaria separada para B0, B1 y B2, con la misma máscara, calendario y objetivos de cada ventana.

Para cada sesión pronosticada y conjunto de información:

1. Usar exactamente las últimas diez sesiones elegibles del entrenamiento, nunca la sesión pronosticada. Para esas diez sesiones, conservar las predicciones del candidato LightGBM seleccionado, entrenado en `inner_fit`, anterior al bloque de validación. No usar predicciones ajustadas dentro de muestra del refit que ya incorporó los objetivos de esas diez sesiones.
2. Agregar RV30 y pronóstico a medias de sesión: primero media de orígenes dentro de activo-sesión, después peso igual por activo presente. Ajustar sobre los diez pares de medias la regresión MZ en niveles `media_RV30_d = a + b * media_pronostico_d + error_d`, con intercepto y sin restricciones de signo.
3. Reutilizar el cálculo de coeficientes del diagnóstico MZ de v1: escalar ambas magnitudes por la media positiva del RV30 de esas diez sesiones y resolver mínimos cuadrados con `rcond=1e-10`; devolver el intercepto a las unidades originales. No usar la pendiente global de v2 como factor fijo. La prueba HAC del diagnóstico no determina si se aplica la recalibración.
4. Aplicar `a + b * f` a cada pronóstico por origen del LightGBM final, reajustado con todo el entrenamiento previo según la regla primaria. Mantener el piso numérico `1e-12` para QLIKE y contar cuántos valores lo alcanzan; no aplicar las cotas percentiles exclusivas de ridge a LightGBM.
5. Si no existen los diez pares válidos, el diseño MZ tiene rango menor de dos o los coeficientes no son finitos, usar identidad `(a=0,b=1)` para esa sesión/conjunto, decidida exclusivamente con entrenamiento. Si al aplicar coeficientes válidos aparece un valor no finito en un origen, usar identidad solo para ese origen, sin modificar pronósticos anteriores ni excluir filas. Registrar ambos tipos de respaldo por separado, el motivo y los coeficientes intentados/aplicados. Una calibración finita adversa no activa ese respaldo ni se descarta por su QLIKE.

El bloque de diez sesiones se comparte con el afinado de hiperparámetros: es entrenamiento/validación interna, no una validación independiente adicional. Los coeficientes quedan fijados antes de observar los objetivos de la sesión que se evalúa. El hash previo registra el procedimiento; los coeficientes se estiman causalmente en cada paso.

El informe secundario presenta, para cada ventana y B0/B1/B2, QLIKE original, QLIKE recalibrado, diferencia, reducción porcentual y N de sesiones/orígenes. QLIKE se calcula por origen antes de la agregación original por activo y sesión; no se calcula QLIKE sobre las medias de RV30 usadas para ajustar MZ. Se añaden los dos contrastes pareados recalibrados y se conservan sus signos, sin reemplazar la media primaria ni ampliar o reutilizar su Holm como inferencia del secundario.

Registro por sesión/conjunto: fechas y número de sesiones de calibración, procedencia temporal de sus predicciones, hojas/ronda seleccionadas, coeficientes MZ intentados/aplicados, rango del diseño, motivo de respaldo si existe y conteos del piso. Los QLIKE usados para informar resultados no retroalimentan coeficientes, selección ni aplicación del secundario.

## Evidencia que motiva este añadido, no resultados de v3

En [session_losses.csv](../../artifacts/rp4_v2_b2/session_losses.csv), el 2025-09-18 tiene QLIKE `4.019650448306192` para `log_ridge_harq__B2`, agregado por sesión. En [summary.json](../../artifacts/rp4_v2_b2/summary.json), las pendientes MZ primarias de LightGBM v2 son B0=`1.5515950313514582`, B1=`1.4045448250373596` y B2=`1.5115655752231416`. Son cifras ya cerradas de v2; no se reajustó ningún modelo para verificarlas.

Acotar pronósticos no impone una cota a QLIKE ni garantiza una mejora; la recalibración con diez sesiones puede ser inestable y reutilizar resultados observados para diseñar v3 no convierte sus ventanas en evidencia independiente nueva.

## Verificación exigida al integrar el ejecutor v3

- Pruebas sintéticas de recorte ±5, percentiles con interpolación lineal, ambos extremos y conteos; constantes, colinealidad y ausencias siguen controladas.
- Cambiar objetivos o distribuciones de la sesión pronosticada no altera parámetros aprendidos; cambiar la validación no altera medianas, escalas ni percentiles de `inner_fit`.
- MZ usa solo diez sesiones anteriores y predicciones del ajuste previo a ellas; pruebas de identidad por degeneración y del piso positivo. Un fallo numérico de un origen posterior no cambia ningún pronóstico anterior. QLIKE se agrega desde pérdidas por origen y las filas son idénticas entre original/recalibrado.
- Reportar resultados primarios y secundarios por separado, cualquier signo, comandos, códigos de salida y hashes. No sobrescribir ni reejecutar v1/v2.

Estas son condiciones de aceptación de la implementación futura, no pruebas ejecutadas por este registro. No se cambian fuentes, variables, ventanas, inferencia primaria, colectores ni publicaciones con este añadido. RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false.
