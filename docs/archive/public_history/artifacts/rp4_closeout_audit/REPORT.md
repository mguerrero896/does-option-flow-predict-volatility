# Auditoría descriptiva de cierre RP4 — RV30, RV15 y RV5

Se extrajeron pronósticos y diagnósticos ya cerrados: 419 sesiones/160.832 orígenes primarios y 25/9.750 de confirmación por horizonte. No se ajustó ningún modelo, no se consultó tape bruto ni se calculó ningún nuevo p, AUC o bootstrap. Las 7.992 medias QLIKE de sesión reconstruidas desde pronósticos coinciden con los CSV fijados hasta 6,67e-16. No cambia ninguna decisión primaria.

## Coeficientes: escala y correspondencia exacta

B2 tiene 138 predictores registrados más cinco efectos de activo, 109 indicadores de presencia y un intercepto: 253 términos representados por sesión. El CSV privado contiene 336.996 filas (253×444×3); el resumen público tiene 1.518 filas (253×2 ventanas×3 horizontes). `presence:nombre` corresponde a disponibilidad finita de esa variable, no a su pendiente.

Los coeficientes actúan sobre variables transformadas, centradas/escaladas sólo con entrenamiento y recortadas a ±5 desviaciones; no se reestandariza después. Predicen log-RV antes de Duan y las cotas de salida. Una poda se representa como contribución cero y motivo explícito, NO como efecto estimado nulo. Su magnitud/signo no identifica causalidad, aportación marginal aislada ni importancia de ablación.

[Resumen completo de coeficientes](../../../../../artifacts/rp4_closeout_audit/b2_coefficient_summary.csv) · [Sólo presencias](../../../../../artifacts/rp4_closeout_audit/b2_presence_coefficient_summary.csv). Los valores siguientes son B2 ridge, RV15, primaria.

| column | mean | median | positive_count | negative_count | active_sessions |
| --- | --- | --- | --- | --- | --- |
| rp4_gamma_imb_near_short | -0.00129336502 | -0.00138662622 | 92 | 327 | 419 |
| rp4_gamma_imb_near_spot | -0.000554679861 | 0.000975071627 | 259 | 160 | 419 |
| rp4_gamma_imb_signed_trades | -0.0427061571 | -0.0382967244 | 0 | 419 | 419 |
| rp4_gamma_imb_total | 0.00462475943 | 0.00331558535 | 361 | 58 | 419 |

Gamma total es positivo en 361/419 sesiones (86,16%); el contador `signed_trades` es negativo en 419/419. Ese predictor cuenta operaciones con dirección identificada y usa log1p: no es una variable firmada de compra/venta. Los signos no demuestran que estas cuatro columnas causen la mejora observada.

| column | mean | median | absolute_mean | zero_count | active_sessions |
| --- | --- | --- | --- | --- | --- |
| b2_5m_buy_premium_share | 0.249162202 | 0.000792709287 | 0.251512199 | 26 | 393 |
| b2_5m_passive_premium_share | 0.304915624 | -0.00215875112 | 0.312081496 | 2 | 417 |
| b2_5m_sell_premium_share | 0.248024656 | 0.00316042823 | 0.249845475 | 0 | 419 |

Las medias absolutas 0,25–0,31 pertenecen a shares de 5 minutos, no a todas las shares de 30 minutos. Las medianas están cerca de cero, pero NO son exactamente cero; la media absoluta no describe una contribución típica estable.

## Regularización, podas y cotas

Se verifican 102/114/111 elecciones de lambda=1e-4 en B0/B1/B2 sobre 419 sesiones RV15. El objetivo implementado es suma de residuos cuadrados de log-RV más lambda×L2, sin penalizar intercepto; no es MSE+lambda independiente de N. El factor n/(n+lambda) sólo es una ilustración bajo un diseño ortogonal y escalado apropiado, no la contracción real de este diseño correlacionado y winsorizado.

| information_set | N_sessions | removed_min | removed_median | removed_max | count_low | count_high |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | 419 | 5 | 5 | 6 | 0 | 223 |
| B1 | 419 | 17 | 17 | 22 | 0 | 324 |
| B2 | 419 | 88 | 89 | 97 | 0 | 302 |

