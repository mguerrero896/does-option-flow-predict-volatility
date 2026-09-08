# Auditoría acotada de RP4 v1

Lectura de los paneles autorizados y de pronósticos RP4 v1 ya guardados. Cero refits, cero consultas a proveedores, cero cambios en v1 y cero selección adicional de predictores.

Los defectos medidos no demuestran que todos sesguen hacia «no efecto». Esta auditoría separa las cifras verificadas de esa interpretación causal.

## Diseño activo frente a listas registradas

B0/B1/B2 activos y anidados: 29/71/136. Listas nominales registradas: 22/28/68. La regla v1 exige 111 columnas finitas y permite NaN en 25 celdas de IV.

| Columna | En registro | Activa en X v1 | Obligatoria v1 |
|---|---|---|---|
| b1_implied_rate | sí | sí | sí |
| b1_implied_dividend_yield | sí | sí | sí |
| b1_pcp_residual | sí | no | no |
| b2_5m_late_arrival_share | sí | no | no |
| b2_30m_late_arrival_share | sí | no | no |
| b2_5m_mean_provider_latency_s | sí | no | no |
| b2_30m_mean_provider_latency_s | sí | no | no |
| b2_5m_is_empty_window | sí | no | no |
| b2_30m_is_empty_window | sí | no | no |
| b2_5m_observed_span_s | sí | sí | sí |
| b2_30m_observed_span_s | sí | sí | sí |
| b1_median_quote_age_s | sí | no | no |

Fe de erratas verificable: la frase de v1 «los diagnósticos de calidad, antigüedad y latencia no se usan como predictores» era demasiado amplia: los dos `observed_span_s` sí estaban en X; los otros siete diagnósticos señalados ya estaban excluidos. No es correcto decir que estaban activos los nueve. `b1_pcp_residual` tampoco era predictor activo.

## Cobertura de orígenes

Elegible = objetivo RV30 finito y positivo, predictores obligatorios finitos y compuerta de calidad de v1. Ambos paneles carecen de `rp4_eligible`; se replica el fallback de v1. Se muestran los denominadores programados, incluidos los días que v1 perdió por su máscara. El JSON conserva además panel completo y sesiones v1 efectivamente ejecutadas.

| Ventana | Activo | Orígenes programados | v1 elegibles | v1 % | Sin tasa/dividendo/PCP % | B0+HARQ elegibles | B0+HARQ % |
|---|---|---:|---:|---:|---:|---:|---:|
| primary | ALL | 162329 | 92261 | 56.835809 | 98.498112 | 160832 | 99.077799 |
| primary | AAPL | 27055 | 13759 | 50.855664 | 98.961375 | 26898 | 99.419701 |
| primary | AMZN | 27055 | 14426 | 53.321013 | 98.369987 | 26743 | 98.846794 |
| primary | META | 27054 | 11715 | 43.302284 | 98.344053 | 26853 | 99.257041 |
| primary | MSFT | 27055 | 10123 | 37.416374 | 97.664018 | 26729 | 98.795047 |
| primary | NVDA | 27055 | 21560 | 79.689521 | 98.665681 | 26764 | 98.924413 |
| primary | TSLA | 27055 | 20678 | 76.429495 | 98.983552 | 26845 | 99.223803 |
| confirmation | ALL | 9750 | 5360 | 54.974359 | 99.630769 | 9750 | 100.000000 |
| confirmation | AAPL | 1625 | 740 | 45.538462 | 99.753846 | 1625 | 100.000000 |
| confirmation | AMZN | 1625 | 875 | 53.846154 | 100.000000 | 1625 | 100.000000 |
| confirmation | META | 1625 | 638 | 39.261538 | 98.830769 | 1625 | 100.000000 |
| confirmation | MSFT | 1625 | 772 | 47.507692 | 99.200000 | 1625 | 100.000000 |
| confirmation | NVDA | 1625 | 1249 | 76.861538 | 100.000000 | 1625 | 100.000000 |
| confirmation | TSLA | 1625 | 1086 | 66.830769 | 100.000000 | 1625 | 100.000000 |

En todo a2 (185.729 orígenes), la completitud de predictores v1 es 56,118861%; al quitar tasa y dividendo sube a 97,510351%. PCP ya estaba fuera. Tras exigir RV30 válido, las coberturas son 56,115631% y 97,505505%; la regla B0+HARQ da 98,144070%. MSFT completo: 35,971572% → 96,656437%.

La primaria programó 419 sesiones tras 60 de entrenamiento, pero v1 ejecutó 418. La sesión 2025-10-20 tenía cero orígenes v1 elegibles y tiene 378 con B0+HARQ: incorporarla en v2 mantiene la ventana programada; no es añadir una fecha seleccionada por el signo.

## Afinación y calibración guardadas

