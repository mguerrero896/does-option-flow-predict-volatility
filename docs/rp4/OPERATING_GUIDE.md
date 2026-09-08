# RP4 — runbook de reproducción y verificación local

La lectura científica vigente es [RESULTADO_FINAL.md](RESULTADO_FINAL.md).
El cierre es v4: ventaja secuencial en RV15 de la familia lineal, no ventaja
uniforme de las dos familias ni réplica independiente. Este documento no cambia
especificaciones, datos, modelos, resultados ni autorizaciones.

## 1. Tres operaciones distintas

| Operación | Qué demuestra | Qué no hace |
| --- | --- | --- |
| Verificar la copia pública | Igualdad de bytes con los pins de este cierre | No valida datos licenciados ausentes ni vuelve a calcular estadísticas |
| Verificar la custodia local | Lo anterior más hashes de los resultados privados y logs citados por seis recibos B2/B3 | No vuelve a recorrer todos los componentes, cargar paneles ni ajustar modelos |
| Repetir productores con originales | Procedimiento histórico de materialización y ejecución, sujeto a las raíces y recibos originales | No convierte sesiones reutilizadas en evidencia independiente |

La repetición completa desde cero **no se ejecutó en esta revisión: NO
VERIFICABLE**. Una copia con rutas o nombres saneados no sustituye por sí sola los
originales fijados por hash. Los supervisores de evaluación no tienen una opción
`--output-root`: sus raíces proceden de la especificación. No se deben editar
esas raíces, hashes ni recibos para forzar una repetición.

## 2. Configuración local sin publicar rutas ni credenciales

Ejecutar desde la raíz del checkout original. `RP4_PYTHON_ENV` debe estar
configurada localmente con la ruta del entorno existente; este documento no
instala paquetes, descarga datos ni muestra su valor. Los originales de UW/FMP,
tasas, dividendos, eventos, paneles y recibos requieren acceso local bajo las
licencias correspondientes. No copiar claves ni archivos licenciados al repositorio.

```powershell
$repositoryRoot = (Get-Location).Path
if (-not $env:RP4_PYTHON_ENV) { throw 'Falta configurar RP4_PYTHON_ENV localmente' }
$env:UV_PROJECT_ENVIRONMENT = $env:RP4_PYTHON_ENV
$env:PYTHONPATH = @(
    $repositoryRoot
    (Join-Path $repositoryRoot 'src')
    (Join-Path $repositoryRoot 'scripts')
    (Join-Path $repositoryRoot 'artifacts/rp4_code')
    (Join-Path $repositoryRoot 'artifacts/rp4_v2_code')
    (Join-Path $repositoryRoot 'artifacts/rp4_v3_code')
) -join [IO.Path]::PathSeparator
$env:MYPYPATH = $env:PYTHONPATH
$env:PYTHONIOENCODING = 'utf-8'
$env:OMP_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
$env:MKL_NUM_THREADS = '2'
```

El entorno cerrado registra Python 3.12.12; LightGBM 4.7.0, NumPy 2.5.2,
pandas 3.0.5, Polars 1.44.1, PyArrow 25.0.1 y SciPy 1.18.0.
El lockfile esperado es
`960c8a2638cdf39be44acb6d06b0e355eceab4e6658357f089f2b9aa159d61d0`.
Fuente: [release v3](../../artifacts/rp4_v3_a2/evaluation_release.json) y
[release v4 RV15](../../artifacts/rp4_v4_a2/evaluation_release_rv15.json).
La ausencia del entorno no se resuelve actualizando esas dependencias.

## 3. Gates sin modelos ni inferencia

Estos comandos nuevos de auditoría son de lectura y usan sólo la biblioteca
estándar. El modo público omite explícitamente los hashes de archivos fuera del
checkout; el modo local requiere los originales, pero sólo lee sus bytes.
Los alias de salida evitan mostrar sus rutas. Un cambio de bytes produce salida 1.
Estos gates se verificaron en el checkout original del cierre. Los recibos
contienen raíces originales: trasladar o sanear una copia requiere comprobar
aparte el mapa de rutas y hashes. Este gate no certifica esa portabilidad.

