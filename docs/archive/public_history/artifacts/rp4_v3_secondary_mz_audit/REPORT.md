# RP4 v3 — auditoría MZ de confirmación

## Resultado

**NO ARITHMETICAL BUG. MZ permanece NO_VERIFICABLE** bajo el fallback solicitado: la aritmética es reproducible, pero la recalibración no es un secundario fiable para reclamar una mejora predictiva.

Se comprobaron las 25 sesiones de confirmación, 2026-08-03 a 2026-09-04, y 9.750 orígenes por conjunto. Sólo se leyeron pronósticos, coeficientes y medias de calibración ya guardados; cero ajustes, cero cambios de fórmula y cero alteraciones de v3/v4.

| Conjunto | QLIKE original | QLIKE MZ reconstruida | Afines negativos llevados a 1e-12 | Sesiones con piso | Porcentaje de pérdida MZ debido al piso |
|---|---:|---:|---:|---:|---:|
| B0 | 0,174940270804 | 0,186230618526 | 0 / 9.750 | 0 | 0 % |
| B1 | 0,172026112671 | 1.988,177282690929 | 9 / 9.750 | 1 | 99,98963269 % |
| B2 | 0,176178634120 | 2.400,218830477228 | 11 / 9.750 | 2 | 99,99030140 % |

B1: los nueve pisos ocurrieron el 2026-08-07. B2: siete el 2026-08-07 y cuatro el 2026-08-10. Son pronósticos por conjunto, no 20 orígenes necesariamente distintos.

## Prueba realizada

El auditor nuevo conserva las expresiones del [auditor primario](../../../../../artifacts/rp4_v3_b4/audit_mz_identity.py). Una prueba AST compara sus expresiones de transformación afín, piso, QLIKE, agregación y coeficientes cerrados. Sólo cambian la ventana, sus rutas/conteos y los controles de procedencia y recursos.

Para cada origen se reprodujo exactamente la regla guardada: `a + b × pronóstico_original`; si no era finita, se aplicaba el fallback de identidad; después, `max(valor, 1e-12)`. La QLIKE se recalculó como `y/f - log(y/f) - 1`, con las mismas medias iguales por activo y sesión. No se suprimieron pisos ni se eligió un nuevo nivel.

| Comprobación | Máxima discrepancia en B0/B1/B2 |
|---|---:|
| Pronóstico MZ guardado frente a fórmula aplicada | 0 |
| Contador de pisos guardado frente a reconstruido | 0 |
| Escala guardada frente a media del objetivo de calibración | 0 |
| Intercepto frente a su expresión cerrada | 2,202285662861181e-20 |
| Pendiente frente a su expresión cerrada | 1,3322676295501878e-15 |
| QLIKE MZ agregada guardada frente a reconstruida | 2,273736754432321e-13 |
| Paridad de puntuación inicial registrada en los candidatos | 1,734723475976807e-15 |

Las diferencias de coeficientes/agregación son redondeo numérico y están separadas de la igualdad exacta de los pronósticos por origen. Los 20 contactos con el piso nacieron de valores afines estrictamente negativos: cero ceros exactos, cero afines positivos menores que el piso, cero fallback no finito y cero fallback de identidad del entrenamiento.

## Causa e interpretación

La recta MZ ajustada a diez medias de sesión no impone positividad al aplicarse a cada origen. Un intercepto negativo y un pronóstico individual pequeño pueden producir una varianza negativa, aunque la pendiente y la escala estén bien calculadas. El piso registrado la lleva a 1e-12; al dividir una RV30 positiva entre ese valor, la QLIKE resulta enorme.

Esto explica la inestabilidad observada, no demuestra un defecto de escala. Cambiar el enlace, imponer positividad o alterar el piso sería otra metodología, no una reparación de un error aritmético. Esta auditoría no hizo ninguna de esas modificaciones y no promueve MZ como evidencia de ventaja.

## Custodia y ejecución

Se verificaron los 25 hashes de checkpoints antes y después de la auditoría, los 13 hashes de código del release y las referencias de cierre, panel, manifiestos, especificación y freeze. La comprobación final cubrió 33 rutas únicas de entradas/código además de los 25 checkpoints. No se reprocesó UW ni FMP.

Comando ejecutado, salida 0:

```text
uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_secondary_mz_audit/audit_mz_identity.py
```

El recibo contiene el entorno de un hilo, prioridad Windows `BELOW_NORMAL_PRIORITY_CLASS` verificada, inicio 2026-09-07 17:31:45,966762 UTC y fin 17:31:47,069666 UTC. El script está acotado al límite solicitado de 18:25 UTC; no es una autorización de reejecución posterior.

Ruff y tres regresiones estáticas pasaron. La skill de evaluación de modelos guio la comparación sobre exactamente las mismas observaciones y la separación entre corrección aritmética y utilidad predictiva.

- [Resumen agregado](../../../../../artifacts/rp4_v3_secondary_mz_audit/confirmation_summary.json) y [tabla reproducida](../../../../../artifacts/rp4_v3_secondary_mz_audit/confirmation_table.csv).
- [Recibo y hashes de entradas](../../../../../artifacts/rp4_v3_secondary_mz_audit/receipt.json).
- El JSON completo, incluidos ejemplos por origen, permanece en la raíz privada identificada por el recibo; SHA-256 `835c404a24e7513270f25172286dc50cbf8fe5753dd576b179456e0fcca5edce`.

RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false.

