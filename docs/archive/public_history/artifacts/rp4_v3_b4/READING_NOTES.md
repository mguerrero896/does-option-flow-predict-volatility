# RP4 v3 — notas de lectura y límites de los secundarios

Estas notas acompañan al [informe principal](../../../../rp4/results_v3.md) y no modifican la especificación, los modelos, las ventanas ni sus resultados. Se añaden para hacer explícitas distinciones del [contrato registrado](../../docs/rp4/specification_v3.md) que no deben perderse al leer las tablas.

## Fallo numérico, falta de inferencia y falta de rechazo son distintos

Un ajuste que agota el límite de convergencia registrado no produce un pronóstico certificado para ese estimando. Una sesión incompleta se contabiliza como NO VERIFICABLE para la comparación común del secundario afectado: no se convierte en una pérdida cero, una AUC de 0,5 ni evidencia de ausencia de efecto. Tampoco se elimina por ello de los otros estimandos que sí se calcularon. Los conteos y las causas por ventana están en el informe y en sus agregados.

Una AUC calculada sólo representa los orígenes y sesiones completos de ese estimando, no automáticamente las 419 sesiones primarias o las 25 de confirmación. Además, un punto estimado puede carecer de intervalo o p verificable por insuficiencia de sesiones o réplicas monoclase. Eso es distinto de un contraste calculado que no rechaza su hipótesis nula; este último tampoco prueba equivalencia o absorción sin un margen y prueba de equivalencia registrados.

En [primaria](../../../../../artifacts/rp4_v3_b2/summary.json), 418 sesiones de salto quedaron incompletas por agotamiento de las 1.000 iteraciones de la logística. Sólo el 20 de diciembre de 2024 quedó completo (390 orígenes): su AUC puntual no representa las 419 sesiones y no tiene inferencia suficiente. QLIKE y el cuantil sí conservaron las 419 sesiones y 160.832 orígenes.

En [confirmación](../../../../../artifacts/rp4_v3_b3/summary.json), las 25 sesiones de salto quedaron incompletas por el mismo límite; no hay AUC verificable. QLIKE y el cuantil sí conservaron las 25 sesiones y 9.750 orígenes. Por tanto, **la hipótesis del flujo sobre saltos no queda resuelta por esta ejecución**.

La [auditoría logística sintética](logistic_numerical_audit/README.md) comprueba el gradiente y reproduce el agotamiento de 1.000 iteraciones en un diseño mal condicionado. No demuestra el condicionamiento del panel real, no cambia el solver y no recupera como válidos los ajustes fallidos.

## La recalibración MZ empeora gravemente el pronóstico

En primaria, la recalibración afín registrada `max(intercepto + pendiente * pronóstico, 1e-12)` genera valores negativos antes de aplicar el piso. El recálculo de las 482.496 predicciones almacenadas (160.832 orígenes por tres conjuntos) coincidió exactamente con esa fórmula; no se demostró un error de escala ni de aplicación del intercepto. [Script de comprobación sin reajustes](../../../../../artifacts/rp4_v3_b4/audit_mz_identity.py) · [comando, código de salida, hashes y resultados](../../../../../artifacts/rp4_v3_b4/mz_identity_receipt.json). Que los diez pares de calibración sean válidos no garantiza positividad al aplicar la recta a cada origen.

| Conjunto LightGBM | QLIKE original | QLIKE recalibrado | Orígenes en el piso | Porcentaje de 160.832 |
|---|---:|---:|---:|---:|
| B0 | 0,149317 | 635.736,361672 | 18.631 | 11,5841 % |
| B1 | 0,146194 | 711.247,777085 | 20.834 | 12,9539 % |
| B2 | 0,146427 | 730.463,855331 | 21.100 | 13,1193 % |

Son resultados adversos reales del secundario: el cociente RV30/pronóstico se dispara cuando el denominador llega a `1e-12`. No se reemplaza la fórmula, no se cambia el piso ni se vuelven a ajustar modelos tras verlos. El pronóstico principal permanece intacto. Los valores por ventana se conservan en el [informe](../../../../rp4/results_v3.md), en el [agregado de primaria](../../../../../artifacts/rp4_v3_b2/summary.json) y en los [coeficientes, pisos y fallbacks por sesión](../../../../../artifacts/rp4_v3_b4/mz_calibration.csv).

En confirmación, QLIKE original → recalibrado es 0,174940 → 0,186231 en B0; 0,172026 → 1.988,177283 en B1; y 0,176179 → 2.400,218830 en B2. Los conteos de piso respectivos son 0, 9 y 11 de 9.750 orígenes. La auditoría de identidad por origen enlazada arriba tiene alcance de primaria; no se presenta como auditoría independiente de confirmación.

## Qué identifica el indicador de salto

El objetivo solicitado es `jump30 > 0`, con `jump30 = max(RV30 - BPV30, 0)` del productor registrado. Identifica únicamente la diferencia positiva entre RV30 y BPV30; **no es una prueba estadística formal de salto**. La AUC evalúa la clasificación de ese indicador concreto, no demuestra por sí sola identificación de saltos económicos ni predicción de cualquier cola.

## Qué identifica el secundario de vencimiento semanal

`weekly_expiration` selecciona viernes calendario. Es un proxy registrado, no una verificación de vencimiento de cada contrato. `third_friday` selecciona el tercer viernes calendario. No se desplazan fechas después de mirar resultados.

## Un promedio positivo no implica estabilidad general

El desglose `robustness` del [agregado de primaria](../../../../../artifacts/rp4_v3_b2/summary.json) conserva todos los activos, bloques cronológicos y retiradas de bloque. B1 mejora en los seis activos con ambas familias; B2 mejora en cuatro de seis con ridge y en tres de seis con LightGBM. El contraste B2 sobre B1 de ridge es negativo en el segundo bloque cronológico (−0,000304540); el de LightGBM es negativo en los dos primeros (−0,001577603 y −0,000113651). Son desgloses descriptivos ya calculados, no nuevas pruebas ni criterios elegidos para reemplazar la media principal.

La media QLIKE y su secuencia H1 → H2 constituyen la prueba principal registrada; cuantil, AUC, estratos, recalibración y diagnóstico de ventanas vacías son secundarios no promovibles. Las versiones reutilizan datos y sus ajustes metodológicos se eligieron tras conocer resultados anteriores: los p de v3 no corrigen toda esa búsqueda histórica.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false. Nada de este cierre autoriza publicación o inversión.
