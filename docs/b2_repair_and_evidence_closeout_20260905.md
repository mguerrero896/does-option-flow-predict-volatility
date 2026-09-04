# Reparación de B2 y cierre de evidencia — 5 de septiembre de 2026

Se corrigió un defecto real en la construcción de B2, se midió su efecto real y se
rectificó la interpretación de las campañas. No se compró almacenamiento, no se
hicieron descargas ni se eligió otro candidato después de ver esta comparación.

## 1. Reparación aplicada, no solamente propuesta

`build_b2v2_from_activity` excluye ahora el historial inelegible antes de calcular
centro y escala, incluido el fallback por activo. Conserva las claves originales,
ventana de 60 sesiones anteriores, mínimo 20 sesiones elegibles y cobertura de
historial del 80 %. Un dato inválido no se convierte en cero.

La implementación existente se integró en el checkout local `main`. Además,
`build_target_blind_common_panel_v22.build_panel` pasa efectivamente la elegibilidad
de la variante primaria al normalizador. Los constructores v2.3 y v2.4 delegan en
ese mismo productor y reciben la reparación. La prueba del productor real falló
antes y pasó después. Otra prueba verifica el fallback por activo ante un cambio
sintético de 1e9 exclusivamente en una fila excluida.

Los demás callers se revisaron: source-time, extensión local/legacy y multiscale
ya pasan el sidecar; la replicación independiente elimina las sesiones incidentadas
antes de normalizar. La ruta B1v3 usa transformaciones compactas por fila, no esta
normalización histórica. No se modificaron sus modelos ni se imputaron sus faltantes.

## 2. Impacto medido sobre datos reales

Fuente: [impacto y hashes](../artifacts/b2_history_repair_v1/feature_impact.json).
Se reprodujeron exactamente los valores del panel predictor publicado antes de
compararlo con la reparación; no se leyeron targets en esta etapa.

| Universo | Completos antes/después | Orígenes con variables modificadas | Celdas modificadas |
|---|---:|---:|---:|
| B2, 180 sesiones y 77.328 orígenes totales | 68.237 / 68.237 | 27.153 | 244.377 |
| Panel predictor común publicado, 159 sesiones | 62.266 / 62.266 | 24.604 | 221.436 |

451 filas inelegibles afectaban historial posterior. En el panel común, la
proporción modificada es `24.604 / 62.266 × 100 = 39,51 %`. Se preservan todas las
filas completas; no hubo selección por el signo del resultado.

## 3. Reevaluación ejecutada: reparación aislada, no nueva campaña confirmatoria

Fuente: [protocolo de sensibilidad](../artifacts/b2_history_repair_v1/evaluation_protocol.json)
y [resultado completo](../artifacts/b2_history_repair_v1/evaluation_result.json).

Se reutilizaron los targets ya expuestos, los parámetros archivados de Gamma y
LightGBM y los dos folds originales. No hubo búsqueda de hiperparámetros. Se
conservan 62.254 filas del panel con target válido y se generan 149.688 pronósticos
por brazo de comparación. Los 12 orígenes excluidos por target incompleto son los
mismos del resultado antiguo, no exclusiones nuevas de esta reparación.

El replay anterior reprodujo los pronósticos, QLIKE, errores absolutos y errores
cuadráticos con **error máximo cero**. B0 y B1 también permanecen idénticos entre
los dos brazos, con error máximo cero: el cambio medido corresponde a B2.

El titular siguiente usa únicamente las 32 sesiones del holdout histórico
2026-02-05 a 2026-03-23, no el fold de validación:

| Modelo | Ganancia QLIKE B1 sobre B0 | Ganancia B2 sobre B1 anterior | Ganancia B2 sobre B1 reparada |
|---|---:|---:|---:|
| Gamma | +0,008171247318 | −0,003126621051 | −0,002205552554 |
| LightGBM | +0,004175806123 | +0,001368014098 | +0,001055171107 |

Ganancia = pérdida del modelo padre menos pérdida del hijo, promediada por origen.
El JSON también conserva promedios por sesión, activos, regímenes definidos con
training y cuatro bloques cronológicos. No se promedian validación y holdout para
presentarlos como una réplica nueva.

La corrección reduce el deterioro QLIKE de Gamma, pero no cambia su signo. LightGBM
mantiene B2 > B1 > B0 global descriptivo, aunque la ganancia B2 se reduce. Ambos
B2 conservan bloques y regímenes negativos. Además, MAE y RMSE de B2 empeoran
ligeramente respecto al B2 anterior en ambos modelos, aunque siguen siendo mejores
que los de B1. Por tanto, arreglar el bug no mejoró todas las métricas ni confirmó
robustez general. Se publican ambas direcciones, sin seleccionar la favorable.

## 4. Qué se conserva de HARQ v4, v5 y v6

