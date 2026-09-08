# RP4 v3 — cierre B4, revisión de secundarios 2

Esta revisión documenta los dos pases secundarios de salto y su resultado final combinado; conserva también íntegra la evidencia del primer pase. No cambia los resultados primarios, cuantiles, máscaras, ventanas ni la recalibración MZ. Las tablas completas v1/v2/v3, cobertura, regímenes, extremos y figuras permanecen en el [informe original](../../../../rp4/results_v3.md).

fuera de muestra walk-forward, partición fijada 2026-09-07.

## Resultado primario sin cambios

Delta = QLIKE base menos ampliado; reducción = 100 × delta / QLIKE base. IC95% bilateral por bloques; p unilateral de la secuencia H1 → H2. Las ocho filas siguientes se conservan byte a byte de la revisión 1; los dos agregados originales se verifican por SHA-256.

| Ventana | Familia | Contraste | Delta | IC95% | Reducción % | p unilateral nominal | Decisión | N sesiones/orígenes |
|---|---|---|---:|---|---:|---:|---|---|
| Primaria | Ridge | B1/B0 | +0.0025468959 | [0.0005570053, 0.0055407196] | +1.7289745 | 0.0439 | H1 rechazada | 419/160832 |
| Primaria | Ridge | B2/B1 | +0.0008023897 | [-0.0001534347, 0.0017735437] | +0.5542902 | 0.0525 | H2 no rechazada | 419/160832 |
| Primaria | LightGBM | B1/B0 | +0.0031224859 | [0.0010149407, 0.0054860165] | +2.0911798 | 0.0053 | H1 rechazada | 419/160832 |
| Primaria | LightGBM | B2/B1 | -0.0002326470 | [-0.0016475987, 0.0008319668] | -0.1591353 | 0.6631 | H2 no rechazada | 419/160832 |
| Confirmación | Ridge | B1/B0 | +0.0009113921 | [-0.0028274372, 0.0039476574] | +0.5010983 | 0.3238 | H1 no rechazada | 25/9750 |
| Confirmación | Ridge | B2/B1 | +0.0033669574 | [-0.0007443023, 0.0102227627] | +1.8605313 | 0.1612 | H2 no abierta; p sólo diagnóstico | 25/9750 |
| Confirmación | LightGBM | B1/B0 | +0.0029141581 | [-0.0016852924, 0.0074221881] | +1.6658018 | 0.1104 | H1 no rechazada | 25/9750 |
| Confirmación | LightGBM | B2/B1 | -0.0041525214 | [-0.0103787975, 0.0000249181] | -2.4138902 | 0.9266 | H2 no abierta; p sólo diagnóstico | 25/9750 |

Fuente: [primaria original](../../../../../artifacts/rp4_v3_b2/summary.json) y [confirmación original](../../../../../artifacts/rp4_v3_b3/summary.json). La conjunción primaria registrada no se satisface en ninguna ventana. Ningún secundario sustituye la media ni convierte estas ventanas en una réplica independiente.

## Salto: resultado final combinado tras la resolución numérica

Estas tablas usan los componentes completos del primer pase sin cambiarlos y las salidas del pase Newton exclusivamente para los fallos que eran elegibles. La AUC es la salida guardada del mismo agregador secundario v3: 9.999 remuestreos por bloques de sesión y secuencia unilateral H1 → H2 por familia. No se elige entre los dos pases por su AUC. Los valores del primer pase se conservan a continuación como registro de ejecución, no como otra réplica independiente.

