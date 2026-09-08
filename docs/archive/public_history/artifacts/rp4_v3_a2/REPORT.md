# RP4 v3 — A2: materialización y verificación antes de evaluar

Estado: **A2 COMPLETO; evaluación de modelos todavía no iniciada al cerrar esta etapa**.
RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false. No publicación, descargas ni cambios en v1/v2 o phase9.

## Panel y cadena de custodia

Se completaron 3.024 combinaciones activo–sesión: 195.479 orígenes, 504 sesiones y seis activos. La primera materialización conserva exactamente las 172 columnas de v2 por `(asset, session_date, origin_minute)` y añade las cuatro variables de gamma y `jump30`. La recodificación posterior produce 179 columnas, sin eliminar sesiones ni orígenes. Los conjuntos anidados registrados tienen 29, 69 y 138 predictores; copiar una columna diagnóstica al panel no la incorpora al diseño.

| Artefacto privado | SHA-256 |
|---|---|
| `materialized/panel.parquet` | `ab2977127fde0c65458e15a984924b136b9bf88ba0588240d80bd6a81545dc45` |
| `materialized/manifest.json` | `1e6b5aeade5624bd12ced17d7a55e18b3102a7597ea0af559f5e0a8793b90eb0` |
| `materialized_empty_windows/panel.parquet` — entrada de evaluación | `a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637` |
| `materialized_empty_windows/manifest.json` | `e3a76fecf274d6233c1059221b9755297f5854a6c4519b2b806344008bec59e3` |
| [Configuración de ejecución](../../../../../artifacts/rp4_v3_a2/evaluation_release.json) | `5e3046af023c9f41380307d62537aa4e8fc7514b23d51a95ea1f960ee23fe5bb` |

Raíz privada: `private-input/e63a7488cbab65e3773b`. Especificación efectiva: `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5`; conserva A1 y añade la decisión 132 antes de materializar o evaluar. Las fuentes y el código fueron comprobados por hash antes y después de la extracción. Los metadatos de esta carpeta son copias exactas de sus originales; los paneles y la cinta no se incluyen en Git.

RV30: 195.465 pares finitos, diferencia máxima y media **0**, y 14 pares no finitos coincidentes. No se sustituyeron ni imputaron objetivos. `jump30` se reconstruyó por separado con la máscara de barras observadas del productor RP2; su disponibilidad no excluye filas de la evaluación primaria de QLIKE. [Manifiesto](../../../../../artifacts/rp4_v3_a2/gamma_manifest.json) · [Cobertura por activo y variable](../../../../../artifacts/rp4_v3_a2/gamma_coverage.csv).

## Re-derivación independiente y causa de las diferencias

El candidato entregado tiene SHA-256 `edc0263c8d8a76c897fc6d8e54462fd3ffb8f3aa475eb7ee4b55551b4a7fdfcc`. La derivación independiente precedió a la inspección de su productor. Se conservaron puentes de comparación, no modelos alternativos seleccionables.

Al reproducir su definición, pero conservando los dividendos del panel v2, aparecieron **455 discrepancias** en cada una de las tres exposiciones; el conteo fue exacto en las 195.479 filas. Todas corresponden a NVDA, 65 orígenes en cada sesión del 27, 28 y 31 de agosto y del 1 al 4 de septiembre de 2026. El constructor entregado carga el snapshot antiguo de dividendos; v2 carga el actualizado. Las tasas coinciden.

| Sesiones NVDA | Cash del candidato | Cash de v2/v3 | Diferencia |
|---|---:|---:|---:|
| 2026-08-27 | 0,28 | 0,53 | 0,25 |
| 2026-08-28, 2026-08-31 y 2026-09-01 a 04 | 0,27 | 0,52 | 0,25 |

El snapshot actualizado contiene un dividendo de 0,25 con `declarationDate=2026-08-26` y `date=2026-09-10`, ausente en el snapshot antiguo. La auditoría controlada cambió **únicamente ese cash**: con el dato antiguo reprodujo exactamente el candidato en las cuatro columnas y en las 195.479 filas, con diferencia máxima y media 0. Las otras 3.017 combinaciones activo–sesión ya coincidían. No se modificó el panel de producción ni se leyó ningún objetivo en esta atribución. V3 conserva el carry congelado de v2. [Prueba y hashes de fuentes](../../../../../artifacts/rp4_v3_a2/candidate_carry_audit.json) · [Código](../../../../../artifacts/rp4_v3_a2/audit_candidate_carry.py) · [Log, salida 0](../../../../../artifacts/rp4_v3_a2/candidate_carry_audit.log).