```powershell
uv run --offline --frozen --no-sync python -B artifacts/rp4_cleanup_review/inventory_review.py --verify-public
if ($LASTEXITCODE -ne 0) { throw 'Fallo de custodia pública' }
uv run --offline --frozen --no-sync python -B artifacts/rp4_cleanup_review/inventory_review.py --verify-licensed
if ($LASTEXITCODE -ne 0) { throw 'Fallo de custodia local' }
```

Comprobados en este cierre: 140 verificaciones públicas y 192 verificaciones
incluyendo resultados privados/logs, ambas con salida 0. No son 192 archivos
necesariamente distintos: cada recibo vuelve a comprobar sus dependencias.
Se fijan los seis recibos, sus releases, código, resultados y logs, además de
los documentos/CSV enumerados en `PINS`. No se verifica el grafo completo de
checkpoints ni la integridad intrínseca de los datos mediante este gate.

Las pruebas de este verificador son fixtures sintéticos de metadatos:

```powershell
uv run --offline --frozen --no-sync python -B -m pytest -q -p no:cacheprovider artifacts/rp4_cleanup_review/test_inventory_review.py
uv run --offline --frozen --no-sync ruff check artifacts/rp4_cleanup_review/inventory_review.py artifacts/rp4_cleanup_review/test_inventory_review.py
uv run --offline --frozen --no-sync ruff format --check artifacts/rp4_cleanup_review/inventory_review.py artifacts/rp4_cleanup_review/test_inventory_review.py
uv run --offline --frozen --no-sync python -B -m mypy --explicit-package-bases --follow-imports=silent artifacts/rp4_cleanup_review/inventory_review.py artifacts/rp4_cleanup_review/test_inventory_review.py
```

No usar `--aggregate-only` como gate de hashes: aunque no ajusta modelos,
recalcula inferencia. Tampoco usar un supervisor con recibo ausente como un
verificador inocuo: puede iniciar ajustes.

## 4. Comandos históricos de ejecución

Los siguientes comandos conservan el espacio técnico de módulos original,
permitido por el contrato de publicación. Son comandos existentes de los
supervisores, **no ejecutados durante esta revisión**. Se conserva la historia
base; este runbook no exige migrarla ni crear otro destino de publicación.
Los originales licenciados y sus raíces siguen siendo requisitos separados.

### v3, RV30

El panel efectivo requiere la materialización gamma, la comparación por claves y
la recodificación de ventanas vacías. El [recibo A2](../../artifacts/rp4_v3_a2/receipt.json)
conserva los comandos ejecutados, salidas 0 y hashes de esas tres operaciones.
La raíz local v3 es el valor original de `data_root` en la especificación efectiva;
se puede leer en una variable sin imprimirlo. No sustituir el panel candidato
anterior ni el panel sin recodificar.

Antes del supervisor, la secuencia A2 histórica fue la siguiente. Los alias se
resuelven desde los JSON originales y no se imprimen. Los dos primeros programas
rechazan una salida ya completa; no borrar sus manifiestos para hacerlos pasar.
El productor gamma también escribe sus comparaciones por clave; el segundo
comando atribuye exclusivamente la diferencia de dividendos del candidato.