Las 88 podas de B2 son el mínimo, no una constante: mediana 89 y máximo 97. Incluyen columnas de presencia; el número de predictores brutos no debe confundirse con el rango efectivo. Los límites altos 223/324/302 y bajos cero son incidencias por origen sobre 160.832 pronósticos de cada conjunto.

## Perfiles temporales y ventana de cuatro días

Delta siempre significa QLIKE base menos QLIKE ampliado: positivo favorece B2. Los cortes de esta auditoría son descriptivos posteriores y no nuevas pruebas. La ventana llamada tarifas es únicamente el calendario 2025-04-07 a 2025-04-10 solicitado; estas asociaciones no identifican un efecto causal de aranceles.

| stratum | N_origins | N_sessions | delta_pooled | delta_equal_session_asset |
| --- | --- | --- | --- | --- |
| four_days_first_market_hour_origin_lt60 | 120 | 4 | -0.482621152 | -0.482621152 |
| four_days_first_observed_hour_origin35_94 | 288 | 4 | -0.322087411 | -0.322087411 |
| outside_four_days_first_observed_hour_origin35_94 | 29648 | 415 | 0.000255369377 | 0.00027287889 |
| outside_four_days_remainder_origin_ge95 | 129624 | 415 | 0.00039084636 | 0.000467570981 |

Las 288 observaciones y delta −0,322087411 corresponden a 35≤origin_minute<95, primera hora observable. El corte declarado origin_minute<60 contiene 120 y delta −0,482621152. No son intercambiables. Fuera de los cuatro días, +0,000255369 y +0,000390846 corresponden al corte observable <95 y su resto, con promedio por origen; excluir ese calendario no produce un nuevo p autorizado.

| stratum | N_origins | N_sessions | delta_pooled | delta_equal_session_asset |
| --- | --- | --- | --- | --- |
| first_market_hour_origin_lt60 | 12451 | 419 | 0.000458426639 | 0.000426080481 |
| middle_registered_origin60_299 | 118819 | 419 | 0.0011851248 | 0.0011492755 |
| last_registered_block_origin_ge300 | 29562 | 414 | 0.00147303204 | 0.00144200529 |
| last_market_hour_origin_ge330 | 14794 | 414 | 0.00203392222 | 0.00203352322 |
| first_observed_hour_origin35_94 | 29936 | 419 | 0.00107453041 | 0.00105662119 |

`last_hour` en el productor registrado significa origin_minute≥300. No es la última hora de mercado (≥330 en sesión normal de390min). Por ello se exponen ambos cortes con nombres explícitos. No se trasladan cifras entre cortes ni entre ponderación por origen y por sesión/activo.

| horizon_minutes | stratum | delta_pooled | delta_equal_session_asset |
| --- | --- | --- | --- |
| 30 | 2025-10 | -0.00153992065 | -0.00164305348 |
| 30 | 2025-11 | -0.00173293048 | -0.00225399989 |
| 15 | 2025-10 | -0.00108772379 | -0.00117749099 |
| 15 | 2025-11 | -0.00147340802 | -0.00190642358 |

Octubre y noviembre de2025 son negativos para B2 ridge en RV30 y RV15; la mejora media no implica estabilidad mensual completa.

| profile | stratum | N_sessions | first_session | last_session | delta_equal_session_asset |
| --- | --- | --- | --- | --- | --- |
| training_size_tercile | T1 | 140 | 2024-10-28 | 2025-06-20 | 0.0033171367 |
| training_size_tercile | T2 | 139 | 2025-06-23 | 2026-01-08 | 0.00137705397 |
| training_size_tercile | T3 | 140 | 2026-01-09 | 2026-07-31 | 0.000153035456 |
| calendar_early | 2024-10-28_to_2025-02-28 | 64 | 2024-10-28 | 2025-02-28 | -0.00123328684 |

El tramo evaluado octubre2024–febrero2025 tiene64 sesiones, 15,27% de419, no84/20%. En ese tramo B1 ridge RV15 es negativo. No constituye el primer tercil: los terciles de tamaño de entrenamiento tienen140/139/140 sesiones y sus límites aparecen en la tabla. Tamaño creciente, calendario y regímenes se confunden; esta partición no demuestra que más entrenamiento cause estabilidad.

## Vacíos, extremos y degeneración

