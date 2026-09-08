# ¿Las opciones mejoran el pronóstico de volatilidad intradía?

## Resumen ejecutivo — español

**Pregunta y diseño.** Se contrasta si añadir opciones mejora el pronóstico de variación realizada de AAPL, AMZN, META, MSFT, NVDA y TSLA: B0 contiene precios e historia de volatilidad; B1 añade estado y superficie; B2 añade composición, actividad y desbalance del flujo, con 29/69/138 predictores anidados. Se comparan una familia lineal winsorizada con filtro de rango —ridge nominal— y LightGBM mediante QLIKE, una pérdida de pronóstico, no rentabilidad. El entrenamiento expansivo usa sólo el pasado, 60 sesiones iniciales, selección sobre las últimas diez y purga/embargo de 60 minutos; la primaria contiene 419 sesiones y 160.832 orígenes. La partición 2026-08-01 se fijó el 2026-09-07. [Diseño y muestra](../../../../rp4/RESULTADO_FINAL.md).

**Respuesta y magnitud.** B1 > B0 se sostiene en ambas familias a 30 y 15 minutos; B2 > B1 > B0 se sostiene en la familia lineal a 15 y 5 minutos bajo la secuencia H1→H2 unilateral al 5 %, siendo RV5 secundario. A 15 minutos, el incremento B2/B1 reduce QLIKE **+0,623 %**, con **IC95 % de la diferencia QLIKE [0,000335; 0,001932]** y p = 0,0032; a 5 minutos, +0,256 %. El IC reescalado es [+0,184 %; +1,061 %]: 100 × IC de la diferencia / pérdida base media observada, con denominador fijo; no es un IC bootstrap del cociente. [Escala porcentual](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv). En árboles, B2 ≥ B1 describe medianas positivas a 15/5 minutos, no superioridad media ni equivalencia: Holm = 0,0870/0,0096. [Resultados e intervalos](../../../../rp4/results_v4.md).

**Alcance y prueba pendiente.** La ventana final de 25 sesiones y 9.750 orígenes no confirma la secuencia completa; tampoco queda probado un mecanismo causal de cobertura de intermediarios. La réplica registrada conserva v4: decisión principal única a 20 sesiones; 40 sólo comprueba estabilidad, sin rescate; A/B/C se leen a 20 con Holm; el agrupado secundario combina 25 sesiones observadas y 20 nuevas. [Límites](../../../../rp4/RESULTADO_FINAL.md) · [Registro](../../../../rp4/prospective_confirmation_v1.md) · [Enmienda](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

**Cuatro divulgaciones.**

1. Es la cuarta evaluación de las mismas ventanas, con adaptaciones entre v1–v4 y búsqueda no corregida entre versiones; RV5 es secundario, no réplica independiente.
2. La ventana del 20 de julio al 28 de agosto fue leída previamente con otra especificación.
3. El PIT es un proxy de tiempo fuente a 120 segundos y no demuestra disponibilidad histórica al cliente.
4. Se conserva el hueco del proveedor 2025-01-25–2025-02-24, sin relleno.

[Registro de las divulgaciones](../../../../rp4/RESULTADO_FINAL.md).

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

<div style="page-break-after: always;"></div>

## Executive summary — English

**Question and design.** Does adding options information improve forecasts of realized variance for AAPL, AMZN, META, MSFT, NVDA and TSLA? B0 contains price and volatility history; B1 adds options state and surface; B2 adds flow composition, activity and imbalance, using 29/69/138 nested predictors. A winsorized linear model with rank filtering —nominal ridge— and LightGBM are evaluated with QLIKE, a forecasting loss, not trading returns. Expanding training uses past data only, 60 initial sessions, selection over the last ten training sessions and 60-minute purging/embargo; the primary sample contains 419 sessions and 160,832 origins. The calendar split, 2026-08-01, was fixed on 2026-09-07. [Design and sample](../../../../rp4/RESULTADO_FINAL.md).

**Answer and magnitude.** B1 > B0 holds in both families at 30 and 15 minutes; B2 > B1 > B0 holds in the linear family at 15 and 5 minutes under the one-sided H1→H2 sequence at 5%, with RV5 secondary. At 15 minutes, B2/B1 reduces QLIKE by **+0.623%**, with a **95% CI for the QLIKE difference of [0.000335, 0.001932]** and p = 0.0032; at 5 minutes, the reduction is +0.256%. The rescaled CI is [+0.184%, +1.061%]: 100 × difference CI / observed mean baseline loss, holding the denominator fixed; this is not a bootstrap ratio CI. [Percentage scale](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv). For trees, B2 ≥ B1 describes positive paired medians at 15/5 minutes, not mean superiority or equivalence: Holm = 0.0870/0.0096. [Results and intervals](../../../../rp4/results_v4.md).

**Scope and pending evidence.** The final window of 25 sessions and 9,750 origins does not confirm the complete sequence; a causal dealer-hedging mechanism is not established. The registered replication preserves v4: one primary decision at 20 sessions; 40 assesses stability only, without rescuing a failed primary decision; A/B/C share Holm at 20; the pooled secondary combines 25 observed sessions and 20 new sessions. [Limitations](../../../../rp4/RESULTADO_FINAL.md) · [Registration](../../../../rp4/prospective_confirmation_v1.md) · [Amendment](../../../../rp4/prospective_confirmation_v1_amendment_2.md).

**Four disclosures.**

1. This is the fourth evaluation of the same windows, with adaptations across v1–v4 and no correction for the search across versions; RV5 is secondary, not an independent replication.
2. The 20 July–28 August window was previously read under another specification.
3. Point-in-time alignment uses a 120-second source-time proxy and does not establish historical client availability.
4. The provider gap 2025-01-25–2025-02-24 is retained without filling.

[Disclosure record](../../../../rp4/RESULTADO_FINAL.md).

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