```powershell
$v3Root = (Get-Content artifacts/rp4_v3_a1/specification.json -Raw | ConvertFrom-Json).data_root
uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_code/materialize_gamma.py --spec artifacts/rp4_v3_a1/specification.json --spec-sha256 49b625a4dbca7b725a6b38defc25e76109be7b280d711355a55ce97a7443048b --output-root $v3Root --workers 4
if ($LASTEXITCODE -ne 0) { throw 'Materialización gamma falló o ya está cerrada' }
$comparisonScript = Join-Path $v3Root 'operations/audit_candidate_carry.py'
if ((Get-FileHash $comparisonScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'dccf6d542ef261e982124f22223148d4a8975899927f35c9e95bf5db2b399ace') { throw 'Cambió el comparador original' }
uv run --offline --frozen --no-sync python -B $comparisonScript
if ($LASTEXITCODE -ne 0) { throw 'Comparación gamma falló o ya está cerrada' }
uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_code/empty_windows.py --spec-sha256 930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5
if ($LASTEXITCODE -ne 0) { throw 'Recodificación de ventanas vacías falló' }
```

Salidas históricas: 0, 0 y 0. Gamma productor SHA-256
`2f59184b5a36b301252bb11eaf779c8128cef0f45266368f44b1a7d35f3644a3`;
recodificador SHA-256
`42c5bdc76fe1432a9d0fa2517ac157d4c02237da1ae8e0b331d1c960203564a5`.
El comparador tiene una [copia de custodia](../../artifacts/rp4_v3_a2/audit_candidate_carry.py),
pero su comando histórico usa el original local y depende de sus insumos fijados:
su ejecución desde una distribución pública aislada es **NO VERIFICABLE**.
No invocar `--register`: el registro ya existe y sus tiempos/hashes son inmutables.

```powershell
$v3Hash = '930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5'
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v3_code.execute --spec-sha256 $v3Hash --prepare-only
if ($LASTEXITCODE -ne 0) { throw 'Preflight v3 falló' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v3_code.execute --spec-sha256 $v3Hash --window primary
if ($LASTEXITCODE -ne 0) { throw 'Primaria v3 falló' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v3_code.execute --spec-sha256 $v3Hash --window confirmation
if ($LASTEXITCODE -ne 0) { throw 'Confirmación v3 falló' }
```

El supervisor original fija **4 particiones × 4 hilos**. Con un recibo final
`COMPLETE` válido compara hashes y devuelve `WINDOW_ALREADY_COMPLETE`; no
crea una nueva ejecución. Sin recibo final, reanuda componentes válidos y calcula
lo pendiente. No borrar recibos, componentes o locks para forzar el camino de ajuste.

El cierre original v3 conserva fallos del secundario de salto y la recalibración
MZ adversa. El [cierre secundario final](results_v3_revision2.md) documenta
los pases numéricos separados y el combinado de 419 sesiones; no se obtiene
ese resultado simplemente volviendo a ejecutar el supervisor v3. Sus
[addenda](v3_secondary_implementation_addendum_v1.md) y
[resolución Newton](v3_secondary_newton_addendum_v1.md) siguen siendo la
referencia para esos productores separados; nunca se sustituyen silenciosamente
los fallos originales.

### v4, RV15 primario y RV5 secundario

Se heredan el panel y la máscara v3 y se usan objetivos `rv_15` y `rv_5`
construidos por claves. El orden fijado es RV15 primaria, RV15 confirmación,
RV5 primaria, RV5 confirmación. Se conservan los extremos temporales de 30
minutos para la purga conservadora; no se cambia la máscara por horizonte.

El [recibo A2 v4](../../artifacts/rp4_v4_a2/receipt.json) conserva el exit 2
original de la preparación de objetivos y su resolución pinneada: no se debe
describir como un preflight original aprobado. La resolución distingue las seis
discrepancias de finitud fuera de la máscara y no altera valores finitos elegibles.

La secuencia de objetivos y resolución precede a `--prepare-only`. El recibo
original local `operations/targets_stage_receipt.json`, bajo la raíz v4,
tiene SHA-256
`055d9b432a1765acf22ca78a5dc3ad476fd9118c6afb98c07cdf09edb5ade4b2`.
Conserva también dos intentos iniciales con salida 1; el comando siguiente es la
versión final del productor, que escribió el sidecar con salida 2, no 0.

