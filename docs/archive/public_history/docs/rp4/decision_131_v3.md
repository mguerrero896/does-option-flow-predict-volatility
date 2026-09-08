# Decisión 131 — RP4 v3, mecanismo intradía y estimandos secundarios

2026-09-07. Autoridad: encargo completo RP4 v3 de Miguel en esta conversación; autorización explícita, no firma criptográfica atribuida.

Se adopta `specification_v3.md`, junto con el addendum inmutable del commit `23c521367e9af23129d4591f3df67a7f25140615`. Se autoriza derivar independientemente el desbalance gamma firmado y compararlo con el candidato, añadir sus cuatro medidas a B2 v2, reconstruir jump30 para el secundario, y ejecutar una vez cada ventana primaria/confirmación con los mismos datos y partición v2.

Antes de evaluar se fijan las correcciones causales de ambas marcas temporales, disponibilidad por prefijo, primera versión disponible inmutable por ID y dirección ambigua; revisiones posteriores se auditan sin reescribir el pasado. El filtro IV v2, tasa/dividendo reales y tenor de 365.25 días se explicitan. No se modifica ninguna columna preexistente del panel v2.

Se registra la secuencia unilateral H1→H2 por familia, la regla conjunta de ambas familias, los secundarios no promovibles de distribución, regímenes, cuantil, salto y recalibración MZ; se preservan p bilateral y Holm para comparabilidad. No se identifica ausencia de significación con prueba de absorción o de equivalencia.

El JSON ejecutable y los hashes se fijan en `artifacts/rp4_v3_a1/freeze.json` antes de materializar o ajustar v3. Los resultados y decisiones v1/v2 no se reescriben ni reejecutan. Se conserva todo signo y el N real. No se autoriza publicación, nueva adquisición, modificación de phase9 ni cambios del colector. RESEARCH_ONLY; capital_go=false.