Es otra familia de modelos y otra muestra; no se le atribuye automáticamente el
efecto de reparar la normalización del Full Tape. La
[auditoría HARQ](../artifacts/harq_existing_forecasts_audit_v1/report.md) compara las
mismas 1.968 filas: 164 sesiones, seis activos y dos latencias. Las tres versiones
mejoran descriptivamente las tres métricas globales. A 120 segundos, v4 tiene:

| Modelo | QLIKE, menor es mejor |
|---|---:|
| B0 HARQ | 0,145260992161 |
| B1 | 0,145074418842 |
| B2 | 0,144680332842 |

V4 obtiene menor QLIKE/RMSE para B2 que v6; v5 obtiene menor MAE. Ninguna domina
todas las métricas y regímenes. La afirmación de que v6 era inequívocamente la
mejor y globalmente robusta se rectifica en
[la corrección del reporte v6](../artifacts/harq_fixed_specialist_v6_posthoc/REPORT_CORRECTION.md).
Su selección por activo usó resultados v4, y el replay de agosto copiado en su
resultado corresponde a Phase8, **no a una prueba futura de v6**.

## 5. Clasificación y defectos históricos

La [auditoría WP01](../artifacts/target_blind_v22/successor_holdout_exposure_v1.json)
demuestra que 32/32 sesiones del holdout PIT v2.2 ya formaban parte de los calendarios
anteriores C3 y RP2 de desarrollo. El productor del estado canónico, README, STATUS
y contratos ya lo clasifican como retrospectivo/descriptivo. Los originales
firmados no se reescriben. Cambiar una fecha de corte o autorizar una repetición
permite el análisis retrospectivo, pero no elimina la información ya utilizada
para seleccionar el procedimiento.

OHLCV fabricado, desbordamiento Int8 y benchmarks/cortes sustituidos se mantienen
como incidentes históricos corregidos, no como seis defectos todavía activos.
Las fuentes y cifras verificadas están en la auditoría HARQ. La disponibilidad
histórica para el cliente sigue sin demostrarse mediante `created_at`/`sip_timestamp`;
comparar alertas agregadas con trades individuales tampoco identifica revisiones
ni backfill. No hay metadatos que permitan reparar retrospectivamente esa carencia.

No se suman las sesiones de campañas solapadas ni se cuentan como replicaciones
independientes. La instantánea Git de la auditoría encontró 44 worktrees, 14 con
cambios. Las reparaciones del productor y de la autoridad se integraron en el
checkout local main sin mezclar todos esos árboles ni publicar al remoto.

## 6. Ejecución, custodia y verificación

La ejecución de impacto/sensibilidad se hizo en el worktree prospectivo HARQ retenido
(checkout `cbb6`). El registro conserva hashes de inputs, runtime y pronósticos. El
snapshot `artifacts/b2_history_repair_v1/feature_stage_source.py` conserva exactamente
la fuente usada al generar las variables; posteriormente se corrigió en el lector
de auditoría la distinción entre hash semántico y hash de archivo del preregistro.
La auditoría de custodia original acredita el hash de archivo correcto. No cambió
ningún dato archivado por esa corrección del lector.

Comandos ejecutados desde cbb6:

```powershell
uv run python -X utf8 -m scripts.audit_b2_history_repair_v1 features
uv run python -X utf8 -m scripts.audit_b2_history_repair_v1 evaluate
uv run python -m scripts.audit_harq_existing_forecasts_v1 --verify
uv run pytest tests/unit/test_audit_b2_history_repair_v1.py tests/unit/test_build_target_blind_common_panel_v22.py tests/unit/test_build_target_blind_common_panel_v23.py tests/unit/test_build_target_blind_common_panel_v24.py tests/unit/test_target_blind_panel_v22.py tests/unit/test_phase6_b2.py tests/unit/test_harq_existing_forecasts_audit_v1.py
```

Verificación final: **79 pruebas focalizadas en cbb6 y 73 en main**, todas
aprobadas; Ruff y tipado focalizado de los productores modificados, aprobados.
La auditoría HARQ reprodujo sus inputs, métricas y reporte con `--verify`.

Los writers no sobrescriben evidencia distinta; no se deben borrar artefactos para
forzar un replay. El estado de las pruebas focalizadas no equivale a afirmar que
pasó toda la suite ni todo el tipado del repositorio. Se preservó WIP ajeno,
incluidas modificaciones preexistentes de `phase6_evaluation.py` en cbb6.

Se utilizaron las skills de depuración y evaluación para exigir reproducción del
defecto, controles negativos y comparación de varias métricas en la misma muestra.
Alfa gastado: **0**; peticiones a proveedores: **0**. Reutilizar estos datos no
requiere presentar un gasto de alfa como si recuperara independencia. Se mantiene
`RESEARCH_ONLY`, `NOT INVESTMENT ADVICE`, `capital_go=false`.
