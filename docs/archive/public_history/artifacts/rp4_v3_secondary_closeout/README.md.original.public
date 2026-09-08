# RP4 v3 — generador de cierre secundario, revisión 2

Estado: **generador probado; informe real todavía no generado**. La prueba sintética no es una evaluación científica.

El productor `report_revision2.py` escribe exclusivamente `docs/rp4/results_v3_revision2.md`, `evidence.json` y `receipt.json` nuevos. Rechaza salidas preexistentes. No ajusta modelos, no reconstruye objetivos, no ejecuta el agregador completo, no recalcula AUC y no repite la auditoría MZ.

## Entradas y verificaciones

- Deben existir **ambos** recibos jump, `primary` y `confirmation`, con `COMPLETE`, `exit_code=0`, el mismo release y los hashes de sus cuatro artefactos. Se comprueban los dos recibos antes de abrir cualquier agregado nuevo.
- Release de salto: `7565795ddd4938f4c84068b2c2bb30c01905092150fb78c56aefa7626ca46bed`.
- Addendum JSON previo: `606a8c8d5dbe51628e7507b504cf7c5f8483a9aa5e7c80f62be33b2cb12e55de`.
- Inventario original: `a7f0bd85aa2d817cfc7d1da7b463fc7c8751ee7e966b13fb662a63e403731c38`; 962 componentes reutilizables y 1.702 faltantes. Se cuentan los intentos nuevos exitosos y fallidos sin dar por hecha su convergencia.
- Revisión 1 y ambos agregados primarios v3 se verifican por sus hashes originales. El bloque de ocho filas se copia literalmente, conservando sus bytes. Su SHA-256 es `3812b6a1a881c1ed06dc17f84fc47971d44452c19b4d21a0e3ca4c8af7f0e921`.
- Las tablas AUC/IC/contrastes usan `jump_secondary` guardado. Se validan el estado de la secuencia, sus claves y N comunes; H2 cerrada conserva el p nominal sólo como diagnóstico.
- Se contrastan los censos de componentes y gradientes con los metadatos individuales. Un gradiente antiguo alto no dispara una repetición; un gradiente ausente no se convierte en cero. Los nuevos logit necesitan el certificado de gradiente/objetivo original o la excepción monoclase registrada.
- Se comprueban dos hilos de cálculo como máximo, prioridad baja y no solapamiento de las dos ventanas secundarias. El generador opera con un hilo y prioridad baja.
- MZ permanece `NO VERIFICABLE` como método de recalibración utilizable. El diagnóstico conserva los valores adversos y la prueba de aritmética exacta, con cero nuevos ajustes.

## Comando de cierre

Ejecutar desde el checkout de RP4 **únicamente cuando ambos recibos hayan cerrado**. Los hashes de recibo se capturan fuera del generador; éste verifica su contenido y todos los artefactos vinculados antes de escribir.

```powershell
$env:UV_PROJECT_ENVIRONMENT='private-input/4b06809c9ca2d51ba83b'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH="$($PWD.Path);$($PWD.Path)/src;$($PWD.Path)/scripts;$($PWD.Path)/artifacts/rp4_code;$($PWD.Path)/artifacts/rp4_v2_code;$($PWD.Path)/artifacts/rp4_v3_code"
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:POLARS_MAX_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'
$rp4SecondaryRoot='private-input/27baabfc9067457b5daa'
$rp4PrimaryReceiptSha=(Get-FileHash -Algorithm SHA256 -LiteralPath "$rp4SecondaryRoot/primary/receipt.json").Hash.ToLowerInvariant()
$rp4ConfirmationReceiptSha=(Get-FileHash -Algorithm SHA256 -LiteralPath "$rp4SecondaryRoot/confirmation/receipt.json").Hash.ToLowerInvariant()
uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_secondary_closeout/report_revision2.py --release-sha256 7565795ddd4938f4c84068b2c2bb30c01905092150fb78c56aefa7626ca46bed --primary-receipt-sha256 $rp4PrimaryReceiptSha --confirmation-receipt-sha256 $rp4ConfirmationReceiptSha
```

Si falta un recibo, cambia un hash, aparece un nuevo ajuste fuera del inventario o falla un certificado, el productor no crea el informe. Se investiga esa discrepancia sin modificar fuentes congeladas. El mero final de todos los intentos no obliga a que todos los componentes sean utilizables: los fallos quedan contados y las métricas no verificables se presentan explícitamente.

## QA focal ejecutado

Comandos con el mismo entorno anterior:

```powershell
uv run --offline --frozen --no-sync python -B -m pytest -q -o addopts='' artifacts/rp4_v3_secondary_closeout/test_report_revision2.py --junitxml=artifacts/rp4_v3_secondary_closeout/qa_tests.xml
uv run --offline --frozen --no-sync python -B -m ruff check artifacts/rp4_v3_secondary_closeout/report_revision2.py artifacts/rp4_v3_secondary_closeout/test_report_revision2.py
uv run --offline --frozen --no-sync python -B -m ruff format --check artifacts/rp4_v3_secondary_closeout/report_revision2.py artifacts/rp4_v3_secondary_closeout/test_report_revision2.py
uv run --offline --frozen --no-sync python -B -m mypy --explicit-package-bases --follow-imports=silent --ignore-missing-imports artifacts/rp4_v3_secondary_closeout/report_revision2.py artifacts/rp4_v3_secondary_closeout/test_report_revision2.py
```

Resultado: 32 pruebas sintéticas aprobadas, Ruff/formato y mypy aprobados; códigos de salida 0. También se verificaron los 12 pins históricos y los valores presentados en las ocho filas primarias; no se abrió ningún agregado jump nuevo. Evidencia: `qa_tests.xml` y `qa_receipt.json`. Los avisos de estilo/tipado del borrador se corrigieron antes de este cierre técnico.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false. No se ejecutaron modelos ni se generó el informe real durante la preparación del productor.