| Ventana | Familia | Conjunto | AUC final | IC95% | N sesiones | N orígenes | Réplicas monoclase | Estado | Motivo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primaria | Lineal (logit) | B0 | 0.52176107 | [0.51485246, 0.52832978] | 419 | 160832 | 0 | COMPUTED | — |
| Primaria | Lineal (logit) | B1 | 0.52040811 | [0.51364844, 0.52686781] | 419 | 160832 | 0 | COMPUTED | — |
| Primaria | Lineal (logit) | B2 | 0.51921636 | [0.51284587, 0.525429] | 419 | 160832 | 0 | COMPUTED | — |
| Primaria | LightGBM (binary) | B0 | 0.51706132 | [0.51101359, 0.52277029] | 419 | 160832 | 0 | COMPUTED | — |
| Primaria | LightGBM (binary) | B1 | 0.51567879 | [0.50961469, 0.52142034] | 419 | 160832 | 0 | COMPUTED | — |
| Primaria | LightGBM (binary) | B2 | 0.51614095 | [0.51006249, 0.52219362] | 419 | 160832 | 0 | COMPUTED | — |
| Confirmación | Lineal (logit) | B0 | 0.53985035 | [0.50804318, 0.56962653] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | Lineal (logit) | B1 | 0.5385678 | [0.5091705, 0.56664405] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | Lineal (logit) | B2 | 0.53614532 | [0.50970308, 0.56130055] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | LightGBM (binary) | B0 | 0.52979871 | [0.50813913, 0.55064039] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | LightGBM (binary) | B1 | 0.52948957 | [0.50429081, 0.55462348] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | LightGBM (binary) | B2 | 0.53549843 | [0.51900352, 0.54857203] | 25 | 9750 | 0 | COMPUTED | — |

| Ventana | Familia | Contraste | Delta AUC final | IC95% | p crudo unilateral | p de decisión secuencial | Decisión secundaria | N sesiones | N orígenes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primaria | Lineal (logit) | B1/B0 | -0.0013529644 | [-0.0037324373, 0.00093853647] | 0.8742 | 0.8742 | No rechazada | 419 | 160832 |
| Primaria | Lineal (logit) | B2/B1 | -0.0011917471 | [-0.0033595997, 0.0010454682] | 0.8595 | NO VERIFICABLE | H2 no abierta; p crudo sólo diagnóstico | 419 | 160832 |
| Primaria | LightGBM (binary) | B1/B0 | -0.0013825313 | [-0.0058494105, 0.0030305318] | 0.7237 | 0.7237 | No rechazada | 419 | 160832 |
| Primaria | LightGBM (binary) | B2/B1 | +0.00046215919 | [-0.0034380469, 0.0044636569] | 0.4195 | NO VERIFICABLE | H2 no abierta; p crudo sólo diagnóstico | 419 | 160832 |
| Confirmación | Lineal (logit) | B1/B0 | -0.0012825555 | [-0.0074587472, 0.0060692769] | 0.7055 | 0.7055 | No rechazada | 25 | 9750 |
| Confirmación | Lineal (logit) | B2/B1 | -0.0024224776 | [-0.0087267845, 0.0042261659] | 0.7302 | NO VERIFICABLE | H2 no abierta; p crudo sólo diagnóstico | 25 | 9750 |
| Confirmación | LightGBM (binary) | B1/B0 | -0.0003091384 | [-0.01526464, 0.014349795] | 0.4587 | 0.4587 | No rechazada | 25 | 9750 |
| Confirmación | LightGBM (binary) | B2/B1 | +0.0060088633 | [-0.0088743989, 0.020697055] | 0.1897 | NO VERIFICABLE | H2 no abierta; p crudo sólo diagnóstico | 25 | 9750 |

| Ventana | N sesiones final | N orígenes final | Etiquetas positivas | Etiquetas negativas | Sesiones aún excluidas del salto |
| --- | --- | --- | --- | --- | --- |
| Primaria | 419 | 160832 | 102301 | 58531 | 0 |
| Confirmación | 25 | 9750 | 6268 | 3482 | 0 |

Cero sesiones excluidas del salto final, según los dos agregados cerrados.

Los IC/p ausentes siguen NO VERIFICABLES; nunca se convierten en cero. Una H2 no abierta conserva su p nominal como diagnóstico, sin decisión secuencial.

## Primer pase de salto: resultados preservados antes de Newton

Objetivo: indicador jump30 > 0 (exceso RV−BPV positivo, no un test formal de salto). AUC agrupada por origen, peso uno y empates 0,5. Delta = AUC rica menos AUC base. IC95% y p proceden del agregado de salto v3, con 9.999 remuestreos de bloques de sesiones y secuencia H1 → H2 por familia. No se recalcula inferencia en este informe. Una réplica monoclase invalida los IC/p, sin redibujarla ni convertir lo no verificable en cero.