| Ventana | Ajustes LGB | Ronda 100 elegida | % | Pendiente MZ B0 | Pendiente MZ B1 | Pendiente MZ B2 |
|---|---:|---:|---:|---:|---:|---:|
| primary | 1254 | 1042 | 83.094099 | 1.50766088118 | 1.45807273487 | 1.50491165037 |
| confirmation | 75 | 63 | 84.000000 | 0.825255787771 | 0.902876911783 | 0.923403926549 |

La frecuencia del tope indica que la rejilla limitó la búsqueda; no prueba por sí sola que aumentar rondas mejore fuera de muestra. MZ corresponde a medias de sesión en niveles, como la implementación v1.

## Extremos lineales guardados

| Ventana | Modelo | Mínimo | Sesión mínimo | Máximo | Sesión máximo | Pronósticos en 1e-12 |
|---|---|---:|---|---:|---|---:|
| primary | B0 | 3.77561887757e-7 | 2025-12-26 | 0.00313856702805 | 2025-04-07 | 0 |
| primary | B1 | 4.29342741326e-7 | 2025-12-26 | 0.00473272004291 | 2025-04-07 | 0 |
| primary | B2 | 1.00000000000e-12 | 2025-05-15 | 1.06864745815e+13 | 2025-09-18 | 2 |
| confirmation | B0 | 0.00000181135651968 | 2026-08-14 | 0.000111452301586 | 2026-08-26 | 0 |
| confirmation | B1 | 0.00000186038638455 | 2026-08-14 | 0.000117027233465 | 2026-08-26 | 0 |
| confirmation | B2 | 0.00000182845641702 | 2026-08-14 | 0.000109118780627 | 2026-08-26 | 0 |

El 2025-05-15 el diseño OLS B2 tiene rango 155 de 166 columnas y dos pronósticos en 1e-12. El 2025-09-18, 3,238325630765e10 es el pronóstico agregado por sesión; el máximo por origen es 1,068647458152e13, el techo exp(30) de v1, con rango 157 de 167 columnas. No se sustituyó ninguno.

## Media, mediana y colas: estimandos distintos

| Ventana | Modelo | Media pérdida | Mediana pérdida |
|---|---|---:|---:|
| primary | log_ols_harq__B0 | 0.145966229436 | 0.106246316170 |
| primary | log_ols_harq__B1 | 0.145542483926 | 0.105273194595 |
| primary | log_ols_harq__B2 | 243.853987344 | 0.104803872683 |
| primary | lightgbm_qlike__B0 | 0.150816030102 | 0.108948244929 |
| primary | lightgbm_qlike__B1 | 0.149000811809 | 0.111536573020 |
| primary | lightgbm_qlike__B2 | 0.149109224546 | 0.111628916209 |
| confirmation | log_ols_harq__B0 | 0.214791163610 | 0.113581194484 |
| confirmation | log_ols_harq__B1 | 0.209067552927 | 0.114892257968 |
| confirmation | log_ols_harq__B2 | 0.200320758521 | 0.114230386992 |
| confirmation | lightgbm_qlike__B0 | 0.205317721378 | 0.119172373414 |
| confirmation | lightgbm_qlike__B1 | 0.196137432610 | 0.112415203608 |
| confirmation | lightgbm_qlike__B2 | 0.199692764024 | 0.113009056566 |

| Ventana | Contraste | Media pareada | Mediana pareada | Media recortada 5% por cola | Diferencia de medianas marginales |
|---|---|---:|---:|---:|---:|
| primary | log_ols_harq__B1_over_B0 | 0.000423745509498 | 0.000857481990987 | 0.000653462246857 | 0.000973121575557 |
| primary | log_ols_harq__B2_over_B1 | -243.708444860 | 0.00105617473806 | 0.00115166270114 | 0.000469321911900 |
| primary | lightgbm_qlike__B1_over_B0 | 0.00181521829267 | 0.000737038501665 | 0.000990111335435 | -0.00258832809179 |
| primary | lightgbm_qlike__B2_over_B1 | -0.000108412736491 | 0.000126165403098 | 0.000140908201337 | -0.0000923431884183 |
| confirmation | log_ols_harq__B1_over_B0 | 0.00572361068221 | 0.000649883342739 | 0.000864400715005 | -0.00131106348440 |
| confirmation | log_ols_harq__B2_over_B1 | 0.00874679440628 | 0.00163661597184 | 0.00175547901426 | 0.000661870976407 |
| confirmation | lightgbm_qlike__B1_over_B0 | 0.00918028876793 | 0.00349652652556 | 0.00405753656482 | 0.00675716980541 |
| confirmation | lightgbm_qlike__B2_over_B1 | -0.00355533141388 | -0.000136164932648 | -0.000229320748201 | -0.000593852957473 |

