# Auditoría numérica del secundario de saltos — RP4 v3

Esta auditoría comprueba el algoritmo, no la hipótesis del flujo. No utiliza datos, pronósticos ni pérdidas reales y no modifica la especificación, el código de modelos o sus resultados. Su ejecución terminó con código 0; [recibo](receipt.json), [salida íntegra](stdout.log) y [script con aserciones](audit.py).

Se comprobó el closure real de la regresión logística: suma de logloss más `lambda * sum(beta[1:]**2)`, dividida por N; intercepto sin penalización. El gradiente analítico coincide con diferencias finitas (error máximo 2,64e-11) y con la expresión algebraica independiente (máximo 2,78e-17). No se demostró un defecto en esas operaciones.

Ambos casos usan las mismas 2.000 etiquetas sintéticas, 140 columnas de diseño, lambda 0,0001 y los límites registrados: L-BFGS-B, `maxiter=1000`, `gtol=1e-8`, `ftol=1e-12`.

| Diseño sintético | Condición de la Hessiana regularizada | Iteraciones | Resultado |
|---|---:|---:|---|
| Gaussiano bien condicionado | 3,139619 | 12 | Convergencia por reducción relativa de la función |
| Espectro correlacionado, conservado por el QR registrado | 23.389.102,909408 | 1.000 | Límite de iteraciones, sin convergencia certificada |

Esto demuestra que el límite registrado puede agotarse aun con un gradiente correcto. **No demuestra el condicionamiento de los datos reales**, que esta auditoría no abrió. En la ejecución empírica se observaron ajustes de salto con el mismo mensaje de agotamiento del límite; el conteo final por ventana y los estimandos afectados se reportan en [results_v3.md](../../../docs/rp4/results_v3.md).

Los ajustes no convergidos no son evidencia de ausencia de efecto ni AUC válidas. Conforme a la especificación, una sesión de salto incompleta se cuenta como NO VERIFICABLE para la comparación común de ese estimando; no se elimina por ello de QLIKE ni del cuantil. Aceptar coeficientes no convergidos, omitir el lambda fallido, cambiar el solver o aumentar el límite habría cambiado el procedimiento congelado; no se hizo.

Reproducción sólo sintética, sin sobrescribir el recibo conservado, desde el checkout RP4 y su entorno Python existente:

```powershell
Set-Location -LiteralPath 'private-input/0ec5f26c567f416b9513'
$env:UV_PROJECT_ENVIRONMENT='private-input/4b06809c9ca2d51ba83b'
uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_b4/logistic_numerical_audit/audit.py --worker
```

El script fija cuatro hilos y comprueba los hashes de modelo, especificación y release antes y después. Esta carpeta es una copia exacta por hash de la auditoría privada, salvo este README nuevo. RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
