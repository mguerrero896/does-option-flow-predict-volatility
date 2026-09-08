# Figuras de cierre

Tres figuras nuevas (SVG y PNG) se derivan sólo de resúmenes y pérdidas por sesión congelados. No hay entrenamiento, descargas ni bootstrap nuevo.

- `v4_B1_over_B0_cumulative`: RV15 y RV5, dos familias y ambas ventanas en cuatro paneles separados. Suma por sesión de QLIKE base menos QLIKE ampliado, sin exclusiones nuevas.
- `v4_B2_over_B1_cumulative`: la misma definición para el segundo contraste.
- `comparison_v1_v4`: cuarenta facetas con las cinco combinaciones versión/objetivo, ambas ventanas, familias y contrastes. Cada faceta usa un eje independiente; los extremos adversos no se recortan.

El intervalo porcentual es el IC95% guardado para la diferencia, multiplicado por 100 y dividido por la pérdida base media observada. No es un intervalo bootstrap del cociente: no incluye de nuevo la incertidumbre del denominador. Las comparaciones no son réplicas independientes, y las versiones difieren en muestra, familia lineal y procedimiento de inferencia.

`comparison_v1_v4.csv` conserva estimación, IC, p, N, denominador observado y fuentes con hashes. Los p de v1/v2 son bilaterales; v3/v4 conserva p unilateral y su estado secuencial, además del p bilateral y Holm guardados. Un p formal no abierto permanece vacío, no se transforma en cero.

Las marcas de fechas son contexto, no explicaciones causales ni criterios de exclusión. La marca AMZN identifica un choque observado: no demuestra una noticia ni earnings. `panel_metadata.json` indica si cada fecha anotada está presente en el CSV de sesiones.

Ejecutar con el entorno existente y las variables `RP4_FIGURE_NODE` y `RP4_FIGURE_NODE_MODULES` apuntando a la dependencia de rasterización ya instalada:

```text
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_closeout_figures_code.build
```

Los archivos previos no se sustituyen. Los hashes de las fuentes se verifican antes de calcular las coordenadas de las figuras.