El recorte usa `scipy.stats.trim_mean` con `proportiontocut=0.05`: elimina `floor(0.05 N)` observaciones por cola (20 en primaria, 1 en confirmación). No elimina sesiones de la evaluación primaria ni cambia los contrastes publicados.

En primaria LGB, mediana(B0)=0,108948244929 y mediana(B1)=0,111536573020: su diferencia es negativa. Sin embargo, mediana(B0−B1)=+0,000737038502. Son cantidades distintas; no deben intercambiarse.

Las pérdidas medias de los seis modelos en las tres sesiones señaladas son 1,0888657591 (2024-11-14), 1,4842004363 (2025-04-09) y 1,9112618228 (2026-06-05). Solo la última está próxima a 2; las tres son grandes frente a las medianas y tienen contrastes de signos mixtos.

## Diez sesiones de mayor pérdida por familia y conjunto

Orden descendente por pérdida del modelo indicado; empate resuelto por fecha ascendente. Signos de las diferencias pareadas B0−B1 y B1−B2: positivo favorece el conjunto más rico. Cada modelo tiene su propia lista, sin escoger únicamente un ranking favorable. Valores exactos de los cuatro contrastes están en `audit.json`.

### primary

| Modelo | Rango | Sesión | QLIKE | OLS B1/B0 | OLS B2/B1 | LGB B1/B0 | LGB B2/B1 |
|---|---:|---|---:|---|---|---|---|
| log_ols_harq__B0 | 1 | 2026-06-05 | 1.92740357515 | - | + | - | + |
| log_ols_harq__B0 | 2 | 2025-04-09 | 1.55507586923 | + | - | + | + |
| log_ols_harq__B0 | 3 | 2024-11-14 | 1.00760825785 | - | + | - | - |
| log_ols_harq__B0 | 4 | 2025-05-21 | 0.831206706488 | + | + | + | - |
| log_ols_harq__B0 | 5 | 2026-03-16 | 0.755251433924 | - | + | + | 0 |
| log_ols_harq__B0 | 6 | 2025-09-17 | 0.718299397472 | + | + | + | - |
| log_ols_harq__B0 | 7 | 2025-10-10 | 0.695163260400 | - | + | - | + |
| log_ols_harq__B0 | 8 | 2026-06-11 | 0.681111190170 | + | + | - | 0 |
| log_ols_harq__B0 | 9 | 2024-12-18 | 0.591840728455 | + | + | - | - |
| log_ols_harq__B0 | 10 | 2026-07-17 | 0.554830512864 | + | - | + | - |
| log_ols_harq__B1 | 1 | 2026-06-05 | 1.99676371699 | - | + | - | + |
| log_ols_harq__B1 | 2 | 2025-04-09 | 1.30758198784 | + | - | + | + |
| log_ols_harq__B1 | 3 | 2024-11-14 | 1.16715689802 | - | + | - | - |
| log_ols_harq__B1 | 4 | 2026-03-16 | 0.781470875843 | - | + | + | 0 |
| log_ols_harq__B1 | 5 | 2025-05-21 | 0.741207152333 | + | + | + | - |
| log_ols_harq__B1 | 6 | 2025-10-10 | 0.726504710137 | - | + | - | + |
| log_ols_harq__B1 | 7 | 2026-06-11 | 0.638604458794 | + | + | - | 0 |
| log_ols_harq__B1 | 8 | 2025-09-17 | 0.631705000258 | + | + | + | - |
| log_ols_harq__B1 | 9 | 2025-04-02 | 0.560178210266 | - | + | + | - |
| log_ols_harq__B1 | 10 | 2024-12-18 | 0.547831837382 | + | + | - | - |
| log_ols_harq__B2 | 1 | 2025-05-15 | 101870.782229 | - | - | - | + |
| log_ols_harq__B2 | 2 | 2026-06-05 | 1.99120473270 | - | + | - | + |
| log_ols_harq__B2 | 3 | 2025-04-09 | 1.39652536752 | + | - | + | + |
| log_ols_harq__B2 | 4 | 2024-11-14 | 1.05404918318 | - | + | - | - |
| log_ols_harq__B2 | 5 | 2026-03-16 | 0.772614097981 | - | + | + | 0 |
| log_ols_harq__B2 | 6 | 2025-10-10 | 0.714407780336 | - | + | - | + |
| log_ols_harq__B2 | 7 | 2025-05-21 | 0.695577612903 | + | + | + | - |
| log_ols_harq__B2 | 8 | 2025-09-17 | 0.606045603665 | + | + | + | - |
| log_ols_harq__B2 | 9 | 2026-06-11 | 0.594895548893 | + | + | - | 0 |
| log_ols_harq__B2 | 10 | 2026-07-17 | 0.543194405257 | + | - | + | - |
| lightgbm_qlike__B0 | 1 | 2026-06-05 | 1.81194357537 | - | + | - | + |
| lightgbm_qlike__B0 | 2 | 2025-04-09 | 1.62859567671 | + | - | + | + |
| lightgbm_qlike__B0 | 3 | 2024-11-14 | 1.06477938247 | - | + | - | - |
| lightgbm_qlike__B0 | 4 | 2025-04-07 | 0.917025372515 | - | + | + | - |
| lightgbm_qlike__B0 | 5 | 2025-10-10 | 0.820049598229 | - | + | - | + |
| lightgbm_qlike__B0 | 6 | 2026-06-11 | 0.772528745844 | + | + | - | 0 |
| lightgbm_qlike__B0 | 7 | 2025-05-21 | 0.750782977530 | + | + | + | - |
| lightgbm_qlike__B0 | 8 | 2026-03-16 | 0.692401900842 | - | + | + | 0 |
| lightgbm_qlike__B0 | 9 | 2025-06-04 | 0.605757094542 | + | - | + | + |
| lightgbm_qlike__B0 | 10 | 2026-07-17 | 0.595916664815 | + | - | + | - |
| lightgbm_qlike__B1 | 1 | 2026-06-05 | 1.88880891320 | - | + | - | + |
| lightgbm_qlike__B1 | 2 | 2025-04-09 | 1.53950685060 | + | - | + | + |
| lightgbm_qlike__B1 | 3 | 2024-11-14 | 1.11645242575 | - | + | - | - |
| lightgbm_qlike__B1 | 4 | 2025-10-10 | 0.856765095722 | - | + | - | + |
| lightgbm_qlike__B1 | 5 | 2026-06-11 | 0.814532426584 | + | + | - | 0 |
| lightgbm_qlike__B1 | 6 | 2025-04-07 | 0.716074048857 | - | + | + | - |
| lightgbm_qlike__B1 | 7 | 2025-05-21 | 0.703158048416 | + | + | + | - |
| lightgbm_qlike__B1 | 8 | 2026-03-16 | 0.661521306104 | - | + | + | 0 |
| lightgbm_qlike__B1 | 9 | 2026-07-17 | 0.590530716431 | + | - | + | - |
| lightgbm_qlike__B1 | 10 | 2025-06-04 | 0.541910342801 | + | - | + | + |
| lightgbm_qlike__B2 | 1 | 2026-06-05 | 1.85144642333 | - | + | - | + |
| lightgbm_qlike__B2 | 2 | 2025-04-09 | 1.47791686564 | + | - | + | + |
| lightgbm_qlike__B2 | 3 | 2024-11-14 | 1.12314840729 | - | + | - | - |
| lightgbm_qlike__B2 | 4 | 2025-04-07 | 0.858793673960 | - | + | + | - |
| lightgbm_qlike__B2 | 5 | 2026-06-11 | 0.814532426584 | + | + | - | 0 |
| lightgbm_qlike__B2 | 6 | 2025-10-10 | 0.798322853688 | - | + | - | + |
| lightgbm_qlike__B2 | 7 | 2025-05-21 | 0.710733213855 | + | + | + | - |
| lightgbm_qlike__B2 | 8 | 2026-03-16 | 0.661521306104 | - | + | + | 0 |
| lightgbm_qlike__B2 | 9 | 2026-07-17 | 0.592126814191 | + | - | + | - |
| lightgbm_qlike__B2 | 10 | 2024-12-18 | 0.558451114104 | + | + | - | - |