| Ventana | Familia | Conjunto | AUC | IC95% | N sesiones | N orígenes | Réplicas monoclase | Estado | Motivo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primaria | Lineal (logit) | B0 | 0.52174291 | [0.51486978, 0.52838014] | 418 | 160442 | 0 | COMPUTED | — |
| Primaria | Lineal (logit) | B1 | 0.5203611 | [0.51355187, 0.52682921] | 418 | 160442 | 0 | COMPUTED | — |
| Primaria | Lineal (logit) | B2 | 0.5191887 | [0.51283024, 0.52541441] | 418 | 160442 | 0 | COMPUTED | — |
| Primaria | LightGBM (binary) | B0 | 0.51701391 | [0.51082781, 0.52273128] | 418 | 160442 | 0 | COMPUTED | — |
| Primaria | LightGBM (binary) | B1 | 0.51549593 | [0.50954977, 0.52114568] | 418 | 160442 | 0 | COMPUTED | — |
| Primaria | LightGBM (binary) | B2 | 0.51641308 | [0.51040832, 0.52245986] | 418 | 160442 | 0 | COMPUTED | — |
| Confirmación | Lineal (logit) | B0 | 0.53985035 | [0.50804318, 0.56962653] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | Lineal (logit) | B1 | 0.5385678 | [0.5091705, 0.56664405] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | Lineal (logit) | B2 | 0.53614532 | [0.50970308, 0.56130055] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | LightGBM (binary) | B0 | 0.52979871 | [0.50813913, 0.55064039] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | LightGBM (binary) | B1 | 0.52948957 | [0.50429081, 0.55462348] | 25 | 9750 | 0 | COMPUTED | — |
| Confirmación | LightGBM (binary) | B2 | 0.53549843 | [0.51900352, 0.54857203] | 25 | 9750 | 0 | COMPUTED | — |

| Ventana | Familia | Contraste | Delta AUC | IC95% | p crudo unilateral | p de decisión secuencial | Decisión secundaria | N sesiones | N orígenes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primaria | Lineal (logit) | B1/B0 | -0.0013818156 | [-0.0037659619, 0.00097571816] | 0.8801 | 0.8801 | No rechazada | 418 | 160442 |
| Primaria | Lineal (logit) | B2/B1 | -0.0011723994 | [-0.0033813098, 0.0010762948] | 0.8576 | NO VERIFICABLE | H2 no abierta; p crudo sólo diagnóstico | 418 | 160442 |
| Primaria | LightGBM (binary) | B1/B0 | -0.001517986 | [-0.0060583705, 0.0028983805] | 0.7461 | 0.7461 | No rechazada | 418 | 160442 |
| Primaria | LightGBM (binary) | B2/B1 | +0.00091715593 | [-0.0028495326, 0.0047999853] | 0.3257 | NO VERIFICABLE | H2 no abierta; p crudo sólo diagnóstico | 418 | 160442 |
| Confirmación | Lineal (logit) | B1/B0 | -0.0012825555 | [-0.0074587472, 0.0060692769] | 0.7055 | 0.7055 | No rechazada | 25 | 9750 |
| Confirmación | Lineal (logit) | B2/B1 | -0.0024224776 | [-0.0087267845, 0.0042261659] | 0.7302 | NO VERIFICABLE | H2 no abierta; p crudo sólo diagnóstico | 25 | 9750 |
| Confirmación | LightGBM (binary) | B1/B0 | -0.0003091384 | [-0.01526464, 0.014349795] | 0.4587 | 0.4587 | No rechazada | 25 | 9750 |
| Confirmación | LightGBM (binary) | B2/B1 | +0.0060088633 | [-0.0088743989, 0.020697055] | 0.1897 | NO VERIFICABLE | H2 no abierta; p crudo sólo diagnóstico | 25 | 9750 |

Una H2 no abierta conserva el p crudo como diagnóstico; no tiene p de decisión secuencial. Una AUC puntual disponible no implica que su intervalo sea verificable.

Primaria: 418 sesiones y 160442 orígenes comparables; 102077 etiquetas positivas y 58365 negativas. Sesiones excluidas sólo del salto: 1.

Confirmación: 25 sesiones y 9750 orígenes comparables; 6268 etiquetas positivas y 3482 negativas. Sesiones excluidas sólo del salto: 0.

## Primer pase: alcance y convergencia

