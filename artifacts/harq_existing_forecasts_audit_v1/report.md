# Auditoría comparativa de forecasts HARQ v4, v5 y v6

Las tres jerarquías mejoran descriptivamente QLIKE, MAE y RMSE globales. V6 no domina a v4/v5 en todas las métricas y B1 conserva regímenes adversos. Esta auditoría compara forecasts expuestos; no valida su construcción ni convierte el replay en confirmación independiente.

Misma máscara y RV30: 1968 filas por variante, 164 sesiones × seis activos × dos latencias, 2025-11-05 a 2026-07-10. Sin exclusiones ni reajustes.

| Versión | Latencia | Modelo | QLIKE | MAE | RMSE |
|---|---:|---|---:|---:|---:|
| v4 | 60 s | B0HARQ | 0.144109553911 | 4.714432700e-06 | 9.491370928e-06 |
| v4 | 60 s | B1 | 0.143931954639 | 4.712651157e-06 | 9.484687700e-06 |
| v4 | 60 s | B2 | 0.143545143351 | 4.707429337e-06 | 9.477065950e-06 |
| v4 | 120 s | B0HARQ | 0.145260992161 | 4.719871800e-06 | 9.517694851e-06 |
| v4 | 120 s | B1 | 0.145074418842 | 4.717875237e-06 | 9.512630826e-06 |
| v4 | 120 s | B2 | 0.144680332842 | 4.715470476e-06 | 9.507324689e-06 |
| v5 | 60 s | B0HARQ | 0.144109553911 | 4.714432700e-06 | 9.491370928e-06 |
| v5 | 60 s | B1 | 0.143997671078 | 4.712364270e-06 | 9.489576610e-06 |
| v5 | 60 s | B2 | 0.143615549269 | 4.703693951e-06 | 9.483540468e-06 |
| v5 | 120 s | B0HARQ | 0.145260992161 | 4.719871800e-06 | 9.517694851e-06 |
| v5 | 120 s | B1 | 0.145154665060 | 4.718004031e-06 | 9.515848902e-06 |
| v5 | 120 s | B2 | 0.144785210278 | 4.711696382e-06 | 9.510073993e-06 |
| v6 | 60 s | B0HARQ | 0.144109553911 | 4.714432700e-06 | 9.491370928e-06 |
| v6 | 60 s | B1 | 0.143923744580 | 4.712310799e-06 | 9.484817232e-06 |
| v6 | 60 s | B2 | 0.143695493217 | 4.706944101e-06 | 9.477851822e-06 |
| v6 | 120 s | B0HARQ | 0.145260992161 | 4.719871800e-06 | 9.517694851e-06 |
| v6 | 120 s | B1 | 0.145069499475 | 4.717397403e-06 | 9.512769199e-06 |
| v6 | 120 s | B2 | 0.144835534440 | 4.714713717e-06 | 9.508007422e-06 |

## Correcciones de interpretación

1. V4 obtiene menor QLIKE y RMSE para B2 que v6 en ambas latencias; v5 obtiene menor MAE. V6 mejora marginalmente QLIKE/MAE de B1 y el conteo de activos positivos mediante selección posterior a v4.
2. El PASS de v6 usa los cinco gates registrados en v5: media, últimas 30 y leave-one-block positivos, ≥4 activos positivos y ≤1 negativo. No incluye regímenes. La prueba diagnóstica de v4 sí exige regímenes no negativos y todos los activos positivos. Ninguna versión pasa esa conjunción más estricta. El protocolo v4 no tenía una sección de aceptación explícita; esta es una diferencia de definición, no una atribución de incumplimiento de preregistro.
3. La semana 24–28 de agosto proviene de los modelos Phase8 archivados. El reporte v6 copia ese resumen. No es una evaluación futura de v6.
4. El nombre v6 y una fecha de corte simulada no deshacen la selección basada en resultados ya observados. Los p HAC5 previos se conservan como diagnóstico; no corrigen esa selección ni confirman la hipótesis.

| Versión | Gates diagnósticos v4 | Gates registrados v5 | Peor régimen B1 a 120 s (capped) |
|---|---|---|---:|
| v4 | False | False | -5.50542483317e-05 |
| v5 | False | False | -5.3566472276e-05 |
| v6 | False | True | -3.6816193314e-05 |

## Defectos históricos y procedencia

OHLCV: 22.967/152.954 orígenes de desarrollo afectados; 0 en validación. Se reacquirieron 138.239 barras y se corrigió el productor. El desbordamiento Int8 también fue corregido. Los benchmarks/cortes sustituidos se mantienen en el registro histórico; no se presentan todos como fallos activos.

created_at/sip_timestamp no prueban recepción histórica por el cliente. Backfill/revisiones UW siguen sin identificarse al comparar alertas agregadas con trades individuales. Son límites de procedencia vigentes.

El 96,173532% de SSE concentrado en tres errores corresponde a B0 de la antigua evaluación de 60 sesiones. En estos forecasts B0 a 120 s concentra 38,773396%; las muestras y modelos difieren, por lo que esa diferencia no es una estimación causal del efecto de una reparación.

- historical_60_session_sse: HISTORICAL_DIAGNOSTIC_NOT_CURRENT_SAMPLE. `artifacts/harq_extreme_forecast_audit_v2/result.json:83`.
- historical_customer_availability: PROXY_ONLY_UNRESOLVED. `docs/provider_timing_official_docs_audit_v1_20260812.md:18`.
- intraday_integer_overflow: HISTORICAL_REPAIRED. `docs/methodology_decisions.md:1401`; `src/mds650/har.py`.
- ohlcv: HISTORICAL_REPAIRED. `docs/methodology_decisions.md:976`; `docs/methodology_decisions.md:985`; `docs/rp2_v3/SUPERSEDED_RESULTS.md:37`; `src/mds650/rp2/bars.py:393`.
- target_benchmark_and_clock_replacements: HISTORICAL_SUPERSEDED_RESULTS. `docs/rp2_v3/SUPERSEDED_RESULTS.md:24`; `docs/rp2_v3/SUPERSEDED_RESULTS.md:77`; `docs/rp2_v3/SUPERSEDED_RESULTS.md:84`.
- uw_backfill_revision: CROSS_CHANNEL_NOT_IDENTIFIABLE. `docs/gate5_pit_foundations_v1.md:100`.

Inventario Git a 2026-09-04T20:05:58.021086+00:00: 44 worktrees, 14 con cambios. Es una instantánea; no demuestra que las campañas sean replicaciones independientes.

## Reproducción

`uv run python -m scripts.audit_harq_existing_forecasts_v1 --verify`

[JSON con métricas por activo/régimen, gates, fuentes y hashes](result.json). No se publican filas individuales. QLIKE/MAE/RMSE menores son mejores; ganancias parent−child positivas favorecen al hijo. RESEARCH_ONLY; alpha gastado 0; capital_go=false.