### confirmation

| Modelo | Rango | Sesión | QLIKE | OLS B1/B0 | OLS B2/B1 | LGB B1/B0 | LGB B2/B1 |
|---|---:|---|---:|---|---|---|---|
| log_ols_harq__B0 | 1 | 2026-08-31 | 2.41346092298 | + | + | + | - |
| log_ols_harq__B0 | 2 | 2026-08-17 | 0.249820074750 | - | - | - | + |
| log_ols_harq__B0 | 3 | 2026-08-10 | 0.226222439652 | - | + | + | + |
| log_ols_harq__B0 | 4 | 2026-08-05 | 0.164991612860 | + | + | - | + |
| log_ols_harq__B0 | 5 | 2026-09-04 | 0.158576612362 | + | - | + | - |
| log_ols_harq__B0 | 6 | 2026-08-06 | 0.138222298226 | - | + | + | + |
| log_ols_harq__B0 | 7 | 2026-08-20 | 0.136867668237 | - | - | - | - |
| log_ols_harq__B0 | 8 | 2026-08-11 | 0.135731252719 | + | + | + | + |
| log_ols_harq__B0 | 9 | 2026-08-25 | 0.131736007316 | - | + | + | + |
| log_ols_harq__B0 | 10 | 2026-08-04 | 0.125098778683 | + | + | + | + |
| log_ols_harq__B1 | 1 | 2026-08-31 | 2.26985337550 | + | + | + | - |
| log_ols_harq__B1 | 2 | 2026-08-17 | 0.270218571620 | - | - | - | + |
| log_ols_harq__B1 | 3 | 2026-08-10 | 0.235229372907 | - | + | + | + |
| log_ols_harq__B1 | 4 | 2026-08-05 | 0.160158590877 | + | + | - | + |
| log_ols_harq__B1 | 5 | 2026-09-04 | 0.151893941118 | + | - | + | - |
| log_ols_harq__B1 | 6 | 2026-08-06 | 0.139824547015 | - | + | + | + |
| log_ols_harq__B1 | 7 | 2026-08-20 | 0.139412124669 | - | - | - | - |
| log_ols_harq__B1 | 8 | 2026-08-11 | 0.133203733634 | + | + | + | + |
| log_ols_harq__B1 | 9 | 2026-08-25 | 0.132851078821 | - | + | + | + |
| log_ols_harq__B1 | 10 | 2026-08-27 | 0.124552342288 | - | + | + | - |
| log_ols_harq__B2 | 1 | 2026-08-31 | 2.08811248352 | + | + | + | - |
| log_ols_harq__B2 | 2 | 2026-08-17 | 0.272078963569 | - | - | - | + |
| log_ols_harq__B2 | 3 | 2026-08-10 | 0.228950008186 | - | + | + | + |
| log_ols_harq__B2 | 4 | 2026-08-05 | 0.158521974905 | + | + | - | + |
| log_ols_harq__B2 | 5 | 2026-09-04 | 0.155340990271 | + | - | + | - |
| log_ols_harq__B2 | 6 | 2026-08-20 | 0.141357596448 | - | - | - | - |
| log_ols_harq__B2 | 7 | 2026-08-06 | 0.138944360597 | - | + | + | + |
| log_ols_harq__B2 | 8 | 2026-08-11 | 0.130918508224 | + | + | + | + |
| log_ols_harq__B2 | 9 | 2026-08-25 | 0.130779861870 | - | + | + | + |
| log_ols_harq__B2 | 10 | 2026-08-04 | 0.120144238492 | + | + | + | + |
| lightgbm_qlike__B0 | 1 | 2026-08-31 | 2.11221242864 | + | + | + | - |
| lightgbm_qlike__B0 | 2 | 2026-08-17 | 0.227092534128 | - | - | - | + |
| lightgbm_qlike__B0 | 3 | 2026-08-10 | 0.219583847431 | - | + | + | + |
| lightgbm_qlike__B0 | 4 | 2026-09-04 | 0.214431851959 | + | - | + | - |
| lightgbm_qlike__B0 | 5 | 2026-08-05 | 0.145618789517 | + | + | - | + |
| lightgbm_qlike__B0 | 6 | 2026-08-11 | 0.144809308290 | + | + | + | + |
| lightgbm_qlike__B0 | 7 | 2026-08-25 | 0.142968179904 | - | + | + | + |
| lightgbm_qlike__B0 | 8 | 2026-09-03 | 0.135599716286 | + | + | + | - |
| lightgbm_qlike__B0 | 9 | 2026-08-20 | 0.131152877038 | - | - | - | - |
| lightgbm_qlike__B0 | 10 | 2026-09-01 | 0.127177806242 | - | + | + | - |
| lightgbm_qlike__B1 | 1 | 2026-08-31 | 1.97044048687 | + | + | + | - |
| lightgbm_qlike__B1 | 2 | 2026-08-17 | 0.230018398688 | - | - | - | + |
| lightgbm_qlike__B1 | 3 | 2026-08-10 | 0.218432991080 | - | + | + | + |
| lightgbm_qlike__B1 | 4 | 2026-09-04 | 0.203616634351 | + | - | + | - |
| lightgbm_qlike__B1 | 5 | 2026-08-05 | 0.149366163717 | + | + | - | + |
| lightgbm_qlike__B1 | 6 | 2026-08-25 | 0.142476393926 | - | + | + | + |
| lightgbm_qlike__B1 | 7 | 2026-08-11 | 0.141312781764 | + | + | + | + |
| lightgbm_qlike__B1 | 8 | 2026-08-20 | 0.136740940605 | - | - | - | - |
| lightgbm_qlike__B1 | 9 | 2026-09-03 | 0.127450986166 | + | + | + | - |
| lightgbm_qlike__B1 | 10 | 2026-09-01 | 0.118295295720 | - | + | + | - |
| lightgbm_qlike__B2 | 1 | 2026-08-31 | 2.05848477399 | + | + | + | - |
| lightgbm_qlike__B2 | 2 | 2026-08-17 | 0.228257752378 | - | - | - | + |
| lightgbm_qlike__B2 | 3 | 2026-08-10 | 0.217896163586 | - | + | + | + |
| lightgbm_qlike__B2 | 4 | 2026-09-04 | 0.204543629638 | + | - | + | - |
| lightgbm_qlike__B2 | 5 | 2026-08-05 | 0.148484175213 | + | + | - | + |
| lightgbm_qlike__B2 | 6 | 2026-08-20 | 0.139960640724 | - | - | - | - |
| lightgbm_qlike__B2 | 7 | 2026-08-25 | 0.138624294143 | - | + | + | + |
| lightgbm_qlike__B2 | 8 | 2026-08-11 | 0.138525997425 | + | + | + | + |
| lightgbm_qlike__B2 | 9 | 2026-09-03 | 0.128103756204 | + | + | + | - |
| lightgbm_qlike__B2 | 10 | 2026-09-01 | 0.118994691283 | - | + | + | - |

