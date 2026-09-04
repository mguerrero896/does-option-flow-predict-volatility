# Corrección del reporte narrativo v6 — 2026-09-05

La afirmación anterior «v6 es el mejor resultado disponible» fue demasiado amplia.
En los mismos 1.968 pronósticos, B2 de v4 tiene menor QLIKE y RMSE que B2 de v6
en ambas latencias; v5 tiene menor MAE. V6 mejora marginalmente B1 y el conteo
de activos favorables mediante una selección posterior a observar v4.

El PASS de v6 corresponde a los cinco gates de v5: media, últimas 30 sesiones,
leave-one-block, al menos cuatro activos positivos y como máximo uno negativo.
No incluye regímenes. B1 de v6 conserva ganancias capped negativas en los regímenes
LOW y MID, por lo que no está demostrada una ventaja general entre regímenes.

La semana 24–28 de agosto que figura en el resultado v6 es una copia del replay
de modelos Phase8 archivados. No es una evaluación de v6 sobre esa semana.
La simulación temporal no cambia que los activos se eligieron observando v4.
La jerarquía es descriptiva; los p HAC5 conservados tampoco establecen confirmación.

La [auditoría reproducible con métricas, máscaras y fuentes](../harq_existing_forecasts_audit_v1/report.md)
expone las comparaciones completas. Se conservan sin modificar `result.json`,
`selection_disclosure.json` y los pronósticos originales. RESEARCH_ONLY;
alpha gastado 0; capital_go=false.