Antes de esa atribución, la diferencia máxima/absoluta media candidato–legacy era: gamma total 5.697.464,933521 / 4.104,354958; gamma cerca del spot 5.586.970,567497 / 2.902,383342; gamma cercana y corta 5.485.852,873230 / 2.320,283359. El contador tenía ambas diferencias 0. Son unidades de exposición, no QLIKE.

La versión usada para evaluar **no es el puente legacy**. Aplica IV en [0,03; 3], historial elegible antes del cálculo, primera versión disponible por identificador, disponibilidad simultánea por `created_at` y `executed_at`, y NaN cuando todavía no existe un prefijo válido. Los puentes separan esas modificaciones de la diferencia de dividendos. [Comparación completa, por columna y activo](../../../../../artifacts/rp4_v3_a2/gamma_comparison.csv).

Entre 700.049.350 filas contabilizadas, se rechazaron por IV 28.962.654 (4,137230325 %): 1.337.876 nulas, 26.399.507 inferiores a 0,03 y 1.225.271 superiores a 3; no hubo IV no finita no nula. Respecto al rango antiguo, 26.990.858 filas adicionales quedan fuera. El porcentaje es `100 × rechazadas / filas contabilizadas`; no es una tasa de exclusión de orígenes. [Conteos por activo–sesión](../../../../../artifacts/rp4_v3_a2/gamma_counts.csv).

Las cuatro variables de gamma son finitas en 195.089/195.479 orígenes (99,80049 % aproximadamente). Los 390 sin prefijo válido corresponden al día 2025-10-20 y se mantienen como NaN. No se convierten en actividad cero ni se eliminan del panel.

## Regla de ventanas vacías aplicada

Se conservaron exactamente conteos, contratos, tamaño, prima, tasa y flujos. Sólo las 30 columnas de forma/ratio registradas (17 de 5 minutos y 13 de 30 minutos) se recodifican a NaN cuando el contador correspondiente es cero; 12.356 valores finitos cambiaron. Se añaden los dos indicadores solicitados. Los demás valores, incluidos RV30, B0 y B1, permanecen exactos.

| Sesión | Orígenes vacíos 5 min | Orígenes vacíos 30 min |
|---|---:|---:|
| 2025-05-15 | 5 | 0 |
| 2025-08-21 | 10 | 0 |
| 2025-09-18 | 10 | 6 |
| 2025-10-20 | 390 | 390 |
| 2025-10-22 | 6 | 0 |
| 2026-07-23 | 3 | 0 |
| Total | 424 | 396 |

No hay contadores desconocidos ni ventanas vacías en confirmación. Este es el censo del panel de entrada; B4 distingue también el censo efectivamente evaluado y el contraste dentro/fuera. El signo de esos contrastes no se ha calculado en A2. La atribución de las pérdidas históricas de v2 propuesta por el usuario no se convierte aquí en una conclusión causal. [Censo por activo–sesión](../../../../../artifacts/rp4_v3_a2/empty_window_census.csv) · [Recodificaciones por columna](../../../../../artifacts/rp4_v3_a2/empty_window_recode_audit.json) · [Manifiesto](../../../../../artifacts/rp4_v3_a2/empty_window_manifest.json).

## Comandos y verificación

Entorno y comandos completos, versiones, resultados de prueba y hashes: [verificación previa](../../../../../artifacts/rp4_v3_a2/verification_before_fit.json) y [recibo A2](../../../../../artifacts/rp4_v3_a2/receipt.json). Se usa el entorno Python 3.12 existente, `uv run --offline --frozen --no-sync`, sin instalar paquetes.

| Paso ejecutado | Código de salida |
|---|---:|
| `python -B artifacts/rp4_v3_code/materialize_gamma.py --spec artifacts/rp4_v3_a1/specification.json --spec-sha256 49b625a4dbca7b725a6b38defc25e76109be7b280d711355a55ce97a7443048b --output-root private-input/e63a7488cbab65e3773b --workers 4` | 0 |
| Auditoría independiente de atribución del carry, siete sesiones; comando exacto en su log | 0 |
| `python -B artifacts/rp4_v3_code/empty_windows.py --spec-sha256 930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5` | 0 |
| `python -B -m artifacts.rp4_v3_code.execute --spec-sha256 930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5 --prepare-only` | 0 |
| 142 pruebas sintéticas/regresión, Ruff, formato y tipado focalizado | 0 |
| Tras añadir únicamente el enlace del informe B4 a este cierre A2: 21 pruebas de informe, Ruff y formato | 0 |

Las pruebas sintéticas y la coincidencia de constructores no prueban ventaja predictiva. La etapa siguiente aplica una sola especificación a primaria y confirmación, conserva todos los signos y no convierte la reutilización de ventanas entre versiones en replicaciones independientes.