## Verificación y reproducibilidad

Se verificó por SHA-256 cada uno de los 443 checkpoints y su `binding` con el resumen publicado. Se reprodujeron las medias de los cuatro contrastes de ambas ventanas con tolerancia absoluta 1e-14 y relativa 1e-12. Los resultados MZ proceden de los resúmenes publicados, no de un nuevo ajuste.

La consulta de medición final terminó con código 0. Hubo dos errores no científicos de consulta, ambos corregidos: una suposición inicial de columna opcional presente (código 1) y un intento de previsualización Unicode bajo CP1252 (código 1). No se reestimaron modelos ni se modificaron datos en esos intentos.

Manifiesto canónico de checkpoints: `3200d025435694cbcd8c924a834ba18fe6fb662e98ec44a6e71e8125de023880`. Reconstruible tomando `completed_session_sha256` de ambos resúmenes bajo las claves `primary` y `confirmation` y serializando JSON UTF-8, claves ordenadas, separadores compactos coma/dos puntos, sin salto final.

| Entrada | SHA-256 |
|---|---|
| artifacts/rp4_a1/specification.json | 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 |
| docs/rp4/results_v1.md | 77f7de950386f13b80800c78a77fba8f1db4c33a486217eea3d248d15bf02b26 |
| artifacts/rp4_code/evaluate.py | 0064e37bebb00a0fb2550682e0c5590d64f16d88b2dfd9a4403b9ea82946ff14 |
| artifacts/rp4_b2/summary.json | d311d2773ae195968a59cea7d4e0c68dcf35d5d80e005c6cc0f1e028496d2eb2 |
| artifacts/rp4_b2/session_losses.csv | 345889fb42e9681ba3e530edcd712f41c22cd9976a4f7c3fbcb1ef52030fc4bc |
| data/a2_combined_v2/panel.parquet | 51f04c5937a7922757f929ef0ca53941b7766719cf2799673669f8545f97a949 |
| artifacts/rp4_b3/summary.json | 76816cf06a6483c009f9f148728c02ee39d065e7926fbf44dd80fa27dbf29ad7 |
| artifacts/rp4_b3/session_losses.csv | 468a00fdaa6666b4cb5b2585bae8b7601a9326e8b4d95cd176febd58cf698ae2 |
| data/b1_complete_v1/panel.parquet | ecb1c6cce76cb6464d3cdf3d4ef409c60e204adf2df22fba6851e32199819d93 |