| family | N_origins | N_sessions | N_asset_sessions | base_qlike_pooled | rich_qlike_pooled | base_qlike_equal_session_asset | rich_qlike_equal_session_asset |
| --- | --- | --- | --- | --- | --- | --- | --- |
| log_ridge_harq | 412 | 6 | 25 | 0.185885062 | 0.247087047 | 0.102703519 | 0.202126323 |
| lightgbm_qlike | 412 | 6 | 25 | 0.170592511 | 0.172722343 | 0.0671168877 | 0.0836942017 |

Las412 filas vacías de5min abarcan seis sesiones y25 activo-sesiones. El salto ridge0,102703519→0,202126323 es el promedio igual-sesión/activo; el promedio por origen es0,185885062→0,247087047. Fuera hay160.420 filas repartidas en418 sesiones (una sesión puede tener filas dentro y fuera). El p=0,0007 propuesto para excluirlas es NO VERIFICABLE sin un artefacto fijado que lo respalde; aquí no se recalcula.

| family | information_set | loss_above_5 | selected_rounds_min | selected_rounds_max |
| --- | --- | --- | --- | --- |
| lightgbm_qlike | B0 | 393 | 16 | 1013 |
| lightgbm_qlike | B1 | 371 | 16 | 788 |
| lightgbm_qlike | B2 | 392 | 16 | 847 |
| log_ridge_harq | B0 | 386 | nan | nan |
| log_ridge_harq | B1 | 376 | nan | nan |
| log_ridge_harq | B2 | 364 | nan | nan |

LightGBM RV15 usa entre16 y1.013 rondas, ninguna llega a2.000. Hay364–393 pérdidas QLIKE>5 según conjunto/familia, no un conteo único. Se verificaron cero pronósticos constantes dentro de activo-sesión y cero igualdad exacta entre B0/B1/B2 en5.028 unidades activo-sesión-familia POR horizonte primario (15.084 entre los tres); confirmación aporta300 por horizonte. No igualdad exacta no demuestra ventaja útil.

## UTC, purga y máscaras

| selected_end_utc_clock | selected_end_ny_clock | N_sessions |
| --- | --- | --- |
| 16:40 | 12:40 | 1 |
| 17:40 | 12:40 | 4 |
| 19:40 | 15:40 | 269 |
| 20:40 | 15:40 | 145 |

El objetivo RV15 termina normalmente a15:40 Nueva York:19:40UTC en horario de verano y20:40UTC en invierno, con cierres reducidos separados. No es19:40UTC en419/419. La compuerta temporal usa deliberadamente el fin RV30 heredado:15:55NY normalmente, 15 minutos después del objetivo RV15 y25 después deRV5. No deben compararse ambos campos como si fueran la misma etiqueta. El margen guardado mínimo supera la purga de60min:1.090min.

Los seis bindings son constantes dentro de cada ventana y sus códigos coinciden por hash. Los bitmasks RV15/RV5 son idénticos; frente aRV30 se compararon exactamente claves, número de sesiones de entrenamiento, última sesión y fin del objetivo conservador. RV30 no guardó aquellos bitmasks: no se afirma una comparación binaria inexistente.

## Salto y cierre de interpretación

| window | N_sessions | N_origins | positive_labels | positive_percent |
| --- | --- | --- | --- | --- |
| primary | 419 | 160832 | 102301 | 63.6073667 |
| confirmation | 25 | 9750 | 6268 | 64.2871795 |

La primaria final de salto ya tiene419 sesiones, no418. `jump30>0` clasifica exceso positivo RV−BPV, no un test formal de salto. En estas ventanas cerradas las frecuencias son63,61% y64,29%, no56%; otra población necesita su propio denominador. Los agregados cerrados no rechazan H1 y no abren H2. No se estimó nueva AUC.

## Custodia y publicación

La proyección public_manifest.json contiene sólo aliases neutros de fuentes y hashes, sin rutas privadas. Los CSV por origen, los coeficientes por sesión, los recibos operativos con rutas y los diagnósticos detallados quedan fuera de la allowlist pública. Nada se publica automáticamente. La licencia de software no redistribuye datos de proveedores ni derivados granulares; rige la política de acceso del proyecto.

La skill Model Evaluator guió la separación de métricas, máscaras, escalas y procedencia; no se usó para entrenar o buscar un resultado favorable. RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
