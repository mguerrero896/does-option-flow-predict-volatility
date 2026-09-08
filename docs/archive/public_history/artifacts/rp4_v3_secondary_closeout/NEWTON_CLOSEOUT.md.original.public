# RP4 v3 — cierre de dos pases secundarios

Este adaptador nuevo reemplaza la **ruta de generación futura** del informe con la corrección Newton; no modifica `report_revision2.py`, sus pruebas, sus recibos ni resultados congelados. El destino final sigue siendo el archivo aún inexistente `docs/rp4/results_v3_revision2.md`.

Estado de esta entrega: código conectado al contrato del adaptador failed-only, Ruff/formato y mypy aprobados. Hay 11 pruebas sintéticas nuevas escritas, **todavía no ejecutadas** para no competir con el límite de dos hilos del primer pase. No se consultó ninguna AUC ni se generó el informe real.

## Garantías del productor

1. Exige ambos recibos Newton `COMPLETE/exit 0` antes de abrir los agregados del primer pase. Luego verifica los cuatro cierres, los dos releases, los addenda y sus archivos vinculados.
2. Valida por claves y hashes todas las procedencias. Un componente COMPUTED anterior no puede seleccionarse para Newton; todo éxito reutilizado conserva exactamente su artefacto, ajuste, estado y coste nuevo cero.
3. Usa el predicado de elegibilidad del adaptador verificado por hash. Conserva los fallos inelegibles y los que persistan después de Newton, sin rellenar probabilidades ni ajustar otra familia.
4. Reutiliza las verificaciones previas de máscaras/N, AUC guardada, secuencia y certificado de gradiente/objetivo. No calcula AUC, bootstrap, pérdidas o predicciones.
5. Presenta primero la AUC final combinada y conserva la AUC del primer pase en una sección explícita. No selecciona entre pases por su resultado.
6. Separa los 962 componentes originales, los éxitos del primer pase, las llamadas Newton y los fallos persistentes. El diagnóstico parcial del primer fallo se cuenta una sola vez: no se atribuyen sus 27 iteraciones a cada lambda/refit nuevo.
7. Comprueba que los dos cierres del primer pase preceden a Newton y que las dos ventanas Newton no se solapan. El informe conserva los costes de ambos pases. El generador usa un hilo y prioridad baja.
8. Copia intacto el bloque primario de ocho filas y mantiene MZ NO VERIFICABLE con las dos auditorías de aritmética. No modifica v4 ni afirma una réplica independiente.

## QA pendiente de ejecutar sólo cuando esté libre el presupuesto de recursos

Usar el entorno Python offline ya documentado en `README.md`, con las variables de cálculo a un hilo. No ejecutar esta prueba durante ninguno de los pases numéricos activos sin la coordinación del ejecutor principal.

```powershell
uv run --offline --frozen --no-sync python -B -m pytest -q -o addopts='' artifacts/rp4_v3_secondary_closeout/test_report_newton_revision2.py --junitxml=artifacts/rp4_v3_secondary_closeout/qa_newton_tests.xml
```

El resultado debe registrarse en un recibo nuevo. `newton_static_receipt.json` prueba sólo verificaciones estáticas y no sustituye esa ejecución.

## Comando del informe, después de los cuatro cierres

No ejecutar antes de completar el QA sintético anterior. Mantener el entorno offline y de un hilo del `README.md`.

```powershell
$rp4First='private-input/e90b04c9636db3ce4b5d'
$rp4Newton="$rp4First/newton_failed_only_v1"
$rp4NewtonReleaseSha=(Get-FileHash -Algorithm SHA256 -LiteralPath "$rp4Newton/release.json").Hash.ToLowerInvariant()
$rp4FirstPrimarySha=(Get-FileHash -Algorithm SHA256 -LiteralPath "$rp4First/evaluation/primary/receipt.json").Hash.ToLowerInvariant()
$rp4FirstConfirmationSha=(Get-FileHash -Algorithm SHA256 -LiteralPath "$rp4First/evaluation/confirmation/receipt.json").Hash.ToLowerInvariant()
$rp4NewtonPrimarySha=(Get-FileHash -Algorithm SHA256 -LiteralPath "$rp4Newton/evaluation/primary/receipt.json").Hash.ToLowerInvariant()
$rp4NewtonConfirmationSha=(Get-FileHash -Algorithm SHA256 -LiteralPath "$rp4Newton/evaluation/confirmation/receipt.json").Hash.ToLowerInvariant()
uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_secondary_closeout/report_newton_revision2.py --newton-release-sha256 $rp4NewtonReleaseSha --first-primary-receipt-sha256 $rp4FirstPrimarySha --first-confirmation-receipt-sha256 $rp4FirstConfirmationSha --newton-primary-receipt-sha256 $rp4NewtonPrimarySha --newton-confirmation-receipt-sha256 $rp4NewtonConfirmationSha
```

El productor rechaza cualquier salida ya existente. Los nuevos archivos de cierre son `docs/rp4/results_v3_revision2.md`, `artifacts/rp4_v3_secondary_closeout/evidence.json` y `artifacts/rp4_v3_secondary_closeout/receipt.json`; ninguna fuente congelada se sobrescribe.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