El [addendum de implementación](v3_secondary_implementation_addendum_v1.md), con registro JSON SHA-256 `606a8c8d5dbe51628e7507b504cf7c5f8483a9aa5e7c80f62be33b2cb12e55de`, se congeló antes de nuevos ajustes secundarios. Se reutilizan 962 componentes ya completos (912 de primaria, 50 de confirmación). Sólo se intentan los 1.702 faltantes: 801 logit y 801 LightGBM en primaria; 50 y 50 en confirmación. Intento terminado no significa ajuste exitoso: las fallas se conservan abajo.

La corrección logit es un precondicionamiento invertible de Fisher con el mismo objetivo, las cinco lambdas y la selección en las diez últimas sesiones de entrenamiento. El certificado nuevo exige gradiente original ≤1e-8 y equivalencia algebraica; no se acepta sólo el éxito declarado por el optimizador. Se conserva la excepción registrada para entrenamiento monoclase. Los componentes viejos se reutilizan bajo su contrato de convergencia original: un gradiente viejo mayor al umbral nuevo se revela, no se oculta ni provoca un refit adicional.

| Ventana | Familia | Procedencia | Componentes | COMPUTED | NO VERIFICABLE |
| --- | --- | --- | --- | --- | --- |
| Primaria | Lineal (logit) | REUSED_FROZEN_V3 | 456 | 456 | 0 |
| Primaria | LightGBM (binary) | REUSED_FROZEN_V3 | 456 | 456 | 0 |
| Primaria | Lineal (logit) | NEW_MISSING_COMPONENT | 801 | 800 | 1 |
| Primaria | LightGBM (binary) | NEW_MISSING_COMPONENT | 801 | 801 | 0 |
| Confirmación | Lineal (logit) | REUSED_FROZEN_V3 | 25 | 25 | 0 |
| Confirmación | LightGBM (binary) | REUSED_FROZEN_V3 | 25 | 25 | 0 |
| Confirmación | Lineal (logit) | NEW_MISSING_COMPONENT | 50 | 50 | 0 |
| Confirmación | LightGBM (binary) | NEW_MISSING_COMPONENT | 50 | 50 | 0 |

| Ventana | Procedencia | Fase | Solvers | Convergencia declarada | Convergencia desconocida | Gradientes disponibles | Gradientes ausentes | Gradiente >1e-8 | Gradiente máximo | Certificados nuevos | Excepciones monoclase | Certificado nuevo no aplicado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primaria | REUSED_FROZEN_V3 | refit | 456 | 456 | 0 | 456 | 0 | 446 | 1.3219123e-06 | 0 | 0 | 456 |
| Primaria | REUSED_FROZEN_V3 | candidate | 2280 | 2280 | 0 | 2280 | 0 | 2265 | 1.8975255e-06 | 0 | 0 | 2280 |
| Primaria | NEW_MISSING_COMPONENT | refit | 800 | 800 | 0 | 800 | 0 | 0 | 9.0894167e-09 | 800 | 0 | 0 |
| Primaria | NEW_MISSING_COMPONENT | candidate | 4000 | 4000 | 0 | 4000 | 0 | 0 | 9.9769248e-09 | 4000 | 0 | 0 |
| Confirmación | REUSED_FROZEN_V3 | refit | 25 | 25 | 0 | 25 | 0 | 25 | 1.1799851e-06 | 0 | 0 | 25 |
| Confirmación | REUSED_FROZEN_V3 | candidate | 125 | 125 | 0 | 125 | 0 | 125 | 1.591354e-06 | 0 | 0 | 125 |
| Confirmación | NEW_MISSING_COMPONENT | refit | 50 | 50 | 0 | 50 | 0 | 0 | 3.6456438e-09 | 50 | 0 | 0 |
| Confirmación | NEW_MISSING_COMPONENT | candidate | 250 | 250 | 0 | 250 | 0 | 0 | 8.8247198e-09 | 250 | 0 | 0 |

Los gradientes ausentes no se interpretan como cero. El certificado nuevo no se atribuye retroactivamente a los componentes congelados.

### Primer pase: fallos de componentes y recursos