```powershell
$v4Root = (Get-Content artifacts/rp4_v4_a1/specification.json -Raw | ConvertFrom-Json).data_root
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.materialize_targets --spec artifacts/rp4_v4_a1/specification.json --spec-sha256 0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04 --producer-sha256 8c6f9acc1dd3d995bea1ca75456c8fda6d4b6da1dc0b734dfbc23917b1265ce6 --output-root $v4Root --workers 4
# Registro histórico: exit 2. No autoriza continuar ante cualquier error nuevo.
if ($LASTEXITCODE -ne 2) { throw 'Estado distinto de la materialización histórica investigada' }
$targetManifest = Join-Path $v4Root 'targets/manifest.json'
if ((Get-FileHash $targetManifest -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'ae4c1e7b104c5f2cee2402ded5d0515e04e5264759bf70f0e1098432806c8316') { throw 'Manifiesto distinto del investigado' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_a2.resolve_target_mask --manifest-sha256 ae4c1e7b104c5f2cee2402ded5d0515e04e5264759bf70f0e1098432806c8316
if ($LASTEXITCODE -ne 0) { throw 'Resolución de objetivos no cerrada' }
```

La resolución histórica terminó en 0; su productor tiene SHA-256
`093e1906df0b3e098c3c6981c7762b39b7b84e03d916e108cd11e23ded1c898f`.
Materializador y resolución son escritores de archivos nuevos y sus metadatos
incluyen tiempos: estos comandos no prometen recrear el mismo manifiesto byte a
byte desde cero. La reproducción histórica exige los originales preservados;
no se reemplazan pins para ocultar esa diferencia. Ambos A2 usan cuatro
trabajadores en los comandos históricos y no se ejecutaron durante esta revisión.

```powershell
$v4Hash = '0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04'
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 15 --prepare-only
if ($LASTEXITCODE -ne 0) { throw 'Preflight RV15 falló' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 5 --prepare-only
if ($LASTEXITCODE -ne 0) { throw 'Preflight RV5 falló' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 15 --window primary
if ($LASTEXITCODE -ne 0) { throw 'Primaria RV15 falló' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 15 --window confirmation
if ($LASTEXITCODE -ne 0) { throw 'Confirmación RV15 falló' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 5 --window primary
if ($LASTEXITCODE -ne 0) { throw 'Primaria RV5 falló' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 5 --window confirmation
if ($LASTEXITCODE -ne 0) { throw 'Confirmación RV5 falló' }
```

El supervisor fija **8 particiones × 4 hilos, máximo 32 hilos de modelo**,
y un lock global. El límite de dos hilos del gate de documentación no cambia
ese contrato histórico. No ejecutar ajustes con un presupuesto de dos hilos
suponiendo que las variables anteriores reduzcan automáticamente el supervisor.
Los recibos completos son idempotentes; un cierre incompleto no se reinicia
borrando evidencia. V4 no ajusta MZ, cuantiles ni clasificadores de salto.

## 5. Pins esperados y tiempos observados

| Archivo / alias | SHA-256 esperado |
| --- | --- |
| Especificación efectiva v3 | `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5` |
| Release v3 | `5e3046af023c9f41380307d62537aa4e8fc7514b23d51a95ea1f960ee23fe5bb` |
| Panel efectivo v3, original local | `a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637` |
| Especificación v4 | `0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04` |
| Release RV15 | `7b5499579a66a468f040966d22824501ec1c65c29fefb848b40366bfd1f2351a` |
| Release RV5 | `efeb22b33d992d453a4d766c93b5434e4f3f73271f350b50268a8289c365b08d` |
| Panel de objetivos v4, original local | `b2357a10a8a4955499e94b576b7853129e957ad70702da09bebbc9b6befd35db` |
| Resolución de objetivos v4 | `05ff5f4b8127238dc9fb8371e530c12a1d2bbf23c30ef1363edf0f829b87722f` |
| timing.csv | `b23fcdcc6ffcabb088176e678a95829ea255b9db148d47fe448958112658e483` |

