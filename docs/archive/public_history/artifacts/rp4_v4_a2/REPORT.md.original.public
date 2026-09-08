# RP4 v4 A2 — validación de RV15 y RV5

Estado: **PASS tras investigación documentada; cero ajustes de modelos**. Los objetivos se materializaron después del freeze A1, sobre las mismas barras RP4 y con el estimador de varianza realizada de `rp2_block3`. No se modificaron predictores, RV30, rezagos, máscaras, fechas ni artefactos anteriores.

## Paridad por clave y valor

Unión uno a uno por `(asset, session_date, origin_minute)`, nunca por posición. La comparación binaria se refiere a cada Float64 alineado, no a los contenedores Parquet.

| Objetivo | Claves comunes registradas | Pares finitos comparados | Diferencias binarias finitas | Diferencia máxima | Diferencia media | Diferencias de disponibilidad |
|---|---:|---:|---:|---:|---:|---:|
| RV15 | 83.509 | 83.505 | 0 | 0 | 0 | 4 |
| RV5 | 83.509 | 83.507 | 0 | 0 | 0 | 2 |

Las 81.845 claves comunes que pertenecen a la máscara elegible de v3 coinciden exactamente para ambos horizontes. El nuevo panel contiene 195.479 orígenes y 504 sesiones; sus 192.032 filas elegibles de v3 —incluido entrenamiento— tienen ambos objetivos positivos y finitos. Ninguna exclusión nueva de orígenes o sesiones.

La referencia registrada termina el 2026-07-17. La confirmación no tiene una referencia anterior de RV15/RV5: se calculó desde las mismas barras con los mismos controles, pero su paridad con una referencia previa es **NO VERIFICABLE porque no existe**.

## Resolución de las discrepancias, antes de evaluar

Los seis pares discrepantes corresponden a cuatro orígenes de TSLA del 2025-10-28, ya inelegibles en v3: RV15 en minutos 240/245/250/255 y RV5 en 250/255. Falta el cierre observado del minuto 255 (13:45 Nueva York). La referencia histórica admitía el relleno de ese minuto (1/390 de la sesión); reproducir exactamente su relleno recuperó los seis valores registrados bit a bit. RP4 exige todos los cierres observados del horizonte, por lo que conserva NaN. No se rellenó el panel nuevo ni se cambió la máscara.

El control RV30 tiene 195.465 pares finitos exactamente iguales. Sus otros 14 casos son NULL original frente a NaN de control: siete TSLA 2025-10-28 y siete AAPL 2026-02-11, todos inelegibles y afectados por un cierre faltante. Son dos representaciones de ausencia, no cambios de valor.

El manifiesto de materialización permanece con `preflight_pass=false` y su salida original 2. La resolución independiente, con salida 0, verifica las seis causas, los 14 casos de ausencia y los hashes de las 285 fuentes. El lanzador exige esa resolución y la incluye en cada release; no se convirtió el fallo original en un éxito mediante edición.

## Custodia y ejecución

- Objetivos: `private-input/d6960c1f5596730d9006`, SHA-256 `b2357a10a8a4955499e94b576b7853129e957ad70702da09bebbc9b6befd35db`.
- Manifiesto original: SHA-256 `ae4c1e7b104c5f2cee2402ded5d0515e04e5264759bf70f0e1098432806c8316`.
- Resolución: `private-input/91ab0c3f0ee3b4b9da7e`, SHA-256 `05ff5f4b8127238dc9fb8371e530c12a1d2bbf23c30ef1363edf0f829b87722f`.
- Productor: `artifacts/rp4_v4_code/materialize_targets.py`, SHA-256 `8c6f9acc1dd3d995bea1ca75456c8fda6d4b6da1dc0b734dfbc23917b1265ce6`.
- Recibo original de objetivos: `private-input/736ad0a950ac226f3c3e`, SHA-256 `055d9b432a1765acf22ca78a5dc3ad476fd9118c6afb98c07cdf09edb5ade4b2`.

El recibo de esta etapa registra los comandos completos, los dos errores iniciales de proyección/tipo y sus regresiones, la materialización conservadora con salida 2, la resolución con salida 0, las pruebas y los hashes del código y de los releases. La cobertura por activo y sesión se conserva en `targets/coverage.csv` y `targets/session_census.csv`, referenciados por el manifiesto.

Configuración registrada: ocho shards disjuntos por sesión, cuatro hilos por modelo; orden RV15 primaria, RV15 confirmación, RV5 primaria, RV5 confirmación. Se usa directamente la configuración autorizada; no se afinó el rendimiento sobre una ventana de evaluación. Los 32 hilos lógicos y la memoria física se registran en los recibos de ejecución. No hay descargas, publicación, cambios de phase9 ni modificación de v1/v2/v3. `RESEARCH_ONLY`, `NOT INVESTMENT ADVICE`, `capital_go=false`.