| Ventana | Sesión | Componente | Causa preservada |
| --- | --- | --- | --- |
| Primaria | 2025-03-26 | jump__log_ridge_harq__B2 | RP4_V3_LOGISTIC_REPAIR_NOT_CONVERGED:{"converged": false, "coordinate_objective_abs_difference": 0.0, "fisher_cholesky_infinity_norm": 2.848652397471039, "fisher_diagonal_max": 0.48044122046525306, "fisher_diagonal_min": 0.0002748687574381752, "ftol": 1e-12, "gradient_inf_norm_objective_over_n": 1.0226994386690321e-08, "gtol": 1e-08, "intercept_penalized": false, "iterations": 27, "lambda": 0.0001, "literal_original_gradient_max_abs_difference": 2.9904994511180605e-18, "literal_original_objective_abs_difference": 0.0, "maxiter": 1000, "numerical_repair": "invertible_parameter_preconditioning_same_objective", "objective_initial_divided_by_n": 0.6542887164910202, "objective_total_divided_by_n": 0.6493359254066342, "objective_total_sum_scale": 31627.85425470634, "original_gradient_certificate_applicable": true, "phases": [{"ftol": 1e-12, "function_evaluations": 19, "iterations": 17, "message": "CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH", "objective_over_n": 0.6493359254066704, "original_gradient_inf": 1.0142593263378274e-08, "scipy_success": true, "status": 0}, {"ftol": 0.0, "function_evaluations": 15, "iterations": 10, "message": "CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH", "objective_over_n": 0.6493359254066342, "original_gradient_inf": 1.022699438968082e-08, "scipy_success": true, "status": 0}], "single_class_training": false, "solver": "scipy_L-BFGS-B_in_initial_Fisher_Cholesky_coordinates", "stable_gradient_inf_norm": 1.022699438968082e-08, "training_frequency": 0.6384782787221812, "transformed_gradient_inf_norm": 3.1393822894062135e-08, "transformed_gtol": 3.5104318129083578e-09} |

| Ventana | Máximo hilos de cálculo | Prioridad Windows | PID | Código de salida | Segundos | Inicio UTC | Fin UTC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Primaria | 2 | 16384 | 59448 | 0 | 8648.0499 | 2026-09-07T18:07:25.934654+00:00 | 2026-09-07T20:31:31.981380+00:00 |
| Confirmación | 2 | 16384 | 105116 | 0 | 882.61764 | 2026-09-07T20:35:12.421925+00:00 | 2026-09-07T20:49:55.040151+00:00 |

Las ventanas se ejecutaron secuencialmente, con límite de dos hilos de cálculo y prioridad baja, sin cambiar ni interrumpir la evaluación v4. Este generador sólo lee agregados y metadatos cerrados, con un hilo; no ajusta modelos ni recalcula predicciones o estadística inferencial.

## Segundo pase: Newton sólo para fallos elegibles

El [addendum Newton](v3_secondary_newton_addendum_v1.md) quedó registrado antes de consultar AUC y antes de ejecutar esta resolución: JSON `529067473ff602d47e0466426ce2af2e0f525d1ac5e42b4fd4230e38d17c52fa`; documento `7353209882a75316faf9f60da8d895739a5fb26e6f84bfb3cc01128c21d9f888`. El rechazo inicial de B2 lineal del 2025-03-26 se conserva: gradiente 1.0226994386690321e-8 frente al certificado 1e-8. Su fallo fue correcto bajo el umbral registrado; no se reclasifica como éxito del primer pase.

La resolución mantiene objetivo, cinco lambdas, validación temporal, datos y umbral. Después de las mismas fases L-BFGS permite hasta ocho pasos Newton, sin jitter, con descenso certificado y la excepción de un ULP descrita en el addendum. Los componentes COMPUTED no se vuelven a ajustar, ni se vuelve a ajustar LightGBM. Cada llamada nueva y su pulido se cuentan aparte: reconstruir un coeficiente fallido que no estaba guardado no equivale a reutilizarlo.