Los hashes de paneles de esta tabla proceden de los releases: el gate documental
no vuelve a leer sus contenidos. El preflight del supervisor sí los comprueba
antes de permitir ajustes.

| Ejecución v4 | Segundos observados | Minutos, segundos / 60 |
| --- | ---: | ---: |
| RV15 primaria | 2940,2563865 | 49,0043 |
| RV15 confirmación | 517,0510889 | 8,6175 |
| RV5 primaria | 3121,5861441 | 52,0264 |
| RV5 confirmación | 487,3992208 | 8,1233 |

Fuente: [timing.csv](../../artifacts/rp4_v4_b4/timing.csv), cuatro filas
de Windows 11, 32 CPU lógicas y 66.184.798.208 bytes de memoria física.
Son tiempos de evaluación/agrupación de esas ejecuciones, no de descargas ni
de reconstrucción completa. No garantizan el tiempo de otra máquina. El total
observado de v3 no consta en ese CSV ni en sus recibos B2/B3: **NO VERIFICABLE**
en esta revisión; no se deduce de fechas de modificación.

## 6. Coeficientes por horizonte

El [CSV agregado de coeficientes B2](../../artifacts/rp4_closeout_audit/b2_coefficient_summary.csv)
contiene 1.518 filas, con horizontes 30, 15 y 5 minutos y ambas ventanas;
su SHA-256 es
`150fdf4398072496ef64547df580053907a117921d2c214f9b3c82446254e9be`.
El [CSV de indicadores de presencia](../../artifacts/rp4_closeout_audit/b2_presence_coefficient_summary.csv)
contiene 654 filas y tiene SHA-256
`9d4fc01b00af2ea25ab34b44276c481cf963be83edcc8f4b31ad114e1e6ab5e7`.
Ambos se verifican en el gate anterior.

```powershell
Import-Csv artifacts/rp4_closeout_audit/b2_coefficient_summary.csv |
    Where-Object { $_.horizon_minutes -eq '15' -and $_.window -eq 'primary' } |
    Select-Object column,kind,N_sessions,mean,absolute_mean,active_sessions
Get-FileHash artifacts/rp4_closeout_audit/b2_coefficient_summary.csv -Algorithm SHA256
```

Son coeficientes sobre entradas transformadas, estandarizadas sólo con entrenamiento
y acotadas a ±5 desviaciones, antes del smearing y las cotas de salida.
`absolute_mean` es la media del valor absoluto, no el valor absoluto de la media.
Una columna eliminada tiene contribución codificada cero, no un efecto nulo
estimado. No son una ablación, importancia causal ni exposición de cartera.
El CSV granular por sesión sigue fuera de la proyección pública.

La extracción cerrada se produjo con
`uv run --offline --frozen --no-sync python -B artifacts/rp4_closeout_audit_code/audit_closed.py`
(salida 0, 23,6588847 segundos registrados). No se repitió aquí. Su escritor es
inmutable y contiene metadatos de tiempo: volver a invocarlo sobre la salida
existente no equivale a una reconstrucción limpia garantizada.
Fuente: [recibo de extracción](../../artifacts/rp4_closeout_audit/public_checks_receipt.json).

## 7. Conservación y cierre

La revisión de navegación/limpieza está en [CLEANUP_REVIEW.md](CLEANUP_REVIEW.md).
El [inventario](../../artifacts/rp4_cleanup_review/inventory.json) es un
snapshot acotado, no una autorización de borrado.
El [recibo de esta revisión](../../artifacts/rp4_cleanup_review/receipt.json)
contiene comandos ejecutados, códigos de salida, pruebas, alcance y hashes.
No se publicaron datos ni se activaron tareas. Se conserva `RESEARCH_ONLY`,
`NOT INVESTMENT ADVICE` y `capital_go=false`.
