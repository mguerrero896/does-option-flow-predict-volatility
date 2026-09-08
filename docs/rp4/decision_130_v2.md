# Decisión 130 — RP4 v2

2026-09-07. Autorización explícita del propietario en la instrucción de RP4 v2 de esta conversación; no constituye una firma criptográfica.

Se autoriza una especificación v2 separada, una evaluación primaria y una de confirmación sobre los mismos insumos y ventanas de v1, sin nuevas descargas. El alcance está limitado a obligatoriedad/NaN, early stopping de LightGBM, exclusión de los diagnósticos enumerados, ridge lineal estabilizado, secundarios de colas y filtro IV por operación [0.03,3].

Se adopta [specification_v2.md](specification_v2.md), cuyo hash se fija junto con el JSON ejecutable en `artifacts/rp4_v2_a1/freeze.json`. El registro es un suplemento nuevo de las decisiones 128/129, no una reescritura de ellas ni de los artefactos v1.

La fe de erratas especificará las columnas efectivamente utilizadas: los dos diagnósticos `observed_span_s` sí entraron; otros siete de los nueve enumerados ya estaban excluidos. Las afirmaciones de que todos los defectos sesgan hacia cero se tratan como hipótesis, no como evidencia causal establecida.

Se reporta cualquier signo y el N realmente elegible. La recuperación de una sesión excluida por v1 se atribuye a la nueva máscara, no a datos nuevos. No se cambian ventanas, inferencia, Holm, estratos secundarios ni fórmulas no afectadas por el filtro IV.

Se conserva v1, incluido su informe; la corrección textual se entrega como errata adjunta en el informe v2. No se autoriza publicación de v2 ni modificación del colector. RESEARCH_ONLY; capital_go=false.