| Ventana | Familia | Procedencia final | Componentes | COMPUTED | NO VERIFICABLE |
| --- | --- | --- | --- | --- | --- |
| Primaria | Lineal (logit) | REUSED_ORIGINAL_V3 | 456 | 456 | 0 |
| Primaria | LightGBM (binary) | REUSED_ORIGINAL_V3 | 456 | 456 | 0 |
| Primaria | Lineal (logit) | REUSED_FIRST_REPAIR_SUCCESS | 800 | 800 | 0 |
| Primaria | LightGBM (binary) | REUSED_FIRST_REPAIR_SUCCESS | 801 | 801 | 0 |
| Primaria | Lineal (logit) | NEWTON_FAILED_ONLY_ATTEMPT | 1 | 1 | 0 |
| Primaria | LightGBM (binary) | NEWTON_FAILED_ONLY_ATTEMPT | 0 | 0 | 0 |
| Primaria | Lineal (logit) | PRESERVED_INELIGIBLE_FAILURE | 0 | 0 | 0 |
| Primaria | LightGBM (binary) | PRESERVED_INELIGIBLE_FAILURE | 0 | 0 | 0 |
| Confirmación | Lineal (logit) | REUSED_ORIGINAL_V3 | 25 | 25 | 0 |
| Confirmación | LightGBM (binary) | REUSED_ORIGINAL_V3 | 25 | 25 | 0 |
| Confirmación | Lineal (logit) | REUSED_FIRST_REPAIR_SUCCESS | 50 | 50 | 0 |
| Confirmación | LightGBM (binary) | REUSED_FIRST_REPAIR_SUCCESS | 50 | 50 | 0 |
| Confirmación | Lineal (logit) | NEWTON_FAILED_ONLY_ATTEMPT | 0 | 0 | 0 |
| Confirmación | LightGBM (binary) | NEWTON_FAILED_ONLY_ATTEMPT | 0 | 0 | 0 |
| Confirmación | Lineal (logit) | PRESERVED_INELIGIBLE_FAILURE | 0 | 0 | 0 |
| Confirmación | LightGBM (binary) | PRESERVED_INELIGIBLE_FAILURE | 0 | 0 | 0 |

| Ventana | Sesión | Componente | Fase | Estado | Iteraciones L-BFGS intento anterior | Iteraciones L-BFGS nueva llamada | Pasos Newton intentados | Pasos Newton aceptados | Gradiente previo | Gradiente final | Certificado final |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primaria | 2025-03-26 | jump__log_ridge_harq__B2 | primer fallo; fase no guardada; lambda=0.0001 | NO VERIFICABLE | 27 | NO VERIFICABLE | NO VERIFICABLE | NO VERIFICABLE | 1.0226994e-08 | NO VERIFICABLE | NO VERIFICABLE (intento preservado) |
| Primaria | 2025-03-26 | jump__log_ridge_harq__B2 | candidate lambda=0.0001 | COMPUTED | NO VERIFICABLE | 27 | 1 | 1 | NO VERIFICABLE | 6.9569446e-15 | CERTIFIED |
| Primaria | 2025-03-26 | jump__log_ridge_harq__B2 | candidate lambda=0.01 | COMPUTED | NO VERIFICABLE | 12 | 0 | 0 | NO VERIFICABLE | 7.3907588e-09 | CERTIFIED |
| Primaria | 2025-03-26 | jump__log_ridge_harq__B2 | candidate lambda=1.0 | COMPUTED | NO VERIFICABLE | 10 | 0 | 0 | NO VERIFICABLE | 5.876426e-10 | CERTIFIED |
| Primaria | 2025-03-26 | jump__log_ridge_harq__B2 | candidate lambda=100.0 | COMPUTED | NO VERIFICABLE | 5 | 0 | 0 | NO VERIFICABLE | 9.3064008e-10 | CERTIFIED |
| Primaria | 2025-03-26 | jump__log_ridge_harq__B2 | candidate lambda=10000.0 | COMPUTED | NO VERIFICABLE | 4 | 0 | 0 | NO VERIFICABLE | 3.0546346e-09 | CERTIFIED |
| Primaria | 2025-03-26 | jump__log_ridge_harq__B2 | refit | COMPUTED | NO VERIFICABLE | 4 | 0 | 0 | NO VERIFICABLE | 4.1647856e-09 | CERTIFIED |

La tabla conserva sólo diagnósticos guardados. Un gradiente o coste anterior no registrado figura como NO VERIFICABLE, no como cero; el primer fallo puede documentar una sola lambda y no todo el trabajo de la llamada.

| Ventana | Máximo hilos de cálculo | Prioridad Windows | Código de salida | Segundos segundo pase | Inicio UTC | Fin UTC |
| --- | --- | --- | --- | --- | --- | --- |
| Primaria | 2 | 16384 | 0 | 30.29133 | 2026-09-07T20:52:59.178662+00:00 | 2026-09-07T20:53:29.469787+00:00 |
| Confirmación | 2 | 16384 | 0 | 14.068069 | 2026-09-07T20:55:09.298621+00:00 | 2026-09-07T20:55:23.367332+00:00 |

