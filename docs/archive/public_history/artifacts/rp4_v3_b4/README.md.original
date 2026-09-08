# RP4 v3 — entrada única al cierre

Leer el [informe v1/v2/v3](../../docs/rp4/results_v3.md) junto con las [notas de interpretación y límites](READING_NOTES.md). Las notas forman parte del paquete B4 y aclaran los secundarios de saltos y recalibración; no cambian los resultados ni el procedimiento congelado.

## Resultado principal

Reducción media de QLIKE: positivo significa mejora. La secuencia conjunta registrada **no se satisface en ninguna ventana**.

| Ventana | Familia | B1 sobre B0 | B2 sobre B1 |
|---|---|---:|---:|
| Primaria, 419 sesiones | Ridge | +1,73 % | +0,55 % |
| Primaria, 419 sesiones | LightGBM | +2,09 % | −0,16 % |
| Confirmación, 25 sesiones | Ridge | +0,50 % | +1,86 % |
| Confirmación, 25 sesiones | LightGBM | +1,67 % | −2,41 % |

En primaria, H1 rechaza en ambas familias pero H2 no (p unilateral de B2: ridge 0,0525; LightGBM 0,6631). En confirmación no rechaza H1 en ninguna familia y H2 no se abre formalmente. La prueba de saltos queda NO VERIFICABLE por falta de convergencia; no demuestra ausencia de información. La recalibración MZ empeora el resultado y no reemplaza el pronóstico principal.

## Custodia y etapas

| Etapa | Entregable | Comandos, códigos de salida y hashes |
|---|---|---|
| A1 | [Especificación v3](../../docs/rp4/specification_v3.md) | [Recibo A1](../rp4_v3_a1/receipt.json) |
| A1B | [Regla de ventanas vacías](../../docs/rp4/v3_window_empty_addendum.md) | [Recibo A1B](../rp4_v3_a1_empty_window/receipt.json) |
| A2 | [Re-derivación, comparación y materialización](../rp4_v3_a2/REPORT.md) | [Recibo A2](../rp4_v3_a2/receipt.json) |
| B2 | [Primaria](../rp4_v3_b2/summary.json) | [Recibo B2](../rp4_v3_b2/receipt.json) |
| B3 | [Confirmación](../rp4_v3_b3/summary.json) | [Recibo B3](../rp4_v3_b3/receipt.json) |
| B4 | [Informe](../../docs/rp4/results_v3.md), tablas CSV y dos figuras | [Recibo B4](receipt.json) y [manifiesto del generador](report_manifest.json) |

El manifiesto del generador cubre sus propias salidas. El recibo B4 incorpora además este índice, las notas y las auditorías complementarias, sin modificar el generador ni sus entradas congeladas. Los recibos identifican rutas locales privadas necesarias para reproducir la custodia; este paquete no está autorizado para publicación.

## Comprobaciones complementarias

- [Auditoría logística sintética](logistic_numerical_audit/README.md): gradiente, convergencia y límites; no usa datos reales ni rescata ajustes fallidos.
- [Comprobación de identidad MZ en primaria](audit_mz_identity.py) y [recibo](mz_identity_receipt.json): aritmética de predicciones ya cerradas; no vuelve a entrenar modelos.
- [142 pruebas previas y verificaciones focalizadas](../rp4_v3_a2/verification_before_fit.json): alcance concreto, no una afirmación de pruebas completas de todo el repositorio.

Los comandos de evaluación conservados son evidencia de lo ejecutado, **no instrucciones para repetir ventanas consumidas**. Para consultar resultados se usan los agregados y sus hashes. v1, v2 y phase9 se preservan; no se publican datos, no se activa capital y no se cambian colectores en este cierre v3.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
