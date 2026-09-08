# RP4 v3 — cierre B4, revisión de presentación 1

Esta revisión sustituye la presentación de los dos secundarios indicados, no los resultados primarios ni el [informe v3 original](../../../../rp4/results_v3.md), que permanece congelado con SHA-256 `86703434ae2d1d8e2ef3a9c59ae9737f3a4e4c8460234076b794e04ac2deee1f`. Las tablas completas v1/v2/v3, cobertura, cuantil, regímenes, extremos y figuras siguen en ese informe. No se ha ajustado ni evaluado ningún modelo para este cierre.

fuera de muestra walk-forward, partición fijada 2026-09-07.

## Resultado primario sin cambios

Delta = QLIKE base menos ampliado; reducción = 100 × delta / QLIKE base. IC95% bilateral por bloques; p unilateral de la secuencia H1 → H2.

| Ventana | Familia | Contraste | Delta | IC95% | Reducción % | p unilateral nominal | Decisión | N sesiones/orígenes |
|---|---|---|---:|---|---:|---:|---|---|
| Primaria | Ridge | B1/B0 | +0.0025468959 | [0.0005570053, 0.0055407196] | +1.7289745 | 0.0439 | H1 rechazada | 419/160832 |
| Primaria | Ridge | B2/B1 | +0.0008023897 | [-0.0001534347, 0.0017735437] | +0.5542902 | 0.0525 | H2 no rechazada | 419/160832 |
| Primaria | LightGBM | B1/B0 | +0.0031224859 | [0.0010149407, 0.0054860165] | +2.0911798 | 0.0053 | H1 rechazada | 419/160832 |
| Primaria | LightGBM | B2/B1 | -0.0002326470 | [-0.0016475987, 0.0008319668] | -0.1591353 | 0.6631 | H2 no rechazada | 419/160832 |
| Confirmación | Ridge | B1/B0 | +0.0009113921 | [-0.0028274372, 0.0039476574] | +0.5010983 | 0.3238 | H1 no rechazada | 25/9750 |
| Confirmación | Ridge | B2/B1 | +0.0033669574 | [-0.0007443023, 0.0102227627] | +1.8605313 | 0.1612 | H2 no abierta; p sólo diagnóstico | 25/9750 |
| Confirmación | LightGBM | B1/B0 | +0.0029141581 | [-0.0016852924, 0.0074221881] | +1.6658018 | 0.1104 | H1 no rechazada | 25/9750 |
| Confirmación | LightGBM | B2/B1 | -0.0041525214 | [-0.0103787975, 0.0000249181] | -2.4138902 | 0.9266 | H2 no abierta; p sólo diagnóstico | 25/9750 |

Fuente: [agregado primario](../../../../../artifacts/rp4_v3_b2/summary.json) y [agregado de confirmación](../../../../../artifacts/rp4_v3_b3/summary.json). La conjunción registrada no se satisface en ninguna ventana. La mediana favorable de ridge B2 es secundaria y no sustituye la media registrada.

## Secundarios pendientes de corrección

| Secundario | Estado de presentación | Causa verificada |
|---|---|---|
| AUC de salto | NO VERIFICABLE para las ventanas completas | Logit agotó 1.000 iteraciones en 418/419 sesiones primarias y 25/25 de confirmación; queda una sola sesión primaria completa, insuficiente para inferencia. |
| QLIKE recalibrado MZ | NO VERIFICABLE como recalibración utilizable; no presentar como COMPUTED validado | La recta afín genera pronósticos negativos y el piso 1e-12 dispara QLIKE; la auditoría reproduce exactamente la aritmética, sin demostrar un error de escala. |

La AUC sí conserva el N técnico observado: una sesión/390 orígenes en primaria y cero en confirmación; no tiene N suficiente para la comparación inferencial solicitada. De los 418 fallos primarios, 414 seleccionaron lambda 1e-4 y cuatro lambda 0.01; no fueron todos con 1e-4. No se aceptan coeficientes sin convergencia ni se inventan AUC.

Los QLIKE MZ del orden de 6e5–7e5 se conservan como diagnóstico del fallo de positividad, no como tabla de un método corregido ni como señal contra el modelo principal. El [recálculo de 482.496 pronósticos primarios](../../../../../artifacts/rp4_v3_b4/mz_identity_receipt.json) coincidió exactamente con la fórmula registrada. Corregir la positividad o cambiar la escala de ajuste requiere el addendum autorizado: no se afirmará que se arregló una suma, un intercepto o una escala sin reproducir ese error. La investigación tendrá el límite de una hora solicitado para MZ.

## Divulgación y custodia

La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 con otra especificación. El PIT es proxy de tiempo fuente a 120 s, como en la literatura.

Hueco UW aceptado: 2025-01-25 a 2025-02-24, sin relleno. Las versiones reutilizan ventanas y no son replicaciones independientes; un no rechazo no demuestra equivalencia a cero ni absorción. Esta revisión sólo cambia la presentación y vincula la evidencia congelada. Las correcciones posteriores, si se validan, tendrán otro archivo y otro recibo.

[Recibo de esta revisión](../../../../../artifacts/rp4_v3_b4_revision1/receipt.json) · [Cierre B4 original](../../artifacts/rp4_v3_b4/README.md).

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false. Sin publicación, descargas ni modificación de resultados congelados.