Se verificó que ambos cierres del primer pase preceden al inicio de Newton; no hubo ejecutores secundarios simultáneos. Los recursos del primer pase están en su propia tabla y no se eliminan del coste total. MZ, media primaria, cuantil y v4 permanecen intactos.

Release Newton: `721bcac42d45c88d0d7362dc560097433e12a5161f02ecb82d1c2991eae76b74`. Release del primer pase: `7565795ddd4938f4c84068b2c2bb30c01905092150fb78c56aefa7626ca46bed`.

## MZ: NO VERIFICABLE como recalibración utilizable

No se demostró un error aritmético: la recta afín, el fallback y el piso 1e-12 reproducen los pronósticos guardados. El problema observado es que la recta produce valores negativos en algunos orígenes y el piso positivo dispara QLIKE. No se cambió fórmula, escala, intercepto ni piso para ocultar esa inestabilidad. Los números siguientes son exclusivamente el diagnóstico auditado, no resultados de una recalibración corregida.

| Ventana | Conjunto | QLIKE original | QLIKE MZ diagnóstico | N orígenes | Afines negativos | Pisos activados | % pérdida en piso | Máx. diferencia fórmula/guardado | Estado utilizable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primaria | B0 | 0.14931695 | 635736.36 | 160832 | 18631 | 18631 | 99.999798 | 0 | NO VERIFICABLE |
| Primaria | B1 | 0.14619447 | 711247.78 | 160832 | 20834 | 20834 | 99.999476 | 0 | NO VERIFICABLE |
| Primaria | B2 | 0.14642711 | 730463.86 | 160832 | 21100 | 21100 | 99.999802 | 0 | NO VERIFICABLE |
| Confirmación | B0 | 0.17494027 | 0.18623062 | 9750 | 0 | 0 | 0 | 0 | NO VERIFICABLE |
| Confirmación | B1 | 0.17202611 | 1988.1773 | 9750 | 9 | 9 | 99.989633 | 0 | NO VERIFICABLE |
| Confirmación | B2 | 0.17617863 | 2400.2188 | 9750 | 11 | 11 | 99.990301 | 0 | NO VERIFICABLE |

En confirmación B1 y B2 tienen respectivamente 9 y 11 pisos activados; aportan más del 99,98% de su pérdida MZ. La auditoría verificó las 25 sesiones sin ajustar modelos y sin demostrar fallo de suma, escala ni intercepto. [Prueba primaria](../../../../../artifacts/rp4_v3_b4/mz_identity_receipt.json) · [Prueba de confirmación](../../artifacts/rp4_v3_secondary_mz_audit/REPORT.md) · [Recibo de confirmación](../../../../../artifacts/rp4_v3_secondary_mz_audit/receipt.json). Se aplica el cierre NO VERIFICABLE autorizado para MZ, sin nueva recalibración.

## Divulgación y custodia

La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 con otra especificación. El PIT es proxy de tiempo fuente a 120 s, como en la literatura.

Hueco UW aceptado: 2025-01-25 a 2025-02-24, sin relleno. Las versiones reutilizan ventanas y no son replicaciones independientes; un no rechazo no demuestra equivalencia a cero ni absorción. La reparación numérica no cambia las medias primarias ni demuestra por sí sola una ventaja global robusta.

Release de salto: `7565795ddd4938f4c84068b2c2bb30c01905092150fb78c56aefa7626ca46bed`. Revisión 1: `f209a54519298d8ee7308a8dc20b5c293d0da4fbad807709aed8aca2feb1db03`. Auditoría MZ confirmación: `ebe38763e180d6676e57d13fd65b22df2f9ec537985d8768466ffb7434ee6b4b`.

[Recibo y comandos de esta revisión](../../../../../artifacts/rp4_v3_secondary_closeout/receipt.json) · [Pins y censo de cierre](../../../../../artifacts/rp4_v3_secondary_closeout/evidence.json) · [Revisión anterior intacta](results_v3_revision1.md).

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false. Sin publicación, descargas ni modificación de resultados congelados.