## Comando de medición

Desde la raíz del checkout, con el entorno Python 3.12 existente ya seleccionado. La raíz de datos se obtiene de la especificación v1; no se fija ninguna ruta de usuario. El comando solo lee y emite JSON a stdout.

```powershell
$rp4AuditCode = @'
import hashlib,json,math
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import trim_mean
root=Path.cwd();data=Path(json.loads((root/'artifacts/rp4_a1/specification.json').read_text())['data_root'])
def digest(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
specpath=root/'artifacts/rp4_a1/specification.json';spec=json.loads(specpath.read_text())
assets=spec['assets'];sets=['B0','B1','B2'];families=['log_ols_harq','lightgbm_qlike']
exclude3=['b1_implied_rate','b1_implied_dividend_yield','b1_pcp_residual']
diagnostics=['b2_5m_late_arrival_share','b2_30m_late_arrival_share','b2_5m_mean_provider_latency_s','b2_30m_mean_provider_latency_s','b2_5m_is_empty_window','b2_30m_is_empty_window','b2_5m_observed_span_s','b2_30m_observed_span_s','b1_median_quote_age_s']
mandatory=[c for c in spec['feature_sets']['B2'] if c not in spec['missing_allowed']];active=set(spec['feature_sets']['B2'])
source_hashes={p.relative_to(root).as_posix():digest(p) for p in [specpath,root/'docs/rp4/results_v1.md',root/'artifacts/rp4_code/evaluate.py']}
audit={'schema_version':'rp4-v1-readonly-audit-v1','date':'2026-09-07','scope':'Completed RP4 v1 forecasts and authorized existing panels only; zero model refits, zero altered v1 artifacts, no new feature selection.','data_path_convention':'data/ paths are relative to the pre-existing RP4 data root; all other paths are repository-relative.','active_design_counts':{k:len(v) for k,v in spec['feature_sets'].items()},'registered_design_counts':{k:len(v) for k,v in spec['registered_feature_sets'].items()},'mandatory_v1_columns':mandatory,'claim_column_membership':[{'column':c,'claim_group':'mandatory_removal' if c in exclude3 else 'diagnostic_removal','registered':any(c in v for v in spec['registered_feature_sets'].values()),'active_v1':c in active,'mandatory_v1':c in mandatory} for c in exclude3+diagnostics],'windows':{}}
checkpoint_maps={}
for window,public,panel_name in [('primary','rp4_b2','a2_combined_v2'),('confirmation','rp4_b3','b1_complete_v1')]:
 summary_path=root/'artifacts'/public/'summary.json';csvpath=root/'artifacts'/public/'session_losses.csv';summary=json.loads(summary_path.read_text());frame=pd.read_csv(csvpath)
 for p in [summary_path,csvpath]:source_hashes[p.relative_to(root).as_posix()]=digest(p)
 panelpath=data/panel_name/'panel.parquet';panelhash=digest(panelpath);assert panelhash==summary['binding']['panel_sha256'];source_hashes['data/'+panel_name+'/panel.parquet']=panelhash
 panel=pd.read_parquet(panelpath);panel['session_date']=panel['session_date'].astype(str);target=panel.rv30.to_numpy(float);targetok=np.isfinite(target)&(target>0)
 quality=panel['rp4_eligible'].fillna(False).to_numpy(bool) if 'rp4_eligible' in panel else np.ones(len(panel),bool)
 masks={key:np.isfinite(panel[cols].to_numpy(float)).all(axis=1) for key,cols in [('v1',mandatory),('exclude_rate_dividend_pcp',[c for c in mandatory if c not in exclude3]),('b0_harq_only',spec['feature_sets']['B0'])]}
 windowdef=spec['windows'][window];scheduled=sorted(set(panel.loc[panel.session_date.between(windowdef['start'],windowdef['end']),'session_date']))[windowdef['warmup_sessions']:];completed=sorted(frame.session_date.astype(str));coverage=[]
 for scope,base in [('entire_panel',np.ones(len(panel),bool)),('scheduled_window',panel.session_date.isin(scheduled).to_numpy()),('v1_completed_sessions',panel.session_date.isin(completed).to_numpy())]:
  for asset in ['ALL']+assets:
   local=base if asset=='ALL' else base&(panel.asset==asset).to_numpy();n=int(local.sum());row={'scope':scope,'asset':asset,'origins':n,'valid_target':int((local&targetok).sum()),'quality_pass':int((local&quality).sum())}
   for name,mask in masks.items():
    complete=int((local&mask).sum());eligible=int((local&mask&quality&targetok).sum());row[name]={'complete':complete,'eligible':eligible,'complete_percent':100*complete/n,'eligible_percent':100*eligible/n}
   coverage.append(row)
 counts={s:Counter() for s in sets};extremes={};checkpoint_map={}
 for path in sorted((data/'evaluation'/window/'sessions').glob('*.json')):
  value=digest(path);assert value==summary['completed_session_sha256'][path.name];checkpoint_map[path.name]=value;record=json.loads(path.read_text());assert record['binding']==summary['binding']
  for information_set in sets:
   counts[information_set][record['fits']['lightgbm_qlike__'+information_set]['selected']['rounds']]+=1;forecast=np.asarray(record['forecasts']['log_ols_harq'][information_set]);info=extremes.setdefault(information_set,{'minimum':float('inf'),'maximum':-float('inf'),'at_floor_1e_minus12':0});info['at_floor_1e_minus12']+=int((forecast==1e-12).sum())
   for metric,index,comp in [('minimum',int(forecast.argmin()),lambda a,b:a<b),('maximum',int(forecast.argmax()),lambda a,b:a>b)]:
    value=float(forecast[index])
    if comp(value,info[metric]):info[metric]=value;info[metric+'_origin']=record['keys'][index];info[metric+'_fit']=record['fits']['log_ols_harq__'+information_set]
 assert checkpoint_map==summary['completed_session_sha256'];checkpoint_maps[window]=checkpoint_map;total=sum(sum(v.values()) for v in counts.values());top=sum(v[100] for v in counts.values());contrasts={};contrast_keys=[]
 for family in families:
  for smaller,larger in [('B0','B1'),('B1','B2')]:
   key=family+'__'+larger+'_over_'+smaller;contrast_keys.append(key);values=frame['loss__'+family+'__'+smaller]-frame['loss__'+family+'__'+larger];frame[key]=values;registered=next(r for r in summary['contrasts'] if r['family']==family and r['contrast']==larger+'_over_'+smaller);assert np.isclose(values.mean(),registered['estimate'],rtol=1e-12,atol=1e-14)
   contrasts[key]={'mean':float(values.mean()),'median_of_paired_contrast':float(values.median()),'trimmed_mean_5_percent_each_tail':float(trim_mean(values,.05)),'trimmed_count_each_tail':math.floor(.05*len(values)),'positive_sessions':int((values>0).sum()),'negative_sessions':int((values<0).sum()),'ties':int((values==0).sum()),'difference_of_marginal_loss_medians':float(frame['loss__'+family+'__'+smaller].median()-frame['loss__'+family+'__'+larger].median())}
 losscols=['loss__'+family+'__'+s for family in families for s in sets];centers={c.removeprefix('loss__'):{'mean':float(frame[c].mean()),'median':float(frame[c].median())} for c in losscols};topdays={}
 for model in centers:
  losscol='loss__'+model;ranked=frame.sort_values([losscol,'session_date'],ascending=[False,True]).head(10);rows=[]
  for rank,(_,row) in enumerate(ranked.iterrows(),1):rows.append({'rank':rank,'session_date':str(row.session_date),'loss':float(row[losscol]),'contrasts':{c:{'value':float(row[c]),'sign':'positive' if row[c]>0 else 'negative' if row[c]<0 else 'zero'} for c in contrast_keys}})
  topdays[model]=rows
 specific={str(row.session_date):{'losses':{c.removeprefix('loss__'):float(row[c]) for c in losscols},'forecasts_session_mean':{c.removeprefix('forecast__'):float(row[c]) for c in frame if c.startswith('forecast__')},'contrasts':{c:float(row[c]) for c in contrast_keys}} for _,row in frame.loc[frame.session_date.isin(['2024-11-14','2025-04-09','2025-05-15','2025-09-18','2026-06-05','2026-08-31'])].iterrows()};recovered=[]
 for row in summary['skipped_sessions']:
  local=(panel.session_date==row['session']).to_numpy();recovered.append({'session':row['session'],'v1_reason':row['reason'],'origins':int(local.sum()),'b0_harq_eligible':int((local&masks['b0_harq_only']&targetok&quality).sum())})
 audit['windows'][window]={'input_panel':'data/'+panel_name+'/panel.parquet','panel_origins':len(panel),'panel_sessions':int(panel.session_date.nunique()),'scheduled_sessions':len(scheduled),'completed_v1_sessions':len(completed),'first_completed_session':completed[0],'last_completed_session':completed[-1],'completed_v1_origins':summary['N_origins'],'quality_flag_present':'rp4_eligible' in panel,'quality_absent_fallback':'all rows pass the optional quality flag, exactly as v1 evaluate.run','coverage_by_asset':coverage,'rounds':{'counts_by_information_set':{k:dict(sorted(v.items())) for k,v in counts.items()},'fits':total,'selected_100_rounds':top,'selected_100_rounds_percent':100*top/total},'mincer_zarnowitz_published':summary['mincer_zarnowitz'],'linear_prediction_extremes':extremes,'marginal_loss_centers':centers,'paired_contrast_centers':contrasts,'top10_loss_days_by_model':topdays,'named_session_details':specific,'v1_skipped_session_recovery':recovered,'verified_checkpoint_count':len(checkpoint_map),'checkpoint_manifest_sha256':hashlib.sha256(json.dumps(checkpoint_map,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
audit['checkpoint_manifest']={'encoding':'UTF-8 json.dumps({window: summary.completed_session_sha256}, sort_keys=True, separators=(comma, colon)), no trailing newline','sha256':hashlib.sha256(json.dumps(checkpoint_maps,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'verified_checkpoints':sum(map(len,checkpoint_maps.values())),'manifest_sources':['artifacts/rp4_b2/summary.json#completed_session_sha256','artifacts/rp4_b3/summary.json#completed_session_sha256']};audit['source_sha256']=source_hashes
audit['interpretation']={'confirmed':'Mandatory-mask attrition, upper-bound tuning frequency, saved linear explosions, and tail sensitivity are observed.','not_established':'These observations do not identify a common causal bias toward no effect; missingness and extreme-session contrasts can act in either direction.','diagnostic_erratum':'Only b2_5m_observed_span_s and b2_30m_observed_span_s among the nine named diagnostics were active v1 predictors. The other seven were already excluded; b1_pcp_residual was also excluded.','median_distinction':'Difference of marginal model-loss medians is not the median of paired per-session loss differences. Both are reported separately.','v2_scope':'No v2 fitting or predictor choices are performed by this audit. B0+HARQ masks are the owner-specified coverage rule only.'}
print(json.dumps(audit,ensure_ascii=True,allow_nan=False,separators=(',',':')))
'@
uv run --offline --frozen --no-sync python -B -c $rp4AuditCode
```

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false
